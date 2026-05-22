# 小红书 seed post — W3D1 (2026-05-22)

**Owner**: Founder
**Spec source**: `docs/nexus/06_launch_kit.md §1`(标题 + 9 图 carousel + caption + CTA)
**Probe**: `check_progress.sh` 检测 `seed_post_url_*.md` 文件存在即 `seed=YES`

---

## 发布 URL(填在这里)

发布后把小红书帖子 URL 贴下面这一行,**保留 `seed_url:` 前缀**:

```
seed_url: <FILL 你发出的小红书帖 URL>
posted_at: <FILL YYYY-MM-DD HH:MM Asia/Shanghai>
platform: 小红书
```

---

## 今日最小路径(W3D1 下午,~30min)

如果做不完完整 9 图,**先发一个 minimum viable 版本** — caption + 1 张封面图,probe 就闭环了。剩下的 8 图 W3D2-D3 增量补图(小红书允许编辑帖子)。

### Minimum viable(30min):

1. **拍 / P 1 张封面图**: 你家厨房一角(或办公桌)+ 手机屏幕显示一条 5万赞辅食视频截图(脸打码)+ 一张准备食材的砧板。上方文字"看到这条视频的时候,我以为又要熬夜抄一遍。"
2. **粘 caption**(下方 §"Caption 文案速查"复制即可)
3. 发布
4. 贴 URL 到本文件顶部
5. `git add docs/nexus/founder_log/seed_post_url_2026-05-22.md && git commit -m "founder: seed post published"`

### Full path(完整 9 图,~3h):

按 `06_launch_kit.md §1.2` 9 张图依次准备。其中:
- 图 4 (card stack) + 图 6 (anchor sidebar) 是产品截图 — 录屏后裁图
- 图 8 (10 人内测 免费 6 周) + 图 9 (CTA + QR) 是纯文字卡 — Canva / 美图秀秀 5 分钟做
- 图 1-3, 图 5, 图 7 是真实照片 / 拼贴
- 图 7 (receipts) 只有当你自己已经发过一条改写产物之后才能做 — **可以 W4 补**

---

## 📋 Caption 文案速查(直接复制粘贴,founder voice,500 字)

```
看到一条 5 万赞辅食视频的时候,我以为又要熬夜抄一遍。

以前是这么干的:
刷到 → 截屏 → 写"为什么火" → 切剪映 → 找素材 → 还原 → 改成自己的。
4 小时一条。一周做不出 3 条。

后来我做了一个东西帮自己解决这件事。先告诉我"它为什么火" — 开头是怎么抓人的,中间为什么不被划走,结尾凭什么让人点赞。然后帮我换成我家厨房的版本:还是我女儿,还是我那一套围裙,但故事是我自己的。

它还记得我做过的视频里有哪个角色、哪个场景。下一条不用从头开始。

今天这条 30 分钟。发出去比上一条好。

目前是 10 人内测 — 全程免费 6 周。我个人陪你做完第一条。
评论扣 1,或者私信我赛道(宝妈辅食 / 育儿日常 / 家庭厨房)。剩 5 个名额。

#辅食 #育儿日常 #家庭厨房 #短视频创作 #宝妈日常
```

---

## 📋 即刻 cross-post(同一天,~10min)

`06_launch_kit.md §5` 提到 即刻 thread 同日发布。即刻文案可以更直接、技术倾向更强一点,但同样不要用产品行话(节点/锚点/AI/智能/pipeline 等)。**今日先发小红书,即刻可 W3D2 补**。

---

## 📋 禁用词自查(发布前过一遍)

caption 中**绝不能出现**(Brand Guardian + Naval reviewer):

- ❌ AI / 智能 / 神器 / pipeline / workflow / agent / 平台 / 工具(说"东西" / "它")
- ❌ DAG / 节点 / 锚点 / 画布(用人话:角色 / 场景 / 上次的)
- ❌ 复刻 / 抄 / 搬运(用"借鉴公式 / 改成自己的版本")
- ❌ 营养师 / 米其林 / 功效 / 治疗(广告法雷区)
- ❌ 必爆 / 一键火 / 涨粉神器(过度承诺)

caption 现在干净,如果你改写过,过一遍这个列表。

---

## 📋 发布后的 30 分钟监控

按 `05_launch_package.md §2 W1 Day 1`:

- **Morning 90min (你已经投入了)**: Seed post publish + monitor + reply
- 帖子发出后 30 分钟 守在评论区,**真心回复每条评论**(不要用复制粘贴回复)
- 私信收到 niche 报名 → 立刻进入 DM batch 工作流(`recruitment.md`)
- 互动尖峰过后 → 切到 DM batch 模式(开始今日 ≥5 条 DM)

---

## Done-signal

- 本文件顶部 `seed_url:` 填了真实 URL
- `bash scripts/check_progress.sh` → `Marketing seed=YES`(因为 `seed_post_url_*.md` 文件存在,probe 已自动闭环)
- (可选)9 图全部上齐 + 即刻 cross-post 完成
