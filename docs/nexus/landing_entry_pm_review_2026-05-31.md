# PM Review — Cascade 落地/入口体验改版

**Author**: Product Manager (agent) · **Date**: 2026-05-31 · **Status**: Draft for build
**Scope**: 首屏 hero 以下 + 链接输入框 + 时长提示 + below-the-fold

---

## 0. TL;DR
1. **定位变了,首屏文案没变**:现在是「粘任意短视频 → 看懂为什么火」,但 hero 还在说「改成你自己的版本」(改写已暂挂)、sample 卡还是宝妈三件套 → 清掉过期承诺。
2. **输入框在撒谎**:placeholder 写「小红书/抖音」,但后端只认抖音、且只认 `www.douyin.com/video/<id>` 桌面 URL;用户在 App 复制的 `v.douyin.com/xxxx` 短链当场不工作 → 入口最大隐形流失。
3. **时长提示是灰色脚注**,没人看 → 改「时长甜蜜点」chip。
4. **底部 niche 卡片已失去意义** → 不等 demo 视频,用已有真实分析做「看看能拆出什么」预览轮播 + 多品类「试一条」。

## 1. Positioning
入口一句话:「粘一条你刷到、好奇为什么火的抖音视频,30 秒拆给你看它凭什么火。」
- hero 副标题改:`看懂它凭什么火——钩子、节奏、情绪、人群,逐帧讲给你听`(删「改成你自己的版本」,兑现承诺对齐)。

## 2. 链接输入 — 校验 + 引导(ask #1)
后端实际只解析:`www.douyin.com/video/<digits>` 或 `iesdouyin.com/share/video/<digits>/`。用户最常复制的是带文案的短链 `v.douyin.com/xxxx`,当场不工作 = 最致命摩擦。

**前端分层(从粘贴的整段字符串里提取,不要求整串是 URL)**:
- A 直接可用:含 `www.douyin.com/video/<id>` 或 `iesdouyin.com/share/video/<id>` → 抽取放行(带文案也抽得出,零后端,立刻消除一大类失败)。
- B 短链:含 `v.douyin.com/<token>` → 依赖后端 302 跟随(见 §5,founder 已定为必做)。
- C 平台不支持:含 xiaohongshu/xhslink/kuaishou/bilibili → 拦截 + 打点平台名。
- D 无法识别 → 拦截 + 展开「怎么复制链接」。
**所有拦截态必须埋点**(B/C/D 计数 + 平台名),否则做完仍不知道用户在粘什么。

**去掉「小红书」承诺**(后端完全不支持,主动制造失败)。placeholder 改:`粘抖音链接,或整段分享文案都行`。

**「怎么复制链接」drawer**(桌面 URL 最稳放第一;App 整段文案直接粘):见正文文案。

**拦截态文案**:短链/其他平台/没认出 三态各给可执行中文引导,不是死胡同。

## 3. 时长提示重设计(ask #2)
灰字脚注 → **「时长甜蜜点」chip + mini-meter**:把 5–180s 硬边界与 15–90s 甜区可视化。
- 文案:`⏱ 时长甜蜜点` · 刻度 `5s 15s 90s 180s` · 中段 `⭐ 拆得最透` · 副行 `15–90 秒信息最足,拆出来最过瘾;5 秒以下太短、3 分钟以上拆不了`。
- 暖色科技语言;首次进入甜区做一次 0.4s 暖色呼吸,之后静止。
- 拒绝态复用同一套语言(过长/过短)。

## 4. Below-the-fold 改版(ask #3)
niche 三卡承载旧定位、且窄化认知;demo 视频还没拍 → 不能等。
- **第一段「看看能拆出什么」结果预览轮播**(用已有真实多品类分析,卡面秀「拆出的洞察」如钩子/情绪,而非垂类名;点开进真实完整分析)。**现在能上**,需 founder 挑 4–6 条真实样例。
- **第二段 3 步「怎么用」静态图**(粘链接 → 30s 解析 → 看拆解),零素材;demo 视频录好后升级替换。
- **撤掉假 CreatorTicker**(内测 10 人,假数据伤信任);要社会证明就上真实聚合版。

## 5. 优先级路线图
- **P0(本迭代,前端为主)**:hero/placeholder 文案清洗;链接校验 A/C/D + 埋点;「怎么复制」drawer;时长 chip;below-fold 预览轮播 + 3 步图;撤 ticker。
- **P1(fast-follow,含高价值后端)**:**后端 `v.douyin.com` 302 跟随**(移动 UA 跟一次 302 抽 id)= 手机 App 链接能直接用的唯一钥匙,移动端入口成功率关键 → **founder 已拍板必做**;之后 B 层从拦截改放行。拒绝态文案联动。
- **P2(信号/素材触发)**:demo 视频替换第二段;真实社会证明 ticker;**小红书**(反爬成本高,先用 C 层打点数据决定,UI 在真支持前不再承诺)。

## 6. 度量
粘贴→成功进入解析 转化率(先埋点建基线)、短链拦截后二次成功率、因时长被拒占比、预览轮播→完整分析进入率。**埋点是 P0。**

## 7. 需 founder 决策
below-fold 预览轮播具体放哪 4–6 条真实样例(内容判断,需从已跑通结果里挑「最能秀质量、品类够广」的几条)。

> 实现落点:前端 `frontend/src/components/landing/*`(hero/UrlFallback/时长提示/HotCardGrid/CreatorTicker);后端 `backend/src/agent/cascade/mediakit/douyin_share_resolver.py`(v.douyin.com 302 + 文案抽链接)。
