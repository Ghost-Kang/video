# Codex handoff — P3-R2 LLM provider switch (Doubao default + Gemini fallback)

**Owner**: Codex session
**Source of truth**: `docs/nexus/04_compliance_check.md` (Doubao = 境内 = PIPL §38 不触发) + fixture model field (`doubao-seed-2-0-pro` already documented intent)
**Status**: ready to execute, blocking nothing else
**Time budget**: 1.5-2h (4 call sites + config + dependency wiring + sanity smoke)
**Why**: spec/fixtures/code drifted — spec says Doubao for compliance, fixtures recorded as Doubao, but live code calls Gemini. Switching also unblocks P3-1 (LLM eval baseline) without waiting on `GOOGLE_API_KEY`.

---

## 0. The pattern

Introduce a `LLM_PROVIDER` env toggle and a thin factory function. All 4 call sites read the factory; no call site touches provider-specific libraries directly.

```python
# backend/src/agent/llm_factory.py  (new file)
from __future__ import annotations
from agent import config

def get_chat_model():
    """Return a LangChain BaseChatModel honoring LLM_PROVIDER env.

    doubao → langchain_openai.ChatOpenAI with ARK base_url + DOUBAO_MODEL
    gemini → langchain_google_genai.ChatGoogleGenerativeAI with LLM_MODEL
    """
    provider = config.LLM_PROVIDER.lower().strip()
    if provider == "doubao":
        from langchain_openai import ChatOpenAI
        if not config.ARK_API_KEY:
            raise RuntimeError("LLM_PROVIDER=doubao but ARK_API_KEY missing")
        return ChatOpenAI(
            model=config.DOUBAO_MODEL,
            base_url=config.ARK_BASE_URL,
            api_key=config.ARK_API_KEY,
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not (config.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY")):
            raise RuntimeError("LLM_PROVIDER=gemini but GOOGLE_API_KEY missing")
        return ChatGoogleGenerativeAI(model=config.LLM_MODEL)
    raise RuntimeError(f"unknown LLM_PROVIDER={provider!r}; expected doubao|gemini")


def current_model_name() -> str:
    """For event payloads / eval reports — the actual model string used."""
    p = config.LLM_PROVIDER.lower().strip()
    return config.DOUBAO_MODEL if p == "doubao" else config.LLM_MODEL
```

---

## 1. Config changes (`backend/src/agent/config.py`)

Add to the `# -------- LLM --------` block:

```python
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "doubao").strip().lower()
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = os.getenv("DOUBAO_MODEL", "doubao-seed-2-0-pro")
```

Keep existing `GOOGLE_API_KEY` and `LLM_MODEL` untouched (still used when `LLM_PROVIDER=gemini`).

---

## 2. Call site migrations (4 files)

All 4 sites replace `ChatGoogleGenerativeAI(...)` instantiation with `from agent.llm_factory import get_chat_model; model = get_chat_model()`. The `.invoke([...])` interface is identical between LangChain `ChatGoogleGenerativeAI` and `ChatOpenAI`, so no downstream changes.

| File | Line | Action |
|---|---|---|
| `backend/src/agent/cascade/rewrite.py` | 289-295 | Replace import + instantiation. Keep everything else. The `result.model = ...` field should now record `current_model_name()` |
| `backend/src/agent/cascade/eval/judge.py` | 64-65, 87, 104 | (a) env-check: replace `os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")` with `config.ARK_API_KEY if provider=="doubao" else (GOOGLE_API_KEY or GEMINI_API_KEY)` — cleanest: just call `get_chat_model()` inside a try/except, catch `RuntimeError`, return skipped sentinel. (b) Replace instantiation as above. |
| `backend/src/agent/server.py` | 10, 66 | Same import + instantiation swap |
| `backend/src/agent/main.py` | 18, 49 | Same |

**Important**: `tools/generation.py:132` (image gen via Google) is **NOT in scope**. Image gen has its own provider abstraction (Apimart default per `IMAGE_GEN_PROVIDER`). Leave `genai.Client(api_key=GOOGLE_API_KEY)` alone — it only activates when `IMAGE_GEN_PROVIDER=google`.

---

## 3. Dependency

Add to `backend/pyproject.toml` (likely already present — verify):

```
langchain-openai = ">=0.2.0"
```

If `langchain-openai` is already pulled in transitively, just confirm; no version pin change needed.

`langchain-google-genai` stays — it's the fallback provider library.

---

## 4. Eval report model field (`cascade/eval/report.py:59`)

```python
# was
model: str  # e.g. gemini-3-flash-preview
# update comment to reflect both providers
model: str  # e.g. doubao-seed-2-0-pro | gemini-3-flash-preview
```

No structural change — `current_model_name()` already fills it correctly.

---

## 5. Endpoint ID vs model name (founder-provided value caveat)

Founder shared (2026-05-22) the value `DOUBAO_ENDPOINT_ID=Doubao-Seed-2.0-pro` — note the capital letters and dots. This looks like a console **display name**, not the typical endpoint ID format (`ep-2026XXXXXXXX-xxxxx` lowercase + hyphens) nor the model ID format (`doubao-seed-2-0-pro` lowercase + hyphens).

**ARK accepts both endpoint IDs and model IDs in the `model:` request field**. Codex should test in this order:

1. First try the lowercase canonical form `doubao-seed-2-0-pro` (this matches what every fixture file already records — `fixtures/rewrite_smoke/*/model = "doubao-seed-2-0-pro"`)
2. If ARK returns model-not-found, fall back to the verbatim string founder provided
3. If both fail, ask founder to grab the actual `ep-XXXX` endpoint id from the console

The brief currently spells `DOUBAO_MODEL=doubao-seed-2-0-pro` in `.env.example` per step 1 — best default.

---

## 6. Files (final list)

| Path | Change |
|---|---|
| `backend/src/agent/config.py` | add LLM_PROVIDER + ARK_* + DOUBAO_MODEL |
| `backend/src/agent/llm_factory.py` | **new** — factory + current_model_name |
| `backend/src/agent/cascade/rewrite.py` | swap import + instantiation, use current_model_name |
| `backend/src/agent/cascade/eval/judge.py` | swap import + env check + instantiation |
| `backend/src/agent/server.py` | swap import + instantiation |
| `backend/src/agent/main.py` | swap import + instantiation |
| `backend/src/agent/cascade/eval/report.py:59` | comment refresh only |
| `backend/pyproject.toml` | confirm/add `langchain-openai` |
| `backend/tests/test_llm_factory.py` | **new** — 3 cases below |

---

## 7. Test surface

`backend/tests/test_llm_factory.py`:

```python
def test_factory_returns_doubao_when_provider_doubao(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "doubao")
    monkeypatch.setenv("ARK_API_KEY", "fake")
    # reload config + factory
    # assert isinstance(model, ChatOpenAI) AND model.openai_api_base startswith ARK
    # do NOT actually call .invoke — would hit real API

def test_factory_returns_gemini_when_provider_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake")
    # assert isinstance(model, ChatGoogleGenerativeAI)

def test_factory_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "doubao")
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ARK_API_KEY missing"):
        get_chat_model()
```

Existing rewrite + judge tests already mock out the upstream call (they don't hit a real API), so they should pass unchanged. **Verify** by running:

```bash
cd backend && uv run pytest tests/test_rewrite.py tests/test_analysis_service.py tests/test_cascade_contract.py -q
```

All green = no regression. If anything fails, it's almost certainly a mock assuming the Gemini class — swap to mocking `agent.llm_factory.get_chat_model` instead.

---

## 8. Sanity smoke (Codex runs after PR ready, founder reviews)

Once `.env` has `ARK_API_KEY` + `DOUBAO_MODEL`, manually:

```bash
cd backend && uv run python -c "
from agent.llm_factory import get_chat_model
m = get_chat_model()
r = m.invoke([{'role': 'user', 'content': '说一句:OpenRHTV 接入 Doubao 成功'}])
print(r.content if hasattr(r, 'content') else r)
"
```

Expected: non-error response in Chinese. If 400/401, key/endpoint issue → check §5.

Then re-run P2-4 smoke against synthetic fixtures (NOT real fixtures, founder hasn't shipped those yet):

```bash
cd backend && uv run python scripts/p2-4_run_real_urls.py --mode llm --fixture-source synthetic 2>&1 | tail -40
```

Expected: similar mechanical_pass_rate to the Gemini baseline (within ±5%). Style/realism may differ slightly — that's expected provider drift, NOT a regression. **Not** a re-signoff trigger; we only re-signoff after real_v1 fixtures land (P0-C).

---

## 9. Done-signal

- `LLM_PROVIDER=doubao bash -c 'cd backend && uv run pytest tests/ -q'` all pass
- `LLM_PROVIDER=gemini bash -c 'cd backend && uv run pytest tests/ -q'` all pass (both providers green)
- Sanity smoke (§8) shows Doubao live call succeeds with non-error response
- `grep -rn "ChatGoogleGenerativeAI\|langchain_google_genai" backend/src/agent/cascade backend/src/agent/server.py backend/src/agent/main.py` returns **only** in `llm_factory.py` (no direct calls anywhere else)
- New `llm_factory.py` exists with `get_chat_model` + `current_model_name` exports
- `.env.example` already updated by PM (2026-05-22) — Codex does not touch it

---

## 10. NOT in this ticket

- Streaming / async support (current code is all `.invoke()` sync; matches today's pattern)
- Doubao function calling / tool use (Phase 2 if needed)
- Image gen provider switch (separate path; Apimart default; out of scope)
- Auto-failover Doubao → Gemini on Doubao 5xx (deferred; `LLM_PROVIDER` is manual toggle for now)
- Cost tracking per provider (separate ticket — Doubao pricing is per-token, similar shape but different rates)
- Re-running P2-4 qualitative signoff (only when real_v1 fixtures land; sanity smoke in §8 is enough for now)

---

## 11. PM notes

- This unblocks P3-1 (LLM eval baseline) — judge.py now works with `ARK_API_KEY` set
- This consumes part of P0-R: compliance #1 用户协议 can drop the "境外 Gemini" clause; compliance #3 跨境 hard block becomes belt-and-suspenders (Doubao means no LLM-side cross-border; the W9 host check is now just defensive)
- Maintains zero rollback cost — `LLM_PROVIDER=gemini` in `.env` restores old behavior
- Carry the [[pm-4-owner-allocation-rule]] — this is the 2nd Codex W3D1+ workitem alongside P3-R1

**Recommended sequence**: P3-R2 first (faster, smaller), then P3-R1 (3 sub-tickets). Or batch both into one Codex session — they touch different files.
