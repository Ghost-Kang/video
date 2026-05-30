// Cascade analysis contract — TypeScript mirror of backend Pydantic types.
// Source of truth: docs/TOPRADOR_SCHEMA.md
// Keep in sync with backend/src/agent/cascade/contract.py

export const SCHEMA_VERSION = '1.0' as const;
export const LOW_CONFIDENCE_THRESHOLD = 0.5;

export type Platform = 'douyin' | 'xiaohongshu' | 'other';

export type ShotType =
  | 'close_up'
  | 'medium'
  | 'wide'
  | 'aerial'
  | 'pov'
  | 'unknown';

export type CameraMovement =
  | 'static'
  | 'push'
  | 'pull'
  | 'pan'
  | 'tilt'
  | 'tracking'
  | 'handheld'
  | 'unknown';

export type Severity = 'info' | 'warn' | 'error';

export interface Warning_ {
  code: string;
  field: string;
  message: string;
  severity: Severity;
}

export interface AudioDim {
  bgm: string;
  voice_pace: string;
  sound_effects: string;
}

export type CostTier = 'solo_phone' | 'small_team' | 'post_heavy';

export interface ProductionDim {
  cost_tier: CostTier;
  estimated_hours: number;
  replaceable_anchors: string[];
}

export interface ViralAnalysis {
  // toprador 爆点 10 维(渲染用)
  summary: string;
  theme: string;
  target_audience: string;
  material_benefit: string;
  hook: string;
  main_elements: string;
  micro_innovation: string;
  pain_points: string;
  emotion_trigger: string;
  bgm_style: string;
  // 遗留(改写暂挂期保留,不渲染)
  pacing?: string;
  climax?: string;
  visual_style?: string;
  emotional_arc?: string;
  engagement_levers?: string;
  replicable_formula?: string;
  audio?: AudioDim | null;
  production?: ProductionDim | null;
}

export interface Scene {
  scene_index: number;
  timestamp_start: number;
  timestamp_end: number;
  // toprador 视频分析维度
  theme: string;
  segment_note: string;
  segment_description: string;
  dialogue_and_narration: string;
  emotion: string;
  visual_summary: string;
  visual_content: string;
  audio_summary: string;
  audio_content: string;
  cinematography: string;
  camera_position: string;
  actors: string;
  on_screen_text: string;
  visual_presentation_style: string;
  scene: string;
  props_list: string;
  costume: string;
  lighting_and_color: string;
  // 遗留(可选)
  subject?: string | null;
  shot_type?: ShotType;
  camera_movement?: CameraMovement;
  first_frame_url: string | null;
  warnings: Warning_[];
}

export interface CascadeAnalysisContract {
  schema_version: '1.0';
  analysis_id: string;
  source_url: string;
  platform: Platform;
  created_at: string; // RFC3339
  model: string;
  cost_cny: number;
  duration_s: number;
  video_summary: string;
  viral_analysis: ViralAnalysis;
  scenes: Scene[];
  warnings: Warning_[];
  confidence: number; // 0..1
  full_transcript: string;
}

// ============================================================================
// Error envelope (HardFailure.to_payload() over the wire)
// ============================================================================

export type RecoveryAction =
  | 'RETRY_SAME_URL'
  | 'RETRY_SAME_URL_AFTER_30S'
  | 'RETRY_SAME_URL_AFTER_60S'
  | 'RETRY_WITH_NEW_URL'
  | 'PICK_FROM_FEATURED'
  | 'RELOAD'
  | 'REPORT';

export const ACTION_LABELS: Record<RecoveryAction, string> = {
  RETRY_SAME_URL: '再试一次',
  RETRY_SAME_URL_AFTER_30S: '30 秒后重试',
  RETRY_SAME_URL_AFTER_60S: '1 分钟后重试',
  RETRY_WITH_NEW_URL: '换一条爆款链接',
  PICK_FROM_FEATURED: '从今日精选挑一条',
  RELOAD: '刷新页面',
  REPORT: '告诉我们这条',
};

export type FailureCode =
  | 'S1_NO_SOURCE_URL'
  | 'S2_VERSION_MISMATCH'
  | 'S3_NO_FORMULA'
  | 'S4_SCENES_LEN_OUT_OF_RANGE'
  | 'S5_INVALID_PAYLOAD'
  | 'S6_NEGATIVE_COST'
  | 'S7_UPSTREAM_TIMEOUT'
  | 'S8_UPSTREAM_REFUSED'
  | 'S11_INTERNAL_ERROR';

/** Production-safe error payload — never includes debug_detail. */
export interface FailurePayload {
  code: FailureCode;
  hint: string;
  actions: RecoveryAction[];
  request_id: string;
  /** Only present in dev/staging — never trust this for UI rendering. */
  debug_detail?: string;
}
