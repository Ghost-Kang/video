"""ws_messages Pydantic contract tests.

Coverage gap closure(W4D5 audit):Claude-B 的 ws_messages.py 之前只被 ws_server
分派路径间接覆盖。直接测每个模型的 validation 行为(discriminator / extra=forbid /
min_length / Literal 边界),防止 schema 改动悄无声息地破契约。
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from agent.transport.ws_messages import (
    INBOUND_MODELS,
    AnalysisAnswerReturnedEvent,
    AnalysisReturnedEvent,
    AuthMsg,
    CreateEdgeMsg,
    DeleteEdgeMsg,
    DeleteSessionMsg,
    ExecuteNodeMsg,
    GetSessionStateMsg,
    ListSessionsMsg,
    OptimizePromptMsg,
    ReorderEdgeMsg,
    ReviewNodeMsg,
    RewriteReturnedEvent,
    ShotFirstFrameReturnedEvent,
    UpdateNodeStatusMsg,
    UpdatePositionMsg,
    UserMessageMsg,
    WSInbound,
)


_WSInboundAdapter = TypeAdapter(WSInbound)


# ---------- AuthMsg ----------


class TestAuthMsg:
    def test_happy_path(self):
        msg = AuthMsg.model_validate({"type": "auth", "user_id": "u1"})
        assert msg.user_id == "u1"

    def test_missing_user_id(self):
        with pytest.raises(ValidationError):
            AuthMsg.model_validate({"type": "auth"})

    def test_empty_user_id_rejected(self):
        # min_length=1 — empty string 不通过
        with pytest.raises(ValidationError):
            AuthMsg.model_validate({"type": "auth", "user_id": ""})

    def test_extra_field_rejected(self):
        # extra="forbid" — typo 会失败而不是 silently ignored
        with pytest.raises(ValidationError):
            AuthMsg.model_validate({"type": "auth", "user_id": "u1", "uesr_id": "u1"})

    def test_wrong_type_literal(self):
        with pytest.raises(ValidationError):
            AuthMsg.model_validate({"type": "not_auth", "user_id": "u1"})

    def test_invite_code_optional(self):
        # invite_code 可不传 — dev 模式无 gate;production gate 在 ws_server 层
        msg = AuthMsg.model_validate({"type": "auth", "user_id": "u1"})
        assert msg.invite_code is None

    def test_invite_code_parsed(self):
        msg = AuthMsg.model_validate(
            {"type": "auth", "user_id": "u1", "invite_code": "CASCADE-2026"}
        )
        assert msg.invite_code == "CASCADE-2026"


# ---------- ListSessionsMsg ----------


class TestListSessionsMsg:
    def test_happy_path(self):
        msg = ListSessionsMsg.model_validate({"type": "list_sessions"})
        assert msg.type == "list_sessions"

    def test_does_not_require_thread_id(self):
        # P2 fix(W4D2):list_sessions 不需要 thread_id
        msg = ListSessionsMsg.model_validate({"type": "list_sessions"})
        assert not hasattr(msg, "thread_id")


# ---------- ExecuteNodeMsg ----------


class TestExecuteNodeMsg:
    _base = {
        "type": "execute_node",
        "thread_id": "t1",
        "node_id": "n1",
        "node_type": "image",
    }

    def test_happy_path_with_optionals(self):
        msg = ExecuteNodeMsg.model_validate({
            **self._base,
            "description": "a cat",
            "image_gen_provider": "google",
            "duration": 5,
            "resolution": "1080p",
            "generate_audio": True,
        })
        assert msg.node_type == "image"
        assert msg.duration == 5

    def test_happy_path_minimal(self):
        msg = ExecuteNodeMsg.model_validate(self._base)
        assert msg.description == ""  # default
        assert msg.image_gen_provider is None
        assert msg.duration is None

    def test_missing_thread_id(self):
        bad = {**self._base}
        del bad["thread_id"]
        with pytest.raises(ValidationError):
            ExecuteNodeMsg.model_validate(bad)

    def test_empty_thread_id_rejected(self):
        with pytest.raises(ValidationError):
            ExecuteNodeMsg.model_validate({**self._base, "thread_id": ""})

    def test_invalid_node_type(self):
        with pytest.raises(ValidationError):
            ExecuteNodeMsg.model_validate({**self._base, "node_type": "audio"})

    def test_video_node_type_ok(self):
        msg = ExecuteNodeMsg.model_validate({**self._base, "node_type": "video"})
        assert msg.node_type == "video"


# ---------- UserMessageMsg ----------


class TestUserMessageMsg:
    def test_happy_path(self):
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
        })
        assert msg.content == "hi"
        # 默认 None — 旧客户端不带字段也得通过
        assert msg.selected_niche is None

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            UserMessageMsg.model_validate({
                "type": "user_message",
                "thread_id": "t1",
                "content": "",
            })

    def test_with_selected_niche(self):
        # 三个合法 niche 值都能通过
        for niche in ("baomam_fushi", "yuer_richang", "jiating_chufang"):
            msg = UserMessageMsg.model_validate({
                "type": "user_message",
                "thread_id": "t1",
                "content": "hi",
                "selected_niche": niche,
            })
            assert msg.selected_niche == niche

    def test_without_selected_niche_backwards_compat(self):
        # 字段缺失 → 不报错且 None(向后兼容老客户端,关键保证)
        msg = UserMessageMsg.model_validate({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
        })
        assert msg.selected_niche is None

    def test_invalid_niche_rejected(self):
        # Literal 兜底 — 未知 niche 应在 WS 边界就被拒掉,不该漏到下游
        with pytest.raises(ValidationError):
            UserMessageMsg.model_validate({
                "type": "user_message",
                "thread_id": "t1",
                "content": "hi",
                "selected_niche": "music_dance",
            })


# ---------- ReviewNodeMsg ----------


class TestReviewNodeMsg:
    def test_approve(self):
        msg = ReviewNodeMsg.model_validate({
            "type": "review_node",
            "thread_id": "t1",
            "node_id": "n1",
            "action": "approve",
        })
        assert msg.action == "approve"
        assert msg.feedback is None

    def test_reject_with_feedback(self):
        msg = ReviewNodeMsg.model_validate({
            "type": "review_node",
            "thread_id": "t1",
            "node_id": "n1",
            "action": "reject",
            "feedback": "too dark",
        })
        assert msg.feedback == "too dark"

    def test_invalid_action(self):
        with pytest.raises(ValidationError):
            ReviewNodeMsg.model_validate({
                "type": "review_node",
                "thread_id": "t1",
                "node_id": "n1",
                "action": "maybe",
            })


# ---------- ReorderEdgeMsg ----------


class TestReorderEdgeMsg:
    def test_default_direction_up(self):
        msg = ReorderEdgeMsg.model_validate({
            "type": "reorder_edge",
            "thread_id": "t1",
            "edge_id": "e1",
        })
        assert msg.direction == "up"

    def test_explicit_down(self):
        msg = ReorderEdgeMsg.model_validate({
            "type": "reorder_edge",
            "thread_id": "t1",
            "edge_id": "e1",
            "direction": "down",
        })
        assert msg.direction == "down"

    def test_invalid_direction(self):
        with pytest.raises(ValidationError):
            ReorderEdgeMsg.model_validate({
                "type": "reorder_edge",
                "thread_id": "t1",
                "edge_id": "e1",
                "direction": "left",
            })


# ---------- UpdatePositionMsg ----------


class TestUpdatePositionMsg:
    def test_happy_path(self):
        msg = UpdatePositionMsg.model_validate({
            "type": "update_position",
            "thread_id": "t1",
            "node_id": "n1",
            "x": 100.5,
            "y": 200.0,
        })
        assert msg.x == 100.5

    def test_int_coords_accepted(self):
        # x, y are float — int coerces fine in pydantic
        msg = UpdatePositionMsg.model_validate({
            "type": "update_position",
            "thread_id": "t1",
            "node_id": "n1",
            "x": 100,
            "y": 200,
        })
        assert msg.x == 100.0
        assert msg.y == 200.0

    def test_missing_x(self):
        with pytest.raises(ValidationError):
            UpdatePositionMsg.model_validate({
                "type": "update_position",
                "thread_id": "t1",
                "node_id": "n1",
                "y": 200.0,
            })


# ---------- UpdateNodeStatusMsg ----------


class TestUpdateNodeStatusMsg:
    def test_default_reviewing(self):
        msg = UpdateNodeStatusMsg.model_validate({
            "type": "update_node_status",
            "thread_id": "t1",
            "node_id": "n1",
        })
        assert msg.node_status == "reviewing"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            UpdateNodeStatusMsg.model_validate({
                "type": "update_node_status",
                "thread_id": "t1",
                "node_id": "n1",
                "node_status": "approved",  # 不是 NodeStatus 枚举值
            })


# ---------- OptimizePromptMsg ----------


class TestOptimizePromptMsg:
    def test_happy_path(self):
        msg = OptimizePromptMsg.model_validate({
            "type": "optimize_prompt",
            "thread_id": "t1",
            "node_id": "n1",
            "prompt": "cat",
            "feedback": "make it warmer",
        })
        assert msg.prompt == "cat"


# ---------- Edge / Session boilerplate ----------


class TestEdgeMsgs:
    def test_create_edge(self):
        msg = CreateEdgeMsg.model_validate({
            "type": "create_edge",
            "thread_id": "t1",
            "source": "n1",
            "target": "n2",
        })
        assert msg.source == "n1" and msg.target == "n2"

    def test_delete_edge(self):
        msg = DeleteEdgeMsg.model_validate({
            "type": "delete_edge",
            "thread_id": "t1",
            "edge_id": "e1",
        })
        assert msg.edge_id == "e1"


class TestSessionMsgs:
    def test_delete_session_requires_thread_id(self):
        with pytest.raises(ValidationError):
            DeleteSessionMsg.model_validate({"type": "delete_session"})

    def test_delete_sessions_requires_nonempty_thread_ids(self):
        from agent.transport.ws_messages import DeleteSessionsMsg

        with pytest.raises(ValidationError):
            DeleteSessionsMsg.model_validate({"type": "delete_sessions", "thread_ids": []})
        msg = DeleteSessionsMsg.model_validate(
            {"type": "delete_sessions", "thread_ids": ["a", "b"]}
        )
        assert msg.thread_ids == ["a", "b"]

    def test_get_session_state(self):
        msg = GetSessionStateMsg.model_validate({
            "type": "get_session_state",
            "thread_id": "t1",
        })
        assert msg.thread_id == "t1"


# ---------- WSInbound discriminator ----------


class TestWSInboundDiscriminator:
    """WSInbound = Annotated[Union[...], Field(discriminator="type")]
    — 这是 ws_server 分派的核心 contract,直接测它能否 route 到正确模型。"""

    def test_routes_auth(self):
        msg = _WSInboundAdapter.validate_python({"type": "auth", "user_id": "u1"})
        assert isinstance(msg, AuthMsg)

    def test_routes_execute_node(self):
        msg = _WSInboundAdapter.validate_python({
            "type": "execute_node",
            "thread_id": "t1",
            "node_id": "n1",
            "node_type": "image",
        })
        assert isinstance(msg, ExecuteNodeMsg)

    def test_routes_user_message(self):
        msg = _WSInboundAdapter.validate_python({
            "type": "user_message",
            "thread_id": "t1",
            "content": "hi",
        })
        assert isinstance(msg, UserMessageMsg)

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            _WSInboundAdapter.validate_python({"type": "rename_session", "thread_id": "t1"})

    def test_missing_discriminator_rejected(self):
        with pytest.raises(ValidationError):
            _WSInboundAdapter.validate_python({"user_id": "u1"})


# ---------- Cascade outbound events ----------


class TestAnalysisReturnedEvent:
    """Outbound frame from `cascade_analyze` tool — verifies wire schema sticks."""

    def test_happy_path(self):
        msg = AnalysisReturnedEvent.model_validate({
            "type": "analysis_returned",
            "thread_id": "t1",
            "analysis": {"analysis_id": "ana_x", "scenes": []},
        })
        assert msg.type == "analysis_returned"
        assert msg.analysis["analysis_id"] == "ana_x"

    def test_serialize_round_trip(self):
        msg = AnalysisReturnedEvent(
            type="analysis_returned",
            thread_id="t1",
            analysis={"k": 1, "nested": {"v": 2}},
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "analysis_returned"
        assert dumped["analysis"]["nested"]["v"] == 2
        # round-trips back
        AnalysisReturnedEvent.model_validate(dumped)

    def test_missing_thread_id_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisReturnedEvent.model_validate({
                "type": "analysis_returned",
                "analysis": {},
            })

    def test_missing_analysis_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisReturnedEvent.model_validate({
                "type": "analysis_returned",
                "thread_id": "t1",
            })

    def test_wrong_type_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisReturnedEvent.model_validate({
                "type": "analysis_done",
                "thread_id": "t1",
                "analysis": {},
            })


class TestRewriteReturnedEvent:
    def test_happy_path(self):
        msg = RewriteReturnedEvent.model_validate({
            "type": "rewrite_returned",
            "thread_id": "t1",
            "analysis_id": "ana_x",
            "rewrite": {"rewrite_id": "rw_1", "shots": []},
        })
        assert msg.analysis_id == "ana_x"
        assert msg.rewrite["rewrite_id"] == "rw_1"

    def test_serialize_round_trip(self):
        msg = RewriteReturnedEvent(
            type="rewrite_returned",
            thread_id="t1",
            analysis_id="ana_x",
            rewrite={"rewrite_id": "rw_x", "shots": [{"shot_index": 1}]},
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "rewrite_returned"
        assert dumped["analysis_id"] == "ana_x"
        RewriteReturnedEvent.model_validate(dumped)

    def test_missing_analysis_id_rejected(self):
        with pytest.raises(ValidationError):
            RewriteReturnedEvent.model_validate({
                "type": "rewrite_returned",
                "thread_id": "t1",
                "rewrite": {},
            })


class TestShotFirstFrameReturnedEvent:
    """Outbound frame from `cascade_generate_first_frame` — per-shot image URL push."""

    def test_happy_path(self):
        msg = ShotFirstFrameReturnedEvent.model_validate({
            "type": "shot_first_frame_returned",
            "thread_id": "t1",
            "rewrite_id": "rw_x",
            "shot_index": 2,
            "image_url": "https://cdn/img.png",
        })
        assert msg.shot_index == 2
        assert msg.image_url == "https://cdn/img.png"
        assert msg.rewrite_id == "rw_x"

    def test_serialize_round_trip(self):
        msg = ShotFirstFrameReturnedEvent(
            type="shot_first_frame_returned",
            thread_id="t1",
            rewrite_id="rw_x",
            shot_index=3,
            image_url="https://cdn/img.png",
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "shot_first_frame_returned"
        assert dumped["shot_index"] == 3
        ShotFirstFrameReturnedEvent.model_validate(dumped)

    def test_failure_frame_carries_error_no_url(self):
        # 生成草稿图 leg:失败帧带 error、无 image_url(image_url 现可选,默认 "")。
        msg = ShotFirstFrameReturnedEvent.model_validate({
            "type": "shot_first_frame_returned",
            "thread_id": "t1",
            "rewrite_id": "rw_x",
            "shot_index": 1,
            "error": "草稿图功能还没开通(管理员需配置生图密钥)",
        })
        assert msg.error and "管理员" in msg.error
        assert msg.image_url == ""

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ShotFirstFrameReturnedEvent.model_validate({
                "type": "shot_first_frame_returned",
                "thread_id": "t1",
                "rewrite_id": "rw_x",
                "shot_index": 1,
                "image_url": "https://cdn/img.png",
                "bogus": "x",
            })


class TestAnalysisAnswerReturnedEvent:
    """W4D5: cascade_ask outbound frame. Same `discriminator="type"` rails as
    the other Cascade events, with an `analysis_id` correlator + the original
    `question` echoed back so the frontend doesn't have to remember it."""

    def test_happy_path(self):
        msg = AnalysisAnswerReturnedEvent.model_validate({
            "type": "analysis_answer_returned",
            "thread_id": "t1",
            "analysis_id": "ana_x",
            "question": "为啥这条 BGM 让我想起 90s 港片",
            "answer": "这条 BGM 用了大提琴下行 + 雨声，节拍接近 90s 港片配乐套路。",
        })
        assert msg.analysis_id == "ana_x"
        assert "BGM" in msg.question
        assert "大提琴" in msg.answer

    def test_serialize_round_trip(self):
        msg = AnalysisAnswerReturnedEvent(
            type="analysis_answer_returned",
            thread_id="t1",
            analysis_id="ana_x",
            question="q",
            answer="a",
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "analysis_answer_returned"
        AnalysisAnswerReturnedEvent.model_validate(dumped)

    def test_missing_analysis_id_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisAnswerReturnedEvent.model_validate({
                "type": "analysis_answer_returned",
                "thread_id": "t1",
                "question": "q",
                "answer": "a",
            })

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            AnalysisAnswerReturnedEvent.model_validate({
                "type": "analysis_answer_returned",
                "thread_id": "t1",
                "analysis_id": "ana_x",
                "question": "q",
                "answer": "a",
                "bogus": "x",
            })


# ---------- INBOUND_MODELS registry ----------


class TestInboundModelsRegistry:
    """INBOUND_MODELS 是 ws_handlers HANDLERS 的对账表,确保 type 字符串 / 模型 / handler 三向一致。"""

    def test_all_models_have_matching_type_literal(self):
        """key 必须等于模型的 type Literal 默认值。"""
        for type_str, model_cls in INBOUND_MODELS.items():
            sample = model_cls.model_fields["type"].annotation
            # Literal[X] — get_args 取 X
            from typing import get_args
            literals = get_args(sample)
            assert type_str in literals, (
                f"INBOUND_MODELS['{type_str}'] = {model_cls.__name__} 但 type Literal 是 {literals}"
            )

    def test_registry_includes_auth(self):
        assert INBOUND_MODELS["auth"] is AuthMsg

    def test_registry_has_no_unexpected_keys(self):
        expected = {
            "auth", "list_sessions", "delete_session", "delete_sessions",
            "get_session_state",
            "reorder_edge", "create_edge", "delete_edge", "update_position",
            "review_node", "execute_node", "update_node_status",
            "optimize_prompt", "regenerate_node", "list_node_versions",
            "restore_node_version", "regenerate_script_node",
            "review_decision", "user_message",
        }
        assert set(INBOUND_MODELS) == expected, (
            f"INBOUND_MODELS keys drift: extra={set(INBOUND_MODELS) - expected}, "
            f"missing={expected - set(INBOUND_MODELS)}"
        )

    def test_wsinbound_union_covers_every_inbound_model(self):
        """WSInbound 判别联合必须含 INBOUND_MODELS 里的每个模型 —— 否则 TypeAdapter(WSInbound)
        会误拒一个合法消息(曾漏 DeleteSessionsMsg:在 INBOUND_MODELS/HANDLERS/前端都有、唯独
        不在 union 里)。守住这条防再漂移。"""
        from typing import get_args

        union = get_args(WSInbound)[0]  # Annotated[Union[...], meta] → 取 Union[...]
        members = set(get_args(union))
        missing = set(INBOUND_MODELS.values()) - members
        assert not missing, f"WSInbound union 漏了 INBOUND_MODELS 里的模型: {[m.__name__ for m in missing]}"
