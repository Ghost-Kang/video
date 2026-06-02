export const COPY = {
  script_header: "改完的版本",
  shots_header: "镜头草稿",
  source_shots_header: "源视频每一幕",
  rewrite_shots_header: "改写后的镜头",
  publish_header: "准备发出去",
  hook_label: "开头怎么抓人",
  pacing_label: "中间为什么不快进",
  climax_label: "结尾为什么忍不住点赞",
  formula_label: "可复制套路 · 照这个骨架改",
  spread_label: "谁会忍不住转发评论",
  shot_label_prefix: "第",
  shot_label_suffix: "段",
  shot_dialogue_placeholder: "（这段没有台词，是画面）",
  anchor_picker_title: "你之前用过的",
  anchor_character_label: "角色",
  anchor_scene_label: "场景",
  copy_button: "一键复制，去发",
  copy_success: "复制好了，去抖音粘贴吧",
  empty_state:
    "还没有分析内容。在左侧聊天里发一条爆款链接，或从今日精选里挑一条。",
  low_confidence_banner: "系统对这条分析的把握一般，仅供参考",
  why_viral_header: "为什么这条会火",

  // ── toprador 对齐:爆点分析 + 视频分析 维度标签(2026-05-30)────────
  viral_header: "爆点分析",
  video_analysis_header: "视频分析",
  va_theme: "主题",
  va_summary: "总结",
  va_target_audience: "目标人群",
  va_material_benefit: "素材利益点",
  va_hook: "钩子",
  va_main_elements: "主要视频元素",
  va_micro_innovation: "微创新方向",
  va_pain_points: "痛点需求",
  va_emotion_trigger: "情绪触发",
  va_bgm_style: "BGM 风格",
  sc_segment_note: "分段说明",
  sc_dialogue: "片段和口播",
  sc_visual: "视觉内容",
  sc_audio: "听觉内容",
  sc_cinematography: "摄影",
  sc_camera_position: "机位",
  sc_actors: "演员",
  sc_on_screen_text: "画面文字",
  sc_presentation: "画面表现形式",
  sc_scene: "场景",
  sc_props: "道具清单",
  sc_costume: "服装造型",
  sc_lighting: "光影与色彩",
  sc_emotion: "情感",
  change_character: "换个角色",
  reuse_scene: "用我之前的场景",
  edit_script: "改一改",
  save_script: "保存",
  pro_view_label: "流程视图",
  card_view_label: "卡片视图",
  suggested_titles: "标题备选",
  tags_label: "话题标签",

  onboarding_title: "粘条爆款链接,看懂它为什么火",
  onboarding_subtitle: "粘一条链接,通常一分钟内看懂它为什么火",
  onboarding_step1_title: "粘条爆款链接",
  onboarding_step1_desc: "抖音链接,直接复制粘贴(整段分享文案也行)",
  onboarding_step2_title: "看完整拆解",
  onboarding_step2_desc: "爆点分析 + 逐幕视频分析,看懂这条为什么火",

  // niche_* 仅供暂挂的改写基建(nicheStore.NICHE_LABELS)引用,不在任何页面渲染。
  niche_baomam: "宝妈辅食",
  niche_yuer: "育儿日常",
  niche_kitchen: "家庭厨房",

  sample_url_label: "想先试试?挑一条真实样例",
  sample_try_prefix: "试一条",

  chat_placeholder_empty: "粘一条抖音爆款链接到这里 ↓",
  chat_placeholder_followup: "想改哪里,直接说",
  chat_quick_continue: "继续下一步",
  chat_quick_hook: "开头再抓",
  chat_quick_oral: "更口语",

  shot_generate_first_frame: "生成首帧",
  shot_generating_first_frame: "正在生成…",
  // 生成草稿图 leg(改写镜头的画面参考)
  shot_draft_generate: "生成草稿图",
  shot_draft_generating: "正在生成草稿图…",
  shot_draft_retry: "重试",
  // 前端兜底超时文案(正常失败用后端下发的友好提示;这条只在帧丢失时出现)。
  shot_draft_timeout: "生成有点慢,点重试试试",
  // 图生视频 leg(草稿图 → 视频)
  shot_video_generate: "生成视频",
  shot_video_generating: "生成视频中·约几分钟",
  shot_video_timeout: "视频生成有点久,点重试",
  // 合成整片
  film_compose: "合成整片",
  film_composing: "合成整片中…",
  film_header: "成片",
  film_timeout: "合成有点久,点重试",
  film_retry: "重试",

  rewrite_cta_header: "改成你自己的版本",
  rewrite_cta_hint: "套用这条的爆款骨架, 帮你改成你自己的脚本 — 想拍什么主题填一句(选填)",
  rewrite_topic_placeholder: "想拍什么?一句话,如「免烤提拉米苏」(留空也行)",
  rewrite_cta_button: "改成我的版本",

  duration_hint: "建议 ≤ 3 分钟·最佳 15-90 秒",
  duration_too_long_fallback: "这条视频过长,建议先剪到 3 分钟内再来分析",
  duration_too_short_fallback: "视频太短,没什么可分析的",
  ask_acknowledge: "好的,问下面这个",

  audio_header: "音频拆解",
  audio_bgm_label: "BGM",
  audio_pace_label: "口播 / 语速",
  audio_sfx_label: "音效",

  detail_drawer_label: "想还原拍摄细节?",
  detail_drawer_hint: "原片逐镜、台词、音频、成本 — 想照着拍才需要,默认收起",

  your_version_header: "你的版本",
  your_version_waiting: "正在帮你改成你自己的版本…",

  transcript_header: "完整原片台词",
  transcript_expand: "展开",
  transcript_collapse: "收起",
  transcript_copy: "复制",
  transcript_copied: "已复制完整台词",

  production_header: "拍这条要花多少",
  production_cost_solo: "一个人 + 手机",
  production_cost_team: "小团队",
  production_cost_heavy: "重后期",
  production_hours_suffix: "h",
  production_replaceable_header: "能换成你自己的",

  ask_chip_label: "问点别的",
  ask_placeholder: "比如:这条 BGM 给人什么感觉?",
  ask_submit: "发问",
  ask_hint: "针对刚才的分析提任何问题",

  // ── 右侧面板 5 状态(W5D3 重设计)─────────────────────────────
  // 状态标题 — 替换原来的「问导演」,告诉用户「右侧现在能干什么」
  side_title_idle: "先发一条链接",
  side_title_running: "正在拆解…",
  side_title_failed: "这条没拿下,换一条试试",
  side_title_ready: "分析好了 →",
  side_title_refine: "想改哪儿就告诉我",

  // 状态 1:等待粘链接
  side_idle_hint: "贴一条爆款链接,我先帮你拆解为什么火",
  side_idle_sample_label: "或者直接挑一条试试",

  // 状态 2:拆解中(进度可视化)
  side_running_eta_prefix: "约 ",
  side_running_eta_suffix: " 秒",
  side_running_finishing: "马上好了…",
  side_running_stage_fetch: "解析链接",
  side_running_stage_analyze: "拆解视频",
  side_running_stage_finalize: "整理输出",
  side_running_done_mark: "✓",
  side_running_pending_mark: "○",

  // ── 分析中沉浸态(AnalyzingHero,主画面)──────────────────────────
  // 把「用户刚点的那条」连续地带进等待态:封面 + 逐幕扫描 + 已拆出的钩子。
  analyzing_hero_title_case: "正在拆解你刚点的这条",
  analyzing_hero_title_generic: "正在拆解你这条",
  analyzing_hero_subtitle: "AI 正在一幕一幕看完它,找出它为什么火 —— 多数 1 分钟内出结果",
  analyzing_hero_scanning: "逐幕扫描中",
  analyzing_hero_scene_prefix: "第 ",
  analyzing_hero_scene_suffix: " 幕",
  analyzing_hero_hook_label: "已经拆出的钩子",
  analyzing_hero_generic_note: "你粘的这条正在逐幕进入分析,马上把「为什么火」摆给你看",
  // dock running 降级提示(进度真理之源已上移到主画面 AnalyzingHero)
  side_running_dock_hint: "正在逐幕拆解,进度和实时画面在上方 ↑",

  // 状态 3:出错了
  side_failed_retry_sample: "再试一条样本",
  side_failed_report: "告诉客服这条",
  side_failed_code_prefix: "错误代码 ",

  // 状态 4:分析好了(改写暂挂 — 不再引导挑方向改写)
  side_ready_headline: "分析好了 →",
  side_ready_hint: "左侧是完整拆解:爆点分析 + 逐幕视频分析,往下滑看每一幕。有问题直接问我。",

  // 状态 5(refine)输入框 placeholder — 替换原「想改哪里,直接说」
  side_refine_placeholder: "想改哪儿就告诉我,比如「开头再短一点」",

  // ── 95% pin escape(W5D3 founder feedback;W6 话术反转)──────────
  // 进度条卡 95% 超过 90s 时,顶出来一段软提示。
  // 旧文案「比预期慢,要不要换一条试试?」在用户焦虑时把锅甩给这条视频/用户的选择;
  // 改成安抚 + 解释(信息量大=拆得更值),并把「继续等」升为推荐主操作、「换一条」降为次选。
  pin_escape_warning: "这条信息量有点大,AI 还在逐幕抠细节 —— 已经到最后一步了,再给它一点点时间。",
  pin_escape_switch: "换一条",
  pin_escape_wait: "继续等",

  // ── 底部 dock(W5D3 layout reform)─────────────────────────────
  dock_collapse_label: "收起对话",
  dock_expand_label: "展开对话",
  dock_history_label: "历史",
  // pro-view 画布创作对话 dock(CanvasChatDock)
  canvas_dock_title: "对话创作",
  canvas_dock_hint: "告诉导演你想做什么 —— 比如「做一支 30 秒赛博朋克短片,主角是男侦探」。导演会在画布上搭好 策划书 → 角色 → 场景 → 分镜 → 视频,你逐个审核、生成。",
  canvas_dock_placeholder: "描述你想创作的视频…",
  canvas_dock_thinking_prefix: "导演正在",
  messages_overlay_title: "对话历史",
  messages_overlay_close: "收起历史",
  url_show_full: "展开完整链接",
  url_show_short: "收起完整链接",

  // 超时/系统繁忙的同义 hint — 用在前端启发式合成的 FailurePayload 上。
  synth_failure_timeout_hint: "拆解超时了,刚才那条视频上游没响应。换一条样本试试,或者 1 分钟后再来一次。",
  synth_failure_refused_hint: "上游暂时繁忙拒绝了这条,换一条样本试试。",

  // ── 原视频脚本抽屉(2026-05-31)──────────────────────────────────
  script_entry: "原视频脚本",
  script_drawer_title: "原视频脚本",
  script_drawer_subtitle: "照着这个骨架,能复刻这条视频",
  script_tab_shots: "分镜脚本",
  script_tab_transcript: "逐字稿",
  script_shot_field_shot: "景别 / 运镜",
  script_shot_field_visual: "画面",
  script_shot_field_dialogue: "台词",
  script_shot_field_props: "道具 / 服装",
  script_shot_field_scene: "场景",
  script_shot_field_light: "光影色彩",
  script_shot_field_audio: "听觉",
  script_shot_field_actors: "出镜",
  script_shots_count_suffix: "镜",
  script_transcript_empty: "这条没有逐字稿",
  script_copy: "复制脚本",
  script_copied: "已复制 ✓",
  script_close: "关闭",

  // ── 逐幕视频片段(2026-05-31)────────────────────────────────────
  clip_play_label: "播放这一幕",
  clip_loading: "加载中…",
  clip_poster_only: "仅首帧",

  // ── 数据条(暖色科技重设计 2026-05-31)──────────────────────────
  stat_scenes: "镜头",
  stat_duration: "时长",
  stat_confidence: "把握",
  stat_duration_unit: "秒",

  // ── 链接校验 + 引导(2026-05-31 入口改版)──────────────────────
  url_placeholder_a: "粘抖音链接,或整段分享文案都行",
  url_placeholder_b: "抖音 App:分享 → 复制链接,直接粘这里",
  link_ok_full: "认出抖音链接",
  link_ok_short: "认出抖音短链 · 会自动展开",
  link_err_platform_prefix: "目前只支持抖音,",
  link_err_platform_suffix: " 还在排期。先粘一条抖音视频试试 →",
  link_err_unknown: "没认出抖音视频链接。把抖音「分享 → 复制链接」整段贴进来,或粘 www.douyin.com/video/… 的网址",
  link_help_toggle: "不确定怎么复制?看这里",
  link_help_desktop_t: "电脑最稳",
  link_help_desktop_d: "抖音网页版进入视频,复制地址栏 www.douyin.com/video/… 粘进来。",
  link_help_app_t: "手机也行",
  link_help_app_d: "抖音 App 点「分享 → 复制链接」,整段文案直接粘,我们会自动认出里面的链接(含短链)。",

  // ── 时长甜蜜点 chip(2026-05-31)────────────────────────────────
  duration_chip_title: "时长甜蜜点",
  duration_chip_best: "拆得最透",
  duration_chip_sub: "15–90 秒信息最足,拆出来最过瘾;5 秒以下太短、3 分钟以上拆不了",

  // ── 样例案例预览轮播(2026-05-31)──────────────────────────────
  sample_cases_header: "没有链接?先看看我们能拆出什么",
  sample_case_tag: "真实拆解",
  sample_case_hook: "钩子",
  sample_case_cta: "看 AI 怎么逐幕拆这条",
} as const;

/** Terms that must never appear in card-stack UI copy or DOM. */
export const FORBIDDEN_TERMS = [
  "节点",
  "锚点",
  "DAG",
  "agent",
  "Agent",
  "画布",
  "AI",
  "平台",
  "工具",
  "智能",
  "pipeline",
  "workflow",
] as const;

// Safe display synonyms. Analysis content (hook / pacing / replicable_formula
// 等) is upstream LLM text and may legitimately contain a banned substring —
// e.g. 辅食配方「换工具」里的「工具」。We scrub at the UI boundary so the brand
// guardrail (FORBIDDEN_TERMS never in DOM) holds regardless of what the model
// emitted, without mangling the creator-facing meaning.
const UI_TERM_REPLACEMENTS: Record<string, string> = {
  节点: "环节",
  锚点: "素材",
  DAG: "流程",
  agent: "助手",
  Agent: "助手",
  画布: "画面",
  AI: "",
  平台: "渠道",
  工具: "用具",
  智能: "顺手",
  pipeline: "流程",
  workflow: "流程",
};

/** Replace any UI-forbidden term in upstream/analysis text with a safe synonym. */
export function scrubUiForbidden(text: string): string {
  let out = text ?? "";
  for (const term of FORBIDDEN_TERMS) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    out = out.replace(new RegExp(escaped, "gi"), UI_TERM_REPLACEMENTS[term] ?? "");
  }
  return out;
}

// 分析侧 hook/climax 常以钩子分类码开头(如「H4 发现孩子落水…」「H6 夏天+童年…」),
// 有时还带前导「+」(模型实测「+H8 家庭温情+情绪共鸣」)。那是内部 hook taxonomy
// (hook_taxonomy.py),不该出现在创作者看见的「为什么火」或发布包标题里。剥掉句首
// 「[+/空白]* H<1-2 位数字> <分隔符>」前缀即可;正文里偶然的「H4」(不在句首)不动。
export function stripHookCode(text: string): string {
  return (text ?? "").replace(/^[\s+＋]*H\d{1,2}\s*[:：·、.\-—\s]*/, "").trim();
}
