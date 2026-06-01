# 改写质量验收标准 + 解封 Gating(REWRITE_ENABLED)

> 作者:质量 agent · 日期:2026-05-31 · 状态:**待 founder 拍板阈值后生效**
> 范围:为解封「改写 leg(『你的版本』生成)」定义**可度量**的验收标准、自动化硬检查、eval 流程、解封 gating checklist。
> 权威基线:`docs/nexus/phase1_retro_handoff_2026-05-31.md`(8 条铁律 + H3)、`docs/PHASED_PLAN.md`(§5.3 Phase2 Gate、§7 H3)、`docs/nexus/product_redesign_breakdown_ux_2026-05-29.md`(P1 代笔意图,**只取意图,不取已被反转的 3+1/三幕方案**)。
> 本文每条断言均经代码核对(见末尾「证据台账」)。**禁止臆造**。

---

## 0. 一句话结论

改写当前线上跑的是 `_fixture_rewrite` 模板套娃(`CASCADE_REWRITE_UPSTREAM` 默认 `fixture`,所有部署文件未设),且前端 `REWRITE_ENABLED=false` 整条关闭。LLM 路径代码写完且加固,但**生产/真 URL 从未验证过质量**。本标准定义「LLM 改写好到能让用户发出去而非弃稿」的可度量门槛 + 自动判分 + 解封顺序。**达标前不得 flip 任一开关。**

---

## 1. 标准要映射的产品意图(H3 + P1 代笔)

### 1.1 PHASED_PLAN H3(`docs/PHASED_PLAN.md §7`)

> **H3:「改写质量足以让用户继续而非弃稿」**

这是改写解封的**唯一终极判据**。所有 rubric/硬检查都是 H3 的**可度量代理**;真正的通过信号是 founder + Beta 用户「我会把这个版本直接发出去」。

### 1.2 product_redesign P1 的「代笔」意图(只取意图)

从「审计员」prompt → 「代笔(ghostwriter)」:
- **保留源片的套路内核**(`replicable_formula` 的结构:悬念开场→N 步→反差结尾),开头用和原片**同一招**抓人;
- **换成创作者自己的口吻**(口语化台词,不是说明书/审计报告腔);
- **可拍**:`shots` 3-5 个,`script_markdown` 80-400 字(详见 §2.3 长度争议);
- **开头一行交代「保留了什么套路 / 换成你的什么」**(rationale marker,prompt 已要求,见 `rewrite_baomam_fushi.md:16`)。

### 1.3 定位已收窄 —— 口吻标准**禁止写死「像妈妈」**

> 铁律级提醒:定位已收窄为「**任意短视频 / 抖音**」,niche(宝妈/育儿/厨房)已被 commit `929cb21` 从产品 UI 清除。

因此本标准的「口吻自然度」维度评的是 **「像一个真人创作者对着镜头自然说话」**,而**不是**「像妈妈/像辅食博主」。
- 现有 eval 的 niche-specific 强制项(`nutrient_category_consistency` / `dish_anchor_present`)在**去 niche 的通用改写**下应**降级为非强制 / 仅当 niche≠null 时生效**(详见 §3.4)。
- 现有三套 niche prompt(`rewrite_baomam_fushi.md` 等)在通用定位下需 founder/设计决策:保留为「赛道模板」还是合并为单一通用代笔 prompt。**这是开放问题(§7),不在本质量标准内拍板,但 eval 必须能在 niche=null 通用路径下运行。**

---

## 2. 可度量评分卡(Rubric)

每条改写产出按 **5 个维度**评分,每维 0–4 分锚点,加权求总分(0–100)。**LLM judge 自动给 1–5 realism + kept_formula + ad_risk,人评给最终 rubric 分**;§3 的硬检查是**一票否决前置**(任一硬检查 fail → 该条直接判 0,不进 rubric)。

### 2.1 五维 + 权重 + 通过阈值

| # | 维度 | 权重 | 它在问什么 | 主要信号源 |
|---|------|-----|-----------|-----------|
| D1 | **套路保真度** (formula fidelity) | 30% | 源片为什么火的结构内核是否搬过来?开头是否用同一招抓人? | LLM judge `kept_formula` + 人评 + `replicable_formula` 对照 |
| D2 | **口吻自然度** (voice naturalness) | 25% | 像真人创作者自然口语,还是说明书/审计腔/AI 味? | LLM judge `realism_1to5` + 人评 |
| D3 | **可拍性** (shootability) | 20% | 每镜画面具体可执行(景别+主体+光)、镜头各不相同、时长可拍? | 硬检查 `visual_diversity` + 人评 |
| D4 | **信息完整** (completeness) | 15% | shots 3-5、script 长度达标、rationale marker 在、字段齐全无残缺 | 硬检查(可全自动) |
| D5 | **合规** (compliance) | 10% | 零品牌名 / 零广告法背书词 / 零安全焦虑话术 | 硬检查(一票否决,见 §3) |

> **D5 同时是一票否决项**:权重 10% 只用于「软合规」(语气是否制造焦虑),**硬合规**(品牌名/背书词/hook-code/QA 字段泄漏)走 §3 硬检查,fail 即 0 分。

### 2.2 每维评分锚点(0–4)

**D1 套路保真度**
- 4:结构内核完整搬移(悬念开场→N 步→反差结尾全在),开头同一招,讲的是创作者自己的事 → judge `kept_formula=yes`
- 3:内核基本在,某一环弱化 → `kept_formula=partial` 偏强
- 2:抓到一半,节奏散了 → `kept_formula=partial`
- 1:只换了表面词,结构没搬 / 或直接抄原片台词食材
- 0:完全没保留套路 → `kept_formula=no`

**D2 口吻自然度**
- 4:口语自然,像真人对镜头说话,有情绪起伏 → judge `realism=5`
- 3:基本自然,个别句生硬 → `realism=4`
- 2:能读但书面/平淡,AI 味可感 → `realism=3`
- 1:说明书/审计腔,堆形容词 → `realism=2`
- 0:语病/不通顺/明显机翻感 → `realism=1`

**D3 可拍性**
- 4:每镜「景别+主体+光」具体,镜头全不同,总时长可拍(见 §3 时长硬检查)
- 3:大部分镜可拍,1 个偏笼统
- 2:画面笼统(如「暖色厨房俯拍」重复),需创作者二次脑补
- 1:多镜重复 / 画面缺失 → `visual_diversity` fail
- 0:无法据此开拍

**D4 信息完整**
- 4:shots 3-5、script 80-400 字、rationale marker 在、无残缺字段
- 2:边界擦边(如 script 600 字 / shots=5 但有一镜空)
- 0:硬检查 `shot_count_3_5` / `script_length` / `rationale_marker` 任一 fail

**D5 合规(软)**
- 4:语气稳,零焦虑话术,品类词得体
- 2:轻微夸张但不踩线
- 0:制造安全焦虑(千万别/绝对不能/出事)等 → 人评否决

### 2.3 ⚠ 长度规格冲突 —— 必须先对齐再标定

| 来源 | 规定 | 文件:行 |
|------|------|---------|
| founder brief | 「80-220 字 / 3-5 shot」 | 本任务书 |
| 实际 prompt | 「`script_markdown` **80-400** 字」 | `rewrite_baomam_fushi.md:24` |
| 实际硬检查 | `script_length_80_600`(**80-600** 通过) | `eval/checks.py:41` |
| fixture 兜底 | <80 补足,>600 截断 | `rewrite.py:215-218` |

**三处不一致。** 本标准按**代码现状**写阈值(prompt 目标 80-400,硬上限 80-600),并把 brief 的「220」作为**开放问题交 founder 拍板**(§7-1)。若 founder 选 220 上限:必须**同步**改 prompt(`:24`)、`checks.py:41` 的 `script_length_80_600`、`rewrite.py:215-218` 的 fixture 兜底**三处**,否则标准与代码脱节。

### 2.4 总分计算 + 通过阈值

```
rubric_score = 25*D1' + 25*D2'... 实际:
rubric_100 = (D1/4*30) + (D2/4*25) + (D3/4*20) + (D4/4*15) + (D5/4*10)
```

**单条通过线**:
- **硬检查(§3)全过** —— 否则直接 0(一票否决);
- **rubric_100 ≥ 70**;
- **D1 套路保真度 ≥ 3**(套路没搬到位 = 抄爆款骨架失败 = H3 核心失守,单维硬底);
- **D2 口吻自然度 ≥ 2**(不能是审计腔)。

**批次通过线(解封门,见 §4.4)**:见 §4。

---

## 3. 自动化硬检查(先于人评,一票否决)

这些**可程序化**,在 LLM judge / 人评**之前**跑;任一 fail → 该条判 0、不进 rubric。**全部已有现成代码可复用**,本标准只是把它们升格为「解封硬门」。

### 3.1 硬检查清单

| ID | 检查 | 通过条件 | 现成代码(复用,勿重写) |
|----|------|---------|----------------------|
| HC1 | **无品牌名 / 无广告法背书词** | `FORBIDDEN_TERMS`(AI/智能/算法/平台/神器/必备/营养师/米其林/权威)零命中,扫 script + 每个 shot 的 dialogue/visual | 后端 `rewrite.py:FORBIDDEN_TERMS` + `_clean()` + `_FORBIDDEN_SUBS`;eval `checks.py:no_forbidden_terms`;前端 `cardCopy.ts:scrubUiForbidden` / `FORBIDDEN_TERMS` |
| HC2 | **无 hook-code(Hxx)泄漏** | 输出文本无句首 `+H8`/`H6` 这类钩子分类码 | 前端 `cardCopy.ts:stripHookCode`(:282,正则剥句首 `[+＋空白]*H<1-2位>`);**后端 eval 需补一个等价 check**(见 §3.3) |
| HC3 | **无 QA / 内部字段泄漏** | 输出不含 `self_check`/`hooks_used`/scratch 等;`RewriteResult`/`RewriteShot` 是 `extra='forbid'` | 后端 `rewrite.py:_normalize_llm_output` 末尾 `_RESULT_KEYS`/`_SHOT_KEYS` 白名单硬过滤(:437-439) |
| HC4 | **全境内 provider(PIPL §38)** | LLM 走 doubao(`LLM_PROVIDER=doubao` → ARK `ark.cn-beijing`),**禁 gemini 跑改写** | `llm_factory.get_chat_model()` provider=doubao;铁律⑦ |
| HC5 | **时长可拍** | shots 3-5 且每镜有可拍画面;总镜数 × 合理单镜时长落在可成片区间 | eval `checks.py:shot_count_3_5`;可拍画面看 `visual_diversity` |
| HC6 | **script 长度达标** | `80 ≤ len(script) ≤ 600`(待 §2.3 拍板) | eval `checks.py:script_length_80_600` |
| HC7 | **rationale marker 在** | script 含「保留」+「改」(交代保留了什么套路 / 换成你的什么) | eval `checks.py:rationale_marker_present` |
| HC8 | **shots 画面多样** | `visual_diversity` ≥ 0.5(不是每镜「暖色厨房俯拍」) | `hook_taxonomy.visual_diversity` |
| HC9 | **confidence 不自欺** | positive 源 `confidence ≥ 0.5`;negative_ref 源 `0.4-0.6` | eval `checks.py:confidence_*` |

### 3.2 一票否决子集(任一 fail → 直接 0 分,且**阻断解封**)

**HC1 / HC2 / HC3 / HC4** 是**安全/合规红线**,任一条在批次内出现 **>0 次** → 解封门直接不通过(详见 §4.4)。HC5-HC9 是质量门,允许少量 fail(进批次通过率统计)。

### 3.3 ⚠ 现有 eval 缺口:HC2 后端无对应 check

`eval/checks.py` 的 `run_checks` 当前**没有** hook-code 泄漏检查 —— `stripHookCode` 只在前端 `cardCopy.ts`。后端 LLM 输出层若把 `+H8` 写进 dialogue,eval **抓不到**,要等前端剥。
**整改要求(解封前必做)**:在 `eval/checks.py:run_checks` 加一个 `no_hook_code_leak` check(正则 `^[+＋\s]*H\d{1,2}\b` 扫 script + 每 shot),与前端 `stripHookCode` 同正则,纳入 §3.2 一票否决子集。

### 3.4 ⚠ 现有 eval 的 niche 强绑定 —— 去 niche 后必须放开

`eval/checks.py` 的 `MANDATORY_CHECK_NAMES` 把 `nutrient_category_consistency`(baomam 强制)、`dish_anchor_present`(jiating 强制)、`hook_p0_compliance`(全强制)设为 mandatory。**在去 niche 的通用改写下**:
- `nutrient_category_consistency` / `dish_anchor_present`:仅当该条 case 的 `niche != null` 且属对应赛道时强制,否则**bypass**(代码已对非匹配 niche 返回 pass,但 mandatory 标记仍在 —— 需确认 niche=通用时不误判);
- `hook_p0_compliance`(全强制):依赖 `HOOK_P0_MAP` 的三 niche 映射,通用路径需要一个**通用 hook 命中**判据(至少命中 H1-H9 之一即可),否则通用 case 会被强制项卡死。
**整改要求**:解封前确认 `run_checks(result, niche=None or "generic", ...)` 不会因 niche 强制项全部 fail 而把通用改写判死。**这是 eval 能否跑通用路径的前提。**

---

## 4. Eval 流程(复用现有框架 + 通用化改造)

### 4.1 用现成框架,不重造

仓库**已有**完整 P2-6 eval 框架,直接用:

| 构件 | 路径 | 作用 |
|------|------|------|
| CLI 入口 | `scripts/p2-6_eval.py` | `uv run python ../scripts/p2-6_eval.py [--niche all] [--mode fixture\|llm] [--baseline last] [--skip-judge]` |
| 编排 | `backend/src/agent/cascade/eval/runner.py` | 载评测集 → `rewrite_for_niche` → 硬检查 → LLM judge → 解析 founder signoff → 聚合 `EvalReport` |
| 硬检查 | `eval/checks.py` | §3 全部机械检查 + `is_passing`(默认 ≥8/10 + mandatory 全过) |
| LLM judge | `eval/judge.py` | 独立 LLM(默认 doubao)三问:`kept_formula` / `realism_1to5` / `ad_risk` |
| 报告 | `eval/report.py` | `EvalReport` + markdown 渲染 + **`prompt_version_hash`(sha256 over `rewrite_*.md`)** |
| 基线 | `eval/baselines.py` | `p2-6_baseline_<UTC>.json` 存/读/diff |

### 4.2 评测集(评测集 = N 条真实抖音 URL,跨题材)

**现成评测集**:`docs/nexus/founder_log/real_urls_for_p2-4.md`(v2.0,founder 标注 `hook_pattern_id` / `classification` / `title` / `author`),由 `runner._load_p24_helpers()` 经 `scripts/p2-4_run_real_urls.py` 的 `parse_url_entries` + `synthesize_contract_from_entry` 载入。

**解封评测集要求**:
- **N ≥ 15**(跨题材,**不限三 niche**;定位已收窄通用,评测集必须含非宝妈/育儿/厨房的题材 —— 如知识、好物、剧情、口播),且含 **≥3 条 `negative_ref`**(确认负向源不被照抄)和 **≥2 条 `edge_case`**(超长/低信息源,验证降级)。
- 现 `real_urls_for_p2-4.md` 是 niche 分组的,**需扩充通用题材条目**(开放问题 §7-2:沿用旧文件加分组,还是新建 `real_urls_rewrite_unseal.md`)。
- 评测集 URL 必须能经 §3.4 通用路径跑,不被 niche 强制项卡死。

### 4.3 判分三层(自动 → 半自动 → 人工)

1. **机械硬检查(全自动)** —— `eval/checks.py`,§3 全部。**先跑,fail 即 0。**
2. **LLM judge(半自动)** —— `eval/judge.py`,独立 doubao 给 `kept_formula`/`realism_1to5`/`ad_risk`。**provider 必须 doubao(HC4)**,judge 用境内模型评境内输出。
3. **人工抽检(founder signoff)** —— `runner.parse_founder_qualitative` 解析 `docs/nexus/founder_log/p2-4_qualitative_signoff_<date>.md`,checkbox「我会把这个版本发出去」=pass / 「还需要调整」=fail。**人工至少抽检 N 的 50%,且 100% 抽检所有 LLM judge `realism≤3` 或 `kept_formula≠yes` 的条目**(机器存疑的必须人看)。

### 4.4 批次通过线(= 解封门阈值)

对一次 `--mode llm` 全量 eval,**同时满足**才算 H3 达标、可解封:

| 指标 | 阈值 | 来源 |
|------|------|------|
| **硬合规零泄漏** | HC1/HC2/HC3/HC4 命中 = **0**(全批次) | §3.2 一票否决,合规红线 |
| **机械通过率** | `overall_mechanical_pass_rate ≥ 0.85` | `report.aggregate_overall` |
| **LLM judge realism 均值** | `overall_judge_realism_avg ≥ 3.8 / 5` | `judge.py` |
| **kept_formula=yes 率** | `≥ 0.70`(套路真搬过来) | `judge.py` 映射 D1 |
| **judge ad_risk 命中** | `overall_judge_ad_risk_count = 0` | `judge.py` |
| **人工 signoff 通过率** | `founder_pass_rate ≥ 0.70`(抽检集内) | `parse_founder_qualitative` |
| **vs fixture 提升** | LLM 批次 realism 均值 **显著高于** fixture 批次(同评测集跑两遍 `--mode fixture` / `--mode llm` 对比 `delta_from_baseline`) | `baselines.diff_baselines` |

> 最后一条是关键:MEMORY 记「fixture 套娃 = 脚本质量差头号根因」。**解封的全部意义是 LLM 必须明显优于 fixture**;若 `--mode llm` 跑出来 realism 没显著高于 `--mode fixture`,则解封无意义,打回 prompt 调优。

### 4.5 标准跑法(命令)

```bash
# 0) 先建 fixture 基线(对照锚点)
cd backend && uv run python ../scripts/p2-6_eval.py --mode fixture --baseline none
#    → 把产出 EvalReport 存为 p2-6_baseline_<UTC>.json(save_baseline)

# 1) 跑 llm 真实批次(需 ARK_API_KEY,doubao;judge 也走 doubao)
cd backend && uv run python ../scripts/p2-6_eval.py --mode llm --baseline last
#    → delta_from_baseline 给出 vs fixture 的 realism/机械通过率提升

# 2) founder 人工抽检:在 p2-4_qualitative_signoff_<date>.md 勾 checkbox,重跑 runner 聚合 founder_pass_rate
```

---

## 5. 解封 Gating Checklist(达标后按序执行,漏一处 = 假解封)

> 三件事**联动**,前端开后端还 fixture / 后端切了前端不触发,都是假解封。

### 5.1 前置门(必须全绿才进解封动作)

- [ ] **G0 eval 改造完成**:§3.3(加 `no_hook_code_leak`)+ §3.4(通用 niche 路径不被强制项卡死)落地,`uv run pytest backend/tests/test_eval_harness.py` 绿。
- [ ] **G1 评测集就绪**:§4.2 的 N≥15 跨题材 URL(含 negative_ref/edge_case)写入评测集文件。
- [ ] **G2 cost 定价改 doubao**:`rewrite.py:422` 的 `LLM_INPUT_PRICE_CNY_PER_1K` 默认值(现 0.005/0.020 注释明写 Gemini Flash)改为 doubao 实际单价,否则 `cost_cny` 显示失真(不阻断功能,但影响 §4.4 成本观测;Phase2 Gate 有 <¥15 成本项)。
- [ ] **G3 §4.4 批次门全部达标**:`--mode llm` eval 满足 §4.4 七项 + 显著优于 fixture。
- [ ] **G4 confidence 阈值标定**:`_normalize_llm_output` 硬约束很严(shots<3 / script 越界 / 任何 scrub → confidence≤0.4)。真跑确认 doubao 不会大面积被压到 0.4;若是,先调 prompt 而非放宽约束。

### 5.2 解封动作(达标后,按序)

- [ ] **① 后端 upstream flip**:`.env` / `docker-compose.yml` 加 `CASCADE_REWRITE_UPSTREAM=llm`(默认 fixture,所有部署文件都没设)。**改 mirror/依赖另需重 lock(铁律⑥),此处仅加 env 不动 lock。**
- [ ] **② 前端开关**:`frontend/src/App.tsx:157` `REWRITE_ENABLED = false → true`,**前端需重新构建部署**(是源码硬常量,非运行时开关;**强烈建议顺手改成 env / 远程 flag**,见 §7-3,否则无法灰度)。
- [ ] **③ bump ANALYSIS_PIPELINE_REVISION(铁律①)**:`backend/src/agent/cascade/contract.py:28`(现=3)→ 4。**⚠ 见 §6:这一步对 rewrite 缓存其实不生效**,但仍必须 bump —— 因为解封会改 analysis 侧的下游预期且铁律①强制;**真正护 rewrite 缓存的是 §6 的独立守卫**。
- [ ] **④ rewrite 缓存守卫(§6,新工作,强制)**:给 `rewrites` 表缓存键加 `prompt_version_hash` 或 `REWRITE_PIPELINE_REVISION`,否则切 llm 后 24h 内旧 fixture 结果被命中,founder 实测「还是老样子」。
- [ ] **⑤ 真 URL 端到端验证(铁律⑤)**:容器健康 ≠ 功能可用。真 douyin URL → 分析 → 自动改写 → 看「你的版本」→ 确认走 LLM(查 `model` 字段 / `cost_cny`≈doubao 价,不是 fixture 的 0.42)→ 前端无禁词(`forbiddenTerms.test.tsx` + 真浏览器 DOM 扫)。
- [ ] **⑥ 改 UI 跑 lint(铁律②)**:`REWRITE_ENABLED` flip + 任何卡片变动后 `cd frontend && npm run lint`(rules-of-hooks 0 违规)+ Playwright 真旅程。

### 5.3 灰度(强烈建议)

- [ ] **⑦ 灰度而非全量**:HTTP 已有两级 invite-code(cohort)gate。**建议改写先对一个 cohort 邀请码灰度**(如新建 `rewrite-beta` 码),验证一周 H3 信号(用户是否真发出去、弃稿率)后再对全量 Beta 开。
  - 前提:**②的 env/远程 flag 化是灰度的必要条件** —— 当前硬常量无法按 cohort 切。若不做 flag 化,灰度只能靠「只发部分人邀请码 + 后端 env 全开」的弱灰度,粒度粗。
  - 灰度期埋点(P2-10)必须能区分:进入改写 / 看到「你的版本」/ 复制发布包(`publish_pack_copied` 已有)/ 弃稿(无复制即离开)。

---

## 6. ⚠ 头号工程债:rewrite 缓存无版本守卫(解封前必修)

**事实**(代码核对):`rewrites_repo.load_recent_rewrite` 缓存键 = `(analysis_id, niche, user_id, created_at >= since)`,24h 窗口,**无 pipeline/upstream/prompt 版本**。`ANALYSIS_PIPELINE_REVISION`(=3)只守 `analyses` 永久缓存,**完全不作用于 rewrite**。

**后果**:从 fixture 切到 llm、或改任一 rewrite prompt 后,24h 内同 `(analysis_id, niche, user_id)` 的旧 fixture 结果会被当缓存命中返回 —— 这是 MEMORY『分析缓存版本守卫』坑在改写侧的**完整翻版**,且目前**零防护**。

**整改(解封 checklist ④,强制)**:任选其一,推荐 A:
- **A**:`rewrites` 表加 `prompt_version_hash` 列(复用 `report.compute_prompt_version_hash()` 的 sha256-over-`rewrite_*.md`),`load_recent_rewrite` 的 WHERE 加 `AND prompt_version_hash = ?`。改 prompt 自动失效旧缓存,无需手 bump。
- **B**:加 `REWRITE_PIPELINE_REVISION` 常量进缓存键,改 prompt/模型/upstream 手动 bump(同铁律①模式,但独立于 ANALYSIS_PIPELINE_REVISION)。

> **别误以为 bump ANALYSIS_PIPELINE_REVISION 能让新 rewrite prompt 生效 —— 它不进 rewrite 缓存键。** 这是下游最易踩的认知坑。

---

## 7. 开放问题(交 founder / 设计拍板,不在质量标准内定)

1. **长度上限到底 220 还是 400/600?**(§2.3)brief 说 80-220,prompt 写 80-400,硬检查 80-600,三处不一致。拍板后**同步改 prompt + checks.py + fixture 兜底三处**(改 prompt 触发 §6 缓存守卫 / 铁律①)。
2. **评测集**:沿用 `real_urls_for_p2-4.md` 加通用题材分组,还是新建 `real_urls_rewrite_unseal.md`?(§4.2)需 founder 提供 ≥15 条跨题材真 URL + 标注。
3. **三套 niche prompt 在去 niche 定位下的去留**:保留为「赛道模板」(用户选 / 自动判)还是合并为单一通用代笔 prompt?(§1.3)直接决定 eval 是否还需 per-niche 强制项。
4. **口吻基准**:去 niche 后「自然口吻」由谁定锚?建议 founder 在 signoff 文件里对 3-5 条标「这就是我会发的口吻」做人类锚点,供 judge prompt 校准。
5. **灰度 cohort**:是否新建 `rewrite-beta` 邀请码先灰度?(§5.3)还是直接全量 Beta?

---

## 8. 证据台账(每条断言的代码出处,已核对)

| 断言 | 文件:行 |
|------|---------|
| eval 框架存在(checks/judge/report/runner/baselines) | `backend/src/agent/cascade/eval/*.py` + `scripts/p2-6_eval.py` |
| 机械检查 + `is_passing`(≥8/10 + mandatory) | `eval/checks.py:104-111` |
| 硬检查含 forbidden/length/shot/confidence/rationale/visual_diversity | `eval/checks.py:41-95` |
| LLM judge 三问 + 默认 doubao | `eval/judge.py:26-127` |
| `prompt_version_hash` = sha256 over `rewrite_*.md` | `eval/report.py:68-74` |
| 评测集 URL 文件存在 | `docs/nexus/founder_log/real_urls_for_p2-4.md`(实测存在,9308 bytes) |
| founder signoff checkbox 解析 | `eval/runner.py:81-132` |
| `FORBIDDEN_TERMS`(AI/智能/.../权威)+ `_clean`/`_FORBIDDEN_SUBS` | `rewrite.py:37-47, 247-263` |
| `_RESULT_KEYS`/`_SHOT_KEYS` 白名单过滤 QA 字段 | `rewrite.py:437-460` |
| confidence ≤0.4 硬约束(scrub/越界) | `rewrite.py:404-418` |
| cost 定价默认 Gemini Flash | `rewrite.py:420-422` |
| 前端 `stripHookCode`(句首 Hxx 正则) | `frontend/src/lib/cardCopy.ts:282` |
| 前端 `scrubUiForbidden` + `FORBIDDEN_TERMS` | `frontend/src/lib/cardCopy.ts:233, 269` |
| prompt = 代笔风格 + rationale + 80-400 + 3-5 shot | `rewrite_baomam_fushi.md:1, 16, 24` |
| `REWRITE_ENABLED=false`(前端硬常量) | `frontend/src/App.tsx:157` |
| `CASCADE_REWRITE_UPSTREAM` 默认 fixture | `rewrite.py:70` |
| rewrite 缓存键无 revision/prompt 守卫 | `rewrites_repo.py:47-60` |
| `ANALYSIS_PIPELINE_REVISION=3`(铁律①常量真实位置) | `contract.py:28` |
| niche 已清理(positioning 收窄) | commit `929cb21` |
| H3 / Phase2 Gate | `docs/PHASED_PLAN.md §7 / §5.3` |

---
**质量 agent** · 2026-05-31 · 下游执行前必读 §6(缓存守卫)+ §7(开放问题先拍板)
