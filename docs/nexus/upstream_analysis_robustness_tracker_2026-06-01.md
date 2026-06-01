# 上游分析鲁棒性 · 跟踪(2026-06-01 起)

**起因**: 改写解封 eval(15 条真 doubao,run4)暴露 **5/15 = 33% 分析层失败**。failures
全在「分析」(doubao_direct 上游),**不是改写质量问题**(改写质量门全过:机械100% /
realism 4.70 / kept 100% / ad_risk 0)。故未卡改写解封,但影响**真实用户分析成功率**,
独立跟踪。

**负责**: PM 立项;待 founder 排期修复。**性质**: 产品健康债,非阻断。

---

## 1. 失败清单(run4,/tmp/eval_run4.log)

| # | URL | 失败码 | 根因(读码推断) |
|---|-----|--------|------|
| 2 | v.douyin.com/ojHthCnJu9c/ | S5_INVALID_PAYLOAD | scenes 字段 contract 校验失败(模型吐的 scenes 不合 schema / 时间戳异常) |
| 5 | v.douyin.com/pykgmulFYDg/ | S8_UPSTREAM_REFUSED | ARK http_400(火山拒了该视频请求 — 可能时长/格式/帧数) |
| 8 | v.douyin.com/c60TvNaoMIA/ | S5_INVALID_PAYLOAD | 同 #2(scenes 校验) |
| 10 | v.douyin.com/UBVd-dvLBS4/ | S5_INVALID_PAYLOAD | **doubao 吐的 JSON 格式错**:`assistant content not JSON: Expecting ',' delimiter`(模型输出非法 JSON,现有重试没救回) |
| 13 | v.douyin.com/Dkg8wR79C-k/ | S8_UPSTREAM_REFUSED | ARK http_400(同 #5) |

**两类**:
- **S5(3 条)**:doubao 输出问题 — scenes 不合契约 / JSON 格式错。**模型输出鲁棒性**。
- **S8(2 条)**:ARK 直接 http_400 拒请求。**请求/视频兼容性**(某些视频火山不收)。

## 2. 已知缓解 vs 待查

**已有**(不够):
- `doubao_direct_client` 对 **invalid-JSON(S5)重试至多 3 次** —— 但 #10 仍漏(重试没救回,可能每次都同样格式错)。
- adapter 有 scenes pad/clamp/drop 兜底 —— 但 #2/#8 仍 S5,说明某些 scenes 异常兜底没覆盖。
- ARK 超时已 120→165s(60432d9)—— 但 S8 是 http_400(拒绝,非超时),无关。

**待查(按优先级)**:
1. **[P1] S5 JSON 格式错(#10)**:看 doubao 全契约 prompt 是否太复杂导致模型偶发吐坏 JSON;考虑 ① 加更强的 JSON 修复/二次解析 ② 降契约复杂度 ③ 提高重试上限或换 temperature。
2. **[P1] S5 scenes 校验(#2/#8)**:拉这两条的原始模型输出,看 scenes 到底哪里不合 schema(字段缺失?时间戳倒挂?数量?)→ adapter 补对应兜底。
3. **[P2] S8 http_400(#5/#13)**:抓 ARK 返回的 400 body,看火山具体拒什么(视频太长?分辨率?帧数 max_frames=60 不够?)→ 调请求参数或对这类视频降级提示用户。

## 3. 复现 / 诊断手段
```
# 单条诊断(本地需 NO_PROXY 绕代理,见 reference_prod_server)
CASCADE_UPSTREAM=doubao_direct TOPRADOR_RESOLVER_MODE=douyin_share \
NO_PROXY="ark.cn-beijing.volces.com,.douyin.com,.douyinvod.com,.iesdouyin.com" \
  uv run python -c "import asyncio; from agent.cascade.analysis_service import request_shallow_analysis as r; \
  print(asyncio.run(r('<失败URL>', user_id='diag')))"
# 看 ARK 原始返回:在 doubao_direct_client.analyze_video_direct 临时 print response.text
```

## 4. 影响评估
- 当前 33% 失败率若代表真实分布 → **每 3 条用户分析约 1 条失败**。失败有 UI 可见恢复路径(失败有下一步,铁律),不是静默,但伤体验/转化。
- **不卡改写解封**(改写质量已验);但应在 30 人 Beta 放量前压下来(目标失败率 <10%)。
- Phase 2 Gate「热点→创作转化≥15%」会被分析失败率拖累 → 这是 Gate 相关债。

## 5. 跟踪状态
- [x] **P1 S5 JSON 修复(#10)已落地** — `doubao_direct_client._repair_json`:json.loads
      失败时先做保守结构修复(去尾逗号 / 相邻 token 间补缺失逗号),修复后再解析,
      仍失败才 S5。只动结构标点不动值;合法 JSON 不被误改(逗号已在处不匹配)。
      5 条单测覆盖(test_doubao_direct_client.py,16 passed)。**#10 的确证根因
      (`Expecting ',' delimiter`)正是此修复目标。**
- [x] **adapter scenes 兜底全路径审计 = 已足够鲁棒**(2026-06-01)。逐项确认:
      ① 逐幕额外杂键 → 白名单过滤(adapter.py:150-155,`extra="forbid"` 不再炸);
      ② 全部受约束 string 字段 → 截断到 contract 上限(3 个显式 + 16 个 `_SCENE_TEXT_MAXLEN`);
      ③ timestamp → clamp 负值 / clamp 超 duration / bump 倒挂 / drop 不可救 / 重排 / 重编号;
      ④ scene_index → 排序/drop 后一律 1..N 重写;⑤ 数量 → pad 到 ≥3 / 截到 ≤12。
      → **tracker 原先「#2/#8 = scenes 校验失败」是读码推断,非确证**;现有兜底已覆盖所有
      已知 scenes 失败形态。**不再盲加投机兜底**(铁律:investigate before guess)。
- [ ] **P1 #2/#8 待确证** — 现有兜底覆盖不到的某字段。**唯一确证手段 = 拉这两条原始
      ARK 输出**(需 1-2 次 doubao vision 调用 + 本地 NO_PROXY)。founder 在外,未擅自
      烧 ARK 预算;留作下次 eval 重跑时顺带 `print(response.text)` 抓原文 → 对症补。
- [ ] P2 抓 #5/#13 的 ARK 400 body 诊断 S8(同上,需 ARK 调用,留待重跑)
- [ ] 修复后重跑 eval_generic_real_urls(同 15 URL)验证失败率 <10%
      —— **#10 类(JSON 格式)预期已修;重跑可量化降幅**。

*本跟踪不阻断改写解封(已 GO)。改写解封后,生成/发布 leg 继续按 master plan 推进;
本债在 P1 生成 leg 期间或之前并行修。JSON 修复(#10)已随 2026-06-01 部署上线。*
