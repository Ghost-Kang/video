# Upstream sync policy — waHhhHao/OpenRHTV → Ghost-Kang/video

**Owner**: PM(`upstream-sync-watch` routine + manual override)
**Source repos**:
- Upstream: `https://github.com/waHhhHao/OpenRHTV` (remote `origin`)
- This repo: `https://github.com/Ghost-Kang/video` (remote `gk`)
**Sync state file**: `docs/nexus/founder_log/upstream_sync_state.md`
**Routine**: `upstream-sync-watch` (daily 02:00 UTC, trigger `trig_01AZqceZ6NDTocTUHGq3EEFd`)

---

## 0. 为什么有这个 policy

我们和 waHhhHao 共享同一个 OpenRHTV 代码基础,但有两个独立的产品方向:
- **Upstream (waHhhHao)**: 多用户 canvas 协作平台,集成各种生图/视频/auth 工具
- **This fork (Ghost-Kang)**: **Cascade Phase 1 创作者工具**(10 创作者内测,辅食/育儿/家庭厨房 niche),严格的合规设计(PIPL,境内 LLM,anon 试用)

**核心原则**:不是 wholesale sync。每次 upstream sync 都是选择性的 — 拿对我们 Phase 1 有用的,拒收跟我们设计冲突的。

---

## 1. 哪些 upstream commits **应该** 合入

✅ **接收(默认):**

| 类别 | 标志关键词 | 例子 |
|---|---|---|
| **Bug fixes** | `fix:`, `fix(...)`,修 race / leak / 数据错误 | `9bea52c fix: set canvas contextvars in _run_agent` ✓ |
| **基础设施改进** | session SQLite,multi-user 隔离,worker queue 这种"和 Cascade 共用底盘" | `4b58767 feat: cross-device session sync`(只要不冲突 Phase 1 设计) |
| **TypeScript / ESLint 修复** | `fix: tsc -b`,build cleanup | `d634ce4 fix: remove unused imports` ✓ |
| **依赖升级** | `chore: bump XX` | 一般 ✓,但 review 是否引入兼容性问题 |
| **测试改进** | 新增覆盖 + 修 flaky | ✓ |
| **性能优化** | 数据库 index, lazy load | ✓ |

## 2. 哪些 upstream commits **需要 founder review** 再决定

⚠️ **暂不自动接受,founder 决定:**

| 类别 | 为什么 | 处理 |
|---|---|---|
| **改变默认值** | 可能跟我们合规设计冲突 | review 后人工选择 — 例如 `3c948d9 fix: default image gen to google gemini` 是境外默认,跟 `privacy_v0.md §4.3` 冲突 |
| **新增大功能** | 可能没必要进 Phase 1(节省 review 时间) | review;若 Phase 1 不用,可以推到 Phase 2 时再合 |
| **改 auth/identity 模型** | 跟我们 Phase 1 anon 设计有冲突可能 | review 后桥接(参考 `87288d5 merge-followup` 的处理方式)|
| **触碰 `docs/nexus/` 或 `docs/legal/`** | 这是 PM-管理的目录,upstream 不应该改 | 跳过,保我们这边的版本 |
| **改 Cascade 核心**(adapter, contract, fixtures, prompts) | 我们的 P1-Pn 工作主战场 | 一律 review |

## 3. 哪些 upstream commits **不应该** 合入

❌ **跳过(默认):**

| 类别 | 为什么 |
|---|---|
| **跟我们设计冲突的功能** | 例如要求显式 login,跟我们 anon trial 矛盾 — 除非有 bridge |
| **改我们已经定型的 v0 文档** | `user_agreement_v0.md`, `privacy_v0.md` 等是 founder 签字的,不接受 upstream 改 |
| **跟 niche 无关的实验性功能** | upstream 可能在尝试 3D / VR / 其他,不在 Phase 1 scope |
| **改变项目元数据** | `package.json` name, `pyproject.toml` name 等 |
| **upstream 加的禁用词或合规策略与我们冲突** | 我们的合规依据是 `04_compliance_check.md`,以我们为准 |

---

## 4. Sync 流程(每次 routine fire 或手动 trigger)

### Step 1 — Fetch + diff 统计
```bash
git fetch --all --prune
LAST=$(grep last_evaluated_sha docs/nexus/founder_log/upstream_sync_state.md | head -1 | awk '{print $2}')
git log --oneline $LAST..origin/main | wc -l         # 数量
git log --oneline $LAST..origin/main                 # 列表
git diff --name-only $LAST..origin/main | sort -u    # 涉及哪些文件
```

### Step 2 — 分类 commits(按 §1/§2/§3)
- 自动接收(§1): 默认 cherry-pick
- 需 review(§2): 列在 PR 描述里,founder 决定
- 不应合入(§3): 跳过 + 写明理由

### Step 3 — Dry-run merge,看冲突
```bash
BASE=$(git merge-base origin/main main)
git merge-tree --merge-base $BASE origin/main main 2>&1 | grep "^CONFLICT"
```

### Step 4 — 决策路径
- **冲突 ≤ 3 文件且无语义冲突**: 跑 routine 自动合并 + PR 给 founder review
- **冲突 ≥ 4 文件 或 有语义冲突**: PM 接手手动合(像 2026-05-22 这次)
- **零冲突,全部 §1 类**: 直接 fast-forward main

### Step 5 — 测试
```bash
cd backend && uv run pytest tests/ -q                            # 全跑;关注新增 fail
cd frontend && npx tsc -b && npm test                            # 前端 + ts 类型
bash scripts/check_progress.sh                                   # probe 应保持 healthy
```

### Step 6 — Push + 更新 `upstream_sync_state.md`
- 更新 `last_evaluated_sha` = 当前 origin/main tip
- 在 `## Sync log` 顶部加新条目说明合了哪些 commits / 跳过哪些 / 解了什么冲突
- `git push gk main`

---

## 5. 语义冲突 review 框架(per §2 任何 commit)

当 upstream commit 改变默认值或行为,问 4 个问题:

1. **跟 `privacy_v0.md` / `user_agreement_v0.md` / `04_compliance_check.md` 冲突吗?**
   → 是 → 跳过 OR 桥接(像 `87288d5` 那样保留 upstream code path 但默认值改回我们的)

2. **跟 Phase 1 8 个 Gate(G1-G8 in `05_launch_package.md`)冲突吗?**
   → 是 → 跳过

3. **founder 签字的 `pre_registration_2026-05-21.md` 任何 commitment 受影响吗?**
   → 是 → 跳过 + 写明给 founder 看

4. **能在不破坏 Phase 1 的前提下"双向兼容"吗?(像 ConsentGate auto-write rhtv_user)**
   → 能 → 桥接 + 注释引用此 policy 文档

---

## 6. 历史背景:为什么我们 fork 出来

详见 `03_routing.md §0.1`(founder 决策)。简短:
- waHhhHao 是产品 sandbox,功能堆叠多但 niche 不聚焦
- 我们走 **Phase 1 严格合规 + 创作者工具**路线
- 共享底盘(WS / canvas / SQLite / agent pool),不共享产品方向

定期 sync 是"白嫖 upstream 的 bug fixes 和 infra 改进",而不是 "无脑 follow upstream 的产品方向"。

---

## 7. Routine 配置(`upstream-sync-watch`)

**触发器**: `trig_01AZqceZ6NDTocTUHGq3EEFd`
**频率**: 每天 02:00 UTC
**操作**: 见 `routines/upstream_sync_watch.yml`(如果存在)

**当前状态(2026-05-22)**: routine 自 2026-05-21 seed 后未自动 fire。需要检查触发器是否 active。如果继续不 fire,降级为**每周手动 sync**(每周一早上 PM 跑一次 §4 流程)。

---

## 8. PR 模板(routine 提交 PR 时用)

```markdown
## Upstream sync NNN — 2026-MM-DD

**Anchor**: `<last_evaluated_sha>`
**Upstream tip**: `<origin/main HEAD>`
**Window**: <N> commits

### ✅ Auto-accepted (per policy §1)
- <commit_sha> <subject>
- ...

### ⚠️ Need founder review (per policy §2)
| commit | 为什么需要 review |
|---|---|
| ... | ... |

### ❌ Skipped (per policy §3)
| commit | 跳过原因 |
|---|---|
| ... | ... |

### Tests
- backend full: <N passed / N failed>
- frontend npm test: <N/N>
- check_progress.sh probe: <healthy/regressed>

### Conflicts resolved (if any)
- file1: ...
- file2: ...

### Semantic flags raised
- ...
```

---

**Last revised**: 2026-05-22 by PM after manual sync of 28 commit backfill
