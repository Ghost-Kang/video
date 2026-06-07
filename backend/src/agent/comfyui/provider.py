"""ComfyUI 执行 Provider 抽象 —— 对齐 tools/generation.py 的 submit()/poll() + get_*() 范式。

    ComfyUIProvider(ABC).submit(graph, *, user_id, run_id) -> {"task_id"} | {"error"}
    ComfyUIProvider.poll(task_id)                          -> {"status", "outputs":[url..], "error"?}
        status ∈ {"running","completed","failed"}

三个实现:
    SelfHostedComfyUIProvider —— 境内 GPU 自建实例(**默认**,数据不出境)。POST /prompt → prompt_id;
                                 GET /history/{id} 取产物。
    RunningHubComfyUIProvider —— 境外托管 workflow-as-API(**opt-in**)。受 STRICT_CROSS_BORDER_REJECT
                                 默认拦截(comfyui_provider_blocked);二次同意 UI 属 P3,当前为「默认禁用」。
    FixtureComfyUIProvider    —— 无 GPU 的确定性占位实现:submit 先用 compiler 校验图(把编译错误前移),
                                 poll 立即返回占位产物。让 编译/队列/成本/WS 全链在无 GPU 时也可端到端跑通+可测。

合规:factory 纯路由(不放合规逻辑,保持路由测试干净);跨境拦截在「使用点」由
comfyui_provider_blocked() 判定 —— 与 generation.cross_border_image_blocked 同款 seam。
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod

import httpx

from agent.comfyui.compiler import (
    TARGET_RUNNINGHUB,
    TARGET_SELFHOSTED,
    CompileError,
    compile_graph,
)

# 1×1 半透明 PNG(占位产物)。fixture 产出可直接在前端 <img> 渲染,且不依赖外部网络/S3。
_FIXTURE_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


class ComfyUIProvider(ABC):
    """提交整图执行 + 轮询产物。错误以 {"error": str} 返回,绝不抛(worker 可记账/重试)。"""

    name: str = "base"

    @abstractmethod
    async def submit(self, graph: dict, *, user_id: str, run_id: str) -> dict:
        """提交计算图,返回 {"task_id": ...} 或 {"error": ...}。"""

    @abstractmethod
    async def poll(self, task_id: str) -> dict:
        """轮询一次,返回 {"status": running|completed|failed, "outputs": [url..], "error"?}。"""


# ── SelfHosted(境内,默认) ──────────────────────────────────────────────────────


class SelfHostedComfyUIProvider(ComfyUIProvider):
    name = "selfhosted"

    def __init__(self):
        from agent import config

        self._base = (config.COMFYUI_BASE_URL or "http://127.0.0.1:8188").rstrip("/")

    async def submit(self, graph: dict, *, user_id: str, run_id: str) -> dict:
        try:
            prompt = compile_graph(graph, target=TARGET_SELFHOSTED)
        except CompileError as e:
            return {"error": f"图编译失败({e.code}): {e.message}"}
        body = {"prompt": prompt, "client_id": run_id or uuid.uuid4().hex}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base}/prompt", json=body)
                data = resp.json()
        except Exception as e:  # noqa: BLE001 — provider 错误以 dict 返回
            return {"error": f"ComfyUI 提交失败: {e}"}
        if resp.status_code != 200:
            return {"error": f"ComfyUI 提交失败 {resp.status_code}: {data}"}
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return {"error": f"ComfyUI 未返回 prompt_id: {data}"}
        return {"task_id": prompt_id}

    async def poll(self, task_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{self._base}/history/{task_id}")
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"status": "running", "outputs": [], "error": f"轮询异常: {e}"}
        entry = data.get(task_id) if isinstance(data, dict) else None
        if not entry:
            return {"status": "running", "outputs": []}
        status = (entry.get("status") or {})
        if status.get("status_str") == "error":
            return {"status": "failed", "outputs": [], "error": "ComfyUI 执行报错"}
        outputs: list[str] = []
        for node_out in (entry.get("outputs") or {}).values():
            for img in node_out.get("images", []) or []:
                fn = img.get("filename")
                if not fn:
                    continue
                sub = img.get("subfolder", "")
                typ = img.get("type", "output")
                outputs.append(f"{self._base}/view?filename={fn}&subfolder={sub}&type={typ}")
        if outputs:
            return {"status": "completed", "outputs": outputs}
        # history 有条目但还没图 → 仍在跑
        return {"status": "running", "outputs": []}


# ── RunningHub(境外,opt-in,默认禁用) ──────────────────────────────────────────


class RunningHubComfyUIProvider(ComfyUIProvider):
    name = "runninghub"

    def __init__(self):
        from agent import config

        self._base = (config.RUNNINGHUB_BASE_URL or "https://www.runninghub.ai").rstrip("/")
        self._key = config.RUNNINGHUB_API_KEY or ""

    async def submit(self, graph: dict, *, user_id: str, run_id: str) -> dict:
        if not self._key:
            return {"error": "RunningHub 未配置 API key"}
        try:
            payload = compile_graph(graph, target=TARGET_RUNNINGHUB)
        except CompileError as e:
            return {"error": f"图编译失败({e.code}): {e.message}"}
        if not payload.get("workflowId"):
            return {"error": "RunningHub 需要 workflowId(种子图未提供,P3 接线)"}
        body = {"apiKey": self._key, **payload}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._base}/task/openapi/create", json=body)
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"error": f"RunningHub 提交失败: {e}"}
        task_id = (data.get("data") or {}).get("taskId") if isinstance(data, dict) else None
        if not task_id:
            return {"error": f"RunningHub 未返回 taskId: {data}"}
        return {"task_id": str(task_id)}

    async def poll(self, task_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/task/openapi/outputs",
                    json={"apiKey": self._key, "taskId": task_id},
                )
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            return {"status": "running", "outputs": [], "error": f"轮询异常: {e}"}
        records = (data.get("data") or []) if isinstance(data, dict) else []
        outputs = [r.get("fileUrl") for r in records if r.get("fileUrl")]
        if outputs:
            return {"status": "completed", "outputs": outputs}
        return {"status": "running", "outputs": []}


# ── Fixture(无 GPU,确定性占位) ─────────────────────────────────────────────────


class FixtureComfyUIProvider(ComfyUIProvider):
    """确定性占位 provider:submit 先 compiler 校验(把编译错误前移),poll 立即返回占位图。

    用于无 GPU 时把 编译→队列→成本→WS 全链端到端跑通 + 写测。结果在内存(进程内,够单测/dev)。
    """

    name = "fixture"
    _pending: dict[str, dict] = {}
    _seq: int = 0

    async def submit(self, graph: dict, *, user_id: str, run_id: str) -> dict:
        try:
            # 走真编译以暴露非法图(与 SelfHosted 同款失败语义)。
            compile_graph(graph, target=TARGET_SELFHOSTED)
        except CompileError as e:
            return {"error": f"图编译失败({e.code}): {e.message}"}
        FixtureComfyUIProvider._seq += 1
        task_id = f"fixture-{FixtureComfyUIProvider._seq}"
        FixtureComfyUIProvider._pending[task_id] = {
            "status": "completed",
            "outputs": [_FIXTURE_PNG_DATA_URL],
        }
        return {"task_id": task_id}

    async def poll(self, task_id: str) -> dict:
        return FixtureComfyUIProvider._pending.get(
            task_id, {"status": "failed", "outputs": [], "error": "fixture: 无此任务"}
        )


# ── 合规闸 + 工厂 ────────────────────────────────────────────────────────────────

# 境外 provider 集合(数据出境)。selfhosted/fixture 境内,不在内。
_CROSS_BORDER_COMFYUI_PROVIDERS = {"runninghub"}


def comfyui_provider_blocked(name: str | None) -> bool:
    """STRICT_CROSS_BORDER_REJECT 开(默认)时,该 ComfyUI provider 是否因跨境被禁。

    用在 Run 入口(handle_pro_run_submit)即时拒绝跨境执行 —— 与 generation.cross_border_image_blocked
    同款「factory 纯路由、合规在使用点拦」约定。动态读 config 以便 env 变更/测试 monkeypatch 生效。
    注:二次同意/opt-in 解锁路径属 P3,当前为「跨境=默认禁用」的二元闸。"""
    from agent import config

    return config.STRICT_CROSS_BORDER_REJECT and (name or "").lower() in _CROSS_BORDER_COMFYUI_PROVIDERS


def get_comfyui_provider(name: str | None = None) -> ComfyUIProvider:
    """按 config.COMFYUI_PROVIDER(或显式 name)返回 provider(动态读 config,resp env/测试)。

    纯路由,无合规逻辑(合规在 comfyui_provider_blocked 使用点拦)。未知 → SelfHosted(境内兜底)。"""
    from agent import config

    p = (name or config.COMFYUI_PROVIDER or "selfhosted").lower()
    if p == "fixture":
        return FixtureComfyUIProvider()
    if p == "runninghub":
        return RunningHubComfyUIProvider()
    return SelfHostedComfyUIProvider()


def comfyui_ready(name: str | None = None) -> bool:
    """当前 ComfyUI provider 是否就绪(密钥/地址)。fixture 恒就绪;selfhosted 看 base_url;
    runninghub 看 key。动态读 config。"""
    from agent import config

    p = (name or config.COMFYUI_PROVIDER or "selfhosted").lower()
    if p == "fixture":
        return True
    if p == "runninghub":
        return bool(str(config.RUNNINGHUB_API_KEY or "").strip())
    return bool(str(config.COMFYUI_BASE_URL or "").strip())
