# P0-C Founder 交付文档 (Handoff)

**Task**: P0-C 手动标注 ≥ 20 条真实 fixture
**Founder action date**: 2026-05-22
**Status**: ✅ **Founder 决策与工具链阶段完成**,待 PM 执行 scaffold + 字幕预填
**Original SOP**: `docs/p0-c_real_fixture_labeling_sop.md`

---

## TL;DR (给 PM / Codex / 接手人 30 秒读完)

Founder 已完成 P0-C 任务中 **唯一不可委派的判断决策部分**:

1. ✅ 确认 P0-C 的真正瓶颈是 `viral_analysis.replicable_formula` 的产品判断,不是体力活
2. ✅ 把原 SOP 的"凑齐 20 条再开干"调整为 **"15 条先开干,缺什么补什么"**(节省 1-1.5 天)
3. ✅ 拆解每条 fixture 的字段为 A/B/C 三档,明确 founder 只必填 C 档(viral_analysis 8 维度)
4. ✅ 交付 scaffold 脚本(自动生成 A 档机械字段)
5. ✅ 交付 8 维度标注 cheatsheet(批量填 C 档时贴屏幕用)
6. ✅ 交付 PM 执行指令(可直接转发)

**剩下未完成的部分**:见本文档 §6 "后续动作 owner 分配"。Founder 这边的判断类工作已经全部 unblock,任何接手人按本文档执行即可推进。

---

## 1. 关键决策与理由

### 决策 1: 不等齐 20 条,先用现有 15 条跑通

**原 SOP**: 凑齐 20 条 URL 后开始标注
**调整后**: 现有 15 条立即开干,缺的 5 条根据填前 15 条暴露的盲点针对性补

**理由**:
- 15 条已能暴露 schema 在真实数据下的大部分问题
- "做着做着发现缺什么 hook 类型" 比 "盲目预补 5 条" 质量高一档
- 把 P0-C 从 3 天工单压缩到 1-2 天

### 决策 2: 拆解字段为 A/B/C 三档,只有 C 档 founder 必填

| 档位 | 字段 | Owner | 工具 |
|---|---|---|---|
| **A. 机械字段** | `schema_version` / `analysis_id` / `source_url` / `platform` / `created_at` / `model` / `cost_cny` | **脚本** | `scaffold_real_v1.py` |
| **B. 看视频转录** | `scenes[].timestamp` / `dialogue` / `visual_content` / `shot_type` / `camera_movement` / `duration_s` | **PM 字幕脚本预填 + Founder review** | Whisper / 抖音字幕 |
| **C. 产品判断** | `viral_analysis` 8 维度 (尤其 `replicable_formula`) / `confidence` | **Founder 唯一不可委派** | 8 维度 cheatsheet (§4) |

**理由**: 原 SOP 把"看视频判断 hook"和"抄写 timestamp"都归为"founder 不可委派",实际上后者是体力活,可委派给 AI / PM 脚本。每条 fixture 工时从 25 min → 5-8 min。

### 决策 3: `replicable_formula` 是这次工作的真正产出

20 条 formula 横向归纳后,能抽出 3-5 个**元公式 (meta-formula)**,这才是 cascade 系统的训练目标 / PRD 骨架 / 投资人故事素材。

**附加产出**: founder 维护 `formulas.md`,做完 20 条后做一次 retro 归纳。

---

## 2. 工具链 (已交付,可直接使用)

### 2.1 Scaffold 脚本 — `scaffold_real_v1.py`

**用途**: 输入 URL list,自动生成 N 个 JSON 骨架,A 档字段全部预填

**下载**: https://www.genspark.ai/api/files/s/fq3ePBNk

**功能验收 (已自测通过)**:
- ✅ 输入 `<niche>,<url>` 格式 txt
- ✅ 输出 `fixtures/real_v1/<niche>/NNN.json`
- ✅ 自动按 niche 分组 + 自动 001/002/003 编号
- ✅ Platform sniff (douyin / xiaohongshu / other)
- ✅ `analysis_id` 命名: `ana_real_<niche>_<3位序号>`
- ✅ `created_at` 自动 UTC ISO 时间戳
- ✅ 已存在文件默认跳过 (`--force` 覆盖)
- ✅ 支持 `--dry-run` 预览

**用法**:
```bash
# 默认输出到 backend/src/agent/cascade/fixtures/real_v1/
python scaffold_real_v1.py urls.txt

# 预览不写文件
python scaffold_real_v1.py urls.txt --dry-run

# 自定义输出目录
python scaffold_real_v1.py urls.txt --output-dir ./real_v1

# 覆盖已存在文件
python scaffold_real_v1.py urls.txt --force
```

### 2.2 URL list 模板 — `urls_15.txt`

**用途**: PM 把 `real_urls_for_p2-4.md` 里的 15 条 URL 按 niche 分类填入此模板

**下载**: https://www.genspark.ai/api/files/s/azEw36Cf

**结构**: 3 个 niche × 5 条 (`baomam_fushi` / `yuer_richang` / `jiating_chufang`)

### 2.3 骨架样例 — `example_skeleton_001.json`

**用途**: 看一眼就知道脚本生成出来的 JSON 长什么样

**下载**: https://www.genspark.ai/api/files/s/QY9Vena2

---

## 3. 待补 5 条 URL 的候选清单

**Founder 决策**: 不预先盲补,做完 15 条后根据暴露的盲点针对性补。下面是候选博主/位置,供后续补 URL 时参考。

| # | Niche | 候选博主/位置 | 抖音入口 | 为什么选这个 |
|---|---|---|---|---|
| 1 | baomam_fushi | 年糕妈妈 (3000万粉,姐妹感) | [主页](https://www.douyin.com/user/MS4wLjABAAAAaBc7pkhIHqnJ8X5zoe2AFuT53uoIzDoL9DBmGWIk-lQ) | 辅食制作类完整链路 |
| 2 | baomam_fushi | 育学园 / 崔玉涛 (专家感) | [搜索](https://www.douyin.com/search/%E8%82%B2%E5%AD%A6%E5%9B%AD%20%E8%BE%85%E9%A3%9F) | 跟年糕妈妈互补,hook 类型不同 |
| 3 | yuer_richang | 年糕妈妈非辅食类 | 同上主页 | 价值观/选择题型爆款 |
| 4 | yuer_richang | 非年糕妈妈百万号 | [搜索"育儿日常"](https://www.douyin.com/search/%E8%82%B2%E5%84%BF%E6%97%A5%E5%B8%B8) | 避免博主集中,抛对比型 hook |
| 5 | jiating_chufang | 美食作家王刚 (556万粉) | [主页](https://www.douyin.com/user/MS4wLjABAAAAIE9S7IWTNu3yKX6yNRXsftjCspMH68sCH-zMuJ2wfNI) | 标准化爆款公式标杆 |
| (备选) | jiating_chufang | 老饭骨 (900万粉) | [主页](https://www.douyin.com/user/MS4wLjABAAAAzsEzo_6VeyzpnmdVHAq0zJjc75UD5YQuMK2Jp_isYMU) | 跟王刚形成对照(人设型 vs 技法型) |

**挑选标准** (founder 在抖音 app 上手动挑):
- 时长 30-180s
- 点赞 ≥ 10w
- niche 典型 (避免边缘案例)
- 跨博主分布 (避免 overfitting 单一风格)

---

## 4. `viral_analysis` 8 维度标注 Cheatsheet

**用途**: Founder 批量填 C 档时贴屏幕边照着扫。**所有字段 ≤ 80 字,`replicable_formula` ≤ 120 字。**

### 4.1 `hook` — 第 1-3 秒怎么抓住人

| 类型 | 标志 | 写法示例 |
|---|---|---|
| 痛点直击型 | "你家娃是不是也…" | "开场直接 callout 宝宝吃饭追着喂的痛点,引发宝妈代入" |
| 反常识型 | "千万别给娃吃 XX" | "颠覆常识:标题党式警告'这种辅食别再做了'" |
| 成品诱惑型 | 一上来怼脸拍成品 | "0.5s 怼脸拍金黄酥脆的成品,视觉冲击引发好奇" |
| 身份代入型 | "作为一个 XX 妈妈…" | "人设开场'三个娃的妈'建立信任感" |
| 悬念型 | "今天教大家一道…" | "王刚式标准开场,悬念式承诺" |

❌ 反面: "视频开始博主出现并讲话" (描述不是分析)

### 4.2 `pacing` — 镜头节奏

| 模式 | 写法示例 |
|---|---|
| 渐进加速 | "前 5s 单镜头铺垫,中段 2-3s/切,结尾 1s/切堆高潮" |
| 匀速快切 | "全程 1.5-2s/切,无停留,制造信息密度焦虑" |
| 长镜头沉浸 | "5-8s 一镜,跟手操作不切,强调真实感" |
| 双速对比 | "教学段慢节奏,成品段突然快切音乐配合" |

❌ 反面: "节奏很快" (太空,要给秒数)

### 4.3 `climax` — 高潮在哪个镜头

**格式**: `在 第 N 秒,[具体动作/画面],因为 [情绪点]`

示例:
- "在 0:18 宝宝主动张嘴吃下平时拒绝的菜,情绪反转点"
- "在 0:42 揭盖瞬间油花四溅 + ASMR 滋啦声,感官峰值"

### 4.4 `visual_style` — 视觉风格 (4 维度都说一句)

| 维度 | 常见值 |
|---|---|
| 色温 | 暖黄(家庭感) / 冷白(专业感) / 高饱和(食欲感) |
| 光源 | 自然光窗边 / 厨房顶灯 / 补光柔光箱 |
| 机位 | 俯拍(食物) / 平视(人物) / 怼脸(成品) / 第一人称(沉浸) |
| 后期 | 原片感 / 字幕花字密集 / 滤镜偏黄油润 |

写法示例: "暖黄色调 + 窗边自然光 + 俯拍切菜/平视讲解切换,字幕密集"

### 4.5 `emotional_arc` — 情绪弧线

**模板**: `[起点情绪] → [中段情绪] → [终点情绪]`

示例:
- "好奇(这道菜?) → 紧张(步骤会不会难?) → 满足(成品诱人)"
- "共鸣(也太难带了) → 期待(有救星?) → 信赖(原来这么简单)"

### 4.6 `target_audience` — 目标受众 (3 标签同时给)

**格式**: 人群 + 场景 + 痛点

示例:
- "0-3 岁宝宝的新手妈妈,辅食阶段焦虑挑食问题"
- "20-35 岁独居打工人,工作日晚饭懒做但想吃好"

### 4.7 `engagement_levers` — 互动钩子

| Lever 类型 | 标志 |
|---|---|
| 抛问题 | "你家娃挑食吗?评论区告诉我" |
| 抛对比 | "A 做法 vs B 做法,你选哪个" |
| 抛悬念 | "看到最后有彩蛋" |
| 抛清单 | "记不住的收藏!三步搞定" |
| 抛立场 | "不同意我观点的来评论区辩论" |
| 抛福利 | "评论区扣 1 抽 XX" |

写法示例: "抛清单('记不住的收藏') + 抛对比(科学辅食 vs 老人喂法),驱动收藏 + 评论"

### 4.8 🔥 `replicable_formula` — 可复制爆款公式 (≤ 120 字,必填非空)

**写作模板**:
> 【Hook 类型】+ 【内容结构】+ 【情绪曲线】+ 【收尾互动】= 【适用赛道】

✅ 好示例 (辅食类):
> "痛点 hook(挑食) + 三步法主体结构(食材展示→关键步骤特写→成品诱惑) + 焦虑→希望→满足的情绪曲线 + 收藏型互动('保存这条')。适用: 母婴辅食 / 减脂餐类"

✅ 好示例 (家常菜类):
> "悬念式开场('今天教一道') + 工序拆解(调料→火候→翻炒) + ASMR 感官峰值(滋啦声/特写) + 转发型互动('转给爱做菜的家人')。适用: 中餐技法教学"

❌ 坏示例: "前面铺垫后面高潮然后引导互动" (太空,不可复制)
❌ 坏示例: "用了好看的画面和好听的配乐" (描述不是公式)

**自检 3 问**:
1. 拿掉品牌/人物,公式还成立吗? (成立才是公式)
2. 别人能照着拍吗? (能才是 replicable)
3. 跨 niche 能迁移吗? (能就是元公式,记到 `formulas.md`)

---

## 5. PM 执行指令 (已在 founder 那边发出 / 可直接转发)

> **【P0-C 调整 · 不等齐 20 条,先跑 15 条】**
>
> 调整决策:
> - 不等新补的 5 条 URL,**先用 `real_urls_for_p2-4.md` 现有 15 条** 跑通 scaffold 流程
> - 缺的 5 条根据 founder 填前 15 条暴露的盲点再针对性补
>
> 今晚需要交付:
>
> **1. 跑 scaffold 脚本生成骨架** (5 分钟)
>    - 脚本: https://www.genspark.ai/api/files/s/fq3ePBNk
>    - 模板: https://www.genspark.ai/api/files/s/azEw36Cf
>    - 从 `real_urls_for_p2-4.md` 提取 15 条 URL,按 niche 整理成 `urls.txt`
>    - 跑: `python scaffold_real_v1.py urls.txt`
>    - 验收: `find backend/src/agent/cascade/fixtures/real_v1 -name '*.json' | wc -l` == 15
>
> **2. B 档字幕预填** (尽量做,降级方案见下)
>    - 用 Whisper / yt-dlp + 抖音字幕,把每条视频的 dialogue 预填到 `scenes[]`
>    - 粗粒度即可:每 3-5s 一个 timestamp,dialogue 填语音转文字结果
>    - **降级**: 如果字幕脚本今晚搞不定,跳过 B 档,founder 看视频时直接听写
>
> **3. 不要做的事**
>    - ❌ 不要等 founder 补 5 条 URL,15 条先做
>    - ❌ 不要填 `viral_analysis` 任何字段 (那是 founder 的活)
>    - ❌ 不要 over-engineer 字幕脚本,Whisper 默认参数够用
>
> ETA: 今晚 23:00 前完成 step 1。22:00 还没动则降级到只交付 step 1。

---

## 6. 后续动作 Owner 分配

| # | 动作 | Owner | ETA | Blocker |
|---|---|---|---|---|
| 1 | 提取 `real_urls_for_p2-4.md` 15 条 URL → `urls.txt` | PM | 今晚 22:00 | 无 |
| 2 | 跑 `scaffold_real_v1.py urls.txt` 生成 15 个骨架 | PM | 今晚 23:00 | 依赖 #1 |
| 3 | (可选) Whisper 字幕预填到 `scenes[].dialogue` | PM | 明天 9:00 | 依赖 #2,可降级跳过 |
| 4 | 做 1 条样板 (建议王刚家常菜) 验通 schema | **Founder** | 明天上午 | 依赖 #2 |
| 5 | 批量填 14 条 `viral_analysis` + scenes | **Founder** | 明天下午 | 依赖 #4 通过 |
| 6 | 同步维护 `formulas.md` 横向归纳 | **Founder** | 明天下午滚动 | 无 |
| 7 | Self-review 15 条暴露的盲点,精准补 5 条 URL | **Founder** | 后天 | 依赖 #5 |
| 8 | 对新 5 条跑增量 scaffold | PM | 后天 | 依赖 #7 |
| 9 | 填完 5 条 = 20 条达标 | **Founder** | 后天 | 依赖 #8 |
| 10 | 跑完成判定,通知 PM 解锁 P0-T | Founder + PM | 后天 EOD | 依赖 #9 |

---

## 7. 完成判定 (SOP 原文保留)

```bash
# 数量达标
find backend/src/agent/cascade/fixtures/real_v1 -name '*.json' | wc -l   # ≥ 20

# 全部 schema 通过
cd backend && uv run pytest tests/test_cascade_contract.py -k real_v1 -v

# 整体进度探针
bash scripts/check_progress.sh   # → Phase0 fixtures=20+
```

**注**: 如 `test_cascade_contract.py` 里没有 `real_v1` 集合 tests,PM 派 Codex 加 `test_validate_all_real_v1_fixtures` 让 contract 测试遍历整个 `real_v1/` 目录 (这是 P0-T 的本质)。

---

## 8. Founder 视角的关键 observation (留给后续 P 阶段)

1. **判断力 vs 体力活混淆是 SOP 设计的常见 bug**。下次写 SOP 时,先做 A/B/C 字段分档,只把 C 档归到不可委派 owner。
2. **"≥ N 条" 类闸门不要 anchor 在 N 上**,先跑通流程暴露问题,再凑数。这个 pattern 适用于所有 Reality Checker 给出的最低值类工单。
3. **`replicable_formula` 的价值 > fixture 本身**。这次产出的 20 条 formula 是 cascade 的训练目标 / PRD 骨架 / 投资人故事素材,优先级应高于 schema 验证。
4. **抖音 web 端不能爬,反爬强度 app >> web 登录态 > web 未登录态 > 爬虫**。后续涉及抖音数据的工单,默认走人工挑 + 脚本辅助路线,别在自动化上花超过 30 分钟。

---

## 9. 文件清单 (项目可读取)

| 文件 | 类型 | 链接 |
|---|---|---|
| 本交付文档 | Markdown | (本文件) |
| Scaffold 脚本 | Python | https://www.genspark.ai/api/files/s/fq3ePBNk |
| URL list 模板 (15 条) | Text | https://www.genspark.ai/api/files/s/azEw36Cf |
| 骨架样例 JSON | JSON | https://www.genspark.ai/api/files/s/QY9Vena2 |
| 原 SOP | Markdown | `docs/p0-c_real_fixture_labeling_sop.md` (项目内) |

---

**Handoff 状态**: ✅ Founder 决策与工具链阶段全部完成。等 PM 执行 §6 #1-#3,Founder 明天上午继续 #4-#5。

**最后更新**: 2026-05-22
**Founder 签字**: ✓
