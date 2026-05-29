"""W5D2 — /api/health/summary contract tests."""

from __future__ import annotations

import asyncio

from agent.cascade.event_names import EventName
from agent.transport.http_router import handle_health_summary


def test_health_summary_happy_path(monkeypatch):
    async def fake_stats(*, five_min_ago, one_hour_ago):
        return (
            {
                "total": 4,
                "by_type": {
                    EventName.ANALYSIS_RETURNED.value: 2,
                    EventName.SCRIPT_REWRITTEN.value: 1,
                    EventName.FAILURE_EMITTED.value: 1,
                },
            },
            {
                EventName.ANALYSIS_RETURNED.value: 0.667,
                EventName.SCRIPT_REWRITTEN.value: 1.0,
            },
            [
                {
                    "id": 76,
                    "ts": "2026-05-28T08:11:43+00:00",
                    "event_name": EventName.FAILURE_EMITTED.value,
                    "user_id": "anon-xxx",
                    "run_id": None,
                    "payload": {"failure_code": "S5_INVALID_PAYLOAD", "stage": "analysis"},
                }
            ],
        )

    monkeypatch.setattr("agent.transport.http_router._health_event_stats", fake_stats)

    status, body, reason = asyncio.run(handle_health_summary(qs={}, body={}))

    assert status == 200
    assert reason == "OK"
    assert set(body) == {"server", "events_5min", "upstream_success_rate", "recent_failures"}
    assert body["events_5min"]["total"] == 4
    assert body["events_5min"]["by_type"][EventName.ANALYSIS_RETURNED.value] == 2
    assert body["upstream_success_rate"][EventName.ANALYSIS_RETURNED.value] == 0.667
    assert body["upstream_success_rate"][EventName.SCRIPT_REWRITTEN.value] == 1.0
    assert body["recent_failures"][0]["id"] == 76


def test_health_summary_empty_events(monkeypatch):
    async def fake_stats(*, five_min_ago, one_hour_ago):
        return (
            {"total": 0, "by_type": {}},
            {
                EventName.ANALYSIS_RETURNED.value: None,
                EventName.SCRIPT_REWRITTEN.value: None,
            },
            [],
        )

    monkeypatch.setattr("agent.transport.http_router._health_event_stats", fake_stats)

    status, body, _ = asyncio.run(handle_health_summary(qs={}, body={}))

    assert status == 200
    assert body["events_5min"] == {"total": 0, "by_type": {}}
    assert body["upstream_success_rate"] == {
        EventName.ANALYSIS_RETURNED.value: None,
        EventName.SCRIPT_REWRITTEN.value: None,
    }
    assert body["recent_failures"] == []


def test_health_summary_server_section_types(monkeypatch):
    async def fake_stats(*, five_min_ago, one_hour_ago):
        return (
            {"total": 0, "by_type": {}},
            {
                EventName.ANALYSIS_RETURNED.value: None,
                EventName.SCRIPT_REWRITTEN.value: None,
            },
            [],
        )

    monkeypatch.setattr("agent.transport.http_router._health_event_stats", fake_stats)

    _, body, _ = asyncio.run(handle_health_summary(qs={}, body={}))
    server = body["server"]

    assert isinstance(server["cpu_percent"], (int, float))
    assert 0 <= server["cpu_percent"] <= 100
    assert isinstance(server["mem_used_mb"], int)
    assert isinstance(server["mem_total_mb"], int)
    assert server["mem_total_mb"] > 0
    assert isinstance(server["disk_used_gb"], (int, float))
    assert isinstance(server["disk_total_gb"], (int, float))
    assert server["disk_total_gb"] > 0
    assert isinstance(server["uptime_seconds"], int)
