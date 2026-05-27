"""画布工具 — SQLite 持久化"""

import json
import sqlite3
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

from agent.config import STORYBOARD_COLUMNS


NodeType = Literal["script", "image", "video", "composite"]
ImageSubtype = Literal["character", "scene", "grid"] | None
NodeStatus = Literal["reviewing", "confirmed"]
AssetStatus = Literal["idle", "generating", "done", "failed", "timeout"]
# 旧 status 保留兼容，新代码使用 node_status + asset_status
LegacyStatus = Literal["pending", "approved", "executing", "awaiting_review", "done", "failed"]

_DB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_DB_PATH = _DB_DIR / "canvas.db"
_current_thread_id: ContextVar[str] = ContextVar("canvas_thread_id", default="default")
_current_user_id: ContextVar[str] = ContextVar("canvas_user_id", default="default")


def set_thread_id(thread_id: str):
    _current_thread_id.set(thread_id)


def set_user_id(user_id: str):
    _current_user_id.set(user_id)


def _node_id(type: str) -> str:
    return f"{type}-{uuid.uuid4().hex[:6]}"


# ---------- 数据库 ----------


def _db() -> sqlite3.Connection:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_nodes (
            user_id TEXT NOT NULL DEFAULT 'default',
            thread_id TEXT NOT NULL,
            node_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            node_status TEXT NOT NULL DEFAULT 'reviewing',
            asset_status TEXT NOT NULL DEFAULT 'idle',
            result TEXT,
            subtype TEXT,
            feedback TEXT,
            x REAL, y REAL,
            PRIMARY KEY (user_id, thread_id, node_id)
        )"""
    )
    # 兼容旧数据库：添加新列（如果不存在）
    for col, defn in [("user_id", "TEXT NOT NULL DEFAULT 'default'"), ("node_status", "TEXT NOT NULL DEFAULT 'reviewing'"), ("asset_status", "TEXT NOT NULL DEFAULT 'idle'"),
                       ("shot_no", "TEXT"), ("image_gen_provider", "TEXT"),
                       ("generation_status", "TEXT NOT NULL DEFAULT 'idle'"),
                       ("generation_task_id", "TEXT"),
                       ("generation_error", "TEXT")]:
        try:
            db.execute(f"ALTER TABLE canvas_nodes ADD COLUMN {col} {defn}")
        except sqlite3.OperationalError:
            pass  # 列已存在
    db.execute(
        """CREATE TABLE IF NOT EXISTS canvas_edges (
            user_id TEXT NOT NULL DEFAULT 'default',
            thread_id TEXT NOT NULL,
            edge_id TEXT NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, thread_id, edge_id)
        )"""
    )
    try:
        db.execute("ALTER TABLE canvas_edges ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    try:
        db.execute("ALTER TABLE canvas_edges ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
    except sqlite3.OperationalError:
        pass
    return db


def _row_to_node(row: sqlite3.Row) -> dict:
    """SQLite row → node dict（按列名访问，兼容新旧表结构）"""
    d = {
        "id": row["node_id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "status": row["status"],
        "node_status": row["node_status"] or "reviewing",
        "asset_status": row["asset_status"] or "idle",
        "result": None,
        "subtype": row["subtype"],
        "shot_no": row["shot_no"],
        "image_gen_provider": row["image_gen_provider"],
        "generation_status": row["generation_status"] or "idle",
        "generation_task_id": row["generation_task_id"],
        "generation_error": row["generation_error"],
        "user_id": row["user_id"],
        "thread_id": row["thread_id"],
        "x": row["x"],
        "y": row["y"],
    }
    if d["result"] is None and row["result"]:
        try:
            d["result"] = json.loads(row["result"])
        except json.JSONDecodeError:
            d["result"] = None
    return d


def _load_node(node_id: str) -> dict | None:
    db = _db()
    row = db.execute(
        "SELECT * FROM canvas_nodes WHERE user_id=? AND thread_id=? AND node_id=?",
        (_current_user_id.get(), _current_thread_id.get(), node_id),
    ).fetchone()
    db.close()
    return _row_to_node(row) if row else None


def _load_all_nodes() -> dict[str, dict]:
    db = _db()
    rows = db.execute(
        "SELECT * FROM canvas_nodes WHERE user_id=? AND thread_id=?", (_current_user_id.get(), _current_thread_id.get(),)
    ).fetchall()
    db.close()
    return {r["node_id"]: _row_to_node(r) for r in rows}


def _load_all_edges() -> list[dict]:
    db = _db()
    rows = db.execute(
        "SELECT edge_id, source, target, position FROM canvas_edges WHERE user_id=? AND thread_id=? ORDER BY position",
        (_current_user_id.get(), _current_thread_id.get()),
    ).fetchall()
    db.close()
    return [{"id": r["edge_id"], "source": r["source"], "target": r["target"], "position": r["position"]} for r in rows]


def _upsert_node(node: dict):
    db = _db()
    r = node.get("result")
    result_json = json.dumps(r, ensure_ascii=False) if r is not None else None
    user_id = _current_user_id.get()
    thread_id = _current_thread_id.get()
    values = (
        node["type"], node["title"], node.get("description", ""), node.get("status", "pending"),
        node.get("node_status", "reviewing"), node.get("asset_status", "idle"),
        result_json, node.get("subtype"),
        node.get("shot_no"), node.get("image_gen_provider"),
        node.get("generation_status", "idle"),
        node.get("generation_task_id"),
        node.get("generation_error"),
        node.get("x"), node.get("y"),
        user_id, thread_id, node["id"],
    )
    cursor = db.execute(
        """UPDATE canvas_nodes SET
           type=?, title=?, description=?, status=?, node_status=?, asset_status=?,
           result=?, subtype=?, shot_no=?, image_gen_provider=?,
           generation_status=?, generation_task_id=?, generation_error=?, x=?, y=?
           WHERE user_id=? AND thread_id=? AND node_id=?""",
        values,
    )
    if cursor.rowcount == 0:
        db.execute(
            """INSERT INTO canvas_nodes (user_id, thread_id, node_id, type, title, description, status, node_status, asset_status, result, subtype, shot_no, image_gen_provider, generation_status, generation_task_id, generation_error, x, y)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, thread_id, node["id"], node["type"], node["title"],
                node.get("description", ""), node.get("status", "pending"),
                node.get("node_status", "reviewing"), node.get("asset_status", "idle"),
                result_json, node.get("subtype"),
                node.get("shot_no"), node.get("image_gen_provider"),
                node.get("generation_status", "idle"),
                node.get("generation_task_id"),
                node.get("generation_error"),
                node.get("x"), node.get("y"),
            ),
        )
    db.commit()
    db.close()


# ---------- 层级约束配置 ----------
# 每条规则: (子节点类型, 子节点subtype) → 允许的父节点 [(类型, subtype), ...]
# None 作为 subtype 表示匹配该类型任意节点。
# 不在配置中的组合 = 无层级约束，可随意连接。
# 创作流水线: script(策划书) → image(character|scene) → image(grid)

HIERARCHY: dict[tuple[str, str | None], list[tuple[str, str | None]]] = {
    ("image", "character"): [
        ("script", None),
    ],
    ("image", "scene"): [
        ("script", None),
    ],
    ("image", "grid"): [
        ("image", "character"),
        ("image", "scene"),
    ],
}


def _validate_hierarchy(child_type: str, child_subtype: str | None, parent: dict) -> dict | None:
    """校验父子节点是否符合层级约束。通过返回 None，违反返回 error dict。"""
    rules = HIERARCHY.get((child_type, child_subtype))
    if rules is None:
        return None  # 无约束

    p_type = parent["type"]
    p_subtype = parent.get("subtype")

    for allowed_type, allowed_subtype in rules:
        if p_type == allowed_type and (allowed_subtype is None or p_subtype == allowed_subtype):
            return None

    # 构造友好的错误描述
    allowed_desc = " / ".join(
        f"{t}{'(' + s + ')' if s else ''}" for t, s in rules
    )
    child_desc = f"{child_type}{'(' + child_subtype + ')' if child_subtype else ''}"
    parent_desc = f"{p_type}{'(' + p_subtype + ')' if p_subtype else ''}"
    return {
        "error": f"层级约束：{child_desc} 的父节点必须是 {allowed_desc}，当前为 {parent_desc}"
    }


def _find_parent_by_type(type: str, subtype: str | None = None) -> str:
    """在画布中找最新匹配的节点作为父节点。"""
    nodes = _load_all_nodes()
    candidates = [
        n for n in nodes.values()
        if n["type"] == type and (subtype is None or n.get("subtype") == subtype)
    ]
    return candidates[-1]["id"] if candidates else ""


def _upsert_edge(edge: dict):
    db = _db()
    # 自动分配 position：该 target 已有边数 + 1
    if edge.get("position") is None:
        existing = db.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM canvas_edges WHERE user_id=? AND thread_id=? AND target=?",
            (_current_user_id.get(), _current_thread_id.get(), edge["target"]),
        ).fetchone()
        edge["position"] = existing[0] if existing else 1
    db.execute(
        "INSERT INTO canvas_edges (user_id, thread_id, edge_id, source, target, position) VALUES (?, ?, ?, ?, ?, ?)",
        (_current_user_id.get(), _current_thread_id.get(), edge["id"], edge["source"], edge["target"], edge["position"]),
    )
    db.commit()
    db.close()


def create_canvas_edge(source: str, target: str) -> dict:
    """手动创建一条边。返回 edge 或 error。"""
    # 验证两端节点存在
    src_node = _load_node(source)
    tgt_node = _load_node(target)
    if not src_node:
        return {"error": f"源节点 {source} 不存在"}
    if not tgt_node:
        return {"error": f"目标节点 {target} 不存在"}
    # 检查重复
    existing = _load_all_edges()
    for e in existing:
        if e["source"] == source and e["target"] == target:
            return {"error": "边已存在"}
    edge_id = f"e-{source}-{target}"
    edge = {"id": edge_id, "source": source, "target": target}
    _upsert_edge(edge)
    return edge


def _renormalize_positions(target_id: str):
    """重整 position，确保同一 target 下的边位置连续（1,2,3...）"""
    db = _db()
    rows = db.execute(
        "SELECT edge_id FROM canvas_edges WHERE user_id=? AND thread_id=? AND target=? ORDER BY position",
        (_current_user_id.get(), _current_thread_id.get(), target_id),
    ).fetchall()
    for i, row in enumerate(rows):
        db.execute(
            "UPDATE canvas_edges SET position=? WHERE user_id=? AND thread_id=? AND edge_id=?",
            (i + 1, _current_user_id.get(), _current_thread_id.get(), row["edge_id"]),
        )
    db.commit()
    db.close()


def reorder_edge(edge_id: str, direction: str) -> dict:
    """将边向上或向下移动一个位置。direction: 'up' | 'down'"""
    edges = _load_all_edges()
    edge = next((e for e in edges if e["id"] == edge_id), None)
    if not edge:
        return {"error": f"边 {edge_id} 不存在"}

    # 找同 target 的相邻边
    siblings = sorted(
        [e for e in edges if e["target"] == edge["target"]],
        key=lambda e: e["position"],
    )
    idx = next((i for i, e in enumerate(siblings) if e["id"] == edge_id), -1)
    if idx < 0:
        return {"error": "边不在同组中"}

    swap_idx = idx - 1 if direction == "up" else idx + 1
    if swap_idx < 0 or swap_idx >= len(siblings):
        return {"error": "已是边界位置"}

    # 交换 position
    a, b = siblings[idx], siblings[swap_idx]
    pos_a, pos_b = a["position"], b["position"]
    db = _db()
    db.execute("UPDATE canvas_edges SET position=? WHERE user_id=? AND thread_id=? AND edge_id=?", (pos_b, _current_user_id.get(), _current_thread_id.get(), a["id"]))
    db.execute("UPDATE canvas_edges SET position=? WHERE user_id=? AND thread_id=? AND edge_id=?", (pos_a, _current_user_id.get(), _current_thread_id.get(), b["id"]))
    db.commit()
    db.close()
    _renormalize_positions(edge["target"])
    return {"id": edge_id, "direction": direction, "swapped_with": b["id"]}


def delete_canvas_edge(edge_id: str) -> dict:
    """手动删除一条边。"""
    # 先找到 target 用于重整
    edges = _load_all_edges()
    edge = next((e for e in edges if e["id"] == edge_id), None)
    if not edge:
        return {"error": f"边 {edge_id} 不存在"}
    target_id = edge["target"]

    db = _db()
    db.execute("DELETE FROM canvas_edges WHERE user_id=? AND thread_id=? AND edge_id=?", (_current_user_id.get(), _current_thread_id.get(), edge_id))
    db.commit()
    db.close()
    _renormalize_positions(target_id)
    return {"id": edge_id, "deleted": True}


# ---------- 节点 CRUD ----------


def _default_position(node_type: str, parent_ids: list[str] | None) -> tuple[float, float]:
    """为新节点计算默认位置。

    X: 有父节点 → 父节点右侧 400px；无父节点 → 已有节点最右侧 + 400，或 100
    Y: 有父节点 → 父节点下方 280px；无父节点 → 已有节点最下方 + 200，或 100
    同一 X 列内已有其他节点时向下错开。
    """
    nodes = _load_all_nodes()
    x_gap = 400
    y_gap = 280

    # X 坐标
    base_x: float = 100
    if parent_ids:
        parent_xs = []
        for pid in parent_ids:
            p = _load_node(pid)
            if p and p.get("x") is not None:
                parent_xs.append(p["x"])
        if parent_xs:
            base_x = max(parent_xs) + x_gap
    elif nodes:
        max_x = max((n.get("x") or 100 for n in nodes.values()), default=100)
        base_x = float(max_x + x_gap)

    # Y 坐标
    ref_y: float = 100
    if parent_ids:
        parent_ys = []
        for pid in parent_ids:
            p = _load_node(pid)
            if p and p.get("y") is not None:
                parent_ys.append(p["y"] + y_gap)
        if parent_ys:
            ref_y = max(parent_ys)
    elif nodes:
        max_y = max((n.get("y") or 100 for n in nodes.values()), default=100)
        ref_y = float(max_y + 200)

    # 同列中已有节点 → 继续向下错开
    same_col = [n for n in nodes.values() if n.get("x") == base_x and n.get("y", 0) >= ref_y - 20]
    if same_col:
        ref_y = max((n.get("y") or 0 for n in same_col)) + y_gap

    return (base_x, float(ref_y))


def create_canvas_node(
    type: NodeType,
    title: str,
    description: str = "",
    parent_ids: list[str] | None = None,
    subtype: str | None = None,
    shot_no: str | None = None,
) -> dict:
    """在画布上创建一个节点。type: script/image/video/audio。

    parent_ids: 上游节点 ID 列表，支持多个父节点。
    shot_no: 分镜序号（如 "1", "2"），用于自动排版时按镜号排序。
    """
    nid = _node_id(type)
    # script 节点创建时自动处理：解析分镜表 + 写入 result
    result = None
    if type == "script":
        shots = _parse_storyboard(description)
        result = {"content": description, "word_count": len(description), "shots": shots}

    # 计算默认位置：基于已有节点做增量偏移，避免全部堆在 (100,100)
    x, y = _default_position(type, parent_ids)

    node = {
        "id": nid, "type": type, "title": title, "description": description,
        "status": "pending", "node_status": "reviewing", "asset_status": "idle",
        "result": result, "subtype": subtype,
        "shot_no": shot_no,
        "x": x, "y": y,
    }

    ids = parent_ids or []

    # 自动路由：未指定 parent 时根据 type+subtype 推断
    if not ids:
        if type == "image" and subtype in ("character", "scene"):
            pid = _find_parent_by_type("script")
            if pid:
                ids = [pid]
    # 上游校验（每个父节点独立校验）
    for pid in ids:
        parent = _load_node(pid)
        if not parent:
            return {"error": f"上游节点 {pid} 不存在"}
        if parent.get("node_status") != "confirmed":
            return {
                "error": (
                    f"上游节点「{parent['title']}」({pid}) 尚未确认"
                    f"（node_status={parent.get('node_status')}），无法创建下游节点。\n"
                    f"请告知用户：需先在画布上确认该节点后，才能继续创建 {type} 节点。"
                )
            }

        # 层级约束（配置驱动）
        err = _validate_hierarchy(type, subtype, parent)
        if err:
            return err

    _upsert_node(node)

    for pid in ids:
        edge = {"id": f"e-{pid}-{nid}", "source": pid, "target": nid}
        _upsert_edge(edge)

    return node


def _update_node_result(node_id: str, updates: dict):
    node = _load_node(node_id)
    if node:
        existing = node.get("result") or {}
        if isinstance(existing, dict):
            existing.update(updates)
        else:
            existing = updates
        node["result"] = existing
        _upsert_node(node)


def update_canvas_node(
    node_id: str,
    title: str | None = None,
    description: str | None = None,
    node_status: NodeStatus | None = None,
    asset_status: AssetStatus | None = None,
    confirmed: bool = False,
) -> dict:
    """更新画布节点属性。修改 confirmed 节点内容需 confirmed=True。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}

    changing_content = title is not None or description is not None
    if changing_content and node.get("node_status") == "confirmed" and not confirmed:
        return {
            "error": (
                f"节点「{node['title']}」({node_id}) 已确认，"
                f"修改其内容前必须先向用户确认。\n"
                f"请先向用户说明你要修改什么内容，征得同意后，"
                f"再调 update_canvas_node 并传入 confirmed=True。"
            )
        }

    if title is not None:
        node["title"] = title
    if description is not None:
        node["description"] = description
        if node["type"] == "script":
            shots = _parse_storyboard(description)
            node["result"] = {"content": description, "word_count": len(description), "shots": shots}
            node["node_status"] = "reviewing"
    if node_status is not None:
        node["node_status"] = node_status
    if asset_status is not None:
        node["asset_status"] = asset_status
    _upsert_node(node)
    return node


def delete_canvas_node(node_id: str) -> dict:
    """删除画布上的一个节点。"""
    db = _db()
    db.execute("DELETE FROM canvas_nodes WHERE user_id=? AND thread_id=? AND node_id=?", (_current_user_id.get(), _current_thread_id.get(), node_id))
    db.execute("DELETE FROM canvas_edges WHERE user_id=? AND thread_id=? AND (source=? OR target=?)", (_current_user_id.get(), _current_thread_id.get(), node_id, node_id))
    db.commit()
    db.close()
    return {"id": node_id, "deleted": True}


# ---------- 分镜解析 ----------


def _parse_storyboard(text: str) -> list[dict]:
    keys = [c["key"] for c in STORYBOARD_COLUMNS]
    required = [i for i, c in enumerate(STORYBOARD_COLUMNS) if c.get("required")]
    shots = []
    for line in text.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < max(required) + 1:
            continue
        # 跳过表头行
        if parts[0] in ("镜号", "no", "#", "shot"):
            continue
        shot = {}
        for i, key in enumerate(keys):
            shot[key] = parts[i] if i < len(parts) else ""
        shots.append(shot)
    return shots


# ---------- 节点执行 ----------


def execute_node(node_id: str, node_type: NodeType, description: str, image_gen_provider: str = "google") -> dict:
    """执行节点资产生成。文字节点直接结构化，媒体节点需 approved 状态。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在，请先 create"}

    if node_type == "script":
        # 策划书：内容以 create 时的 node.description 为准
        content = node["description"]
        shots = _parse_storyboard(content)
        node["node_status"] = "reviewing"
        node["result"] = {"content": content, "word_count": len(content), "shots": shots}
        _upsert_node(node)
        return {"id": node_id, "node_status": "reviewing", "result": node["result"]}

    # 媒体节点：同步提交生图任务，拿到 task_id 后切 generating
    subtype = node.get("subtype")

    if node_type == "image":
        # 立即标记 generating 状态，后台提交生图
        node["asset_status"] = "generating"
        node["image_gen_provider"] = image_gen_provider
        node["result"] = {"prompt": description, "resolution": "1920x1080", "subtype": subtype}
        _upsert_node(node)
        # 返回临时状态，实际 task_id 由后台任务写入
        return {"id": node_id, "asset_status": "generating", "result": node["result"], "_pending_submit": True}
    elif node_type == "composite":
        node["asset_status"] = "generating"
        _upsert_node(node)
        return {"id": node_id, "asset_status": "generating", "_pending_submit": True}

    elif node_type == "video":
        node["asset_status"] = "generating"
        node["result"] = {"prompt": description, "resolution": "1920x1080"}
        _upsert_node(node)
        return {"id": node_id, "asset_status": "generating", "result": node["result"], "_pending_submit": True}
    else:
        node["asset_status"] = "failed"
        _upsert_node(node)
        return {"id": node_id, "asset_status": "failed", "error": f"未知节点类型: {node_type}"}


def get_canvas_state(node_id: str = "") -> dict:
    """读取画布节点。传 node_id 返回单个节点详情，不传返回全部节点。"""
    nodes = _load_all_nodes()
    edges = _load_all_edges()

    if node_id:
        n = nodes.get(node_id)
        if not n:
            return {"error": f"节点 {node_id} 不存在"}
        detail = {
            "id": n["id"], "type": n["type"], "title": n["title"],
            "status": n.get("status", "pending"), "node_status": n.get("node_status", "reviewing"),
            "asset_status": n.get("asset_status", "idle"), "subtype": n.get("subtype"),
            "description": n.get("description", ""),
            "result": n.get("result"),
        }
        # 返回该节点的上下游连线
        related_edges = [e for e in edges if e["source"] == node_id or e["target"] == node_id]
        return {"node": detail, "edges": related_edges}

    summary = []
    for n in nodes.values():
        summary.append({
            "id": n["id"], "type": n["type"], "title": n["title"],
            "status": n.get("status", "pending"), "node_status": n.get("node_status", "reviewing"),
            "asset_status": n.get("asset_status", "idle"), "subtype": n.get("subtype"),
            "description": n.get("description", ""),
            "result": n.get("result"),
            "shot_no": n.get("shot_no"),
            "image_gen_provider": n.get("image_gen_provider"),
        })
    return {"nodes": summary, "edges": edges}


# ---------- 审核操作 ----------


def approve_node(node_id: str) -> dict:
    """确认节点（node_status: reviewing → confirmed）。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}
    node["node_status"] = "confirmed"
    _upsert_node(node)
    return node


def reject_node(node_id: str, feedback: str = "") -> dict:
    """驳回节点（将媒体节点的 asset 标记为 failed，反馈给 agent）。"""
    node = _load_node(node_id)
    if not node:
        return {"error": f"节点 {node_id} 不存在"}
    node["node_status"] = "reviewing"
    node["asset_status"] = "failed"
    if feedback:
        node["feedback"] = feedback
    _upsert_node(node)
    return node


# ---------- 生成任务队列 ----------


def enqueue_generation(node_id: str) -> dict | None:
    """将节点加入生成队列（generation_status: pending）。"""
    node = _load_node(node_id)
    if not node:
        return None
    node["generation_status"] = "pending"
    node["asset_status"] = "generating"
    _upsert_node(node)
    return node


def claim_pending_tasks(task_type: str | None = None) -> list[dict]:
    """跨用户查询:获取所有 generation_status='pending' 的节点并原子认领。

    Args:
        task_type: 可选 node type 过滤。None = 所有 type;非 None 时 SQL 层过滤。
                   配合 per-type worker(image/video/composite)使用,避免 worker 间互相认领。
    asyncio 单线程下原子安全(sqlite3 同步调用,无 yield 点)。
    """
    db = _db()
    if task_type is None:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status='pending' ORDER BY rowid"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status='pending' AND type=? ORDER BY rowid",
            (task_type,),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    # 批量标记为 submitted（中间态，避免被重复捡起）
    for t in tasks:
        db.execute(
            "UPDATE canvas_nodes SET generation_status='submitted' WHERE user_id=? AND thread_id=? AND node_id=?",
            (t["user_id"], t["thread_id"], t["id"]),
        )
    db.commit()
    db.close()
    if tasks:
        label = task_type or "all"
        print(f"[队列] claim {len(tasks)} 个待生成任务 (type={label})")
    return tasks


def recover_generation_tasks(task_type: str | None = None) -> list[dict]:
    """跨用户查询:获取所有未完成的生成任务(用于服务重启恢复)。

    包括 submitted(已认领但未完成提交)和 polling(正在轮询)状态。
    task_type 可选过滤,语义同 claim_pending_tasks。
    """
    db = _db()
    if task_type is None:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status IN ('submitted', 'polling') ORDER BY rowid"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM canvas_nodes WHERE generation_status IN ('submitted', 'polling') AND type=? ORDER BY rowid",
            (task_type,),
        ).fetchall()
    tasks = [_row_to_node(r) for r in rows]
    db.close()
    if tasks:
        label = task_type or "all"
        print(f"[队列] 恢复 {len(tasks)} 个未完成任务 (type={label})")
    return tasks


def update_generation_state(node_id: str, status: str, task_id: str | None = None, error: str | None = None):
    """更新节点的生成队列状态。"""
    node = _load_node(node_id)
    if not node:
        return
    node["generation_status"] = status
    if task_id is not None:
        node["generation_task_id"] = task_id
    if error is not None:
        node["generation_error"] = error
    if status == "done":
        node["asset_status"] = "done"
    elif status == "failed":
        node["asset_status"] = "failed"
        node["generation_error"] = error
    _upsert_node(node)
