# P2-4 改写输出 · baomam_fushi #2

**源 URL**: https://www.douyin.com/video/7616954826602428411
**源 @作者**: 夏天夏了夏天
**源日期**: 2026-03-14
**源标题**: 添加辅食 #宝宝辅食 #厨房小白 #只有宝妈才懂吧
**hook_pattern_id**: `H5+H7`
**source_classification**: `positive`
**rewrite_id**: `rw_f1827e47ff792c68`
**model**: `p2-4-synth-v1`
**confidence**: 0.75
**cost_cny**: ¥0.4200
**机械检查**: 11/11 通过

## script_markdown

```
### 改写脚本
<!-- 保留:H5+H7 · 添加辅食 #宝宝辅食 #厨房小白 #只有宝妈才懂吧 | hook_pattern_id=H5+H7 | classification=positive | 改:换成宝妈辅食视角和家庭场景 -->
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

- ✅ script_length_80_600 — len=337
- ✅ shot_count_3_5 — count=4
- ✅ no_forbidden_terms — leaked=[]
- ✅ confidence_ge_0_5 — conf=0.75
- ✅ rationale_marker_present — checked '保留' + '改' in script
- ✅ visual_diversity_score — max overlap 0.20 (threshold 0.5)
- ✅ nutrient_category_consistency — single category: ['(none)']
- ✅ hook_p0_compliance — shot 1 hits ['H1'] (required any of ['H1', 'H2'])
- ✅ hook_diversity — 2 distinct hooks: ['H1', 'H3']
- ✅ negative_hook_absence — no forbidden hooks (['H4'])
- ✅ dish_anchor_present — n/a (not jiating_chufang)
