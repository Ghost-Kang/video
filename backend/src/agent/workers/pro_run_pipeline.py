"""Pro 计算图执行 task pipeline —— 两条后端,run.provider 决定:

  - **domestic(默认)**:per-node DAG 执行器。Generate→Seedream(图)、Video→Seedance(i2v)、
    Prompt/LoadImage/Anchor=输入、Upscale=境内透传、Model/Script=忽略、Preview=收产物。
    拓扑执行 + 逐节点记账(canvas_image/canvas_video,对成本闸可见)+ 续租(video 慢)+ 取消守卫。
    部分失败 → 已成产物照出(done with partials),不自动重试(避免重跑已成节点重复扣费)。
  - **comfyui(selfhosted/runninghub/fixture)**:整图编译提交给 ComfyUI,submit→poll→落 media。

成本:enqueue 时 cost_guard 查过整图估算;worker 开跑前再核一次,执行中按节点记真账。
"""

from __future__ import annotations

import asyncio
import json
import time

from agent import config
from agent.cascade import cost_guard
from agent.cascade.failures import HardFailure
from agent.comfyui.provider import comfyui_provider_blocked, get_comfyui_provider
from agent.tools.canvas_persistence import pro_runs_repo
from agent.transport.notify import send_to_user
from agent.workers.s3 import download_and_upload


POLL_INTERVAL_S = 3
POLL_MAX_S = 300

_COMFYUI_PROVIDERS = ("selfhosted", "runninghub", "fixture")
_COMFYUI_BACKEND = "ComfyUI"  # Generate/Video 的 backend 参数值(节点级后端选择)


def _mini_image_graph(prompt: str, ref_url: str | None, params: dict) -> dict:
    """单 Generate 节点 → 最小 ComfyUI 图(Model→Generate←Prompt[←LoadImage]→Preview)。"""
    p = {k: v for k, v in params.items() if k != "backend"}
    nodes = [
        {"id": "m", "type": "Model", "params": {}},
        {"id": "p", "type": "Prompt", "params": {"text": prompt or "高质量竖屏画面", "role": "positive"}},
        {"id": "g", "type": "Generate", "params": p},
        {"id": "o", "type": "Preview", "params": {}},
    ]
    edges = [
        {"id": "e1", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "model"},
        {"id": "e2", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
        {"id": "e3", "source": "g", "sourceHandle": "image", "target": "o", "targetHandle": "image"},
    ]
    if ref_url:
        nodes.append({"id": "li", "type": "LoadImage", "params": {"image_url": ref_url}})
        edges.append({"id": "e4", "source": "li", "sourceHandle": "image", "target": "g", "targetHandle": "image"})
    return {"version": 1, "nodes": nodes, "edges": edges}


def _mini_video_graph(ref_url: str, params: dict) -> dict:
    """单 Video 节点 → 最小 ComfyUI 图(LoadImage→Video→Preview,展开 SVD)。"""
    p = {k: v for k, v in params.items() if k != "backend"}
    return {
        "version": 1,
        "nodes": [
            {"id": "li", "type": "LoadImage", "params": {"image_url": ref_url}},
            {"id": "v", "type": "Video", "params": p},
            {"id": "o", "type": "Preview", "params": {}},
        ],
        "edges": [
            {"id": "e1", "source": "li", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
            {"id": "e2", "source": "v", "sourceHandle": "video", "target": "o", "targetHandle": "image"},
        ],
    }


async def _comfyui_one(mini: dict, *, run_id: str, uid: str) -> str | None:
    """单节点 ComfyUI 执行(节点级 backend=ComfyUI)。返回产物 URL 或 None。需境内 GPU 实例;
    跨境 provider 被合规闸拦 → None。"""
    pname = (config.COMFYUI_PROVIDER or "selfhosted").lower()
    if comfyui_provider_blocked(pname):
        return None
    provider = get_comfyui_provider(pname)
    sub = await provider.submit(mini, user_id=uid, run_id=run_id)
    task_id = sub.get("task_id")
    if not task_id:
        return None
    deadline = time.time() + POLL_MAX_S
    res: dict = {}
    while time.time() < deadline:
        res = await provider.poll(task_id)
        if res.get("status") in ("completed", "failed"):
            break
        await asyncio.sleep(POLL_INTERVAL_S)
    if res.get("status") == "completed" and res.get("outputs"):
        return res["outputs"][0]
    return None


async def _push(user_id: str, payload: dict) -> None:
    try:
        await send_to_user(user_id, payload)
    except Exception:  # noqa: BLE001
        pass


async def _emit_run_done(uid: str, run_id: str, n_outputs: int) -> None:
    """漏斗:出片成功(emit 失败不阻塞)。"""
    try:
        from agent.cascade import events as cascade_events
        from agent.cascade.event_names import EventName

        await cascade_events.emit(EventName.PRO_RUN_DONE, user_id=uid, run_id=run_id, payload={"outputs": n_outputs})
    except Exception:  # noqa: BLE001
        pass


async def _persist_outputs(outputs: list[str], key: str) -> list[str]:
    """把 provider 产物 URL 落到自有 media(易过期)。失败/无法下载(如 fixture data: URL)→ 回落原 URL。"""
    final: list[str] = []
    for i, url in enumerate(outputs):
        persisted = None
        if url and not url.startswith("data:"):
            try:
                persisted = await download_and_upload(url, f"{key}_{i}")
            except Exception:  # noqa: BLE001
                persisted = None
        final.append(persisted or url)
    return final


# ── domestic per-node 执行器 ─────────────────────────────────────────────────────


def _topo(nodes: dict, edges: list) -> tuple[list, dict, dict]:
    """拓扑序 + 单值 incoming {(target,handle):(source,sh)} + 多值 incoming_all {(target,handle):[source,...]}(边序)。"""
    incoming: dict = {}
    incoming_all: dict = {}
    adj: dict = {nid: [] for nid in nodes}
    indeg: dict = {nid: 0 for nid in nodes}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in nodes and t in nodes:
            key = (t, e.get("targetHandle"))
            incoming[key] = (s, e.get("sourceHandle"))
            incoming_all.setdefault(key, []).append(s)
            adj[s].append(t)
            indeg[t] += 1
    queue = [n for n, d in indeg.items() if d == 0]
    order: list = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in adj[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(nodes):  # 兜底(validate 已挡环)
        order = list(nodes)
    return order, incoming, incoming_all


def _save_media_bytes(data: bytes, key: str, ext: str = "mp4") -> str:
    """合成产物 bytes → 写本地 media 卷(nginx /media 服务),返回 /media URL(dev/prod 都行,不依赖 S3)。"""
    from agent.cascade.mediakit.clip_extractor import media_root

    d = media_root() / key
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"out.{ext}"
    p.write_bytes(data)
    return f"/media/{key}/out.{ext}"


async def _run_domestic(run: dict, graph: dict) -> None:
    run_id, uid, tid = run["run_id"], run["user_id"], run["thread_id"]
    nodes = {n["id"]: n for n in graph.get("nodes", []) if isinstance(n, dict) and n.get("id")}
    order, incoming, incoming_all = _topo(nodes, graph.get("edges", []) or [])

    try:
        await cost_guard.cost_guard(uid, run_id, float(run.get("cost_est") or 0.0))
    except HardFailure as exc:
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=exc.hint or "cost cap")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": exc.hint or "生成预算超限"})
        return

    await _push(uid, {"type": "pro_run_progress", "thread_id": tid, "run_id": run_id, "status": "running", "pct": 10})

    produced: dict = {}
    outputs: list[str] = []
    any_failed = False
    seed_provider = None
    video_provider = None

    def _src(nid, handle):
        e = incoming.get((nid, handle))
        return e[0] if e else None

    def _img_in(nid):
        s = _src(nid, "image")
        return produced.get(s, {}).get("image") if s else None

    def _cancelled() -> bool:
        cur = pro_runs_repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
        return (not cur) or cur.get("status") == "cancelled"

    for nid in order:
        node = nodes[nid]
        ntype = node.get("type")
        params = node.get("params") or {}

        if ntype in ("Model", "Script", "TTS"):
            continue  # 配置/信息/占位节点(TTS 执行下轮)→ 不产出、不执行
        if ntype == "Prompt":
            produced[nid] = {"text": str(params.get("text") or "")}
            continue
        if ntype in ("LoadImage", "Anchor"):
            produced[nid] = {"image": str(params.get("image_url") or "")}
            continue
        if ntype == "Upscale":
            img = _img_in(nid)
            if img:
                produced[nid] = {"image": img}  # 境内透传(模型超分属未来扩展)
            continue
        if ntype == "Preview":
            s = _src(nid, "image")
            if s:
                p = produced.get(s, {})
                url = p.get("video") or p.get("image")
                if url:
                    outputs.append(url)
            continue
        if ntype == "Generate":
            if node.get("cached") and node.get("cached_url"):
                produced[nid] = {"image": node["cached_url"]}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": node["cached_url"]})
                continue
            if _cancelled():
                return
            ps = _src(nid, "positive")
            prompt = produced.get(ps, {}).get("text", "") if ps else ""
            # 逐镜锚点:收齐所有连进 image 口的参考图(multi),境内 Seedream 收多图。
            refs = [produced.get(s, {}).get("image") for s in incoming_all.get((nid, "image"), [])]
            refs = [u for u in refs if u]
            ref = refs[0] if refs else None
            if str(params.get("backend") or "境内") == _COMFYUI_BACKEND:
                t0 = time.time()
                url = await _comfyui_one(_mini_image_graph(prompt, ref, params), run_id=run_id, uid=uid)
                if url:
                    await cost_guard.record_generation_cost(
                        user_id=uid, run_id=run_id, call_kind="canvas_comfyui",
                        cost_cny=cost_guard.predict_generation_cost("comfyui", n_images=1),
                        provider=f"comfyui:{config.COMFYUI_PROVIDER}", latency_ms=int((time.time() - t0) * 1000),
                    )
                    final = (await _persist_outputs([url], f"{run_id}_{nid}"))[0]
                    produced[nid] = {"image": final}
                    await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
                else:
                    any_failed = True
                pro_runs_repo.touch_lease(run_id, user_id=uid, thread_id=tid)
                continue
            if seed_provider is None:
                from agent.tools.generation import SeedreamProvider

                seed_provider = SeedreamProvider()
            t0 = time.time()
            res = await seed_provider.generate(prompt or "高质量竖屏画面", image_urls=refs or None)
            url = res.get("url")
            if url:
                # 只在成功(真出图)时记账 —— 失败不扣费(与 image_pipeline 同口径)。
                await cost_guard.record_generation_cost(
                    user_id=uid, run_id=run_id, call_kind="canvas_image",
                    cost_cny=cost_guard.predict_generation_cost("image", n_images=1),
                    provider="seedream", latency_ms=int((time.time() - t0) * 1000),
                )
                final = (await _persist_outputs([url], f"{run_id}_{nid}"))[0]
                produced[nid] = {"image": final}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
            else:
                any_failed = True
            continue
        if ntype == "Video":
            if node.get("cached") and node.get("cached_url"):
                produced[nid] = {"video": node["cached_url"]}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": node["cached_url"]})
                continue
            if _cancelled():
                return
            img = _img_in(nid)
            if not img:
                any_failed = True
                continue
            if str(params.get("backend") or "境内") == _COMFYUI_BACKEND:
                t0 = time.time()
                url = await _comfyui_one(_mini_video_graph(img, params), run_id=run_id, uid=uid)
                if url:
                    await cost_guard.record_generation_cost(
                        user_id=uid, run_id=run_id, call_kind="canvas_comfyui",
                        cost_cny=cost_guard.predict_generation_cost("comfyui", n_images=1),
                        provider=f"comfyui:{config.COMFYUI_PROVIDER}", latency_ms=int((time.time() - t0) * 1000),
                    )
                    final = (await _persist_outputs([url], f"{run_id}_{nid}"))[0]
                    produced[nid] = {"video": final}
                    await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
                else:
                    any_failed = True
                pro_runs_repo.touch_lease(run_id, user_id=uid, thread_id=tid)
                continue
            if video_provider is None:
                from agent.tools.video_generation import get_video_provider

                video_provider = get_video_provider()
            dur = int(params.get("duration") or 5)
            t0 = time.time()
            res = await video_provider.generate("镜头自然流畅运动,过渡平滑", duration=dur, image_urls=[img])
            vurl = res.get("video_url")
            if vurl:
                await cost_guard.record_generation_cost(
                    user_id=uid, run_id=run_id, call_kind="canvas_video",
                    cost_cny=cost_guard.predict_generation_cost("video", video_seconds=float(dur)),
                    provider="seedance", latency_ms=int((time.time() - t0) * 1000),
                )
                final = (await _persist_outputs([vurl], f"{run_id}_{nid}"))[0]
                produced[nid] = {"video": final}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
            else:
                any_failed = True
            pro_runs_repo.touch_lease(run_id, user_id=uid, thread_id=tid)  # video 慢 → 续租防误抢
            continue
        if ntype == "Compose":
            if _cancelled():
                return
            srcs = incoming_all.get((nid, "videos"), [])
            vurls = [produced.get(s, {}).get("video") for s in srcs]
            vurls = [u for u in vurls if u]
            if not vurls:
                any_failed = True
                continue
            from agent.tools.compose import compose_videos

            data = await compose_videos(vurls)
            if data:
                final = _save_media_bytes(data, f"{run_id}_compose")
                produced[nid] = {"video": final}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
            else:
                any_failed = True
            pro_runs_repo.touch_lease(run_id, user_id=uid, thread_id=tid)  # 下载+ffmpeg 略慢 → 续租
            continue
        if ntype in ("Subtitle", "BGM"):
            # 视频后期(字幕烧入 / BGM 混音)。best-effort:失败/无字体/无曲目 → 透传上游视频,不阻断。
            if _cancelled():
                return
            s = _src(nid, "video")
            vurl = produced.get(s, {}).get("video") if s else None
            if not vurl:
                any_failed = True
                continue
            out = None
            try:
                if ntype == "Subtitle":
                    from agent.tools.av_post import burn_subtitle

                    out = await burn_subtitle(vurl, str(params.get("text") or ""))
                else:
                    from agent.tools.av_post import mux_bgm

                    out = await mux_bgm(vurl, str(params.get("track") or ""), float(params.get("volume") or 0.3))
            except Exception:  # noqa: BLE001
                out = None
            if out:
                final = _save_media_bytes(out, f"{run_id}_{nid}")
                produced[nid] = {"video": final}
                await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": final})
            else:
                produced[nid] = {"video": vurl}  # 透传(后期未生效)
            pro_runs_repo.touch_lease(run_id, user_id=uid, thread_id=tid)
            continue

    if _cancelled():
        return
    if outputs:
        pro_runs_repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid, result=outputs)
        await _push(uid, {"type": "pro_run_done", "thread_id": tid, "run_id": run_id, "outputs": outputs})
        await _emit_run_done(uid, run_id, len(outputs))
        print(f"[ProWorker:domestic] 完成 run={run_id[:16]} outputs={len(outputs)} partial={any_failed}")
    else:
        # 不自动重试 domestic(重跑会重复扣已成节点);直接置 failed。
        err = "分镜生成失败,请重试或换主题" if any_failed else "图里没有可输出的预览"
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=err)
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})


# ── comfyui 整图路径 ─────────────────────────────────────────────────────────────


async def _run_comfyui(run: dict, graph: dict, provider_name: str) -> None:
    run_id, uid, tid = run["run_id"], run["user_id"], run["thread_id"]
    if comfyui_provider_blocked(provider_name):
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error="cross_border_blocked")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "境内合规:已禁用跨境执行后端"})
        return
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
    pro_runs_repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id=task_id)
    await _push(uid, {"type": "pro_run_progress", "thread_id": tid, "run_id": run_id, "status": "running", "pct": 30})
    await cost_guard.record_generation_cost(
        user_id=uid, run_id=run_id, call_kind="canvas_comfyui",
        cost_cny=float(run.get("cost_est") or 0.0), provider=f"comfyui:{provider_name}", latency_ms=int(elapsed),
    )
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
        pro_runs_repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid, result=final_urls, expected_prompt_id=task_id)
        for url in final_urls:
            await _push(uid, {"type": "pro_run_node_done", "thread_id": tid, "run_id": run_id, "output_url": url})
        await _push(uid, {"type": "pro_run_done", "thread_id": tid, "run_id": run_id, "outputs": final_urls})
        await _emit_run_done(uid, run_id, len(final_urls))
    else:
        err = res.get("error") or "执行失败"
        retried = pro_runs_repo.schedule_pro_run_retry(run_id, err, user_id=uid, thread_id=tid)
        if not retried:
            pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=err, expected_prompt_id=task_id)
            await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})


# ── 入口 + 恢复 ──────────────────────────────────────────────────────────────────


async def process_pro_run_task(run: dict) -> None:
    run_id, uid, tid = run["run_id"], run["user_id"], run["thread_id"]
    try:
        graph = json.loads(run.get("graph_json") or "{}")
    except (json.JSONDecodeError, TypeError) as e:
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error=f"图损坏: {e}")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "图损坏"})
        return
    provider_name = (run.get("provider") or "domestic").lower()
    if provider_name in _COMFYUI_PROVIDERS:
        await _run_comfyui(run, graph, provider_name)
    else:
        await _run_domestic(run, graph)


async def recover_pro_run_task(run: dict) -> None:
    """恢复中断 run。comfyui 路径:有 comfy_prompt_id 则 re-poll(不 re-submit/扣费);否则退回 pending。
    domestic 路径(无 comfy_prompt_id)退回 pending 重跑(崩溃恢复;罕见)。"""
    run_id, uid, tid = run["run_id"], run["user_id"], run["thread_id"]
    prompt_id = run.get("comfy_prompt_id")
    if not prompt_id:
        pro_runs_repo.update_pro_run_state(run_id, "pending", user_id=uid, thread_id=tid)
        return
    provider_name = (run.get("provider") or "selfhosted").lower()
    if comfyui_provider_blocked(provider_name):
        pro_runs_repo.update_pro_run_state(run_id, "failed", user_id=uid, thread_id=tid, error="cross_border_blocked")
        await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": "境内合规:已禁用跨境执行后端"})
        return
    provider = get_comfyui_provider(provider_name)
    try:
        res = await provider.poll(prompt_id)
    except Exception as e:  # noqa: BLE001
        pro_runs_repo.schedule_pro_run_retry(run_id, str(e), user_id=uid, thread_id=tid)
        return
    if res.get("status") == "completed" and res.get("outputs"):
        final_urls = await _persist_outputs(res["outputs"], run_id)
        pro_runs_repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid, result=final_urls, expected_prompt_id=prompt_id)
        await _push(uid, {"type": "pro_run_done", "thread_id": tid, "run_id": run_id, "outputs": final_urls})
        await _emit_run_done(uid, run_id, len(final_urls))
    elif res.get("status") == "failed":
        err = res.get("error") or "执行失败"
        if not pro_runs_repo.schedule_pro_run_retry(run_id, err, user_id=uid, thread_id=tid):
            await _push(uid, {"type": "pro_run_failed", "thread_id": tid, "run_id": run_id, "error": err})
