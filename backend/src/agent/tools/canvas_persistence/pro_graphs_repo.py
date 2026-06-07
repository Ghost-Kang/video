"""Pro 画布图持久化 —— 当前图(autosave,per user+thread)+ 具名模板(per user)。

图刷新即丢是 Pro 工具的硬伤(tldraw 无 persistenceKey、后端不存图);这里给「自动保存/恢复」+
「另存为模板/套用模板」兜底。graph_json 存原样(可为 WIP,不强制编译通过 —— 用户存草稿也要能存)。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from agent.tools.canvas_persistence.db import _db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── 当前图(autosave)──────────────────────────────────────────────────────────


def save_graph(*, user_id: str, thread_id: str, graph_json: str) -> None:
    """Upsert 该 (user, thread) 的当前图。"""
    db = _db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO pro_graphs (user_id, thread_id, graph_json, updated_at)
               VALUES (?,?,?,?)""",
            (user_id, thread_id, graph_json, _now()),
        )
        db.commit()
    finally:
        db.close()


def load_graph(*, user_id: str, thread_id: str) -> str | None:
    """该 (user, thread) 的当前图 JSON;无则 None。"""
    db = _db()
    try:
        row = db.execute(
            "SELECT graph_json FROM pro_graphs WHERE user_id=? AND thread_id=?",
            (user_id, thread_id),
        ).fetchone()
    finally:
        db.close()
    return row["graph_json"] if row else None


# ── 模板(另存为 / 套用)─────────────────────────────────────────────────────────


def save_template(*, user_id: str, name: str, graph_json: str) -> str:
    """存一个具名模板,返回 template_id。"""
    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    db = _db()
    try:
        db.execute(
            """INSERT INTO pro_graph_templates (user_id, template_id, name, graph_json, created_at)
               VALUES (?,?,?,?,?)""",
            (user_id, template_id, name, graph_json, _now()),
        )
        db.commit()
    finally:
        db.close()
    return template_id


def list_templates(*, user_id: str, limit: int = 50) -> list[dict]:
    """该 user 的模板列表(最新在前),不带 graph_json(列表轻量)。"""
    db = _db()
    try:
        rows = db.execute(
            """SELECT template_id, name, created_at FROM pro_graph_templates
               WHERE user_id=? ORDER BY rowid DESC LIMIT ?""",
            (user_id, int(limit)),
        ).fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]


def load_template(*, user_id: str, template_id: str) -> str | None:
    """模板的 graph JSON;无/越权则 None(user 维度隔离)。"""
    db = _db()
    try:
        row = db.execute(
            "SELECT graph_json FROM pro_graph_templates WHERE user_id=? AND template_id=?",
            (user_id, template_id),
        ).fetchone()
    finally:
        db.close()
    return row["graph_json"] if row else None


def delete_template(*, user_id: str, template_id: str) -> bool:
    """删模板(user 维度)。返回是否删到一行。"""
    db = _db()
    try:
        cur = db.execute(
            "DELETE FROM pro_graph_templates WHERE user_id=? AND template_id=?",
            (user_id, template_id),
        )
        db.commit()
        return cur.rowcount > 0
    finally:
        db.close()
