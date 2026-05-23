# Claude handoff — P5-2 rewrite prompt strip brand / product mentions

**Owner**: Claude session (prompt engineering)
**Source of truth**: `docs/nexus/founder_log/p2-6_baseline_20260523T125354Z.md`(yuer_richang 1 ad_risk hit);`backend/src/agent/prompts/rewrite_*.md`
**Status**: READY · no upstream blocker
**Time budget**: 0.5 day(prompt 改动 + 单 niche 验证 + 全 niche 验证)
**Allocation**: 后续 PM_W5_allocation.md §3.1(写于 W5D0 时)

---

## 0. 背景

P5-1a fix(H8 regex 扩展)后 yuer_richang mechanical pass 100%,但 judge 抓到 **1 个 ad_risk hit**:

> case `7466377349529881856`
> fragment: `散落的安抚海马玩具,枕边翻开着《晚安月亮》绘本`

LLM 在视觉描述里用具体商品名(**安抚海马** 是 IKEA / Mattel 品牌玩具;**《晚安月亮》** 是著名绘本),触发 judge 的 brand placement 标记。Judge 正确,**是 prompt 让 LLM 太具体**。

广告法 §10 + §16:不得在内容里隐性植入未授权品牌 / 商品。Phase 1 内测一旦 creator 把 LLM 输出原样发出,**潜在合规问题**。

---

## 1. Done-signal

- 3 个 niche prompt(`prompts/rewrite_baomam_fushi.md` / `rewrite_yuer_richang.md` / `rewrite_jiating_chufang.md`)各加 1 节 "**§ 品牌 / 商品名禁用约束**":
  - 不得使用具体商品 SKU / 注册商标(例如:迪士尼 / IKEA / 安抚海马 / 蓝威士 / 五常稻花香 / 雀巢 / 美素佳儿)
  - 不得使用具名作品(绘本 / 书名 / 影视 IP);例如:不可写"《晚安月亮》/《如果你给老鼠一块饼干》",改写为"睡前绘本"
  - 视觉描述用**品类词**而非品牌词(改"安抚海马玩具"为"毛绒玩偶";改"碧螺春"为"绿茶")
  - **例外**:用户自己写明的品牌(创作者本人就在 promote 该品牌),不在禁用范围 — 但 Phase 1 内测不期望出现
- 1 个 unit test `test_rewrite.py:test_no_brand_mentions_in_rewrites`:跑 3 个 niche × 各 1 个 fixture,检查输出 `script_markdown` + `shots[].dialogue` + `shots[].visual` 不含小集合的 forbidden brand keywords
- forbidden 列表硬编码在 test(15-20 个常见 brand / IP keywords)— **不在 hook_taxonomy.py**(那是 hook 分类,不是合规过滤)
- 重跑 yuer baseline,verify `judge_ad_risk_count == 0`(从 1 降回 0)
- 全 niche 跑一遍,verify 总 ad_risk_count 不增加

---

## 2. 实现指引

### 2.1 Prompt §"品牌 / 商品名禁用" 模板(3 个 niche 各加)

```markdown
## 品牌 / 商品名禁用约束(P5-2)

**机械约束**(LLM 必须满足):

1. **不得使用具体商品 SKU / 注册商标 / 品牌名**:
   - ❌ 写 "安抚海马玩具" / "迪士尼餐盘" / "雀巢米粉"
   - ✅ 写 "毛绒玩偶" / "卡通餐盘" / "婴儿米粉"
2. **不得使用具名作品(绘本 / 书名 / 影视 IP)**:
   - ❌ 写 "《晚安月亮》绘本" / "小猪佩奇"
   - ✅ 写 "睡前绘本" / "动画片"
3. **视觉描述用品类词,不用品牌词**:
   - 适用所有 `shots[].visual` 字段 + `script_markdown` 全文

**理由**:Phase 1 内测产物可能被 creator 直接发抖音 / 小红书,品牌植入未授权 = 广告法 §10 + §16 风险。
```

### 2.2 Unit test(`backend/tests/test_rewrite.py`)

```python
FORBIDDEN_BRAND_KEYWORDS = (
    # 婴幼儿 / 母婴
    "安抚海马", "迪士尼", "小猪佩奇", "贝亲", "雀巢", "美素佳儿", "嘉宝",
    # 厨房 / 食材
    "五常稻花香", "海天", "李锦记", "茅台", "碧螺春", "西湖龙井",
    # 出版 / IP
    "《晚安月亮》", "《如果你给老鼠一块饼干》", "迪士尼", "皮克斯",
)

def test_no_brand_mentions_in_rewrites():
    # For each niche fixture, run rewrite, assert no forbidden keyword appears
    ...
```

### 2.3 验证

- 重跑 `--niche yuer_richang --mode llm`,verify ad_risk_count: 1 → 0
- 重跑 `--niche all --mode llm`,verify total ad_risk_count 不升

---

## 3. 边界(不在此票)

- **不动** judge prompt(judge 工作正确,不需要调)
- **不动** hook_taxonomy / hook_p0_compliance(P5-1a 已修)
- **不引入** 外部 brand 词库 / API — 硬编码 15-20 个常见 keyword 即可
- **不做** runtime filter(让 LLM 在 prompt 层避免;不要 post-process strip — 那会破坏 shot 结构)
- **不做** "creator 自己授权的品牌例外"(Phase 1 内测不期望出现;后续可加)
- **不做** 数据 audit log(P5-3 可能加,本票不做)

---

## 4. Upstream dep

- ✅ P5-1a H8 regex(`aba55df`)— 否则 yuer 100% pass 这个 baseline 不存在,ad_risk 信号也看不到
- ✅ judge LLM 正常工作(Doubao seed-1.6 in P4-1)
- 无 blocker

---

## 5. 失败兜底

- 若加 § 后 LLM 仍写品牌词 → 在 niche prompt 头部加更显式的 "**警告:输出 JSON 前请扫一遍是否有品牌/商品名**" 自检要求
- 若 forbidden keyword 命中误判(LLM 用了某词意外触发)→ keyword 列表精简,只保留 high-signal 的(如 "迪士尼" / "雀巢" 这种明确品牌)
- 若 jiating_chufang 类别需要某品牌(例如菜谱必须用 "美的电饭煲" 类描述)→ 添加 niche-specific 白名单(本票不做,P5-2.1 处理)

---

## 6. Output 清单

- `backend/src/agent/prompts/rewrite_baomam_fushi.md`(+§)
- `backend/src/agent/prompts/rewrite_yuer_richang.md`(+§)
- `backend/src/agent/prompts/rewrite_jiating_chufang.md`(+§)
- `backend/tests/test_rewrite.py`(+1 test)
- 验证 baseline:`docs/nexus/founder_log/p2-6_baseline_<UTC>.json`(ad_risk=0)
- commit:`fix(P5-2): rewrite prompts strip brand / product / IP mentions`
