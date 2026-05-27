"""Canvas SQLite DAO 层 — 抽自 W4D3 architect followup 的 canvas.py 拆分。

子模块:
- db.py:           连接 / schema bootstrap / ContextVar / _resolve_ids
- nodes_repo.py:   节点 CRUD (_load_node / _load_all_nodes / _upsert_node / _row_to_node / _update_node_result)
- edges_repo.py:   边 CRUD (_load_all_edges / _upsert_edge / _renormalize_positions)
- generation_repo.py: 生成队列状态机 (claim_pending_tasks / recover_generation_tasks / update_generation_state)

`agent.tools.canvas` 仍是 back-compat 总入口,re-export 全部 public + private 函数,
现有 caller 不需要改 import。新代码鼓励 `from agent.tools.canvas_persistence.xxx import ...`。
"""
