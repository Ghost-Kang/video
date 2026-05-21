# Claude handoff — P1-6 anchor backend

**Owner**: Claude session
**Source of truth**: `01_phase1_requirements.md` P1-6 · `02_event_spec.md` events #6, #7 · `topic_intelligence.AccountFit` (for future Phase 2 use)
**Time budget**: 2 days

---

## 0. What you build

The "你之前用过的" backend. A creator who created a character image or scene image in run #1 can drag-drop it into run #2's ShotCard. This is THE load-bearing learning-loop signal (Reviewer Synthesis §5 — H8 moat thesis).

---

## 1. Files

| Path | Purpose |
|---|---|
| `backend/src/agent/cascade/anchors.py` | The anchor service + types |
| `backend/tests/test_anchors.py` | Tests for create/list/reuse |

Hook into `server.py` to add `GET /api/anchors`, `POST /api/anchors`, `POST /api/anchors/<id>/reuse`.

---

## 2. Schema (SQLite)

```sql
CREATE TABLE IF NOT EXISTS anchors (
  id            TEXT PRIMARY KEY,        -- ULID: "anc_..."
  user_id       TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('character', 'scene')),
  label         TEXT NOT NULL,           -- 用户起的名字, e.g. "小张妈妈"
  image_url     TEXT NOT NULL,
  source_run_id TEXT,                    -- the run that created this anchor
  source_shot_index INT,                 -- which shot in that run
  reuse_count   INT NOT NULL DEFAULT 0,  -- ← H8 measurement
  created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_anchors_user_kind ON anchors(user_id, kind, created_at DESC);

CREATE TABLE IF NOT EXISTS anchor_reuses (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  anchor_id     TEXT NOT NULL REFERENCES anchors(id),
  reused_in_run_id TEXT NOT NULL,
  reused_in_shot_index INT,
  reused_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_anchor_reuses_anchor ON anchor_reuses(anchor_id, reused_at DESC);
```

---

## 3. Pydantic types (in `anchors.py`)

```python
class AnchorKind(str, Enum):
    CHARACTER = "character"
    SCENE = "scene"

class Anchor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^anc_[A-Za-z0-9_]+$")
    user_id: str
    kind: AnchorKind
    label: str = Field(..., min_length=1, max_length=40)
    image_url: HttpUrl
    source_run_id: Optional[str] = None
    source_shot_index: Optional[int] = Field(None, ge=1)
    reuse_count: int = Field(..., ge=0)
    created_at: datetime
```

---

## 4. API contracts

### `GET /api/anchors?user_id=...&kind=character|scene`

Returns: `{anchors: Anchor[]}`. Sorted by `(reuse_count DESC, created_at DESC)` so most-used surface first.

### `POST /api/anchors`

Body: `{user_id, kind, label, image_url, source_run_id?, source_shot_index?}`

Returns: `Anchor` with generated ULID. Emits `anchor_created` event:
```json
{
  "anchor_id": "anc_...",
  "kind": "character",
  "source_run_id": "run_..."
}
```

### `POST /api/anchors/<id>/reuse`

Body: `{user_id, reused_in_run_id, reused_in_shot_index?}`

Behavior: Increments `anchors.reuse_count`. Inserts row in `anchor_reuses`. Emits `anchor_reused` event:
```json
{
  "anchor_id": "anc_...",
  "anchor_kind": "character",
  "anchor_label": "小张妈妈",
  "source_run_id": "run_001",
  "reused_in_run_id": "run_007",
  "is_first_reuse_for_user": true,
  "days_since_creation": 3
}
```

`is_first_reuse_for_user` is critical for H8 measurement — true only if this is the user's FIRST `anchor_reused` event ever. Compute by counting events for `user_id`.

---

## 5. Tests (`test_anchors.py`)

1. Create anchor → POST returns 200; row in `anchors`; `anchor_created` event emitted
2. Label too long (>40) → 400, no row, no event
3. Wrong kind value → 400
4. List by user_id returns only that user's anchors (multi-user isolation)
5. List sorted by reuse_count DESC then created_at DESC
6. Reuse twice → reuse_count = 2; two rows in `anchor_reuses`; two `anchor_reused` events
7. `is_first_reuse_for_user` true on first reuse, false on subsequent
8. `days_since_creation` computed correctly
9. Reusing nonexistent anchor → 404
10. Reusing across users (user A's anchor referenced by user B) → 403 (anchor ownership enforced)

---

## 6. Done-signal

- `find backend/src/agent/cascade/anchors.py backend/tests/test_anchors.py | wc -l` = 2
- `uv run pytest tests/test_anchors.py` passes
- `sqlite3 backend/data/messages.db ".tables" | grep -c anchor` = 2 (anchors + anchor_reuses)
- A scripted end-to-end (POST anchor, POST reuse) shows both events in `events` table

---

## 7. NOT in this ticket

- Frontend sidebar (Cursor P1-6 brief)
- Anchor visibility on ShotCard during creation (P1-4 brief)
- Anchor injection into the rewrite prompt (Phase 2 P1-3 enhancement)
- 三视图 anchor (Phase 2)
