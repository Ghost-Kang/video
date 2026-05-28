# 部署 cookbook — W5D2 cohort 内测上线

> **Audience**: Founder (self-serve ops)
> **Target**: 5-10 创作者 cohort, cf tunnel + 腾讯云轻量, 不备案
> **Time to first user**: 30-60 min (服务器买好之后)

---

## 0. 总览

```
用户 (内地)
   ↓ HTTPS
你的 cf 域名 (例如 cascade.yourbrand.com)
   ↓ Cloudflare Tunnel
   ↓
腾讯云轻量 2C4G 80G 广州 (公网 IP 不暴露)
   ├─ docker compose:
   │   ├─ frontend (nginx:80 → 静态 + 反代)
   │   └─ backend  (python:8765 WS + 8766 HTTP) — 仅内部端口
   └─ host:
       ├─ /opt/cascade/data/    (SQLite 持久化)
       └─ /opt/cascade/backups/ (cron 备份)
```

**不需要 ICP 备案**，因为：
- 服务器 IP 不直接绑域名 DNS
- 用户访问的是 cf 域名 → cf 反代 → tunnel → server
- HTTPS 证书是 cf 签发,不是国内 CA

---

## 1. 买服务器（5 分钟）

打开 https://buy.cloud.tencent.com/lighthouse

| 选项 | 值 |
|---|---|
| 地域 | **广州** (douyinvod CDN 最近) |
| 镜像 | **Ubuntu 22.04 LTS** (官方,纯净) |
| 实例套餐 | **2核4G 5Mbps 80G SSD** (¥45/月, 新客 ¥9-24) |
| 时长 | 1-3 个月 (短期试,贵的话续) |
| 实例名 | `cascade-prod` |

下单后约 1 分钟实例就绪。记下 **公网 IP** + **root 密码** (或用密钥)。

---

## 2. 首次连服务器（5 分钟）

```bash
# Mac/Linux 直接 ssh:
ssh root@<服务器公网IP>
# 第一次会问 fingerprint, 输 yes

# 改一下 root 密码或加密钥 (推荐密钥免密)
# 跳过密码登录: 在本机
ssh-copy-id root@<服务器公网IP>
```

服务器系统初始化：

```bash
apt-get update && apt-get upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt-get install -y docker-compose-plugin sqlite3 git

# 验证
docker --version && docker compose version
```

---

## 3. 拉代码 + 配 .env（5 分钟）

```bash
mkdir -p /opt/cascade && cd /opt/cascade
git clone https://github.com/Ghost-Kang/video.git .

# 配 .env (从 .env.example 起手,改关键值)
cp .env.example .env
nano .env  # 或 vim
```

`.env` 最关键的几行：

```bash
# === LLM ===
ARK_API_KEY=ark-xxxxxxxx                     # 火山方舟 真 key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL=doubao-seed-1-6-250615
LLM_PROVIDER=doubao

# === Cascade upstream (W5D1 已验证 work) ===
CASCADE_UPSTREAM=doubao_direct
TOPRADOR_RESOLVER_MODE=douyin_share

# === MediaKit 备用 (transcribe 走它) ===
VOLC_MEDIAKIT_AK=ak-xxxxxxxx                 # 如果你有

# === 内测准入码 ===
# 5 个伙伴用同一个码, 你愿意可以换多个逗号分隔
INVITE_CODES=CASCADE-2026-W5

# === 图片生成 (可选, 用户主动点才用) ===
IMAGE_GEN_PROVIDER=apimart
APIMART_API_KEY=...
```

---

## 4. 起服务（5 分钟）

```bash
cd /opt/cascade

# 第一次 build (3-5 分钟, ARK_API_KEY 不会被 bake 进镜像 — env_file 运行时注入)
docker compose build

# 起
docker compose up -d

# 看日志确认
docker compose logs -f backend
# 出现 'OpenRHTV WebSocket 服务: ws://0.0.0.0:8765' 就 OK,Ctrl+C 退出 follow
```

健康检查：

```bash
# HTTP API
curl http://localhost/api/events?limit=1
# 应返回 {"events":[...],"has_more":...}

# WS (不能 curl,但可看 nginx 反代起没起)
curl -I http://localhost/
# HTTP/1.1 200 OK
```

---

## 5. Cloudflare Tunnel — HTTPS 公网入口（10 分钟）

**本机 Mac 上**（不是服务器）操作 cf:

```bash
brew install cloudflared
cloudflared login   # 浏览器登 cf, 选你的域名 zone, 同意授权

# 创建 tunnel
cloudflared tunnel create cascade-prod
# 输出 tunnel ID, 记下来 (后面叫 <TUNNEL_UUID>)
```

记下 `~/.cloudflared/<TUNNEL_UUID>.json` (cf credential 文件)。

把它 scp 到服务器：

```bash
scp ~/.cloudflared/<TUNNEL_UUID>.json root@<IP>:/root/.cloudflared/
```

服务器上装 cloudflared：

```bash
# 服务器上
mkdir -p /root/.cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb

cat > /root/.cloudflared/config.yml <<'EOF'
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: cascade.yourbrand.com   # ← 改成你的 cf 子域名
    service: http://localhost:80
  - service: http_status:404
EOF

# DNS 路由 — 在 cf dashboard 给你的子域名加一条 CNAME → <TUNNEL_UUID>.cfargotunnel.com (代理灰云开)
# 或者命令行:
cloudflared tunnel route dns cascade-prod cascade.yourbrand.com

# 起 daemon
cloudflared service install
systemctl status cloudflared
# Active: active (running) ✓
```

**测试**：浏览器开 `https://cascade.yourbrand.com` → 看到 InviteCode 输入页 = 上线成功。

---

## 6. cron SQLite 备份（2 分钟）

```bash
crontab -e
# 加一行:
0 3 * * * /opt/cascade/scripts/ops/backup_sqlite.sh /opt/cascade/data /opt/cascade/backups >> /var/log/cascade-backup.log 2>&1
```

第二天看 `/opt/cascade/backups/` 应该有 `events_20260528_030000.db.gz` 等。

---

## 7. 给伙伴发链接（1 分钟）

```
https://cascade.yourbrand.com
邀请码: CASCADE-2026-W5
```

伙伴打开 → 输码 → 进 Landing → 同意 → 输用户名 → 进 chat → 贴抖音 URL → 看分析。

---

## 8. 日常运维

### 查 cost (founder 每天关心)

```bash
sqlite3 /opt/cascade/data/events.db "select sum(json_extract(payload, '\$.cost_cny')) from events where event_name in ('analysis_returned','script_rewritten','shot_first_frame_returned') and ts > date('now', '-1 day');"
# 返回最近 24h 累计 ¥
```

或者更简洁,浏览器开 `https://cascade.yourbrand.com/admin/cost`。

### 重启 backend (改 .env 后)

```bash
cd /opt/cascade
docker compose restart backend
docker compose logs -f backend | head -20
```

### 加新邀请码

```bash
nano .env   # 改 INVITE_CODES=旧码,新码
docker compose restart backend
```

### 看活跃用户

```bash
sqlite3 /opt/cascade/data/events.db "select distinct user_id from events where ts > date('now', '-7 day');"
```

### 紧急熔断 — 关闭对外访问

```bash
# 把 cf tunnel 停掉, 用户立刻 503
systemctl stop cloudflared
# 恢复:
systemctl start cloudflared
```

---

## 9. 常见问题

**Q: 用户说"输了邀请码进不去"**
A: 后端 `.env` 里的 `INVITE_CODES` 是不是跟发给他的码一致 (大小写敏感)。`docker compose logs backend | grep 拒` 看真实拒绝日志。

**Q: 分析 60s 卡住没反应**
A: `docker compose logs backend | grep -i error` 看 ARK 返回。多半 ARK quota 用完或 douyin URL 失效。

**Q: cf tunnel 显示 503 / 502**
A: `systemctl status cloudflared` 看 tunnel 状态。`docker compose ps` 看 frontend / backend 健康度。

**Q: 一会儿就 OOM 重启**
A: 同时分析的用户多了。短期: `docker compose restart`。中期: 服务器升 8G 或加并发 limit。

---

## 10. Roll-back

代码出问题,回到 W5D1 已 ship state:

```bash
cd /opt/cascade
git log --oneline -5
git checkout <上一个稳定 commit>  # 例如 b33a80b
docker compose up -d --build
```

后端 DB 永远不删 (volume `./data` 在 host) — 回滚不丢用户数据。

---

**写于 2026-05-27 (W5D2)**
**Owner**: founder (self-serve);Claude 后续 update 跟踪 deploy 经验。
