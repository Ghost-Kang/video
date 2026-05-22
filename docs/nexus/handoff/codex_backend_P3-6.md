# Codex handoff — P3-6 `/api/anchors/<id>/reuses` endpoint

**Owner**: Codex session
**Source of truth**: `claude_backend_P1-6.md` (anchors backend) · existing `anchor_reuses` table in `storage.py` · `claude_frontend_P2-5.md §6 NOT in this ticket` (defers `days_since_last_reuse`)
**Status**: ready — all dependencies (P1-6 anchors backend, `anchor_reuses` table) shipped in W1
**Time budget**: 0.5 days (small CRUD endpoint with focused test surface)

---

## 0. What you build

Expose the existing `anchor_reuses` table via a read-only HTTP endpoint so the frontend can:
1. **P2-5 follow-up**: show `days_since_last_reuse` on each `AnchorCard` tooltip
2. **P3-5 drill-down**: clicking an anchor in `/analytics/anchors` shows its reuse timeline
3. **Future P4 dashboard**: per-anchor reuse charts

This is a small ticket but it's a frequently-referenced gap in P2-5 / P3-5 briefs ("blocked on `/api/anchors/<id>/reuses`"). Knocking it out unlocks polish on both.

---

## 1. Files

| Path | Change |
|---|---|
| `backend/src/agent/cascade/anchors.py` | new `list_reuses(anchor_id, user_id)` async function |
| `backend/src/agent/server.py` | new `GET /api/anchors/<id>/reuses?user_id=...` route |
| `backend/tests/test_anchors.py` | extend with reuse-list cases OR new file `test_anchor_reuses_endpoint.py` |
| (No frontend in this ticket — P3-5 / P2-5 follow-up tickets consume the endpoint later) |

---

## 2. Backend contract

### Endpoint

```
GET /api/anchors/<anchor_id>/reuses?user_id=<u>
```

### Behavior

1. Look up anchor by `anchor_id`
2. If not found → `404 {"error": "anchor not found"}`
3. If anchor's `user_id` != query `user_id` → `403 {"error": "anchor belongs to a different user"}` (same ownership semantics as `POST /api/anchors/<id>/reuse`)
4. Otherwise return all rows from `anchor_reuses` table for this anchor, newest first

### Response shape

```json
{
  "anchor_id": "anc_...",
  "anchor_label": "小张妈妈",
  "anchor_kind": "character",
  "reuse_count": 3,
  "reuses": [
    {
      "reused_in_run_id": "run_007",
      "reused_in_shot_index": 3,
      "reused_at": "2026-05-21T08:00:00Z"
    },
    {
      "reused_in_run_id": "run_005",
      "reused_in_shot_index": 1,
      "reused_at": "2026-05-19T14:30:00Z"
    }
  ],
  "days_since_last_reuse": 0,
  "days_since_created": 4
}
```

Top-level convenience fields (`days_since_last_reuse`, `days_since_created`) are computed server-side so the frontend doesn't need to do timestamp math.

---

## 3. Implementation sketch (anchors.py)

Mirror the existing `list_anchors` shape:

```python
async def list_reuses(*, anchor_id: str, user_id: str) -> dict:
    db = await _connect()
    try:
        rows = await db.execute_fetchall(
            "SELECT user_id, kind, label, reuse_count, created_at "
            "FROM anchors WHERE id = ?",
            (anchor_id,),
        )
        if not rows:
            raise LookupError(f"anchor not found: {anchor_id}")
        owner, kind, label, reuse_count, created_at = rows[0]
        if owner != user_id:
            raise PermissionError(f"anchor {anchor_id} belongs to a different user")

        reuse_rows = await db.execute_fetchall(
            "SELECT reused_in_run_id, reused_in_shot_index, reused_at "
            "FROM anchor_reuses WHERE anchor_id = ? ORDER BY reused_at DESC",
            (anchor_id,),
        )
    finally:
        await db.close()

    # Time math
    from datetime import datetime, timezone
    created_dt = datetime.fromisoformat(created_at)
    last_reused_at = reuse_rows[0][2] if reuse_rows else None
    days_since_created = max(0, (datetime.now(timezone.utc) - created_dt).days)
    days_since_last_reuse = (
        max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(last_reused_at)).days)
        if last_reused_at
        else days_since_created
    )

    return {
        "anchor_id": anchor_id,
        "anchor_label": label,
        "anchor_kind": kind,
        "reuse_count": reuse_count,
        "reuses": [
            {
                "reused_in_run_id": row[0],
                "reused_in_shot_index": row[1],
                "reused_at": row[2],
            }
            for row in reuse_rows
        ],
        "days_since_last_reuse": days_since_last_reuse,
        "days_since_created": days_since_created,
    }
```

### server.py wiring

Add **before** the existing `POST /api/anchors/<id>/reuse` handler (more specific path):

```python
elif method == "GET" and path.startswith("/api/anchors/") and path.endswith("/reuses"):
    anchor_id = path[len("/api/anchors/"):-len("/reuses")]
    user_id = qs.get("user_id", ["default"])[0]
    try:
        payload = await list_reuses(anchor_id=anchor_id, user_id=user_id)
    except LookupError as exc:
        writer.write(_http_response(404, {"error": str(exc)}, "Not Found"))
        await writer.drain()
        return
    except PermissionError as exc:
        writer.write(_http_response(403, {"error": str(exc)}, "Forbidden"))
        await writer.drain()
        return
    writer.write(_http_response(200, payload))
```

---

## 4. Tests

Extend `backend/tests/test_anchors.py` with these cases (or split out to `test_anchor_reuses_endpoint.py`):

1. **Empty reuses** — newly created anchor, never reused → `reuses=[]`, `reuse_count=0`, `days_since_last_reuse == days_since_created`
2. **Single reuse** — create anchor + reuse_anchor once → `reuses` has 1 row, `reuse_count=1`, `days_since_last_reuse=0` (just reused)
3. **Multiple reuses sorted newest-first** — 3 reuses across different dates → array sorted DESC by `reused_at`
4. **Anchor not found** — `LookupError` raised → server returns 404
5. **Cross-user reuse list** — user B tries to list user A's anchor → `PermissionError` → 403
6. **`days_since_last_reuse` after backdated reuse** — UPDATE the reuse's `reused_at` to 3 days ago → `days_since_last_reuse >= 3`

---

## 5. Done-signal

- `find backend/src/agent/cascade/anchors.py | xargs grep -c "list_reuses"` ≥ 1
- `grep -c "/api/anchors/.*reuses" backend/src/agent/server.py` ≥ 1
- `uv run pytest backend/tests/test_anchors.py -k reuses -q` ≥ 6 cases pass
- Manual curl smoke (with seeded data):
  ```
  curl localhost:8766/api/anchors/anc_XXX/reuses?user_id=u_test
  ```
  returns the expected JSON

---

## 6. NOT in this ticket

- Frontend integration (P2-5 follow-up will consume this)
- Pagination on reuses array — anchors typically have < 50 reuses in lifetime; cursor-based pagination is W4+ if usage warrants
- Cross-creator analytics (admin view) — separate P4 ticket
- Real-time updates (websocket subscription) — not needed for v1
- Rate limiting — handled at a different layer if cost guard expands

---

## 7. PM notes

- This is a small ticket but it has compound value: unlocks two existing frontend follow-up gaps (P2-5 + P3-5 drill-down) without a frontend rewrite.
- Codex's strength matches this perfectly: well-defined schema, test-heavy, no design judgment required.
- After this ships, file P3-5b (frontend) and P2-5b (anchor card tooltip) as Claude follow-ups consuming the endpoint.
