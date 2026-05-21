# P2-4 改写输出 · jiating_chufang #4

**源 URL**: https://www.douyin.com/video/7296430710208941322
**源 @作者**: 老饭骨
**源日期**: 2023-11-01
**源标题**: 二伯快乐油升级版!梅广明师傅亲自调味制定配方
**hook_pattern_id**: `H5`
**source_classification**: `edge_case`
**rewrite_id**: `rw_c24e041cc576a2fd`
**model**: `p2-4-synth-v1`
**confidence**: 0.75
**cost_cny**: ¥0.4200
**机械检查**: 11/11 通过

## script_markdown

```
### 改写脚本
<!-- 保留:H5 · 二伯快乐油升级版!梅广明师傅亲自调味制定配方 | hook_pattern_id=H5 | classification=edge_case | 改:换成家庭厨房视角和家庭场景 -->
1. 餐厅 88 的家常红烧肉,为什么我在家做只要 12
   画面:自家厨房台面俯拍,菜单照对比,价签特写 · 自家厨房台面,手机/菜单照
2. 蒸蛋羹要过筛两次,你知道吗
   画面:砧板食材近景,刀工手部特写,光线侧射 · 俯拍砧板,食材特写
3. 热锅冷油,30 秒变色
   画面:炒锅侧拍,火光跳跃,油烟升腾 · 侧拍炒锅,火光特写
4. 这一道你家做不做,留言告诉我
   画面:成品装盘近景,斜 45° 蒸汽特写,拉丝/出汁 · 成品装盘俯拍,拉丝/出汁
```

## shots

- shot 1:
  - dialogue: 餐厅 88 的家常红烧肉,为什么我在家做只要 12
  - visual: 自家厨房台面俯拍,菜单照对比,价签特写 · 自家厨房台面,手机/菜单照
- shot 2:
  - dialogue: 蒸蛋羹要过筛两次,你知道吗
  - visual: 砧板食材近景,刀工手部特写,光线侧射 · 俯拍砧板,食材特写
- shot 3:
  - dialogue: 热锅冷油,30 秒变色
  - visual: 炒锅侧拍,火光跳跃,油烟升腾 · 侧拍炒锅,火光特写
- shot 4:
  - dialogue: 这一道你家做不做,留言告诉我
  - visual: 成品装盘近景,斜 45° 蒸汽特写,拉丝/出汁 · 成品装盘俯拍,拉丝/出汁

## parser_warnings

- source_classification=edge_case: information density preserved; brand names and efficacy claims removed
- shot 1 anchored to P0 hook template (jiating_chufang)
- shot 2 anchored to H9 (评论区二次梗钩)

## 机械检查详情

- ✅ script_length_80_600 — len=350
- ✅ shot_count_3_5 — count=4
- ✅ no_forbidden_terms — leaked=[]
- ✅ confidence_ge_0_5 — conf=0.75
- ✅ rationale_marker_present — checked '保留' + '改' in script
- ✅ visual_diversity_score — max overlap 0.21 (threshold 0.5)
- ✅ nutrient_category_consistency — n/a (not baomam_fushi)
- ✅ hook_p0_compliance — shot 1 hits ['H4', 'H9'] (required any of ['H4', 'H9'])
- ✅ hook_diversity — 3 distinct hooks: ['H4', 'H5', 'H9']
- ✅ negative_hook_absence — no forbidden hooks (['H8'])
- ✅ dish_anchor_present — shot 1 has dish '红烧肉'
