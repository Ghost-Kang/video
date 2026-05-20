"""WebSocket 服务

单 WS 连接承载多个会话，agent 实例走 LRU 池管理。
首条消息 auth → 绑定 user_id → 后续消息隔离。
生成任务走 SQLite 队列 → 全局 worker 统一调度。
"""

import asyncio
import json
import time

from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK

from agent.config import LLM_MODEL, IMAGE_GEN_PROVIDER
from agent.pool import AgentPool
from agent.store import get_messages, save_message, list_sessions, ensure_session_exists, delete_session as store_delete_session
from agent.tools import canvas as canvas_tools
from agent.tools.video_generation import get_video_provider


POOL_SIZE = 5

# WS 注册表：user_id → websocket（worker 用来推送 canvas_updated）
_ws_registry: dict[str, object] = {}
_worker_started = False


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


def _canvas_data(thread_id: str) -> dict | None:
    canvas_tools.set_thread_id(thread_id)
    nodes = canvas_tools._load_all_nodes()
    edges = canvas_tools._load_all_edges()
    return {"nodes": nodes, "edges": edges} if nodes else None


def _update_position(thread_id: str, msg: dict):
    canvas_tools.set_thread_id(thread_id)
    nid = msg["node_id"]
    node = canvas_tools._load_node(nid)
    if node:
        node["x"] = msg["x"]
        node["y"] = msg["y"]
        canvas_tools._upsert_node(node)


async def _send(ws, **kwargs):
    await ws.send(json.dumps(kwargs, ensure_ascii=False))


def _notify_user(user_id: str, thread_id: str):
    """向指定用户推送 canvas_updated。无连接则跳过。"""
    ws = _ws_registry.get(user_id)
    if ws:
        asyncio.create_task(_safe_notify(ws, thread_id))
    else:
        print(f"[通知] user={user_id} 未连接，跳过推送 thread={thread_id}")


async def _safe_notify(ws, thread_id: str):
    try:
        await _send(ws, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
    except (ConnectionClosedOK, Exception):
        pass


async def _optimize_prompt(node_id: str, prompt: str, feedback: str) -> str:
    """用 LLM 优化图片生成 prompt，不经过主 agent 流程。"""
    model = ChatGoogleGenerativeAI(model=LLM_MODEL)
    system = "你是一位专业的 AI 绘画提示词优化师。根据用户的反馈优化提示词，只返回优化后的提示词，不要加任何解释或前缀。"
    user = f"当前提示词：\n{prompt}\n\n用户反馈：\n{feedback}\n\n请输出优化后的提示词："
    result = model.invoke([{"role": "system", "content": system}, {"role": "user", "content": user}])
    optimized = result.content if hasattr(result, "content") else str(result)

    node = canvas_tools._load_node(node_id)
    if node:
        node["description"] = optimized
        canvas_tools._upsert_node(node)
        print(f"[润色] 已更新节点 description node={node_id}")

    return optimized


async def _run_agent(user_id: str, pool: AgentPool, thread_id: str, user_content: str, ws):
    """后台执行 agent。"""
    try:
        save_message(user_id, thread_id, "user", user_content)
        entry = await pool.get(thread_id)

        full_reply = ""
        async for chunk in entry["agent"].astream(
            {"messages": [{"role": "user", "content": user_content}]},
            config=entry["config"],
            stream_mode="messages",
            version="v2",
        ):
            msg, meta = chunk["data"]

            if isinstance(msg, AIMessageChunk) and msg.tool_calls:
                for tc in msg.tool_calls:
                    await _send(ws, type="agent_stream", thread_id=thread_id,
                                event="tool_call", name=tc.get("name", ""), args=str(tc.get("args", {})))

            elif isinstance(msg, AIMessageChunk) and msg.content and not isinstance(msg, ToolMessage):
                token = _extract_text(msg.content)
                if token and not full_reply.endswith(token):
                    full_reply += token
                    await _send(ws, type="agent_stream", thread_id=thread_id, event="text", content=token)

        reply = full_reply or "（未生成回复）"
        save_message(user_id, thread_id, "agent", reply)
    except Exception as e:
        reply = f"处理出错: {e}"
        save_message(user_id, thread_id, "agent", reply)
        print(f"[错误] thread={thread_id} {e}")

    try:
        await _send(
            ws,
            type="agent_response",
            thread_id=thread_id,
            content=reply,
            canvas=_canvas_data(thread_id),
        )
    except (ConnectionClosedOK, Exception):
        pass


# ---------- 上传工具 ----------


def _upload_bytes_to_s3(data: bytes, filename: str) -> str | None:
    from agent.tools.s3_upload import upload_bytes as _upload_bytes
    try:
        return _upload_bytes(data, filename)
    except Exception as e:
        print(f"[S3] 上传异常 {filename}: {e}")
        return None


async def _upload_to_s3(image_url: str, node_id: str, ext: str = "png") -> str | None:
    import httpx
    from agent.tools.s3_upload import upload_bytes

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
        dl_ms = (time.time() - t0) * 1000
        print(f"[S3] 下载完成 node={node_id} size={len(resp.content)} 耗时={dl_ms:.0f}ms")

        s3_url = upload_bytes(resp.content, f"{node_id}.{ext}")
        total_ms = (time.time() - t0) * 1000
        if s3_url:
            print(f"[S3] 上传完成 node={node_id} 总耗时={total_ms:.0f}ms")
        return s3_url
    except Exception as e:
        print(f"[S3] 上传异常 node={node_id}: {e}")
        return None


# ---------- 生成任务 worker ----------


def _make_image_provider(name: str):
    from agent.tools.generation import ApimartProvider, GoogleProvider
    if name == "google":
        return GoogleProvider()
    return ApimartProvider()


def _get_ref_urls(node: dict) -> list[str]:
    """获取节点的上游参考图 URL 列表。"""
    canvas_tools.set_thread_id(node["thread_id"])
    canvas_tools.set_user_id(node["user_id"])
    all_edges = canvas_tools._load_all_edges()
    parent_ids = [e["source"] for e in all_edges if e["target"] == node["id"]]
    refs: list[str] = []
    for pid in parent_ids:
        parent = canvas_tools._load_node(pid)
        p_url = (parent.get("result") or {}).get("url") if parent else None
        if p_url:
            refs.append(str(p_url))
    return refs


def _setup_canvas_context(node: dict):
    """为 worker 任务设置正确的 canvas 上下文。"""
    canvas_tools.set_user_id(node["user_id"])
    canvas_tools.set_thread_id(node["thread_id"])


async def _process_image_task(node: dict):
    """处理单个图片生成任务。"""
    nid = node["id"]
    provider_name = node.get("image_gen_provider") or IMAGE_GEN_PROVIDER
    prompt = (node.get("result") or {}).get("prompt") or node.get("description", "")
    _setup_canvas_context(node)

    # 查找上游参考图
    ref_urls = _get_ref_urls(node)

    provider = _make_image_provider(provider_name)
    print(f"[Worker] 图片生成 node={nid} provider={provider_name} prompt={prompt[:50]}... refs={len(ref_urls)}")

    # 提交
    t0 = time.time()
    submitted = await provider.submit(prompt, "16:9", "2k", ref_urls if ref_urls else None)
    elapsed = (time.time() - t0) * 1000
    if not submitted.get("task_id"):
        canvas_tools.update_generation_state(nid, "failed", error=submitted.get("error", "submit failed"))
        print(f"[Worker] 提交失败 node={nid} 耗时={elapsed:.0f}ms")
        _notify_user(node["user_id"], node["thread_id"])
        return

    canvas_tools.update_generation_state(nid, "polling", task_id=submitted["task_id"])
    print(f"[Worker] 已提交 node={nid} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")

    # 轮询结果
    result = await provider.poll(submitted["task_id"])
    _setup_canvas_context(node)

    if result.get("url"):
        s3_url = await _upload_to_s3(result["url"], nid)
        final_url = s3_url or result["url"]
        canvas_tools.update_generation_state(nid, "done")
        canvas_tools._update_node_result(nid, {"url": final_url, "actual_time": result.get("actual_time", 0)})
        print(f"[Worker] 生图完成 node={nid} url={final_url[:60]}...")
    elif result.get("image_data"):
        s3_url = _upload_bytes_to_s3(result["image_data"], f"{nid}.png")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done")
            canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
            print(f"[Worker] 生图完成 node={nid} url={s3_url[:60]}...")
        else:
            canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败")
    else:
        is_timeout = result.get("error") == "timeout"
        status = "failed"
        err = result.get("error", "")
        if is_timeout:
            status = "failed"
            err = "timeout"
        canvas_tools.update_generation_state(nid, status, error=err)
        print(f"[Worker] 生图{'超时' if is_timeout else '失败'} node={nid} {err}")

    _notify_user(node["user_id"], node["thread_id"])


async def _process_video_task(node: dict):
    """处理单个视频生成任务。"""
    nid = node["id"]
    prompt = (node.get("result") or {}).get("prompt") or node.get("description", "")
    params = node.get("result") or {}
    duration = params.get("duration", 5)
    resolution = params.get("resolution", "720p")
    generate_audio = params.get("generate_audio", True)
    _setup_canvas_context(node)

    ref_urls = _get_ref_urls(node)
    provider = get_video_provider()

    print(f"[Worker] 视频生成 node={nid} duration={duration}s res={resolution} audio={generate_audio} refs={len(ref_urls)}")

    t0 = time.time()
    submitted = await provider.submit(prompt, duration=duration, resolution=resolution, ratio="16:9",
                                       generate_audio=generate_audio, image_urls=ref_urls if ref_urls else None)
    elapsed = (time.time() - t0) * 1000
    if not submitted.get("task_id"):
        canvas_tools.update_generation_state(nid, "failed", error=submitted.get("error", "submit failed"))
        print(f"[Worker] 视频提交失败 node={nid} 耗时={elapsed:.0f}ms")
        _notify_user(node["user_id"], node["thread_id"])
        return

    canvas_tools.update_generation_state(nid, "polling", task_id=submitted["task_id"])
    print(f"[Worker] 视频已提交 node={nid} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")

    result = await provider.poll(submitted["task_id"])
    _setup_canvas_context(node)

    if result.get("video_url"):
        s3_url = await _upload_to_s3(result["video_url"], nid, ext="mp4")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done")
            canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
            print(f"[Worker] 视频完成 node={nid} url={s3_url[:60]}...")
        else:
            canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败")
    else:
        is_timeout = result.get("error") == "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=result.get("error", ""))
        print(f"[Worker] 视频{'超时' if is_timeout else '失败'} node={nid} {result.get('error')}")

    _notify_user(node["user_id"], node["thread_id"])


async def _process_composite_task(node: dict):
    """处理单个合成任务：收集上游 video → ffmpeg 拼接 → 上传 S3。"""
    from agent.tools.compose import compose_videos as _compose
    from agent.tools.s3_upload import upload_bytes

    nid = node["id"]
    _setup_canvas_context(node)

    edges = canvas_tools._load_all_edges()
    parent_ids = [e["source"] for e in edges if e["target"] == nid]
    urls: list[str] = []
    for pid in parent_ids:
        parent = canvas_tools._load_node(pid)
        if parent and parent["type"] == "video":
            p_url = (parent.get("result") or {}).get("url")
            if p_url:
                urls.append(str(p_url))

    if len(urls) < 1:
        canvas_tools.update_generation_state(nid, "failed", error="没有可拼接的视频")
        print(f"[Worker] 合成失败 node={nid} 没有视频")
        _notify_user(node["user_id"], node["thread_id"])
        return

    print(f"[Worker] 合成 node={nid} 合并 {len(urls)} 个视频...")
    result_bytes = await _compose(urls)
    if not result_bytes:
        canvas_tools.update_generation_state(nid, "failed", error="ffmpeg 合成失败")
        print(f"[Worker] 合成失败 node={nid} ffmpeg 失败")
        _notify_user(node["user_id"], node["thread_id"])
        return

    s3_url = upload_bytes(result_bytes, "composite.mp4")
    if not s3_url:
        canvas_tools.update_generation_state(nid, "failed", error="S3 上传失败")
        print(f"[Worker] 合成失败 node={nid} S3 失败")
        _notify_user(node["user_id"], node["thread_id"])
        return

    canvas_tools.update_generation_state(nid, "done")
    canvas_tools._update_node_result(nid, {"url": s3_url, "clips": len(urls)})
    print(f"[Worker] 合成完成 node={nid} url={s3_url[:60]}...")
    _notify_user(node["user_id"], node["thread_id"])


async def _generation_worker():
    """全局 worker：轮询 SQLite 队列，处理生成任务。"""
    print("[Worker] 启动生成任务调度器")
    tick = 0
    while True:
        tick += 1
        t_tick = time.time()
        try:
            # 处理新提交的 pending 任务
            tasks = canvas_tools.claim_pending_tasks()
            if tasks:
                print(f"[Worker] tick={tick} 认领 {len(tasks)} 个任务: {[(t['id'][:12], t['type']) for t in tasks]}")
            for task in tasks:
                t_task = time.time()
                print(f"[Worker] 开始处理 node={task['id'][:16]} type={task['type']} user={task['user_id']}")
                try:
                    _setup_canvas_context(task)
                    if task["type"] == "composite":
                        await _process_composite_task(task)
                    elif task["type"] == "video":
                        await _process_video_task(task)
                    else:
                        await _process_image_task(task)
                    dt = (time.time() - t_task) * 1000
                    print(f"[Worker] 完成处理 node={task['id'][:16]} 耗时={dt:.0f}ms")
                except Exception as e:
                    dt = (time.time() - t_task) * 1000
                    print(f"[Worker] 任务异常 node={task.get('id','?')[:16]} 耗时={dt:.0f}ms error={e}")
                    canvas_tools.update_generation_state(task["id"], "failed", error=str(e))
                    _notify_user(task.get("user_id", ""), task.get("thread_id", ""))

            # 恢复中断的任务（submitted/polling 状态）
            # Google provider 的 in-memory task 在重启后丢失，需重新提交
            recovered = canvas_tools.recover_generation_tasks()
            if recovered:
                print(f"[Worker] tick={tick} 恢复 {len(recovered)} 个已中断任务")
            for task in recovered:
                provider_name = task.get("image_gen_provider") or IMAGE_GEN_PROVIDER
                if task["type"] == "image" and provider_name == "google":
                    # Google 用内存 task，重启丢失 → 重新入队
                    print(f"[Worker] 恢复 Google 任务 → 重新入队 node={task['id'][:16]}")
                    canvas_tools.update_generation_state(task["id"], "pending",
                        error="服务重启，重新提交")
                else:
                    # 外部 task_id 仍在，继续轮询
                    print(f"[Worker] 恢复轮询 node={task['id'][:16]} provider={provider_name} task_id={task.get('generation_task_id', '?')[:16]}")
                    try:
                        _setup_canvas_context(task)
                        if task["type"] == "video":
                            provider = get_video_provider()
                        else:
                            provider = _make_image_provider(provider_name)
                        tid = task.get("generation_task_id")
                        if not tid:
                            canvas_tools.update_generation_state(task["id"], "failed", error="缺少 task_id")
                            continue
                        result = await provider.poll(tid)
                        _setup_canvas_context(task)
                        _apply_poll_result(task, result)
                    except Exception as e:
                        print(f"[Worker] 恢复任务异常 node={task.get('id','?')[:16]}: {e}")

            dt_tick = (time.time() - t_tick) * 1000
            if tasks or recovered:
                print(f"[Worker] tick={tick} 完成 耗时={dt_tick:.0f}ms")

        except Exception as e:
            print(f"[Worker] 调度异常: {e}")

        await asyncio.sleep(2)


def _apply_poll_result(task: dict, result: dict):
    """将轮询结果写入节点。"""
    nid = task["id"]
    if result.get("url"):
        canvas_tools.update_generation_state(nid, "done")
        canvas_tools._update_node_result(nid, {"url": result["url"], "actual_time": result.get("actual_time", 0)})
        print(f"[Worker] 恢复完成 node={nid} url={result['url'][:60]}...")
    elif result.get("video_url"):
        canvas_tools.update_generation_state(nid, "done")
        if not result.get("url"):
            canvas_tools._update_node_result(nid, {"url": result["video_url"], "actual_time": result.get("actual_time", 0)})
        print(f"[Worker] 恢复完成 node={nid}")
    elif result.get("image_data"):
        s3_url = _upload_bytes_to_s3(result["image_data"], f"{nid}.png")
        if s3_url:
            canvas_tools.update_generation_state(nid, "done")
            canvas_tools._update_node_result(nid, {"url": s3_url})
    else:
        is_timeout = result.get("error") == "timeout"
        canvas_tools.update_generation_state(nid, "failed", error=result.get("error", ""))
        print(f"[Worker] 恢复{'超时' if is_timeout else '失败'} node={nid}")
    _notify_user(task["user_id"], task["thread_id"])


def _start_worker():
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    asyncio.create_task(_generation_worker())


# ---------- WebSocket handler ----------


async def handle(websocket):
    global _ws_registry

    pool = AgentPool(max_size=POOL_SIZE)
    user_id: str | None = None
    print(f"[连接] 新连接，等待 auth...")

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            msg_type = msg.get("type")
            print(f"[MSG] type={msg_type} thread={msg.get('thread_id','?')} user={user_id or '(未认证)'}")

            # 首条消息必须是 auth
            if msg_type == "auth":
                user_id = msg.get("user_id", "").strip()
                if not user_id:
                    await websocket.close(4001, "user_id required")
                    return
                canvas_tools.set_user_id(user_id)
                _ws_registry[user_id] = websocket
                _start_worker()
                print(f"[连接] user={user_id} pool 上限 {POOL_SIZE}")
                # auth 后自动下发会话列表
                sessions = list_sessions(user_id)
                await _send(ws=websocket, type="session_list", sessions=sessions)
                continue

            if not user_id:
                await websocket.close(4001, "未认证")
                return

            thread_id = msg.get("thread_id", "")
            if not thread_id:
                continue

            if msg_type == "reorder_edge":
                eid = msg.get("edge_id", "")
                direction = msg.get("direction", "up")
                canvas_tools.set_thread_id(thread_id)
                canvas_tools.reorder_edge(eid, direction)
                await _send(ws=websocket, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
                continue

            if msg_type == "create_edge":
                src = msg.get("source", "")
                tgt = msg.get("target", "")
                canvas_tools.set_thread_id(thread_id)
                result = canvas_tools.create_canvas_edge(src, tgt)
                if "error" not in result:
                    await _send(ws=websocket, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
                else:
                    print(f"[边] 创建失败: {result['error']}")
                continue

            if msg_type == "delete_edge":
                eid = msg.get("edge_id", "")
                canvas_tools.set_thread_id(thread_id)
                result = canvas_tools.delete_canvas_edge(eid)
                if "deleted" in result:
                    await _send(ws=websocket, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
                else:
                    print(f"[边] 删除失败: {result.get('error')}")
                continue

            if msg_type == "update_position":
                _update_position(thread_id, msg)
                continue

            if msg_type == "review_node":
                action = msg.get("action", "")
                nid = msg.get("node_id", "")
                canvas_tools.set_thread_id(thread_id)
                if action == "approve":
                    canvas_tools.approve_node(nid)
                elif action == "reject":
                    canvas_tools.reject_node(nid, msg.get("feedback", ""))
                await _send(
                    ws=websocket,
                    type="canvas_updated",
                    thread_id=thread_id,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "execute_node":
                nid = msg.get("node_id", "")
                node_type = msg.get("node_type", "")
                description = msg.get("description", "")
                provider = msg.get("image_gen_provider") or IMAGE_GEN_PROVIDER
                print(f"[执行] execute_node node={nid} type={node_type} provider={provider} prompt={description[:50]}...")
                canvas_tools.set_thread_id(thread_id)

                # execute_node 设置基础状态 + result
                result = canvas_tools.execute_node(nid, node_type, description, provider)
                if "_pending_submit" in result:
                    # 媒体节点：入队让 worker 处理
                    canvas_tools.enqueue_generation(nid)
                    # 视频/合成额外参数存入 result
                    if node_type == "video":
                        canvas_tools._update_node_result(nid, {
                            "prompt": description,
                            "duration": msg.get("duration", 5),
                            "resolution": msg.get("resolution", "720p"),
                            "generate_audio": msg.get("generate_audio", True),
                        })

                await _send(
                    ws=websocket,
                    type="canvas_updated",
                    thread_id=thread_id,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "update_node_status":
                nid = msg.get("node_id", "")
                node_status = msg.get("node_status", "reviewing")
                print(f"[状态] update_node_status node={nid} → {node_status}")
                canvas_tools.set_thread_id(thread_id)
                canvas_tools.update_canvas_node(nid, node_status=node_status)
                updated = canvas_tools._load_node(nid)
                print(f"[状态] 确认 node={nid} node_status={updated.get('node_status') if updated else 'NOT FOUND'}")
                await _send(
                    ws=websocket,
                    type="canvas_updated",
                    thread_id=thread_id,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "optimize_prompt":
                nid = msg.get("node_id", "")
                prompt = msg.get("prompt", "")
                feedback = msg.get("feedback", "")
                print(f"[润色] optimize_prompt node={nid} feedback={feedback[:50]}...")
                canvas_tools.set_thread_id(thread_id)
                optimized = await _optimize_prompt(nid, prompt, feedback)
                print(f"[润色] 完成 node={nid} optimized={optimized[:80]}...")
                await _send(
                    ws=websocket,
                    type="prompt_optimized",
                    thread_id=thread_id,
                    node_id=nid,
                    optimized_prompt=optimized,
                )
                continue

            if msg_type == "delete_session":
                target_thread = msg.get("thread_id", "")
                if target_thread:
                    store_delete_session(user_id, target_thread)
                continue

            if msg_type == "list_sessions":
                sessions = list_sessions(user_id)
                await _send(ws=websocket, type="session_list", sessions=sessions)
                continue

            if msg_type == "get_session_state":
                ensure_session_exists(user_id, thread_id)
                print(f"[请求] get_session_state thread={thread_id}")
                msgs = get_messages(user_id, thread_id)
                print(f"[请求] 返回 msgs={len(msgs)} canvas={_canvas_data(thread_id) is not None}")
                await _send(
                    ws=websocket,
                    type="session_state",
                    thread_id=thread_id,
                    messages=msgs,
                    canvas=_canvas_data(thread_id),
                )
                continue

            if msg_type == "user_message":
                content = msg.get("content", "").strip()
                if not content:
                    continue
                print(f"[用户] thread={thread_id} {content[:80]}...")
                asyncio.create_task(_run_agent(user_id, pool, thread_id, content, websocket))
                await _send(ws=websocket, type="processing", thread_id=thread_id)
                continue

    except ConnectionClosedOK:
        pass
    finally:
        if user_id:
            _ws_registry.pop(user_id, None)
        print("[断开] WS 连接已关闭")


async def main(host="0.0.0.0", port=8765):
    print(f"OpenRHTV WS 服务: ws://{host}:{port}")
    _start_worker()
    async with serve(handle, host, port):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
