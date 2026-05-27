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

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            UserMessageMsg.model_validate({
                "type": "user_message",
                "thread_id": "t1",
                "content": "",
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
            "auth", "list_sessions", "delete_session", "get_session_state",
            "reorder_edge", "create_edge", "delete_edge", "update_position",
            "review_node", "execute_node", "update_node_status",
            "optimize_prompt", "user_message",
        }
        assert set(INBOUND_MODELS) == expected, (
            f"INBOUND_MODELS keys drift: extra={set(INBOUND_MODELS) - expected}, "
            f"missing={expected - set(INBOUND_MODELS)}"
        )
