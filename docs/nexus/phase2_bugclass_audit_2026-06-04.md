# 同类 bug 审计 — 2026-06-04

**触发**: 浏览器真机验证抓出 2 个 bug(events 400 漏列 + run_id=None)后,用 16-agent adversarial workflow(5 猎手 × 5 lens + 逐条对抗复核)扫**同类**:前后端契约不一致 / 退化守卫 / 枚举漏列 / 终态回写竞态 / 缓存版本守卫。
**结果**: 11 条候选,**10 条复核确认**。下面按「已修 / 风险待定价 / 低优先级」三档收口。

## ✅ 已修(本次)
- **#9 schedule_generation_retry 终态守卫只挡 cancelled**(generation_repo.py:178)。已 done/failed 的节点被一条迟到的失败回调拉回 pending → 用户看到「明明好了又转圈」/ 卡住。**修**:守卫扩到 `("cancelled","done","failed")`(正常在途 submitted/polling 不受影响)+ 2 个回归测试。

## 🔴 风险待定价:成本守卫在 prod 实际失效(#1-#7,同一根因)
**七条findings指向同一事**:agent/工具路径的成本守卫(¥3/run + ¥30/天)在 prod **形同虚设**。
- **根因 A**:`agent_runner.py:330/464` 把 RUN_CTX 的 `run_id` 恒设 None(`mark_running` 返回的 run_seq 被丢弃)。
- **根因 B**:生成工具 emit 的是 `SHOT_FIRST_FRAME_RETURNED`/`SHOT_VIDEO_RETURNED`/`FILM_RETURNED`(cascade.py:511/615/766),**不是 `GENERATION_COST`**;而 `sum_generation_cost`(events_repo.py:30)**只统计 `GENERATION_COST` 事件**。prod 实测:生成了 2 张图,`generation_cost` 事件 = **0**。
- **根因 C**:后台任务(`_poll_shot_video`/`_compose_film_bg`)脱离 RUN_CTX,emit 时 run_id 写死 None(#2/#3/#7)。
- **合效果**:`_run_cost()` 永远 ≈0 → 每次只比 `predicted < cap`(单件),**累积上限完全不生效**;成本既没拦也没记录(看不到)。

**⚠️ 为什么不能随手修**:若直接补 emit 但 run_id 仍 None,`_run_cost(None)` 会把**所有用户**的成本累加 → ¥3/run cap 一下把**全局生成全卡死**。

**正确修法(需按序、需测、需定价数字)**:
1. `run_agent`/`resume_agent` 用 `mark_running` 的 run_seq 生成真 run_id(如 `f"{thread_id}_{run_seq}"`),写进 RUN_CTX(替掉 None)。
2. 三个后台任务签名加 `run_id`,在 `create_task` 时从 RUN_CTX 捕获传入(#2/#3/#7)。
3. 生成工具成功后 emit `GENERATION_COST`(带 `cost_fen`+`run_id`+provider/model),让 `sum_generation_cost` 有数。
4. cap 值对齐定价(见 [`phase2_pricing_cost_analysis_2026-06-04.md`](phase2_pricing_cost_analysis_2026-06-04.md) ❓7):per-turn cap 要容纳一次合法生成(单图 ¥1.5);¥30/天是主护栏。
5. 全程真容器测,确认不误杀正常生成。

> 这是 Beta 上量前该修的成本控制硬线,但「改错全挂」+ 依赖定价,故列为**需谨慎、带定价决策**的改动,不在本次硬上。

## 🟡 低优先级(已记,未修)
- **#8 update_generation_state 重生竞态**(generation_repo.py:122):重生后旧任务的迟到回写可能盖掉新 pending。需 **task-id fencing**(回写带源 task_id,与节点当前 task_id 不符则跳过)——要改 worker 签名,较 invasive。注:重生路径若已禁在途重生,窗口很小。待与 #1-7 一起做 run_id 体系时一并加 fencing。
- **#10 toprador_cache 无 revision 守卫**(db.py:152):toprador 上游 schema 变时,旧缓存项(TTL **60s**)仍被返回。实际影响有限(60s 窗口 + schema 极少变)。主分析永久缓存已有 ANALYSIS_PIPELINE_REVISION 守卫;此 60s transient 优先级低。

## 方法论留痕
浏览器真机验证 → 抓 2 真 bug → adversarial workflow 扫同类(每条逐个对抗复核,11→10 确认)。这套「真机抓样本 + workflow 扇出同类」对上量前硬化有效,建议每个大 leg 后跑一次。
