"""WebSocket 服务

单 WS 连接承载多个会话，agent 实例走 LRU 池管理。
首条消息 auth → 绑定 user_id → 后续消息隔离。
"""

import asyncio
import json

from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedOK

from agent.config import LLM_MODEL, IMAGE_GEN_PROVIDER
from agent.pool import AgentPool
from agent.store import get_messages, save_message, set_user_id as store_set_user_id
from agent.tools import canvas as canvas_tools
from agent.tools.video_generation import get_video_provider


POOL_SIZE = 5


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


async def _run_agent(pool: AgentPool, thread_id: str, user_content: str, ws):
    """后台执行 agent。"""
    try:
        save_message(thread_id, "user", user_content)
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
        save_message(thread_id, "agent", reply)
    except Exception as e:
        reply = f"处理出错: {e}"
        save_message(thread_id, "agent", reply)
        print(f"[错误] thread={thread_id} {e}")

    await _auto_execute_pending(thread_id)
    await _poll_image_tasks(thread_id)

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


async def _auto_execute_pending(thread_id: str):
    pass


def _make_provider(name: str):
    from agent.tools.generation import ApimartProvider, GoogleProvider
    if name == "google":
        return GoogleProvider()
    return ApimartProvider()


async def _submit_and_poll(thread_id: str, node_id: str, prompt: str, provider_name: str, ws):
    """后台：找参考图 → 提交生图 → 轮询 → 结果上传 S3。"""
    import time

    provider = _make_provider(provider_name)

    try:
        canvas_tools.set_thread_id(thread_id)

        ref_urls: list[str] = []
        all_edges = canvas_tools._load_all_edges()
        parent_ids = [e["source"] for e in all_edges if e["target"] == node_id]
        for pid in parent_ids:
            parent = canvas_tools._load_node(pid)
            p_url = (parent.get("result") or {}).get("url") if parent else None
            if p_url:
                ref_urls.append(str(p_url))

        print(f"[生图提交] node={node_id} prompt={prompt[:50]}... ref_urls={len(ref_urls)}个")
        t0 = time.time()
        submitted = await provider.submit(prompt, "16:9", "2k", ref_urls if ref_urls else None)
        elapsed = (time.time() - t0) * 1000
        if submitted.get("task_id"):
            canvas_tools._update_node_result(node_id, {"task_id": submitted["task_id"], "ref_urls": ref_urls})
            print(f"[生图提交] 完成 node={node_id} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")
        else:
            canvas_tools.update_canvas_node(node_id, asset_status="failed")
            canvas_tools._update_node_result(node_id, {"error": submitted.get("error", "submit failed")})
            print(f"[生图提交失败] node={node_id} 耗时={elapsed:.0f}ms error={submitted.get('error')}")
            return

        result = await provider.poll(submitted["task_id"])
        canvas_tools.set_thread_id(thread_id)
        if result.get("url"):
            canvas_tools.update_canvas_node(node_id, asset_status="done")
            s3_url = await _upload_to_s3(result["url"], node_id)
            final_url = s3_url or result["url"]
            canvas_tools._update_node_result(node_id, {"url": final_url, "actual_time": result.get("actual_time", 0)})
            print(f"[生图完成] node={node_id} url={final_url[:60]}...")
        elif result.get("image_data"):
            s3_url = _upload_bytes_to_s3(result["image_data"], f"{node_id}.png")
            if s3_url:
                canvas_tools.update_canvas_node(node_id, asset_status="done")
                canvas_tools._update_node_result(node_id, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
                print(f"[生图完成] node={node_id} url={s3_url[:60]}...")
            else:
                canvas_tools.update_canvas_node(node_id, asset_status="failed")
                print(f"[生图失败] node={node_id} S3上传失败")
        else:
            is_timeout = result.get("error") == "timeout"
            status = "timeout" if is_timeout else "failed"
            canvas_tools.update_canvas_node(node_id, asset_status=status)
            canvas_tools._update_node_result(node_id, {"error": result.get("error", "")})
            print(f"[生图{'超时' if is_timeout else '失败'}] node={node_id} {result.get('error')}")
        try:
            await _send(ws, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
        except (ConnectionClosedOK, Exception):
            pass
    except Exception as e:
        print(f"[后台生图] 异常 node={node_id}: {e}")


async def _submit_and_poll_video(thread_id: str, node_id: str, prompt: str, duration: int, resolution: str, generate_audio: bool, ws):
    """后台：找参考图 → 提交 Seedance → 轮询 → 结果上传 S3。"""
    import time

    provider = get_video_provider()

    try:
        canvas_tools.set_thread_id(thread_id)

        ref_urls: list[str] = []
        all_edges = canvas_tools._load_all_edges()
        parent_ids = [e["source"] for e in all_edges if e["target"] == node_id]
        for pid in parent_ids:
            parent = canvas_tools._load_node(pid)
            p_url = (parent.get("result") or {}).get("url") if parent else None
            if p_url:
                ref_urls.append(str(p_url))

        print(f"[视频提交] node={node_id} duration={duration}s res={resolution} audio={generate_audio} prompt={prompt[:50]}... ref_urls={len(ref_urls)}个")
        t0 = time.time()
        submitted = await provider.submit(prompt, duration=duration, resolution=resolution, ratio="16:9", generate_audio=generate_audio, image_urls=ref_urls if ref_urls else None)
        elapsed = (time.time() - t0) * 1000
        if submitted.get("task_id"):
            canvas_tools._update_node_result(node_id, {"task_id": submitted["task_id"], "ref_urls": ref_urls})
            print(f"[视频提交] 完成 node={node_id} task_id={submitted['task_id']} 耗时={elapsed:.0f}ms")
        else:
            canvas_tools.update_canvas_node(node_id, asset_status="failed")
            canvas_tools._update_node_result(node_id, {"error": submitted.get("error", "submit failed")})
            print(f"[视频提交失败] node={node_id} 耗时={elapsed:.0f}ms error={submitted.get('error')}")
            return

        result = await provider.poll(submitted["task_id"])
        canvas_tools.set_thread_id(thread_id)
        if result.get("video_url"):
            s3_url = await _upload_to_s3(result["video_url"], node_id, ext="mp4")
            if s3_url:
                canvas_tools.update_canvas_node(node_id, asset_status="done")
                canvas_tools._update_node_result(node_id, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
                print(f"[视频完成] node={node_id} url={s3_url[:60]}...")
            else:
                canvas_tools.update_canvas_node(node_id, asset_status="failed")
                print(f"[视频失败] node={node_id} S3上传失败")
        else:
            is_timeout = result.get("error") == "timeout"
            status = "timeout" if is_timeout else "failed"
            canvas_tools.update_canvas_node(node_id, asset_status=status)
            canvas_tools._update_node_result(node_id, {"error": result.get("error", "")})
            print(f"[视频{'超时' if is_timeout else '失败'}] node={node_id} {result.get('error')}")
        try:
            await _send(ws, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
        except (ConnectionClosedOK, Exception):
            pass
    except Exception as e:
        print(f"[后台视频] 异常 node={node_id}: {e}")


async def _poll_and_notify(thread_id: str, ws=None):
    try:
        await asyncio.gather(
            _poll_image_tasks(thread_id),
            _poll_video_tasks(thread_id),
        )
        if ws:
            try:
                await _send(ws, type="canvas_updated", thread_id=thread_id, canvas=_canvas_data(thread_id))
            except (ConnectionClosedOK, Exception):
                pass
    except Exception as e:
        print(f"[轮询] 异常: {e}")


async def _poll_image_tasks(thread_id: str):
    canvas = _canvas_data(thread_id)
    if not canvas:
        return

    groups: dict[str, dict[str, str]] = {}
    for nid, node in canvas["nodes"].items():
        if node["type"] == "image" and node.get("asset_status") == "generating":
            tid = (node.get("result") or {}).get("task_id")
            if tid:
                p = node.get("image_gen_provider") or IMAGE_GEN_PROVIDER
                groups.setdefault(p, {})[nid] = tid

    if not groups:
        return

    canvas_tools.set_thread_id(thread_id)
    for provider_name, task_map in groups.items():
        print(f"[生图轮询] {provider_name}: {len(task_map)} 个节点并行轮询...")
        provider = _make_provider(provider_name)
        results = await provider.poll_all(task_map)
        for nid, result in results.items():
            if result.get("url"):
                canvas_tools.update_canvas_node(nid, asset_status="done")
                s3_url = await _upload_to_s3(result["url"], nid)
                final_url = s3_url or result["url"]
                canvas_tools._update_node_result(nid, {"url": final_url, "actual_time": result.get("actual_time", 0)})
                print(f"[生图完成] {provider_name} node={nid} url={final_url[:60]}...")
            elif result.get("image_data"):
                s3_url = _upload_bytes_to_s3(result["image_data"], f"{nid}.png")
                if s3_url:
                    canvas_tools.update_canvas_node(nid, asset_status="done")
                    canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
                    print(f"[生图完成] {provider_name} node={nid} url={s3_url[:60]}...")
                else:
                    canvas_tools.update_canvas_node(nid, asset_status="failed")
                    print(f"[生图失败] {provider_name} node={nid} S3上传失败")
            else:
                is_timeout = result.get("error") == "timeout"
                status = "timeout" if is_timeout else "failed"
                canvas_tools.update_canvas_node(nid, asset_status=status)
                canvas_tools._update_node_result(nid, {"error": result.get("error", "")})
                print(f"[生图{'超时' if is_timeout else '失败'}] {provider_name} node={nid} {result.get('error')}")


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

    t0 = __import__("time").time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
        dl_ms = (__import__("time").time() - t0) * 1000
        print(f"[S3] 下载完成 node={node_id} size={len(resp.content)} 耗时={dl_ms:.0f}ms")

        s3_url = upload_bytes(resp.content, f"{node_id}.{ext}")
        total_ms = (__import__("time").time() - t0) * 1000
        if s3_url:
            print(f"[S3] 上传完成 node={node_id} 总耗时={total_ms:.0f}ms")
        return s3_url
    except Exception as e:
        print(f"[S3] 上传异常 node={node_id}: {e}")
        return None


async def _poll_video_tasks(thread_id: str):
    canvas = _canvas_data(thread_id)
    if not canvas:
        return

    provider = get_video_provider()
    task_map: dict[str, str] = {}
    for nid, node in canvas["nodes"].items():
        if node["type"] == "video" and node.get("asset_status") == "generating":
            tid = (node.get("result") or {}).get("task_id")
            if tid:
                task_map[nid] = tid

    if not task_map:
        return

    print(f"[视频轮询] {len(task_map)} 个节点并行轮询...")
    results = await provider.poll_all(task_map)
    canvas_tools.set_thread_id(thread_id)
    for nid, result in results.items():
        if result.get("video_url"):
            s3_url = await _upload_to_s3(result["video_url"], nid, ext="mp4")
            if s3_url:
                canvas_tools.update_canvas_node(nid, asset_status="done")
                canvas_tools._update_node_result(nid, {"url": s3_url, "actual_time": result.get("actual_time", 0)})
                print(f"[视频完成] node={nid} url={s3_url[:60]}...")
            else:
                canvas_tools.update_canvas_node(nid, asset_status="failed")
                print(f"[视频失败] node={nid} S3上传失败")
        else:
            is_timeout = result.get("error") == "timeout"
            canvas_tools.update_canvas_node(nid, asset_status="timeout" if is_timeout else "failed")
            print(f"[视频{'超时' if is_timeout else '失败'}] node={nid} {result.get('error')}")


async def _recover_polling(ws):
    import sqlite3
    db = sqlite3.connect(str(canvas_tools._DB_PATH))
    rows = db.execute(
        "SELECT DISTINCT thread_id FROM canvas_nodes WHERE asset_status='generating'"
    ).fetchall()
    db.close()
    for (tid,) in rows:
        print(f"[恢复轮询] thread={tid}")
        asyncio.create_task(_poll_and_notify(tid, ws))


async def handle(websocket):
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
                store_set_user_id(user_id)
                print(f"[连接] user={user_id} pool 上限 {POOL_SIZE}")
                asyncio.create_task(_recover_polling(websocket))
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
                canvas_tools.execute_node(nid, node_type, description, provider)
                await _send(
                    ws=websocket,
                    type="canvas_updated",
                    thread_id=thread_id,
                    canvas=_canvas_data(thread_id),
                )
                if node_type == "composite":
                    await _send(
                        ws=websocket,
                        type="canvas_updated",
                        thread_id=thread_id,
                        canvas=_canvas_data(thread_id),
                    )
                    continue

                if node_type == "video":
                    duration = msg.get("duration", 5)
                    resolution = msg.get("resolution", "720p")
                    generate_audio = msg.get("generate_audio", True)
                    asyncio.create_task(_submit_and_poll_video(thread_id, nid, description, duration, resolution, generate_audio, websocket))
                else:
                    asyncio.create_task(_submit_and_poll(thread_id, nid, description, provider, websocket))
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

            if msg_type == "get_session_state":
                print(f"[请求] get_session_state thread={thread_id}")
                msgs = get_messages(thread_id)
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
                asyncio.create_task(_run_agent(pool, thread_id, content, websocket))
                await _send(ws=websocket, type="processing", thread_id=thread_id)
                continue

    except ConnectionClosedOK:
        pass

    print("[断开] WS 连接已关闭")


async def main(host="0.0.0.0", port=8765):
    print(f"OpenRHTV WS 服务: ws://{host}:{port}")
    async with serve(handle, host, port):
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    asyncio.run(main())
