# P2-4 改写输出 · baomam_fushi #1

**源 URL**: https://www.douyin.com/video/7385782607067335962
**源 @作者**: 阿倩
**源日期**: 2024-06-29
**源标题**: 来看看12龄宝宝一周辅食不重样 都吃了些什么😋
**hook_pattern_id**: `H1+H2`
**source_classification**: `positive`
**rewrite_id**: `rw_7cd09ad0e00467ab`
**model**: `p2-4-synth-v1`
**confidence**: 0.75
**cost_cny**: ¥0.4200
**机械检查**: 11/11 通过

## script_markdown

```
### 改写脚本
<!-- 保留:H1+H2 · 来看看12龄宝宝一周辅食不重样 都吃了些什么😋 | hook_pattern_id=H1+H2 | classification=positive | 改:换成宝妈辅食视角和家庭场景 -->
1. 12 月龄宝宝七天辅食,顿顿不一样
   画面:暖色家庭厨房俯拍,餐椅特写,食材碗摆台 · 暖色俯拍,餐椅特写,食材碗
2. 试试换一种食材或工具
   画面:木质砧板特写,妈妈手切食材,自然光 · 砧板/料理台特写
3. 几分钟搞定的小技巧
   画面:蒸锅侧拍,蒸汽升腾,食材若隐若现 · 侧拍灶台,食物变化特写
4. 你家几个月开始吃这个,评论区告诉我
   画面:宝宝面部特写,小手抓勺,餐桌一角 · 宝宝面部特写
```

## shots

- shot 1:
  - dialogue: 12 月龄宝宝七天辅食,顿顿不一样
  - visual: 暖色家庭厨房俯拍,餐椅特写,食材碗摆台 · 暖色俯拍,餐椅特写,食材碗
- shot 2:
  - dialogue: 试试换一种食材或工具
  - visual: 木质砧板特写,妈妈手切食材,自然光 · 砧板/料理台特写
- shot 3:
  - dialogue: 几分钟搞定的小技巧
  - visual: 蒸锅侧拍,蒸汽升腾,食材若隐若现 · 侧拍灶台,食物变化特写
- shot 4:
  - dialogue: 你家几个月开始吃这个,评论区告诉我
  - visual: 宝宝面部特写,小手抓勺,餐桌一角 · 宝宝面部特写

## parser_warnings

- shot 1 anchored to P0 hook template (baomam_fushi)

## 机械检查详情

- ✅ script_length_80_600 — len=335
- ✅ shot_count_3_5 — count=4
- ✅ no_forbidden_terms — leaked=[]
- ✅ confidence_ge_0_5 — conf=0.75
- ✅ rationale_marker_present — checked '保留' + '改' in script
- ✅ visual_diversity_score — max overlap 0.20 (threshold 0.5)
- ✅ nutrient_category_consistency — single category: ['(none)']
- ✅ hook_p0_compliance — shot 1 hits ['H1'] (required any of ['H1', 'H2'])
- ✅ hook_diversity — 3 distinct hooks: ['H1', 'H2', 'H3']
- ✅ negative_hook_absence — no forbidden hooks (['H4'])
- ✅ dish_anchor_present — n/a (not jiating_chufang)
