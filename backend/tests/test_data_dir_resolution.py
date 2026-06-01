"""W5D4 review B4 — shared data-dir resolution invariants.

cascade.db (cascade.persistence.db) and canvas.db (tools.canvas_persistence.db)
must resolve to the SAME volume under every layout. Before the fix, canvas.db
computed its own parent×5 relative path with no container detection and no
CASCADE_DB_PATH support — it only landed on the mounted volume by coincidence of
directory depth, so a Dockerfile/layout change would drop the generation queue
onto an ephemeral layer (restart loses the queue → Google in-memory tasks
re-enqueue = double billing).

These tests pin the three resolution modes (override / container / local) and,
critically, that both stores agree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.cascade.persistence.db import db_path, resolve_data_dir
from agent.tools.canvas_persistence.db import _LOCAL_DATA_DIR, canvas_db_path


def test_override_colocates_both_stores(monkeypatch, tmp_path):
    """CASCADE_DB_PATH override → canvas.db sits in the SAME dir as cascade.db."""
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    assert db_path() == tmp_path / "cascade.db"
    assert canvas_db_path() == tmp_path / "canvas.db"
    assert canvas_db_path().parent == db_path().parent  # no split-brain


def test_container_layout_lands_on_volume(monkeypatch):
    """Inside the image (/app/src exists, no override) → /app/data for both."""
    monkeypatch.delenv("CASCADE_DB_PATH", raising=False)
    monkeypatch.setattr(Path, "exists", lambda self: str(self) == "/app/src")
    assert resolve_data_dir(_LOCAL_DATA_DIR) == Path("/app/data")
    assert canvas_db_path() == Path("/app/data/canvas.db")
    assert db_path() == Path("/app/data/cascade.db")


def test_local_dev_uses_repo_relative_default(monkeypatch):
    """Local dev (no override, no /app/src) → each store's repo-relative default."""
    monkeypatch.delenv("CASCADE_DB_PATH", raising=False)
    # Ensure /app/src isn't accidentally present on the dev box running this.
    real_exists = Path.exists
    monkeypatch.setattr(
        Path, "exists", lambda self: False if str(self) == "/app/src" else real_exists(self)
    )
    assert canvas_db_path() == _LOCAL_DATA_DIR / "canvas.db"
    # cascade keeps its own (different) local default — that's fine; only the
    # container + override paths must agree, and the local files are git-ignored.
    assert canvas_db_path().name == "canvas.db"
