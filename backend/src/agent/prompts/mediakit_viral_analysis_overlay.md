You are analyzing a Chinese short-video for Cascade.

Return only one valid JSON object. Do not wrap it in Markdown.

Required keys:
- hook
- pacing
- climax
- visual_style
- emotional_arc
- target_audience
- engagement_levers
- replicable_formula

Constraints:
- Values must be concise Chinese strings.
- hook/pacing/climax/visual_style/emotional_arc/target_audience/engagement_levers: at most 80 Chinese characters each.
- replicable_formula: at most 120 Chinese characters.
- Use the MediaKit storyline text as the primary evidence.
- Use the video frames only to refine what the storyline cannot tell.
- Prefer creator-actionable wording over abstract critique.

Storyline context:
{{storyline_context}}
