"""ComfyUI Provider 单测:fixture / 工厂路由 / 跨境闸 / self-host(mock httpx)。"""

from __future__ import annotations

import asyncio

from agent import config
from agent.comfyui import provider as prov


def _graph():
    return {
        "version": 1,
        "nodes": [
            {"id": "m", "type": "Model"},
            {"id": "p", "type": "Prompt", "params": {"text": "猫"}},
            {"id": "g", "type": "Generate"},
            {"id": "v", "type": "Preview"},
        ],
        "edges": [
            {"id": "1", "source": "m", "sourceHandle": "model", "target": "g", "targetHandle": "model"},
            {"id": "2", "source": "p", "sourceHandle": "text", "target": "g", "targetHandle": "positive"},
            {"id": "3", "source": "g", "sourceHandle": "image", "target": "v", "targetHandle": "image"},
        ],
    }


# ── fixture ─────────────────────────────────────────────────────────────────────


def test_fixture_submit_poll_roundtrip():
    p = prov.FixtureComfyUIProvider()
    sub = asyncio.run(p.submit(_graph(), user_id="u1", run_id="r1"))
    assert "task_id" in sub
    res = asyncio.run(p.poll(sub["task_id"]))
    assert res["status"] == "completed"
    assert res["outputs"] and res["outputs"][0].startswith("data:image/png")


def test_fixture_submit_rejects_bad_graph():
    p = prov.FixtureComfyUIProvider()
    sub = asyncio.run(p.submit({"nodes": [], "edges": []}, user_id="u", run_id="r"))
    assert "error" in sub
    assert "编译失败" in sub["error"]


def test_fixture_poll_unknown_task():
    p = prov.FixtureComfyUIProvider()
    res = asyncio.run(p.poll("nope"))
    assert res["status"] == "failed"


# ── factory routing ─────────────────────────────────────────────────────────────


def test_get_comfyui_provider_routes(monkeypatch):
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "fixture")
    assert isinstance(prov.get_comfyui_provider(), prov.FixtureComfyUIProvider)
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "runninghub")
    assert isinstance(prov.get_comfyui_provider(), prov.RunningHubComfyUIProvider)
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "selfhosted")
    assert isinstance(prov.get_comfyui_provider(), prov.SelfHostedComfyUIProvider)
    # unknown -> selfhosted fallback
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "bogus")
    assert isinstance(prov.get_comfyui_provider(), prov.SelfHostedComfyUIProvider)
    # explicit name overrides config
    assert isinstance(prov.get_comfyui_provider("fixture"), prov.FixtureComfyUIProvider)


# ── cross-border gate ───────────────────────────────────────────────────────────


def test_comfyui_provider_blocked_runninghub_when_strict(monkeypatch):
    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", True)
    assert prov.comfyui_provider_blocked("runninghub") is True
    assert prov.comfyui_provider_blocked("selfhosted") is False
    assert prov.comfyui_provider_blocked("fixture") is False


def test_comfyui_provider_unblocked_when_strict_off(monkeypatch):
    monkeypatch.setattr(config, "STRICT_CROSS_BORDER_REJECT", False)
    assert prov.comfyui_provider_blocked("runninghub") is False


def test_comfyui_ready(monkeypatch):
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "fixture")
    assert prov.comfyui_ready() is True
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "runninghub")
    monkeypatch.setattr(config, "RUNNINGHUB_API_KEY", "")
    assert prov.comfyui_ready() is False
    monkeypatch.setattr(config, "RUNNINGHUB_API_KEY", "k")
    assert prov.comfyui_ready() is True
    monkeypatch.setattr(config, "COMFYUI_PROVIDER", "selfhosted")
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://127.0.0.1:8188")
    assert prov.comfyui_ready() is True


# ── self-host (mock httpx) ──────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, *, post=None, get=None):
        self._post = post
        self._get = get

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, *, json=None):
        return self._post

    async def get(self, url):
        return self._get


def test_selfhosted_submit_ok(monkeypatch):
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://gpu:8188")
    monkeypatch.setattr(
        prov.httpx, "AsyncClient", lambda *a, **k: _FakeClient(post=_Resp(200, {"prompt_id": "pid-1"}))
    )
    p = prov.SelfHostedComfyUIProvider()
    res = asyncio.run(p.submit(_graph(), user_id="u", run_id="r"))
    assert res == {"task_id": "pid-1"}


def test_selfhosted_submit_compile_error_no_http(monkeypatch):
    # bad graph -> compile error returned, never hits httpx
    def _boom(*a, **k):
        raise AssertionError("httpx should not be called for a bad graph")

    monkeypatch.setattr(prov.httpx, "AsyncClient", _boom)
    p = prov.SelfHostedComfyUIProvider()
    res = asyncio.run(p.submit({"nodes": [], "edges": []}, user_id="u", run_id="r"))
    assert "error" in res


def test_selfhosted_poll_completed(monkeypatch):
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://gpu:8188")
    history = {
        "pid-1": {
            "status": {"status_str": "success"},
            "outputs": {"9": {"images": [{"filename": "a.png", "subfolder": "", "type": "output"}]}},
        }
    }
    monkeypatch.setattr(prov.httpx, "AsyncClient", lambda *a, **k: _FakeClient(get=_Resp(200, history)))
    p = prov.SelfHostedComfyUIProvider()
    res = asyncio.run(p.poll("pid-1"))
    assert res["status"] == "completed"
    assert res["outputs"] == ["http://gpu:8188/view?filename=a.png&subfolder=&type=output"]


def test_selfhosted_poll_running_when_absent(monkeypatch):
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://gpu:8188")
    monkeypatch.setattr(prov.httpx, "AsyncClient", lambda *a, **k: _FakeClient(get=_Resp(200, {})))
    p = prov.SelfHostedComfyUIProvider()
    res = asyncio.run(p.poll("pid-1"))
    assert res["status"] == "running"


class _UploadResp:
    def __init__(self, status_code, data=None, content=b""):
        self.status_code = status_code
        self._data = data or {}
        self.content = content

    def json(self):
        return self._data


class _RoutingClient:
    """按 URL 路由:GET 任意=下图;POST /upload/image=上传;POST /prompt=提交(捕获 body)。"""

    def __init__(self, captured):
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        return _UploadResp(200, content=b"IMGDATA")

    async def post(self, url, *, json=None, files=None, data=None):
        if url.endswith("/upload/image"):
            return _UploadResp(200, {"name": "uploaded.png", "subfolder": ""})
        if url.endswith("/prompt"):
            self._captured["prompt"] = json["prompt"]
            return _UploadResp(200, {"prompt_id": "pid-up"})
        return _UploadResp(404, {})


def test_selfhosted_uploads_url_loadimage(monkeypatch):
    # 真 ComfyUI:LoadImage 的 http URL 提交前上传 → 文件名被改写,/prompt 收到的是已上传名(非 URL)。
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://gpu:8188")
    captured: dict = {}
    monkeypatch.setattr(prov.httpx, "AsyncClient", lambda *a, **k: _RoutingClient(captured))
    graph = {
        "version": 1,
        "nodes": [
            {"id": "li", "type": "LoadImage", "params": {"image_url": "http://x/a.png"}},
            {"id": "pv", "type": "Preview", "params": {}},
        ],
        "edges": [{"id": "1", "source": "li", "sourceHandle": "image", "target": "pv", "targetHandle": "image"}],
    }
    res = asyncio.run(prov.SelfHostedComfyUIProvider().submit(graph, user_id="u", run_id="r"))
    assert res == {"task_id": "pid-up"}
    loadimage = [n for n in captured["prompt"].values() if n.get("class_type") == "LoadImage"]
    assert loadimage and loadimage[0]["inputs"]["image"] == "uploaded.png"  # URL → 上传名


def test_selfhosted_poll_video_gifs(monkeypatch):
    # 视频产物在 history 的 gifs 键(VHS 等)→ poll 也要收。
    monkeypatch.setattr(config, "COMFYUI_BASE_URL", "http://gpu:8188")
    history = {"pid-1": {"status": {"status_str": "success"},
                         "outputs": {"9": {"gifs": [{"filename": "v.webp", "subfolder": "", "type": "output"}]}}}}
    monkeypatch.setattr(prov.httpx, "AsyncClient", lambda *a, **k: _FakeClient(get=_Resp(200, history)))
    res = asyncio.run(prov.SelfHostedComfyUIProvider().poll("pid-1"))
    assert res["status"] == "completed"
    assert "v.webp" in res["outputs"][0]


def test_runninghub_submit_requires_key(monkeypatch):
    monkeypatch.setattr(config, "RUNNINGHUB_API_KEY", "")
    p = prov.RunningHubComfyUIProvider()
    res = asyncio.run(p.submit(_graph(), user_id="u", run_id="r"))
    assert "error" in res and "key" in res["error"].lower()
