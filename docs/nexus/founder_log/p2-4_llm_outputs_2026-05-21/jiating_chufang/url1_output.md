# P2-4 改写输出 · jiating_chufang #1

**源 URL**: https://www.douyin.com/video/6664336625771744520
**源 @作者**: 美食作家王刚
**源日期**: 2019-03-04
**源标题**: (unknown)
**hook_pattern_id**: `H4`
**source_classification**: `positive`
**rewrite_id**: `rw_89306f42780f6ac2`
**model**: `p2-4-synth-v1`
**confidence**: 0.75
**cost_cny**: ¥0.4200
**机械检查**: 11/11 通过

## script_markdown

```
### 改写脚本
<!-- 保留:H4 · jiating_chufang 改写源 #1 | hook_pattern_id=H4 | classification=positive | 改:换成家庭厨房视角和家庭场景 -->
1. 你以为家常红烧肉很难做,其实关键就一步
   画面:自家厨房台面俯拍,菜单照对比,价签特写 · 自家厨房台面,手机/菜单照
2. 为什么牛肉要逆纹切,顺纹一刀就老
   画面:砧板食材近景,刀工手部特写,光线侧射 · 俯拍砧板,食材特写
3. 热锅冷油,30 秒变色
   画面:炒锅侧拍,火光跳跃,油烟升腾 · 侧拍炒锅,火光特写
4. 这一道你家做不做,留言告诉我
   画面:成品装盘近景,斜 45° 蒸汽特写,拉丝/出汁 · 成品装盘俯拍,拉丝/出汁
```

## shots

- shot 1:
  - dialogue: 你以为家常红烧肉很难做,其实关键就一步
  - visual: 自家厨房台面俯拍,菜单照对比,价签特写 · 自家厨房台面,手机/菜单照
- shot 2:
  - dialogue: 为什么牛肉要逆纹切,顺纹一刀就老
  - visual: 砧板食材近景,刀工手部特写,光线侧射 · 俯拍砧板,食材特写
- shot 3:
  - dialogue: 热锅冷油,30 秒变色
  - visual: 炒锅侧拍,火光跳跃,油烟升腾 · 侧拍炒锅,火光特写
- shot 4:
  - dialogue: 这一道你家做不做,留言告诉我
  - visual: 成品装盘近景,斜 45° 蒸汽特写,拉丝/出汁 · 成品装盘俯拍,拉丝/出汁

## parser_warnings

- shot 1 anchored to P0 hook template (jiating_chufang)
- shot 2 anchored to H9 (评论区二次梗钩)

## 机械检查详情

- ✅ script_length_80_600 — len=346
- ✅ shot_count_3_5 — count=4
- ✅ no_forbidden_terms — leaked=[]
- ✅ confidence_ge_0_5 — conf=0.75
- ✅ rationale_marker_present — checked '保留' + '改' in script
- ✅ visual_diversity_score — max overlap 0.21 (threshold 0.5)
- ✅ nutrient_category_consistency — n/a (not baomam_fushi)
- ✅ hook_p0_compliance — shot 1 hits ['H4'] (required any of ['H4', 'H9'])
- ✅ hook_diversity — 2 distinct hooks: ['H4', 'H9']
- ✅ negative_hook_absence — no forbidden hooks (['H8'])
- ✅ dish_anchor_present — shot 1 has dish '红烧肉'
