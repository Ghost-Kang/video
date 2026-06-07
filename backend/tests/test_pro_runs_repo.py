"""pro_runs_repo 队列状态机单测(临时 canvas.db,验证 claim/lease/fencing/retry/cancel)。"""

from __future__ import annotations

from agent.tools.canvas_persistence import pro_runs_repo as repo


def _use_tmp_db(monkeypatch, tmp_path):
    db_file = tmp_path / "canvas.db"
    monkeypatch.setattr(
        "agent.tools.canvas_persistence.db.canvas_db_path", lambda: db_file
    )


def _mk(monkeypatch, tmp_path, run_id="r1", uid="u1", tid="t1"):
    _use_tmp_db(monkeypatch, tmp_path)
    repo.create_pro_run(
        run_id, user_id=uid, thread_id=tid, graph_json='{"nodes":[]}', provider="fixture", cost_est=3.0
    )
    return run_id, uid, tid


def test_create_and_get(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "pending"
    assert run["provider"] == "fixture"
    assert run["cost_est"] == 3.0
    assert run["attempt_count"] == 0


def test_claim_transitions_to_submitted(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    claimed = repo.claim_pending_pro_runs()
    assert len(claimed) == 1 and claimed[0]["run_id"] == run_id
    after = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert after["status"] == "submitted"
    assert after["attempt_count"] == 1
    assert after["lease_until"] is not None
    # second claim finds nothing (already submitted)
    assert repo.claim_pending_pro_runs() == []


def test_polling_writes_prompt_id(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id="pid-9")
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "polling"
    assert run["comfy_prompt_id"] == "pid-9"


def test_done_sets_result_clears_lease(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id="pid-9")
    repo.update_pro_run_state(
        run_id, "done", user_id=uid, thread_id=tid, result=["u1.png", "u2.png"], expected_prompt_id="pid-9"
    )
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "done"
    assert run["result"] == ["u1.png", "u2.png"]
    assert run["lease_until"] is None


def test_fencing_blocks_stale_writeback(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id="pid-NEW")
    # stale worker (had pid-OLD) tries to mark done -> must be skipped
    repo.update_pro_run_state(
        run_id, "done", user_id=uid, thread_id=tid, result=["stale.png"], expected_prompt_id="pid-OLD"
    )
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "polling"
    assert run["result"] is None


def test_cancel_guard_blocks_writeback(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    assert repo.cancel_pro_run(run_id, user_id=uid, thread_id=tid) is True
    # in-flight worker tries to complete -> cancelled guard wins (atomic WHERE status != 'cancelled')
    repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid, result=["late.png"])
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "cancelled"
    assert run["result"] is None


def test_cancel_after_done_returns_false(monkeypatch, tmp_path):
    """worker done 先到 → cancel 原子条件 UPDATE 落空,返回 False(不能取消已完成的 run)。"""
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid, result=["a.png"])
    assert repo.cancel_pro_run(run_id, user_id=uid, thread_id=tid) is False
    assert repo.get_pro_run(run_id, user_id=uid, thread_id=tid)["status"] == "done"


def test_polling_renews_lease(monkeypatch, tmp_path):
    """polling 转写续租 —— lease 覆盖整个 poll 窗口,而非硬扛 claim 时的窗口。"""
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    before = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)["lease_until"]
    repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id="pid")
    after = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)["lease_until"]
    assert after is not None and after >= before  # renewed (>= claim lease)


def test_schedule_retry_then_terminal(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    # bump attempts to max via repeated claims, then a retry should fail it
    for _ in range(repo.PRO_RUN_MAX_ATTEMPTS):
        repo.claim_pending_pro_runs()
        # set back to pending so it can be re-claimed (simulating retries that re-enqueue)
        repo.update_pro_run_state(run_id, "pending", user_id=uid, thread_id=tid)
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["attempt_count"] >= repo.PRO_RUN_MAX_ATTEMPTS
    ok = repo.schedule_pro_run_retry(run_id, "boom", user_id=uid, thread_id=tid)
    assert ok is False
    assert repo.get_pro_run(run_id, user_id=uid, thread_id=tid)["status"] == "failed"


def test_schedule_retry_backoff_when_attempts_left(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()  # attempt_count = 1
    ok = repo.schedule_pro_run_retry(run_id, "transient", user_id=uid, thread_id=tid)
    assert ok is True
    run = repo.get_pro_run(run_id, user_id=uid, thread_id=tid)
    assert run["status"] == "pending"
    assert run["next_retry_at"] is not None
    # not yet due -> claim skips it
    assert repo.claim_pending_pro_runs() == []


def test_schedule_retry_on_terminal_returns_false(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "done", user_id=uid, thread_id=tid)
    assert repo.schedule_pro_run_retry(run_id, "x", user_id=uid, thread_id=tid) is False


def test_recover_picks_lease_expired(monkeypatch, tmp_path):
    run_id, uid, tid = _mk(monkeypatch, tmp_path)
    repo.claim_pending_pro_runs()
    repo.update_pro_run_state(run_id, "polling", user_id=uid, thread_id=tid, comfy_prompt_id="pid")
    # force lease into the past
    db_file = tmp_path / "canvas.db"
    monkeypatch.setattr("agent.tools.canvas_persistence.db.canvas_db_path", lambda: db_file)
    import sqlite3

    conn = sqlite3.connect(str(db_file))
    conn.execute("UPDATE pro_runs SET lease_until='2000-01-01T00:00:00+00:00' WHERE run_id=?", (run_id,))
    conn.commit()
    conn.close()
    recovered = repo.recover_pro_runs()
    assert len(recovered) == 1 and recovered[0]["run_id"] == run_id


def test_list_pro_runs(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    for i in range(3):
        repo.create_pro_run(f"r{i}", user_id="u", thread_id="t", graph_json="{}", provider="fixture", cost_est=1.0)
    runs = repo.list_pro_runs(user_id="u", thread_id="t")
    assert len(runs) == 3
