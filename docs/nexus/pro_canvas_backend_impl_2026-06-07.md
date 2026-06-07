# Pro 高级子画布 · 后端地基落地总结(2026-06-07)

> 依据 [`PRO_CANVAS_TLDRAW_COMFYUI_PLAN.md`](../PRO_CANVAS_TLDRAW_COMFYUI_PLAN.md) 实现 P1 后端地基(fixture-first,无 GPU 依赖)。
> 分支 `gk/pro-canvas-comfyui`,灰度 flag `PRO_CANVAS_ENABLED` 默认 **OFF**,未部署。
> 全量后端测试 **823 passed / 10 skipped**(新增 ~85 个 Pro 单测)。

## 1. 本轮范围(founder 拍板)
后端地基优先 · fixture provider 验证 · tldraw 前端下一轮 · 新分支 + flag 关 + 不部署。
全链(编译/队列/成本/合规/WS/HTTP)在无 GPU 时经 `FixtureComfyUIProvider` 端到端可跑通 + 可测。

## 2. 落地清单

**新增 `backend/src/agent/comfyui/`**
- `node_registry.py` — 5 类 MVP 节点(Model/Prompt/LoadImage/Anchor/Generate/Preview)单一真相源:端口 + 参数(带 min/max)+ ComfyUI class_type + provider 归属 + billable;`registry_json()` 供前端派生 UI。
- `compiler.py` — tldraw 图 JSON → ComfyUI prompt(文生图/图生图宏展开:Checkpoint+CLIPTextEncode×2+EmptyLatent|VAEEncode+KSampler+VAEDecode+SaveImage)/ RunningHub payload;`validate_graph` 8 类错误码(empty/unknown_type/dup_id/bad_edge/port_mismatch/multi_input/missing_required/cycle/no_output);`estimate_graph_cost`。
- `provider.py` — `ComfyUIProvider` ABC + SelfHosted(境内默认)/ RunningHub(境外 opt-in,默认拦)/ Fixture(占位)+ `get_comfyui_provider()` 工厂 + `comfyui_provider_blocked()` 跨境闸。
- `seed_builder.py` — `build_seed_graph(analysis_id, user_id, thread_id=)`:analyses+rewrites+shot_assets+anchors → 开箱可跑种子图(deterministic)。

**队列(canvas.db)**
- `db.py` 新增 `pro_runs` 表(独立于 canvas_nodes)。
- `pro_runs_repo.py` — claim/recover/update(取消守卫 + fencing)/retry/cancel,镜像 generation_repo;原子条件 UPDATE。
- `pro_run_pipeline.py` + `generation_worker.py` 第 4 个 worker `_pro_run_worker`:compile→合规→成本→submit→记账→poll→落 media→fencing 回写→WS 推帧;重启 recover 只 re-poll 不 re-submit。

**配置 / 成本 / 路由**
- `config.py` + `.env.example`:`PRO_CANVAS_ENABLED` / `COMFYUI_PROVIDER` / `COMFYUI_BASE_URL` / `RUNNINGHUB_API_KEY` / `RUNNINGHUB_BASE_URL`。
- `cost_guard.predict_generation_cost` 加 `comfyui` 分支(¥1.5/张,**非 0**)。
- HTTP `POST /api/pro/estimate` + `/api/pro/seed`(flag 门控、COHORT 鉴权);WS `pro_run_submit`/`pro_run_cancel` + 4 个 outbound 事件(`pro_run_progress/node_done/done/failed`)。

## 3. 与 plan 的偏差(实读代码后的订正)
- **改写字段名**:plan §6 写的 `rewriteText/firstFrameUrl/videoUrl` 在代码里不存在。实为 `RewriteShot.visual`(提示词)/`RewriteShot.dialogue`,首帧/视频在 `shot_assets` 表(`image_url`/`video_url`,按 `rewrite_id,shot_index`)。
- **种子定位改写**:`build_seed_graph(analysis_id,user_id)` 两参定位不到改写 → 加 `thread_id` 走 `session_results.load_pointers`,缺则 `load_recent_rewrite(niche='generic')`,再缺降级用 `analysis.scenes` 打底(仍可 Run)。
- **seed/estimate 走 POST**(plan 写 GET):POST 让 dispatcher 把 `body["user_id"]` 钉成 server-derived(mapped 码不可伪造),比 GET 读 qs 更安全。
- **RunningHub = 二元拦截**(非 opt-in 二次同意):代码里「二次同意」机制不存在;本轮实现「跨境=默认禁用」(STRICT_CROSS_BORDER_REJECT 开即拦),二次同意 UI 属 P3。

## 4. 对抗式 review(23 agent,6 维)+ 修复
17 findings / 15 confirmed,已修真问题:
1. **(P0 金钱类)缓存节点仍重渲染**:`estimate` 把 cached Generate 算 ¥0,但 compiler 照发 KSampler → cached 镜在 GPU/按次扣费 provider 上重跑、对成本闸不可见。**修**:compiler 对 cached 节点改发 `LoadImage(cached_url)`、不发 KSampler,执行与估算一致。
2. **取消 TOCTOU**:worker 终态写 + cancel 是 load-then-write 跨连接/跨线程竞态。**修**:原子条件 UPDATE(`status != 'cancelled'` / `comfy_prompt_id = expected` / cancel `status NOT IN (终态)`)。
3. **跨境闸漏 worker 使用点**:持久化的 runninghub 行在 STRICT 翻开后重放仍出境。**修**:worker submit/poll 前再核 `comfyui_provider_blocked` → failed(不重试)。
4. **`load_rewrite_by_id` 未护**:DB 抖动 → seed 500 + 泄异常 + 跳过回落。**修**:try/except → None,落回落链。
5. **重复 shot_index → 撞 node id → 整图 500**:**修**:节点 id 用连续序号,shot_index 仅用于资产查找。
6. **参数 min/max 服务端不强制**:**修**:`_resolved_params` 钳到合法区间。
7. **worker 重试不复核成本闸**(最多 3× predicted):**修**:每次 submit 前复核 cost_guard。
8. **polling 不续租**:**修**:polling 转写续租覆盖整个 poll 窗口。
9. **cancel 漏 flag 门控**:**修**:加 `PRO_CANVAS_ENABLED` 闸。

未改(已记录):seed 共享码下信 client user_id = 全站既有弱模式残留(per-user 码已 server-derived,迁移路径已定);recover 累加 attempt_count 侵蚀重试预算 = 继承 generation_repo 设计,lease 600s 余量充足。

## 5. 下一轮
- **前端 P1**:`/pro/:threadId` + tldraw(免费版带水印)+ 5 节点 UI + compileGraph + Run + cost modal + `pro_run_*` 订阅;入口「⚡ Pro 画布」+ 分析卡「⚡ 展开为计算图」。`make sync-ws-types` 重生 `ws_generated.ts`(已加 ProRun* outbound 模型)。
- **真 ComfyUI E2E**:境内 GPU 起 SelfHosted 实例,`COMFYUI_BASE_URL` 指过去,跑通 submit→poll→出图;LoadImage-from-URL 需配 URL-capable 自定义节点(plan §8 pin 版本)。
- **P2**:端口强类型、cached 节点跳执行(已部分:compiler 不再重渲染 cached)、time-travel 接 pro_runs、ControlNet/Upscale/Video 节点。
