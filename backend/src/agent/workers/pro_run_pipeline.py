"""Pro 计算图执行 task pipeline。

输入:claimed pro_run dict(pro_runs_repo.claim_pending_pro_runs 返回)
流程:compile→submit→记成本→poll→产物落 media→update_pro_run_state(fencing)→WS 推 pro_run_*。

成本(plan §5「成本闸」+ 审计 C1):submit 成功即记 GENERATION_COST(否则整条 ComfyUI Run 对
¥25/run + ¥30/天 两道闸不可见)。run_id 用 pro run 自己的 run_id —— 与 enqueue-time guard 同桶。
"""

from __future__ import annotations

import asyncio
import json
import time

from agent.cascade import cost_guard
from agent.cascade.failures import HardFailure
from agent.comfyui.provider import comfyui_provider_blocked, get_comfyui_provider
from agent.tools.canvas_persistence import pro_runs_repo
from agent.transport.notify import send_to_user
from agent.workers.s3 import download_and_upload


POLL_INTERVAL_S = 3
POLL_MAX_S = 300


async def _push(user_id: str, payload: dict) -> None:
    """向用户推一帧 pro_run_*(经 live 注册表,跨重连自愈)。绝不抛。"""
    try:
        await send_to_user(user_id, payload)
    except Exception:  # noqa: BLE001 — WS 推送失败不应拖垮执行
        pass


async def _persist_outputs(outputs: list[str], run_id: str) -> list[str]:
    """把 provider 产物 URL 落到自有 media(provider/ComfyUI URL 易过期)。

    download_and_upload 失败(如 fixture 的 data: URL 不可下载 / S3 未配)→ 回落原 URL,
    保证 fixture 路径也能端到端跑通。"""
    final: list[str] = []
    for i, url in enumerate(outputs):
        persisted = None
        try:
            persisted = await download_and_upload(url, f"pro_{run_id}_{i}")
        except Exception:  # noqa: BLE001
            persisted = None
        final.append(persisted or url)
    return final


async def process_pro_run_task(run: dict) -> None:
    """处理单条 Pro 计算图执行。所有 repo 调用显式传 user_id/thread_id。"""
    run_id = run["run_id"]
    uid = run["user_id"]
    tid = run["thread_id"]
    provider_name = run.get("provider") or "selfhosted"

    try:
        graph = json.loads(run.get("graph_json") or "{}")
    except (json.JSONDecodeError, TypeError) as e:
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=f"图损坏: {e}")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "图损坏"})
        return

    # 跨境合规(review 修复):worker 是真正的数据出境点。enqueue 时可能 STRICT 关 + 行落库带
    # provider=runninghub;之后 STRICT 打开/重启,重放会从这里出境。使用点再拦一道 → 直接 failed
    # (不重试,避免永久阻塞循环)。
    if comfyui_provider_blocked(provider_name):
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error="cross_border_blocked")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "境内合规:已禁用跨境执行后端"})
        return

    # 成本闸再核(review 修复):enqueue 只查过一次;重试会重新 submit + 记账,这里每次 submit 前
    # 再核,让第 2/3 次重试看到前次已记花费 → 越 ¥25/run 或 ¥30/天即拒(收紧 per-run 上限)。
    try:
        await cost_guard.cost_guard(uid, run_id, float(run.get("cost_est") or 0.0))
    except HardFailure as exc:
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=exc.hint or "cost cap")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": exc.hint or "生成预算超限"})
        return

    provider = get_comfyui_provider(provider_name)
    await _push(uid, {"type": "pro_run_progress", "thread_id": tid, "run_id": run_id, "status": "submitting", "pct": 0})

    t0 = time.time()
    submitted = await provider.submit(graph, user_id=uid, run_id=run_id)
    elapsed = (time.time() - t0) * 1000
    if not submitted.get("task_id"):
        err = submitted.get("error", "submit failed")
        retried = pro_runs_repo.schedule_pro_run_retry(run_id, err, user_id=uid, thread_id=tid)
        if not retried:
            pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=err)
            await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})
        return

    task_id = submitted["task_id"]
    # polling 写入 prompt_id(同时成为后续终态回写的 fencing token)
    pro_runs_repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id=task_id)
    await _push(uid, {"type": "pro_run_progress", "thread_id": tid, "run_id": run_id, "status": "running", "pct": 30})

    # 成本记账(submit 成功 = 可计费)。run_id 与 enqueue-time guard 同桶。best-effort。
    await cost_guard.record_generation_cost(
        user_id=uid,
        run_id=run_id,
        call_kind="canvas_comfyui",
        cost_cny=float(run.get("cost_est") or 0.0),
        provider=f"comfyui:{provider_name}",
        latency_ms=int(elapsed),
    )

    # 轮询
    res: dict = {"status": "running", "outputs": []}
    deadline = time.time() + POLL_MAX_S
    while time.time() < deadline:
        res = await provider.poll(task_id)
        if res.get("status") in ("completed", "failed"):
            break
        await asyncio.sleep(POLL_INTERVAL_S)
    else:
        res = {"status": "failed", "outputs": [], "error": "timeout"}

    if res.get("status") == "completed" and res.get("outputs"):
        final_urls = await _persist_outputs(res["outputs"], run_id)
        # fencing:终态回写带 expected_prompt_id,被取消/重提交的旧 worker 回写会被拦
        pro_runs_repo.update_pro_run_state(
            run_id, "done", user_id=uid, thread_id=tid, result=final_urls, expected_prompt_id=task_id
        )
        for url in final_urls:
            await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": url})
        await _push(uid, {"type": "pro_run_done", "thread_id": tid, "run_id": run_id, "outputs": final_urls})
        print(f"[ProWorker] 完成 run={run_id[:16]} outputs={len(final_urls)}")
    else:
        err = res.get("error") or "执行失败"
        retried = pro_runs_repo.schedule_pro_run_retry(run_id, err, user_id=uid, thread_id=tid)
        if not retried:
            # schedule_pro_run_retry 已置 failed(耗尽次数)或本就终态;补 fencing 终态回写无害
            pro_runs_repo.update_pro_run_state(
                run_id, "failed", user_id=uid, thread_id=tid, error=err, expected_prompt_id=task_id
            )
            await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})
        print(f"[ProWorker] {'超时' if err == 'timeout' else '失败'} run={run_id[:16]} {err}")


async def recover_pro_run_task(run: dict) -> None:
    """恢复一条 submitted/polling 的中断 run(服务重启)。**只 re-poll,不 re-submit**
    (有 comfy_prompt_id 时)—— 避免重复提交 + 重复扣费。无 prompt_id(submit 后未及写回)→ 退回 pending。"""
    run_id = run["run_id"]
    uid = run["user_id"]
    tid = run["thread_id"]
    prompt_id = run.get("comfy_prompt_id")
    if not prompt_id:
        pro_runs_repo.update_pro_run_state(run_id, "pending", user_id=uid, thread_id=tid)
        return
    # 跨境合规:poll 也是出境(RunningHub /outputs)。STRICT 翻开后恢复路径同样拦。
    if comfyui_provider_blocked(run.get("provider") or "selfhosted"):
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error="cross_border_blocked")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "境内合规:已禁用跨境执行后端"})
        return
    provider = get_comfyui_provider(run.get("provider") or "selfhosted")
    try:
        res = await provider.poll(prompt_id)
    except Exception as e:  # noqa: BLE001
        pro_runs_repo.schedule_pro_run_retry(run_id, str(e), user_id=uid, thread_id=tid)
        return
    status = res.get("status")
    if status == "completed" and res.get("outputs"):
        final_urls = await _persist_outputs(res["outputs"], run_id)
        pro_runs_repo.update_pro_run_state(
            run_id, "done", user_id=uid, thread_id=tid, result=final_urls, expected_prompt_id=prompt_id
        )
        await _push(uid, {"type": "pro_run_done", "thread_id": tid, "run_id": run_id, "outputs": final_urls})
    elif status == "failed":
        err = res.get("error") or "执行失败"
        retried = pro_runs_repo.schedule_pro_run_retry(run_id, err, user_id=uid, thread_id=tid)
        if not retried:
            await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})
    # else: still running — lease 已被 recover_pro_runs 续上,下轮再恢复
