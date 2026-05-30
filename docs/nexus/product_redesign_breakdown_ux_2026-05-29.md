# 产品重设计 · 爆点拆解维度 + 内容 + UX 交互(2026-05-29)

> **触发**: Founder 第一次亲自用产品,反馈「拆出来的爆点页面复杂乱、UX 不友好、**维度+内容+还原脚本质量非常差**、无法吸引内测用户」。
> **方法**: PM + UX 视角,从真实源码取证后重设计(非凭空)。
> **作者**: Claude(PM mode)· 用 Opus 4.8
> **状态**: 待 founder 拍板 build order

---

## 0. 用户是谁(锚定一切判断)

30-40 岁宝妈 / 育儿 / 家庭厨房创作者,**手机端**,粉量 50-5000。
她的 job-to-be-done:**「我刷到一条爆款,帮我快速做出我自己的版本。」**
她**不要**影评级拆解。她要:① 为什么火(能听懂、能用的几句)→ ② 我的版本(能今天就拍的脚本,听起来像我)→ ③ 一键拿去发。

当前产品是按「分析师怎么解剖视频」设计的,不是按「宝妈要做什么决定」设计的——这是所有问题的总根。

---

## 1. 根因诊断(全部源码取证)

| # | 根因 | 证据 | 对应吐槽 |
|---|---|---|---|
| **R-A** | **改写从没接模型**。线上 `CASCADE_REWRITE_UPSTREAM` 默认 `fixture`,全仓只有 test/eval/离线脚本设过 `llm`,部署文件全没设 | `rewrite.py:70` + `.env`/`docker-compose` 均无此项 + `p1-3_signoff:157` 已记「fixture『暖色家庭厨房』反复出现」 | **脚本质量非常差(头号)** |
| **R-B** | 模型偏旧。`DOUBAO_MODEL=doubao-seed-1-6-250615`,比 config 默认 `doubao-seed-2-0-pro` 还旧 | `.env` vs `config.py:23` | 「用最新的模型」 |
| **R-C** | 改写 prompt 是「合规审计清单」不是「代笔」。120 行 H1-H9 表 + 营养类目 + 优先级 map + 禁词表 + `self_check.hook_per_shot` QA schema → 模型把算力花在满足约束,不是写得像妈妈 | `prompts/rewrite_baomam_fushi.md` 全文 | 内容差、机械 |
| **R-D** | 拆解维度 11+ 个全 dump。hook/pacing/climax/visual_style/emotional_arc/target_audience/engagement_levers/replicable_formula + audio×3 + production×3,每个 ≤80 字铺成卡 | `contract.py:92-108` + `doubao_direct_analyze.md` | **维度复杂乱** |
| **R-E** | UX 是「分析师 dump」。粘 1 条链接 → 单屏滚过 ConfidenceBanner+ScriptCard+AudioCard+ProductionCard+TranscriptCard+源镜头×3-12+改写镜头+PublishPack+AnchorSidebar = **20+ 块** | `CardStack.tsx:42-104` | **复杂乱 + 交互不友好** |
| **R-F** | 价值被埋。分析出来后,真正有用的「你的版本」要滚到长卡底部、手动点 niche CTA 才触发改写 | `CardStack.tsx:56-59` + `App.tsx:90` | 交互不友好 |

**一句话**:工程没问题,产品模型错了——按解剖学组织信息,还把唯一的真模型路径关着。

---

## 2. 重设计 · 拆解维度(11+ → 3+1)

把「分析维度」换成「创作者决策维度」。她只需内化 **3 个为什么 + 1 个怎么抄**:

| 新维度 | 合并自 | 给她的话 | 内容要求 |
|---|---|---|---|
| **抓人** (Hook) | hook | 前 3 秒靠什么让人不划走 | 一句话 + **引用原片开场那句台词** |
| **留人** (Hold) | pacing + climax + emotional_arc | 中间为什么不快进 + 哪一下最爽 | 一句话点出节奏型 + 第几秒的爽点 |
| **带人** (Spread) | target_audience + engagement_levers | 戳中谁、为什么有人评论/转发 | 一句话:谁会转 + 那个触发点 |
| **套路** (Formula) | replicable_formula | 这条的可复制公式 = 你脚本的骨架 | 「开头X → 中间Y → 结尾Z」结构化,直接喂改写 |

**降级到「想还原拍摄细节?」抽屉**(参考资料,默认折叠,非主流):
`visual_style` · `audio(bgm/语速/音效)` · `production(成本/工时)` · 源逐镜头列表 · 完整逐字稿。

> 数据层 `contract.py` 8 字段**不必删**(向后兼容、便宜),但:① 分析 prompt 改成主推 3+1、字段可更长更深(不再 11 个 80 字浅水);② 前端默认只渲染 3+1,其余进抽屉。

---

## 3. 重设计 · 内容 + 还原脚本(主要矛盾)

### 3.1 P0 — 把改写接上真模型(配置,最高 ROI)
- prod `.env`: `CASCADE_REWRITE_UPSTREAM=llm`
- provider 保持 `doubao`(**境内,PIPL §38 合规红线**,见 `algo_filing_2026-05-21`;**禁止** gemini 跑改写)
- `DOUBAO_MODEL` → 升到 ARK 最新(`doubao-seed-2-0-pro` 或更新)。改写是护城河,值得最好的模型。
- **验收**:真实抖音 URL 走 browser 端到端,看脚本是否① 真模型生成 ② 像妈妈说话 ③ 全境内。容器 healthy ≠ 功能可用。

### 3.2 P1 — 改写 prompt:从「审计员」改成「代笔」
- **喂给模型**:源片的`套路`(1 个公式)+ 3 个为什么 + 创作者人设/历史锚点(她的角色、她娃、她厨房——锚点系统已存在)。
- **要的输出**:她会**念出口**的脚本,逐镜头,她的口吻。80-220 字,3-5 shot。开头一行「我帮你保留了什么套路、换成了你的什么」建立信任。
- **守住的硬护栏**(短小一块,不当 prompt 主体):无品牌名 / 无广告法背书词 / 角色=她本人。
- **把 H1-H9 / 营养类目检查移出生成 prompt,改成生成后校验器**(`hook_taxonomy.py` 逻辑已有):自然生成 → 校验 → 命中硬违规才做 1 次定向重生。别让模型一边写人话一边玩 9 张表。
- **创作者侧输出删掉** `self_check` / `hook_per_shot` / `priority_compliance` / `nutrient_category`(QA 内部物,不给用户看)。

---

## 4. 重设计 · UX 交互(20+ 块 → 三幕一屉)

从「粘 → 分析师 dump → 找 CTA → 脚本」改成「粘 → 3 个为什么 → 你的版本(自动) → 拿去发」。

1. **自动改写**:niche 进入时已知,分析一落地**立刻自动触发改写**。别把唯一的价值(她的脚本)锁在长滚动底部的手动 CTA 后面。(留一个「换个方向」给跨 niche 罕见情况。)
2. **三幕 · 单列 · 渐进披露**:
   - **幕1「为什么火」**:3 个理由 chip(抓/留/带)+ 1 行套路。点 chip 展开。默认这就是全部「分析」。
   - **幕2「你的版本」(主角)**:改写脚本,她的口吻,行内可改,逐镜头。把握度做成脚本头一行小字「把握:中」,不是吓人的大 banner。
   - **幕3「拿去发」**:一键复制 + 标题备选 + 标签 → 「去抖音粘贴」。
   - **抽屉「想还原拍摄细节?」**:源镜头 + 逐字稿 + 音频 + 成本。默认折叠。
3. **去杂**:撤掉顶部 ConfidenceBanner 大卡、常驻 Audio/Production/Transcript/12×ShotCard、右侧 AnchorSidebar(锚点融进改写,不另起一栏)。
4. **手机优先**:单列、大点击区、脚本一拇指可复制。无节点图、无侧栏。

---

## 5. Build order(各自独立可发可测)

| 阶段 | 内容 | 谁 | 风险 | 验收 |
|---|---|---|---|---|
| **P0** | prod `.env` flip `=llm` + 升模型 + 真 URL 验证 | Founder(改 prod)/ Claude(备 diff+验) | 低 | browser 跑 1 条:脚本变真、像妈妈、境内 |
| **P1** | 改写 prompt 审计员→代笔 + H/营养检查移到后置校验器 | Claude | 中 | 同 URL 前后对比,founder 念第一句不出戏 |
| **P2** | 分析 prompt + 维度 11→3+1(字段更深) | Claude | 中 | 拆解只剩抓/留/带/套路,更准 |
| **P3** | 前端三幕一屉 + 自动改写 + 手机优先 | Claude / Cursor | 中 | 单屏三幕,粘→脚本一气呵成 |

P0 是止血。其余按序,每步独立验证。

---

## 6. 「用最新的模型」双重落地
- **产品**:升级跑分析+改写的模型(尤其把改写从 fixture 翻到 llm + 顶配 doubao)。
- **设计**:本重设计用 Opus 4.8 产出。

---

## 7. 待 founder 拍板
- [ ] 认可 3+1 维度切法(or 调整:_______)
- [ ] 认可三幕一屉 UX(or 调整:_______)
- [ ] P0 prod `.env` flip 谁来动(founder SSH / 给 Claude 凭证)
- [ ] build order 是否照 P0→P3
