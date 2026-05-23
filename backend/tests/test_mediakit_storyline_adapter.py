from __future__ import annotations

import pytest

from agent.cascade.adapter import normalize_analysis_result
from agent.cascade.contract import CascadeAnalysisContract
from agent.cascade.failures import FailureCode, HardFailure
from agent.cascade.mediakit.storyline_adapter import storyline_to_payload


def _storyline_result() -> dict:
    return {
        "duration": 36.4,
        "source_video_info": [
            {
                "source_video_title": "一岁宝宝一周辅食不重样",
                "source_video_summary": "用一周不重样辅食解决宝宝挑食,结尾宝宝主动抢勺子。",
                "source_video_tag": ["宝宝辅食", "一周不重样", "营养搭配"],
            }
        ],
        "storyline_clips": [
            {
                "clip_index": 2,
                "clip_start_time": 12.0,
                "clip_end_time": 24.0,
                "clip_title": "妈妈蒸苹果泥",
                "clip_summary": "厨房暖光,妈妈把苹果切块后上锅蒸。",
                "clip_dialogue": "蒸八分钟,又软又香。",
                "clip_score": 3.8,
                "clip_snapshot_url": "https://cdn.test/clip2.jpg",
            },
            {
                "clip_index": 1,
                "clip_start_time": 0.0,
                "clip_end_time": 12.0,
                "clip_title": "宝宝拒绝第一口",
                "clip_summary": "宝宝坐在餐椅上转头,桌上有一碗辅食。",
                "clip_dialogue": "你家宝宝是不是也这样,怎么喂都不吃?",
                "clip_score": 4.0,
            },
            {
                "clip_index": 3,
                "clip_start_time": 24.0,
                "clip_end_time": 36.4,
                "clip_title": "宝宝主动抢勺子",
                "clip_summary": "宝宝笑着伸手抢勺子,妈妈在镜头外笑。",
                "clip_dialogue": "这一口下去,妈妈真的松了一口气。",
                "clip_score": 4.6,
            },
        ],
        "storyline_highlights": [
            {
                "highlight_title": "拒食到抢勺子的反差",
                "highlight_summary": "先给痛点,中段给做法,最后用宝宝主动吃形成反差。",
            }
        ],
    }


def test_storyline_payload_validates_as_contract() -> None:
    payload = storyline_to_payload(
        _storyline_result(),
        source_url="https://www.douyin.com/video/7385782607067335962",
        user_id="user_1",
    )

    contract = normalize_analysis_result(payload)

    assert isinstance(contract, CascadeAnalysisContract)
    assert contract.model == "mediakit-storyline"
    assert contract.duration_s == 36
    assert contract.platform.value == "douyin"
    assert [scene.scene for scene in contract.scenes] == [
        "宝宝拒绝第一口",
        "妈妈蒸苹果泥",
        "宝宝主动抢勺子",
    ]
    assert str(contract.scenes[1].first_frame_url) == "https://cdn.test/clip2.jpg"


def test_missing_snapshot_is_allowed() -> None:
    result = _storyline_result()
    for clip in result["storyline_clips"]:
        clip.pop("clip_snapshot_url", None)

    contract = normalize_analysis_result(
        storyline_to_payload(result, source_url="https://xhslink.com/a", user_id="user_1")
    )

    assert contract.platform.value == "xiaohongshu"
    assert all(scene.first_frame_url is None for scene in contract.scenes)


def test_missing_source_info_falls_back_to_scene_text() -> None:
    result = _storyline_result()
    result["source_video_info"] = []
    result["storyline_highlights"] = []

    contract = normalize_analysis_result(
        storyline_to_payload(result, source_url="https://example.com/video.mp4", user_id="user_1")
    )

    assert contract.platform.value == "other"
    assert contract.viral_analysis.replicable_formula
    assert contract.viral_analysis.target_audience == "目标人群待补充"


def test_multiple_source_infos_uses_first() -> None:
    result = _storyline_result()
    result["source_video_info"].insert(
        0,
        {
            "source_video_title": "第一条标题",
            "source_video_summary": "第一条摘要",
            "source_video_tag": ["第一"],
        },
    )

    contract = normalize_analysis_result(
        storyline_to_payload(result, source_url="https://example.com/video.mp4", user_id="user_1")
    )

    assert contract.viral_analysis.hook == "第一条标题"
    assert contract.viral_analysis.target_audience == "第一"


def test_empty_storyline_clips_raise_s5() -> None:
    result = _storyline_result()
    result["storyline_clips"] = []

    with pytest.raises(HardFailure) as exc:
        storyline_to_payload(result, source_url="https://example.com/video.mp4", user_id="user_1")

    assert exc.value.code == FailureCode.S5_INVALID_PAYLOAD


def test_clip_ordering_by_start_time() -> None:
    payload = storyline_to_payload(
        _storyline_result(),
        source_url="https://example.com/video.mp4",
        user_id="user_1",
    )

    assert [scene["timestamp_start"] for scene in payload["scenes"]] == [0.0, 12.0, 24.0]
    assert [scene["scene_index"] for scene in payload["scenes"]] == [1, 2, 3]
