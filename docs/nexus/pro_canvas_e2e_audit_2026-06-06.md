# 无限画布 Pro 端到端闭环审视报告

**日期**：2026-06-06
**方法**：多 agent 编排审计(`pro-canvas-e2e-audit` workflow,run `wf_2019463d-9b4`)。
Map(前后端 2 个考古员实读代码出闭环事实地图)→ Review(9 维度领域专家:闭环完整性/产品/设计/架构/前端/后端/成本合规/测试/质量)→ Verify(每条 finding 一个 Reality Checker 回代码对抗式核验)→ Synthesize。
**规模**：74 agent · 3.84M tokens · ~40 min。
**核验结果**:60 条 finding → confirmed 55 / uncertain 2 / refuted 3。
**已知缺口**:架构维度 reviewer 未产出结构化结果(StructuredOutput 漏调),其结论由闭环/后端/成本三维交叉覆盖;如需独立架构维度可补跑。
**独立复核**(本人 grep 实证 C1):`cascade.py:568/674` CardStack 路径确实 emit `GENERATION_COST`;`workers/{image,video,composite}_pipeline.py` 三个 worker **零** cost emit;`events_repo.sum_generation_cost` 只统计 `EventName.GENERATION_COST` → 画布路径累计成本恒读 0,**C1 属实**。

---

## 一、一句话判定 —— 端到端闭环到底通不通(及最大的一个风险)

**核心创作引擎是真通的,但两头(进画布的衔接、出画布的发布)是断的,而真正必须立刻处理的是:画布(Pro)生成路径整条不计成本,¥25/run 熔断与 ¥30/天日闸对产品主推的烧钱路径形同虚设——可被循环重试/失控 Director/恶意脚本无上限烧钱,且 /admin/cost 看板对这部分花费完全不可见。**

happy path 能从「粘 URL → 看分析 → 手点进画布 → Director 锚点级联建树(策划书→角色/场景→宫格→视频)→ 逐节点生成 → 合成 composite 节点 → 播放成片」走完。但:① 拿不到「可发布成片包」(画布无 publish 出口,CardStack 那份又被 flag 暂挂);② 进画布靠用户手点 CTA,不是默认流;③ **画布生成的钱根本不记账**,这是与「历史成本守卫 prod 失效」同源、更隐蔽的复刻面,必须 P0 修。

---

## 二、闭环逐段健康度表

| Leg | 状态 | 关键证据 file:line | 备注 |
|---|---|---|---|
| analyze(浅分析+钩子) | wired | `cascade.py:223` `analysis_service.py:140` | 产物落 cascade 主库(非 canvas.db);永久缓存无 TTL,改维度必须 bump `ANALYSIS_PIPELINE_REVISION` |
| rewrite(Doubao niche) | **parked** | `cascade.py:296` `config.py:63` | 代码 live 但 `CASCADE_REWRITE_ENABLED` 默认 0,前端整段不渲染 |
| seed_canvas 桥(analyze→画布) | partial | `ws_handlers.py:554` | 只灌分析摘要文本,不导 rewrite 产物;靠用户手点 CTA,改写靠 Director 重誊 |
| script 节点(策划书) | wired | `canvas.py:230,341` | type==script 直接 `_parse_storyboard`,无需 execute |
| character/scene/grid + 层级约束 | wired | `canvas.py:88,266-281` | 父必须 confirmed + `_validate_hierarchy`,代码级硬约束 |
| 异步生成队列(enqueue→claim→worker) | wired | `ws_handlers.py:364` `generation_repo.py:36` `generation_worker.py:39` | lease/retry/熔断/恢复完整 |
| 锚点级联(读父 result.url) | wired | `image_pipeline.py:32` `get_ref_urls` | 真护城河;`cascade/anchors.py` 是另一套(跨 run 用户素材库) |
| composite 合成 | wired(prompt 漂移) | `composite_pipeline.py:11` | `director.md:251` 指示调不存在的 `compose_canvas()`;真实走建 composite 节点+用户 execute |
| review gate 审核闸 | partial | `canvas.py:455` `config.py:76` | app 级 reviewing/confirmed live;LangGraph `CANVAS_INTERRUPT_GATE` 默认 OFF 且管错路径 |
| time-travel(版本/回滚) | wired | `versions_repo.py:20` `canvas.py:566` | 在途硬拒+null 跳过+标脏下游,守卫充分;已合 main |
| 逐镜 cancel | wired | `canvas.py:649` `generation_repo.py:141,180` | 双闸竞态守卫有效 |
| cost-guard(run_id 注入) | wired(**仅 CardStack**) | `agent_runner.py:337` `cascade.py:412` | CardStack 路径闭环;**画布路径完全不记账** |
| **publish 发布包** | **broken** | `buildPublishPack.ts` `CardStack.tsx:252` | 纯前端,只在 CardStack(被 flag 暂挂);画布端零出口;后端无 publish 端点 |
| 锚点复用 UI(画布右栏) | **broken** | `AnchorSidebar.tsx:69,75` | onPick 只 `console.log`,不调 `reuseAnchor`(ShotCard 已接,右栏漏接) |

---

## 三、确认的问题清单(critical → low)

### CRITICAL

**C1. 画布生成路径整条不计成本 → ¥25/run + ¥30/天两道 cap 对画布全失效(可无限烧钱)**
- 影响:Pro 画布是真正花钱的主创作面(一条整片 ~¥18-20)。三个 worker 完成时只写状态、绝不 emit `GENERATION_COST`;`sum_generation_cost` 只统计该事件,故画布累计花费永远读 0。enqueue 闸只能拦「单次预测过大」,拦不住多次累计。/admin/cost 看板也看不到。这是历史「prod 烧钱」事故复刻面,既无熔断也无可观测。
- file:line:`image_pipeline.py:77-84` / `video_pipeline.py:57-58` / `composite_pipeline.py:48-49`(done 分支无 emit);`events_repo.py:30`;`cost_guard.py:136-141`
- 修复:三个 pipeline 的 done 分支补 emit 等价于 `cascade._emit_generation_cost` 的记账(真 user_id + enqueue 时持久化到节点行的 run_id + `predict_generation_cost` 估值);短期止血改 enqueue 为 provisional reservation(预占额度)。
- 来源:closed-loop / backend / cost-safety(BE-1=COST-1,**亲核确认**,把握高)

### HIGH

**H1. 画布 Pro 无发布出口 —— 闭环最后一公里在主轨断裂**
- 影响:用户在画布走完「看懂→做版本→出成片」后,停在 composite 节点「能播放」,拿不到可直接发抖音/小红书的标题+标签+脚本+成片打包物。CardStack 那份 `buildPublishPack` 又被 `REWRITE_ENABLED` 暂挂。两轨都到不了可发布成片包。
- file:line:`CardStack.tsx:252`(唯一渲染点)/ `buildPublishPack.ts:48` / `App.tsx:337-345`(画布分支无发布组件)/ `http_router.py` 无 publish 端点
- 修复:把 `buildPublishPack` 接进 composite 节点的 NodeDetail ResultView(成片做完即出「一键复制发布包」),从 script 节点取脚本、image 节点取镜头图、composite result.url 取成片。现有前端组件复用,低成本。
- 来源:closed-loop / product(CLOSE-1=PM-1,**亲核确认**,把握高)

**H2. execute_node 无在途幂等守卫 → 重发把 submitted 节点重置 pending,触发重复付费提交 + 并发回写**
- 影响:第二个 tab / 重连重发 / 手构 WS 消息可把在途节点拉回 pending,被 worker 二次 claim → 二次 `provider.submit`(每次 ~¥1.5)。叠加 C1 成本闸失效 = 无兜底;两个 in-flight worker 还会并发回写 result.url。(`restore_node_version` 已对同一竞态加硬闸,execute 路径却没加。)
- file:line:`ws_handlers.py:364-413` / `canvas.py:478-489 enqueue_generation`(无条件置 pending)/ 对比 `canvas.py:584` restore 的在途硬拒
- 修复:enqueue 前查 `generation_status`,若 ∈ pending/submitted/polling 则幂等返回当前快照,不重复入队。
- 来源:backend(BE-2,**亲核确认**,把握中高;前端按钮门控兜了单 tab 双击,触发面窄)

**H3. NodeDetail 生成面板默认且只能发 apimart/google,主动覆盖后端境内合规的 seedream 默认**
- 影响:新建 image 节点 `image_gen_provider` 为 null → 前端 `|| "apimart"` 必然下发 apimart;后端 `msg.provider or IMAGE_GEN_PROVIDER` 对真字符串不回落,绝不走 seedream。结果:从面板生成大概率因 apimart 缺 key 失败,且与节点工具条入口(传 undefined → 正确回落 seedream)行为不一致;选 google 还构成 prompt+参考图跨境。
- file:line:`NodeDetail.tsx:185,192,226-227` / `ws_handlers.py:365` / `config.py:36`(默认 seedream)
- 修复:下拉默认改为不传(让后端单一真相源兜底),或补 seedream/seedance 选项并设默认;对齐后端真实 provider。
- 来源:frontend / product / design / quality(FE-1=PM-9/UX-4/UI-1,**亲核确认**,把握高)

**H4. 画布右栏锚点复用是死按钮 —— 护城河能力建好却点不动**
- 影响:「跨镜角色/场景一致性(防风格漂移)」是对外宣称的真壁垒,但 AnchorSidebar 点选只 `console.log`,不调 `reuseAnchor`。后端 `anchors.py` 复用能力完整(reuse_count + ANCHOR_REUSED 事件/H8 信号),ShotCard 也已真接线,唯独 Pro 主路径右栏漏接。护城河的「可感知价值」兑现不出来。
- file:line:`AnchorSidebar.tsx:69,75` / 对比已接线的 `ShotCard.tsx:32`
- 修复:onPick → reuseAnchor(参考 ShotCard),加点选反馈;若画布端复用语义未定,至少置灰/标注避免哑交互。
- 来源:product / design(PM-5=UX-5,**亲核确认**,把握高)

**H5. 进画布后不自动开工 —— seed_canvas 只搭空脚手架,激活靠用户再次输入**
- 影响:点「在画布上做我的版本」→ 满心期待自动开始 → 看到空策划书脚手架 + 一句要求再输入。从分析到创作多了一个「冷启动空窗」,正是激活漏斗咽喉(对照 funnel 分析27→改写25→草稿图2 的悬崖式掉率)。
- file:line:`ws_handlers.py:554-576`(纯脚手架不调模型)/ `director.md:51-55`(空 seed 节点「不算」)/ `App.tsx:306-325`(只 seed 不发消息)
- 修复:seed_canvas 时若已有 rewrite 产物直接灌进策划书节点 description;或随 seed 附一句默认创作指令触发 Director,让用户进画布就看到导演在动。先验证激活提升。
- 来源:product(PM-2,**亲核确认**,把握高;属设计取舍,非 bug,但对激活率负面影响真实)

**H6. WS handle_execute_node/regenerate 的 enqueue+cost_guard 入口零单测;无一条 URL→成片端到端测试**
- 影响:成本闸「在正确调用点被正确调用」没被验证;若顺序写反/predict 参数取错/超限分支不回 failed 帧,`test_cost_guard` 仍全绿。闭环接缝(seed→execute→enqueue→worker→canvas_updated 帧)无回归网,任一字段/库路径/帧类型漂移单测全绿却 prod 断链(符合「容器 healthy≠功能 work」教训)。
- file:line:`ws_handlers.py:377,383,402,439`(无 handler 测试);两条 e2e 从不进 `?view=pro`
- 修复:补 handler 级测试(monkeypatch cost_guard 抛 HardFailure → 断言不进 pending + 回 failed 帧)+ 一条后端 seam 集成测试 + 一条 Pro 画布 Playwright smoke。
- 来源:testing(TEST-1+TEST-3,**亲核确认**,把握高)

### MEDIUM(择要)

- **M1. create_canvas_node 三条拒绝分支(上游未确认/层级非法/父不存在)零负向测试** —— 这是「上游未确认不能建下游」护栏的唯一机制,改 HIERARCHY / 把 confirmed 检查写反则测试全绿但护栏失效。`canvas.py:268,270,279`。补负向 + 表驱动 `_validate_hierarchy` 单测。(TEST-2)
- **M2. create_canvas_edge 完全绕过层级/confirmed 约束** —— 前端可手拖连出非法层级/未确认父/环;成环后 `get_ref_urls` 会把不该作参考的 url 喂进生成致产出错乱。属用户自助画布的数据一致性 gap(非跨用户/非提权)。`canvas.py:125-140`。create_edge 复用 `_validate_hierarchy`+父 confirmed+BFS 环检测。(BE-3)
- **M3. STRICT_CROSS_BORDER_REJECT 只拦分析源 URL,不拦生成图经 google/apimart 出境** —— 合规口径漂移(默认 seedream 境内,需显式选才触发;视频 leg 不受影响,仅图像)。`adapter.py:240-268` / `generation.py:327`。在 provider 工厂加跨境门控。(COST-3)
- **M4. per-run cap 的 enqueue-charge/completion-record 时间差**(docstring 自承)—— 即使已记账的 CardStack 路径,一轮 burst 多 video 也能短暂越过 ¥25,靠日闸兜底。`cost_guard.py:25-29`。正解=provisional reservation(同 C1 止血)。(COST-4)
- **M5. NodeDetail/AnchorSidebar 右栏是旧色孤岛** —— NodeDetail 内联 zinc/紫 + 英文状态 toggle + 无 font-serif-cn;AnchorSidebar 全亮色无 dark: 分支,暗色下几乎不可读。`NodeDetail.tsx:489-499,779` / `AnchorSidebar.tsx:41,67`。(UX-1)
- **M6. 画布生成全程不向用户暴露成本/额度** —— 只会「失败」不会「事前提示要花多少/剩多少」;撞 cap 时哑失败(画布视图连 FailureBanner 都不渲染)。后端 `/api/cost/status` 现成无人调。复用 `predict_generation_cost` 给轻量预估 + 给 cap 一个可辨识 error code。(UX-2)
- **M7. 「找到该操作哪个节点」导航缺失**(下一步按钮/reviewing 节点光环/StageBadge 全未建)—— 大画布里用户得自己找 reviewing 节点。`Canvas.tsx:306-359`。补「下一步」fitView+selectNode 性价比最高。(UX-3)
- **M8. Director 路由无断言、director.md 工具名漂移** —— 唯一 director 测试是打真 LLM 的 smoke;`director.md:251` 指示调不存在的 `compose_canvas()`,`director.md:393` 指示调不在工具集的 `execute_node`。拆脚本化假模型路由测试 + prompt-lint 抓漂移。(TEST-4 / PROMPT-1 / PROMPT-2)
- **M9. run_id 注入那行(成本 cap 复活根因修复)无直接断言** —— 反复栽跟头的成本守卫,若重构 mark_running/set_run_ctx 顺序或拼接格式与 emit 侧不一致,cap 再次静默归零而测试全绿。`agent_runner.py:337`。加 CapturingAgent 断言 run_id==`f'{thread_id}#{run_seq}'`。(TEST-5)
- **M10. regenerate/restore 在 to_thread 跑,与事件循环上 worker 回写跨线程非事务,TOCTOU 竞态** —— 触发窄(生成临完成时点回滚/重生),后果单节点状态短暂错乱,可自愈。`canvas.py:566` `generation_repo.py:6`。把在途判定+写回收进单连接 BEGIN IMMEDIATE 或条件 UPDATE。(BE-5)

### LOW(技术债 / 卫生,择要)

- **L1.** `director.md` 行号清理:`compose_canvas` 删/改、`execute_node` 改 update_canvas_node(1 行改动消除真实误导陷阱)。(PROMPT-1/2)
- **L2.** StoryboardNode/AudioNode 死组件(~100 行)+ StoryboardNode 引用废弃 node.status;LegacyStatus 死类型 —— 一并删。(DEAD-1/DEAD-2)
- **L3.** frontend/ 下 10 个未跟踪调试脚本(`_render_*.mjs` 等,含硬编码本机/prod IP)裸露未 gitignore —— 删残骸 + 有用的迁 scripts/ + `.gitignore` 补规则。(HYGIENE-1)
- **L4.** 设计文档 `canvas_unified_plan` 行数已漂移(530→715 / 781→850)、「6 节点 ✅」实为 4 节点+2 死组件 —— 顶部加过期声明,避免架构级误判。(DOC-1)
- **L5.** 生成成本不向用户预暴露 + circuit_breaker 仅接分析上游 + 画布 worker 无密钥就绪检查(无谓提交→失败)—— 均健壮性/体验,非漏费。(COST-5/COST-6)
- **L6.** canvas_updated 整图快照在空画布返回 null 被静默忽略(Agent 删到 0 节点时旧节点残留)+ 整图全量替换语义(大画布性能)。(FE-2)

**两条被对抗式核验「证伪/降级」的**(不进问题清单,仅说明):
- **BE-4/COST-2「画布用 thread_id 当 run_id 与 thread_id#run_seq 永不匹配」=refuted/uncertain**:亲核 canvas/workers/persistence 全链路 **零 run_id 处理**,画布根本没有 run 维度,谈不上「键对不上」;真问题是 C1(根本不记账),不是 run_id 格式不一致。修 C1 时画布天然以 thread_id 为成本单元即可,无需第二处对齐。
- **FE-3「拖动定时器写到错误 thread」=refuted**:setTimeout 回调闭包捕获创建时刻的旧 tid,迟到的 update_position 仍写回正确会话;残留只是定时器泄漏(low,代码卫生)。

---

## 四、九维度速览

1. **闭环完整性**:核心创作引擎真 wired(级联护城河+失败可见+上游硬阻断),但两头断(进=手点非默认流、出=无 publish)+ 画布不记账。亮点:`get_ref_urls` 沿边读父 result.url 的节点级级联真实落地,director.md 明禁画布走 cascade_rewrite 扁路。
2. **产品价值与定位**:最大问题不是技术而是「最后一公里 + 激活路径」断在产品层。优先级应是「兑现现有闭环」而非「再造 ComfyUI Pro 轨」。亮点:「混合演进不替换」的战略判断扎实;成本治理(CardStack 路径)是真护城河且已修到位。
3. **设计与交互**:节点级体验成熟(暖色科技皮消灭黑/白块、StatusChip 折叠三态、time-travel UX 自洽、reduced-motion/a11y 到位);缺口集中在右栏两面板皮没套全 + 成本不可见 + 导航引导未建。
4. **架构与编排**:(本维度结构化 reviewer 未产出,结论由闭环/后端/成本三维交叉给出)双库边界清晰、Director 单 agent + canvas-manager subagent 编排稳定、time-travel 走 app-level 版本自洽;主要架构债=审核两套机制(app-level + 默认 OFF 的 LangGraph interrupt)管不同路径、CardStack 与画布两套生成实现并存。
5. **后端正确性**:状态机/time-travel 守卫设计扎实(取消双闸/终态守卫/snapshot 跳 null);成本闸在画布是「假绑定」(C1)+ execute 无幂等守卫(H2)+ create_edge 零校验(M2)。亮点:`_descendants` BFS visited 去重环安全、worker 任务级异常隔离。
6. **前端正确性**:hooks 纪律非常好(React #310 教训已内化)、跨 thread 缓冲重放扎实、乐观更新边 id 对齐;主问题是 provider 链路(H3)+ 若干瞬态边角。无致命崩溃级 bug。
7. **成本守卫与合规**:CardStack 的 run_id 注入是真的完整修复;画布路径整条不计成本(C1,与历史事故同源、更隐蔽)。跨境硬阻只拦分析源不拦生成图出境(M3)。亮点:身份不可由客户端伪造(server-derived user_id)、回滚不花钱、幂等防重复计费。
8. **测试覆盖**:危险段(成本 cap/time-travel/cancel 竞态/worker 失败/真 interrupt)覆盖意外扎实且多是对抗性用例;盲区在「接缝」与「编排约定」(H6/M1/M8/M9)。亮点:`test_cost_guard` 直接守 b94ca84 修复、time-travel 测真出过的同源 bug。
9. **代码质量与技术债**:主链单点实现+注释充分;债是典型演进残渣(prompt 漂移/死组件/调试脚本裸露/文档行数漂移),多数低风险高 ROI。亮点:`_descendants` 不重复、time-travel 三函数注释把「为什么」讲清。

---

## 五、战略判断 —— 给 founder 的方向建议

**现状护城河成立,但「兑现率」远低于「建成率」。** 你真正的壁垒不是画布 UX(tldraw/ComfyUI 能白拿),而是这四样:① 审核闸 + 层级约束(代码级强制,非口头约定);② 锚点级联防风格漂移;③ 境内合规(火山 ARK 一个 key 打通改写/草稿图/视频/合成);④ time-travel 回溯。这些 tldraw/ComfyUI **带不走**——你们自己的对比文档结论正确。

但问题是:这些壁垒**建好了却没接通用户能感知的出口**——锚点复用是死按钮(H4)、time-travel 已合 main 但产品价值未演示、改写默认暂挂、画布无发布。**护城河的「可感知价值」兑现不出去,等于没有护城河。**

**混合演进该吸收什么**:ComfyUI/litegraph 的「端口强类型 + 图编译」思路值得在「找到该操作哪个节点」「连线时即时校验」上吸收(对应 M2/M7);tldraw 的画布手势/缩略图体验可增量借鉴。**不该做的**:在第一条闭环还没被真实用户走通、还没有留存信号之前,投入 ComfyUI 全栈(境内 GPU 采购 + tldraw 商用授权 + 图编译正确性风险)。

**该砍的过度工程**:`CANVAS_INTERRUPT_GATE`(默认 OFF + 管错路径,画布节点 app 级 reviewing/confirmed 已够)——不再加码,保持 dark,等真用户「跑过头烧钱」的实际信号再说。

**`PRO_CANVAS_TLDRAW_COMFYUI_PLAN` 已是保守口径,且目前是零代码纯文档**(核实无任何 comfyui/ 代码、无 tldraw 依赖)。建议:P0/P1 当低成本技术探针(验证 ComfyUI provider 可达),P2+(seed_builder/全节点集/GPU)gate 在「现有画布闭环被真实用户走通 + 有留存」之后。「为什么是现在」这个问题没回答前不启动 P2。

---

## 六、行动路线 P0 / P1 / P2

### P0 —— 阻断闭环 / 金钱 / 合规风险,必须先修

| # | 动作(owner 友好的最小步) | 风险类别 | owner |
|---|---|---|---|
| P0-1 | **画布三个 pipeline done 分支补 emit GENERATION_COST**:`image/video/composite_pipeline` 完成处调一个等价 `_emit_generation_cost` 的 helper(真 user_id + enqueue 时持久化到节点行的 run_id + predict 估值)。配套测试:worker 完成后已记账。**这是金钱风险头号项。** | 💰 金钱 | Claude/Codex |
| P0-2 | **enqueue 闸改 provisional reservation(预占)** 作为 P0-1 的短期止血 + 永久正解:enqueue 即预占额度,完成转实记/失败回滚,堵住 burst 越 cap(C1+H2+M4 一起解)。 | 💰 金钱 | Claude/Codex |
| P0-3 | **execute_node enqueue 前加在途幂等守卫**:`generation_status ∈ pending/submitted/polling` 则幂等返回,不重复 submit(防重复付费 + 并发回写)。 | 💰 金钱 | Claude |
| P0-4 | **修 H3 provider 默认**:NodeDetail provider 默认改为不传(后端回落 seedream),或补 seedream 选项设默认。防 from-panel 生成走 apimart 失败 + google 跨境。 | 🛡️ 合规 | Cursor |
| P0-5 | **补 H6 最小测试**:execute_node/regenerate handler 级测试(cost_guard 抛 HardFailure → 断言不进 pending）+ 一条后端 seam 集成测试。防成本闸回归静默归零。 | 💰 金钱回归网 | Codex |

### P1 —— 兑现现有闭环价值(高 ROI、低成本)

| # | 动作 | owner |
|---|---|---|
| P1-1 | **画布补发布出口(H1)**:`buildPublishPack` 接进 composite 节点 NodeDetail ResultView,成片做完即出「一键复制发布包」。复用现有组件 + 现有 analysis/script 数据。 | Cursor |
| P1-2 | **锚点复用接线(H4)**:AnchorSidebar onPick → reuseAnchor(参考 ShotCard),加反馈。把已建后端能力变成可感知壁垒。 | Cursor |
| P1-3 | **seed_canvas 带方向种入(H5)**:若已有 rewrite 产物直接灌进策划书节点;或随 seed 附默认创作指令触发 Director。验证激活提升。 | Claude |
| P1-4 | **画布成本可见 + 可辨识失败(M6)**:生成按钮旁轻量预估(复用 `/api/cost/status`),cap raise 回可辨识 error code,画布视图渲染失败提示。 | Cursor |
| P1-5 | **prompt 漂移修正(L1/M8)**:删/改 `director.md:251` compose_canvas、`:393` execute_node;加 prompt-lint 测试(工具名必须在注册集)。 | Claude(1 行级) |
| P1-6 | **改写解封小 cohort 灰度(PM-3)**:`CASCADE_REWRITE_ENABLED=1` 对小 cohort,confidence 闸已能拦平稿,翻车秒关。让默认路径能看到「复刻」。 | Founder 决策 |
| P1-7 | **「下一步」导航(M7)**:右下角按钮 fitView+selectNode 到首个 reviewing 节点 + reviewing 节点光环。性价比最高的导航项。 | Cursor |

### P2 —— 加固与收敛(策略定后做)

| # | 动作 | owner |
|---|---|---|
| P2-1 | create_edge 复用 `_validate_hierarchy`+父 confirmed+BFS 环检测(M2);补 create_canvas_node 三条拒绝分支负向测试(M1)。 | Codex |
| P2-2 | 生成图跨境 provider 门控:`STRICT_CROSS_BORDER_REJECT=1` 时禁 google/apimart(M3)。 | Claude |
| P2-3 | NodeDetail/AnchorSidebar 套全暖色科技皮 + dark: 分支(M5);右栏旧色孤岛收口。 | Cursor |
| P2-4 | regenerate/restore 竞态收进单事务/条件 UPDATE(M10);run_id 注入直接断言(M9)。 | Codex |
| P2-5 | 技术债清理:删死组件 StoryboardNode/AudioNode/LegacyStatus(L2)、调试脚本归档+gitignore(L3)、文档行数/节点数更新(L4)。等双轨策略定后收敛双套生成实现。 | 任一 |
| P2-6 | ComfyUI 新架构:P0/P1 当低成本探针;P2+ gate 在现有画布闭环被真实用户走通 + 有留存信号之后。砍 `CANVAS_INTERRUPT_GATE` 进一步投入。 | Founder 决策 |

**一句话给 founder**:先用一两天把 P0(画布记账+幂等+止血)堵死——这是会真烧钱的活漏洞;再用 P1 把已经造好的护城河(发布/锚点复用/改写)接通让用户摸得到;ComfyUI 全栈等第一条闭环跑出留存再谈。**别在第一条闭环还没收钱时,把资源压到还没验证的第二条产品上。**
