# 视频闭环 + 草稿图改 Seedream · 交接/复盘(2026-06-02)

**作者**: Claude(本会话)· **性质**: 端到端闭环补完 + 生图供应商切换的交接文档
**关联**: [`architecture_layers_2026-06-01.md`](architecture_layers_2026-06-01.md) §5(详细流程)·
[`phase2_gap_analysis_2026-06-01.md`](phase2_gap_analysis_2026-06-01.md) · [`../PHASED_PLAN.md`](../PHASED_PLAN.md) P2-1/P2-9

---

## 0. TL;DR

**Cascade 端到端闭环全段建完、部署、prod 实测跑通,且整链只用一个火山 ARK key,零新密钥。**

```
分析 → 改写 → 草稿图 → 图生视频 → 合成整片 → 发布
doubao  doubao  Seedream  Seedance   ffmpeg     文案+成片包
vision  LLM     (图)      (视频)     (本地)
└──────────── 全部 ARK_API_KEY(已设)────────────┘  └─免费─┘
```

prod HEAD `cf95175`。本会话两件大事:**① 加视频段(图生视频 + 整片合成)② 草稿图从
apimart 中转切到火山 Seedream**(去掉唯一的"缺第三方 key"阻断)。

---

## 1. 做了什么(本会话)

### 视频段(PHASED_PLAN P2-1 + P2-9)
- 后端两个**异步**工具:`cascade_generate_shot_video`(草稿图→Seedance 图生视频)+
  `cascade_compose_film`(逐镜片→ffmpeg 拼整片)。Seedance poll 上限 900s ≫ 180s agent turn
  → **提交后丢后台 `asyncio.create_task` poll,完成 `notify.send_to_user` 推帧**(不读 RUN_CTX,
  捕获 user/thread;抗 ws 重连)。两工具幂等(已生成回推已存 URL,不重复烧钱)。
- 持久化:`shot_assets`(草稿图/视频 URL per 镜)+ `rewrite_films`(整片);资产落 `/media`
  持久(ARK 视频 URL 24h 过期),`_replay_results` 会话重载重放。
- 复用既有:`SeedanceProvider`、`compose.py`(抽出 `compose_local_files` 读本地不重下载)、
  `media_root()`+nginx `/media`。WS 帧 `shot_video_returned` / `film_returned`(regen)。
- 前端:RewriteShotCard 视频四态(草稿图出图后才出「生成视频」,image-grounded;
  DONE=`<video poster=草稿图>`)+ CardStack「合成整片」区 + 成片播放器 + 发布包带成片链接。

### 草稿图改 Seedream(去 apimart)
- `SeedreamProvider`(`{ARK_BASE_URL}/images/generations`,`doubao-seedream-4-0-250828`,同步单 POST
  出 url,接口对齐 ApimartProvider.generate)。`IMAGE_GEN_PROVIDER` 默认改 **seedream**;
  `get_provider`/`image_gen_ready` 动态读 config(seedream→ARK / apimart→IMAGE_GEN / google→GOOGLE)。
- **原因**:apimart 是第三方中转(代理跨境 OpenAI gpt-image),缺 key 且与"火山境内合规"路线
  不一致。Seedream 是火山官方境内、**复用现有 ARK key**、更便宜(¥0.2/张)。

---

## 2. prod 实测(铁律⑤:不只 submit-accepted)

| 验证 | 结果 |
|---|---|
| 草稿图(Seedream + 现有 ARK key) | ✅ 8s 出图(ark TOS) |
| 图生视频(Seedance,萌宠 poster) | ✅ 5s 720p 含音频,~123s |
| **全链 草稿图→视频** | ✅ Seedream 草稿图(9s)→ 喂 Seedance → 5s 视频,287s 总 |
| 火山可达自托管图 | ✅ `cascade.herwin.top/media` 能被火山拉取 |

**关键认知**:Seedance **拒真人图**(`InputImageSensitiveContentDetected.PrivacyInformation`)
→ **Seedream 的 AI 草稿图(合成、无真人)正好绕开**。这就是"先草稿图再视频"而非直接喂源帧的
根本工程原因(源帧有真人,会被拒)。

---

## 3. 成本(都按镜手动触发 + cost_guard 兜底)
- 草稿图 Seedream ~¥0.2/张;图生视频 Seedance 5s ~¥1.5/镜;合成整片本地 ffmpeg 免费。
- 一条 4-5 镜的完整成片粗估:草稿图 ~¥1 + 视频 ~¥6-7.5 + 合成 0 ≈ **¥7-9/条**。
  配额/付费免费额度待 founder 定(建议随视频上线定档)。

## 4. 剩余(交接给后续)
- 🔴【founder】**P0-c prod 凭证轮换**(SSH/root/CF/admin token)——正式 Beta 放量前安全 Gate,
  独立运维项,不影响功能。见 [[reference_prod_server]] memory。
- ⚪ 视频增强:字幕(SRT,从 dialogue)/ BGM / TTS(PHASED_PLAN P2-6/7/8);整片目前=逐镜
  拼接(每片自带 Seedance 音频)。
- ⚪ 配额付费免费额度数字;25 事件埋点(P2-10);改写/视频按 cohort 灰度。
- ⚪ 后端**重启**中途丢 poll 的 boot-resume(持久 task_id + 开机重连);v1 抗 ws 重连即可。
- ⚠️ 全链浏览器 e2e:本机 macOS 代理挡 WSS(见 [[reference_prod_server]] 代理坑),由 founder
  本机走查(真实用户经公网 WSS 不受影响)。

## 5. 教训(本会话新增,供后续避坑)
1. **长任务必须异步**:Seedance poll 900s ≫ agent turn 180s → 提交后台 poll 推帧,不能同步阻塞。
2. **后台任务不能读 RUN_CTX**:turn 结束 ContextVar 就没了;捕获 user/thread + `notify.send_to_user`
   (实时注册表)推帧,天然抗 ws 重连。
3. **`from X import Y` 是静态绑定**:`get_provider`/`image_gen_ready` 必须**动态读 `config.X`**,
   否则 env 变更/测试 monkeypatch 不生效(本会话踩了,改成 `from agent import config; config.X`)。
4. **跨 test DB 污染**:cascade 持久化 DB 没被 `isolated_ws` 隔离 → 加 `CASCADE_DB_PATH` 隔离;
   加新表/重放逻辑时尤其会暴露(本会话 _replay_results 撞上)。
5. **生图供应商要跟整体合规路线一致**:别为省事接中转商代理跨境模型;火山同账号 Seedream/Seedance
   一个 key 打通,合规 + 省心 + 省钱。
6. **AI 生成图 vs 真人源帧**:视频模型有真人隐私拦截 → 这是"草稿图作为视频输入"的设计正当性。

---

*配套 memory:[[project-video-loop-built]]、[[project-generation-leg-blocked-imagekey]](已 RESOLVED)、
[[project-rewrite-publish-loop-live]]。*
