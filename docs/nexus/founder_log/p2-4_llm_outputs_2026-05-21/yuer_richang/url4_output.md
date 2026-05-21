# P2-4 改写输出 · yuer_richang #4

**源 URL**: https://www.douyin.com/video/7551614334665755919
**源 @作者**: 薇薇安
**源日期**: 2025-09-19
**源标题**: 刷短视频是怎么让大脑变笨的
**hook_pattern_id**: `H4`
**source_classification**: `positive`
**rewrite_id**: `rw_fee8377cc0d71429`
**model**: `p2-4-synth-v1`
**confidence**: 0.75
**cost_cny**: ¥0.4200
**机械检查**: 10/11 通过

## script_markdown

```
### 改写脚本
<!-- 保留:H4 · 刷短视频是怎么让大脑变笨的 | hook_pattern_id=H4 | classification=positive | 改:换成育儿日常视角和家庭场景 -->
1. 当妈以后才发现,最累的不是熬夜,是没人懂
   画面:夜灯昏黄,卧室广角,凌晨时钟若隐若现 · 夜灯昏黄,卧室广角
2. 当妈以后才发现,真累的是没人理解
   画面:妈妈侧脸特写,自拍角度,情绪沉重 · 妈妈侧脸,自拍角度
3. 他突然说了句让我破防的话
   画面:孩子局部特写,小手或睡颜,被子细节 · 孩子局部特写,小手小脚
4. 你被娃哪句话戳过,评论区聊聊
   画面:母子靠在一起中景,日光从窗外漏进 · 妈妈和娃靠在一起
```

## shots

- shot 1:
  - dialogue: 当妈以后才发现,最累的不是熬夜,是没人懂
  - visual: 夜灯昏黄,卧室广角,凌晨时钟若隐若现 · 夜灯昏黄,卧室广角
- shot 2:
  - dialogue: 当妈以后才发现,真累的是没人理解
  - visual: 妈妈侧脸特写,自拍角度,情绪沉重 · 妈妈侧脸,自拍角度
- shot 3:
  - dialogue: 他突然说了句让我破防的话
  - visual: 孩子局部特写,小手或睡颜,被子细节 · 孩子局部特写,小手小脚
- shot 4:
  - dialogue: 你被娃哪句话戳过,评论区聊聊
  - visual: 母子靠在一起中景,日光从窗外漏进 · 妈妈和娃靠在一起

## parser_warnings

- shot 1 anchored to P0 hook template (yuer_richang)

## 机械检查详情

- ✅ script_length_80_600 — len=326
- ✅ shot_count_3_5 — count=4
- ✅ no_forbidden_terms — leaked=[]
- ✅ confidence_ge_0_5 — conf=0.75
- ✅ rationale_marker_present — checked '保留' + '改' in script
- ✅ visual_diversity_score — max overlap 0.08 (threshold 0.5)
- ✅ nutrient_category_consistency — n/a (not baomam_fushi)
- ✅ hook_p0_compliance — shot 1 hits ['H8'] (required any of ['H8'])
- ❌ hook_diversity — 1 distinct hooks: ['H8']
- ✅ negative_hook_absence — no forbidden hooks (['H2'])
- ✅ dish_anchor_present — n/a (not jiating_chufang)
