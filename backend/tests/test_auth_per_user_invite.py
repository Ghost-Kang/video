"""鉴权 A (B8-3) — per-user invite codes carry a server-derived identity.

Closes the cost-cap evasion: with a mapped code, the server pins user_id to the
code (ignoring the client's claim), so a caller can't rotate user_id to dodge
CASCADE_RUN/USER_DAY caps. Shared codes keep legacy (client-claimed) behavior.
"""

from __future__ import annotations

import pytest

from agent import config


@pytest.fixture
def auth_a(monkeypatch):
    """A shared code + two per-user mapped codes."""
    monkeypatch.setattr(config, "INVITE_CODES", frozenset({"SHARED"}))
    monkeypatch.setattr(config, "INVITE_CODE_MAP", {"alice-code": "alice", "bob-code": "bob"})


# --- config helpers ---------------------------------------------------------


def test_parse_invite_code_map_well_formed():
    m = config._parse_invite_code_map("c1:userA, c2:userB ,bad,  : ,c3:userC")
    assert m == {"c1": "userA", "c2": "userB", "c3": "userC"}  # bad/empty pairs dropped


def test_has_invite_gate_reads_live(monkeypatch):
    monkeypatch.setattr(config, "INVITE_CODES", frozenset())
    monkeypatch.setattr(config, "INVITE_CODE_MAP", {})
    assert config.has_invite_gate() is False
    monkeypatch.setattr(config, "INVITE_CODE_MAP", {"x": "u"})
    assert config.has_invite_gate() is True  # map-only deploy still gated


def test_is_valid_invite_accepts_shared_and_mapped(auth_a):
    assert config.is_valid_invite("SHARED") is True
    assert config.is_valid_invite("alice-code") is True
    assert config.is_valid_invite("nope") is False
    assert config.is_valid_invite("") is False
    assert config.is_valid_invite(None) is False


def test_resolve_user_id_mapped_overrides_client(auth_a):
    # mapped code → server identity wins, client claim ignored (the刷钱 fix)
    assert config.resolve_user_id("alice-code", "attacker-claims-bob") == "alice"
    assert config.resolve_user_id("bob-code", "x") == "bob"


def test_resolve_user_id_shared_falls_back_to_client(auth_a):
    # shared code has no mapped identity → legacy client-claimed user_id
    assert config.resolve_user_id("SHARED", "whoever") == "whoever"
    # unknown / no code → client claim (gate elsewhere rejects invalid codes)
    assert config.resolve_user_id(None, "whoever") == "whoever"
