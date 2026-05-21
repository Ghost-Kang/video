// Cascade Topic Intelligence — TypeScript mirror.
// Source of truth: backend/src/agent/cascade/topic_intelligence.py
// Spec: docs/TOPIC_INTELLIGENCE_DEEPENING_PLAN.md
// Karpathy §14.7: every ScoreSignal carries 5 mandatory attributes.

export const TIP_SCHEMA_VERSION = 'tip-0.2' as const;

export type SignalSource =
  | 'hotspot_60s'
  | 'newrank'
  | 'toprador_video_analysis'
  | 'douyin_hotspot_bao'
  | 'douyin_official_hot_videos'
  | 'xhs_creator_center'
  | 'xhs_pugongying'
  | 'xhs_spotlight'
  | 'xhs_qianfan'
  | 'xhs_third_party'
  | 'user_manual_input'
  | 'ocr_screenshot'
  | 'llm_inference'
  | 'rule_derived';

export type TrendStage = 'rising' | 'peak' | 'declining' | 'unknown';

export type TopicPlatform = 'douyin' | 'xiaohongshu';

export type PredictionMethod = 'rule' | 'lightgbm' | 'transformer' | 'mock';

/** Per Karpathy §14.7: every scored field carries these 5 attributes. */
export interface ScoreSignal {
  value: number; // 0..100
  source: SignalSource;
  confidence: number; // 0..1
  explanation: string | null;
  user_visible: boolean;
  used_in_ranking: boolean;
  fallback_used: boolean;
}

export interface RecommendationSignals {
  hook_strength: ScoreSignal;
  completion_potential: ScoreSignal;
  interaction_potential: ScoreSignal;
  share_collect_potential: ScoreSignal;
  negative_feedback_risk: ScoreSignal;
}

export interface BusinessSignals {
  account_fit: ScoreSignal;
  commercial_value: ScoreSignal;
  saturation_risk: ScoreSignal;
  brand_safety_risk: ScoreSignal;
}

export interface PlatformPrediction {
  platform: TopicPlatform;
  opportunity_score: ScoreSignal;
  prediction_method: PredictionMethod;
  model_version: string;
  top_10_prob: number | null;
  top_1_prob: number | null;
  pred_completion_rate: number | null;
  pred_interaction_rate: number | null;
}

export interface AccountFit {
  fit_score: ScoreSignal;
  matched_audience: string[];
  historical_best_dna: string[];
  commercial_goal_match: 'high' | 'medium' | 'low' | 'unknown';
  risk_notes: string[];
}

export interface ReplicationBlueprint {
  required_materials: string[];
  script_formula: string;
  shot_plan: string[];
  estimated_difficulty: 'low' | 'medium' | 'high';
}

export interface ViralMechanism {
  hook_type: string | null;
  pain_point: string | null;
  emotion_tags: string[];
  comment_trigger: string | null;
  replication_requirements: string[];
  risk_notes: string[];
  source: SignalSource;
  confidence: number;
  extracted_from_analysis_id: string | null;
}

export interface OfficialSignals {
  source: SignalSource;
  official_hotspot_score: ScoreSignal;
  is_rising: boolean;
  is_low_follower_hit: boolean;
  is_official_activity: boolean;
  related_video_count: number | null;
  trend_stage: TrendStage;
  comment_keywords: string[];
}

export interface XhsSignals {
  source: SignalSource;
  xhs_seed_score: ScoreSignal;
  search_trend_score: ScoreSignal;
  collect_rate_score: ScoreSignal;
  comment_quality_score: ScoreSignal;
  long_tail_growth_score: ScoreSignal;
  commercial_conversion_score: ScoreSignal;
  note_format: string | null;
  recommended_cover_style: string | null;
}

export interface DeepTopicIntelligence {
  schema_version: 'tip-0.2';
  opportunity_score: ScoreSignal;
  recommendation_signals: RecommendationSignals;
  business_signals: BusinessSignals;
  prediction: PlatformPrediction;
  official_signals: OfficialSignals | null;
  xhs_signals: XhsSignals | null;
  explain: string[]; // ≤3 entries
}

export interface TopicBrief {
  schema_version: 'tip-0.2';
  topic: string;
  why_now: string[]; // ≤5
  target_audience: string[]; // ≤8
  viral_mechanism: ViralMechanism;
  replication_blueprint: ReplicationBlueprint;
  account_fit: AccountFit | null;
  constraints: Record<string, string>;
  deep_intelligence: DeepTopicIntelligence;
  created_at: string; // RFC3339
  derived_from_analysis_id: string | null;
}

export interface PerformanceSnapshot {
  schema_version: 'tip-0.2';
  platform: TopicPlatform;
  opus_id: string;
  account_id: string | null;
  minutes_after_publish: number;
  captured_at: string; // RFC3339
  source: SignalSource;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  collects: number | null;
  followers_gain: number | null;
  completion_rate: number | null; // 0..1
  avg_watch_time_sec: number | null;
  replay_rate: number | null; // 0..1
  negative_feedback_rate: number | null; // 0..1
}
