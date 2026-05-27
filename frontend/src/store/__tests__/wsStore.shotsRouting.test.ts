/**
 * W5D1-T1 — analysis_returned 永远绑源 scenes 到 shots,rewrite_returned
 * 只动 rewriteShots,不再覆盖 shots。保证「源视频每一幕」和「改写后的镜头」
 * 是两套独立数据,以前的 bug(rewrite 把源 scenes 给覆盖了)不会回潮。
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useCanvasStore } from "../canvasStore";
import { useWSStore } from "../wsStore";
import type { CascadeAnalysisContract, Scene } from "../../types/cascade";

const SOURCE_SCENES: Scene[] = [
  {
    scene_index: 1,
    timestamp_start: 0,
    timestamp_end: 3.2,
    scene: "源视频第 1 幕",
    dialogue_and_narration: "源视频第 1 幕的台词",
    visual_content: "源视频第 1 幕的画面",
    subject: null,
    shot_type: "medium",
    camera_movement: "static",
    first_frame_url: null,
    warnings: [],
  },
  {
    scene_index: 2,
    timestamp_start: 3.2,
    timestamp_end: 7.5,
    scene: "源视频第 2 幕",
    dialogue_and_narration: "源视频第 2 幕的台词",
    visual_content: "源视频第 2 幕的画面",
    subject: null,
    shot_type: "close",
    camera_movement: "static",
    first_frame_url: null,
    warnings: [],
  },
];

const FAKE_ANALYSIS = {
  schema_version: "v1.0",
  analysis_id: "ana_test_w5d1_t1",
  source_url: "https://www.douyin.com/video/7000000000000000000",
  platform: "douyin",
  created_at: "2026-05-27T00:00:00Z",
  model: "fixture",
  cost_cny: 0.0,
  duration_s: 7.5,
  viral_analysis: {
    hook: "测试 hook",
    pacing: "测试 pacing",
    climax: "测试 climax",
    visual_style: "测试 visual",
    emotional_arc: "测试 emotion",
    target_audience: "测试 audience",
    engagement_levers: "测试 levers",
    replicable_formula: "测试 formula",
    audio: { bgm: "n/a", voice_pace: "n/a", sound_effects: "n/a" },
    production: { cost_tier: "solo_phone", estimated_hours: 1.0, replaceable_anchors: [] },
  },
  scenes: SOURCE_SCENES,
  warnings: [],
  confidence: 0.85,
  full_transcript: "",
} as unknown as CascadeAnalysisContract;

describe("wsStore shots routing (T1)", () => {
  beforeEach(() => {
    useCanvasStore.getState().clear();
  });

  afterEach(() => {
    useCanvasStore.getState().clear();
  });

  it("analysis_returned binds analysis.scenes to canvasStore.shots", () => {
    useWSStore.getState().dispatch(
      {
        type: "analysis_returned",
        thread_id: useWSStore.getState().currentThreadId || "",
        analysis: FAKE_ANALYSIS,
      },
      "user_test",
    );

    // queueMicrotask used in dispatch — flush
    return Promise.resolve().then(() => {
      const s = useCanvasStore.getState();
      expect(s.analysis?.analysis_id).toBe("ana_test_w5d1_t1");
      expect(s.shots).toHaveLength(2);
      expect(s.shots[0].scene).toBe("源视频第 1 幕");
      expect(s.rewriteShots).toEqual([]);
    });
  });

  it("rewrite_returned writes script + rewriteShots WITHOUT touching shots", async () => {
    // 先种入源 scenes (模拟 analysis_returned 已经发生)
    useCanvasStore.getState().setShots(SOURCE_SCENES);

    useWSStore.getState().dispatch(
      {
        type: "rewrite_returned",
        thread_id: useWSStore.getState().currentThreadId || "",
        analysis_id: "ana_test_w5d1_t1",
        rewrite: {
          rewrite_id: "rw_test",
          script_markdown: "改写后的脚本",
          shots: [
            { shot_index: 1, dialogue: "改写第 1 镜台词", visual: "改写第 1 镜画面" },
            { shot_index: 2, dialogue: "改写第 2 镜台词", visual: "改写第 2 镜画面" },
            { shot_index: 3, dialogue: "改写第 3 镜台词", visual: "改写第 3 镜画面" },
          ],
        },
      } as Parameters<typeof useWSStore.getState.prototype.dispatch>[0],
      "user_test",
    );

    await Promise.resolve();
    const s = useCanvasStore.getState();

    // 源 scenes 必须保留不变
    expect(s.shots).toHaveLength(2);
    expect(s.shots[0].scene).toBe("源视频第 1 幕");
    expect(s.shots[1].scene).toBe("源视频第 2 幕");

    // rewrite 落到独立 state
    expect(s.script).toBe("改写后的脚本");
    expect(s.rewriteShots).toHaveLength(3);
    expect(s.rewriteShots[0].dialogue).toBe("改写第 1 镜台词");
  });
});
