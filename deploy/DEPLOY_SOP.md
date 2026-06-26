# 部署操作规程（DEPLOY_SOP）

> 适用项目：智能简历筛选工具（Resume Screening）
> 服务器：腾讯云 82.156.87.244
> 生产地址：https://zhimacoder.com/resume/server/

---

## 一、首次部署

### 1.1 服务器准备

```bash
# 登录服务器
ssh root@82.156.87.244

# 创建项目目录
mkdir -p /opt/resume-screening
cd /opt/resume-screening
```

### 1.2 上传代码

在本地项目根目录执行：

```bash
# 打包源码（排除 .git、logs、config 中的敏感文件）
cd /Users/weichen03/Documents/zhimacoder/Resume_screening

rsync -avz --exclude='.git' \
  --exclude='logs/' \
  --exclude='config/.key' \
  --exclude='config/models.json.enc' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  ./ root@82.156.87.244:/opt/resume-screening/
```

### 1.3 构建并启动容器

```bash
ssh root@82.156.87.244 << 'EOF'
cd /opt/resume-screening/deploy
docker compose up -d --build
docker compose ps
EOF
```

### 1.4 初始化加密密钥（首次配置 API Key 时自动生成）

容器启动后，密钥文件位于 volume `resume-key` 对应的 `/root/.config/resume_screening/.key`。

### 1.5 Nginx 路由配置

在品牌站 `zhima-soccer-nginx` 容器中，确保 `nginx.conf` 已包含以下 location（配置文件位于本项目 `deploy/nginx/nginx-resume.conf`）：

```nginx
location /resume/server/ {
    proxy_pass http://resume-screening:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    client_max_body_size 50M;
}

location = /resume/server {
    return 301 /resume/server/;
}
```

热重载 Nginx：

```bash
docker exec zhima-soccer-nginx nginx -t
docker exec zhima-soccer-nginx nginx -s reload
```

### 1.6 验证

```bash
# 健康检查
curl https://zhimacoder.com/resume/server/api/health

# 页面访问
curl -I https://zhimacoder.com/resume/server/
curl -I https://zhimacoder.com/resume/server/app
curl -I https://zhimacoder.com/resume/server/config
```

---

## 二、日常更新

### 2.1 仅前端更新（页面/CSS/JS）

在本地执行部署脚本（自动修正子路径、打包上传、更新容器）：

```bash
bash deploy/scripts/deploy.sh
```

### 2.2 后端更新（Python 代码变更）

```bash
# 1. 上传新代码
rsync -avz --exclude='.git' \
  --exclude='logs/' \
  --exclude='config/.key' \
  --exclude='config/models.json.enc' \
  ./server/ root@82.156.87.244:/opt/resume-screening/server/

# 2. 重建并重启容器
ssh root@82.156.87.244 << 'EOF'
cd /opt/resume-screening/deploy
docker compose up -d --build
EOF

# 3. 验证
curl https://zhimacoder.com/resume/server/api/health
```

### 2.3 配置更新（requirements.txt / Dockerfile / docker-compose.yml）

```bash
# 上传 deploy/ 目录
rsync -avz ./deploy/ root@82.156.87.244:/opt/resume-screening/deploy/

# 重建容器
ssh root@82.156.87.244 << 'EOF'
cd /opt/resume-screening/deploy
docker compose up -d --build
EOF
```

---

## 三、回滚

### 3.1 镜像 tag 管理

每次重大更新前，为当前镜像打 tag：

```bash
# 在服务器上
docker tag resume-screening:latest resume-screening:rollback-$(date +%Y%m%d-%H%M)
```

### 3.2 回滚到上一版本

```bash
ssh root@82.156.87.244 << 'EOF'
# 查看可用镜像
docker images resume-screening

# 停止当前容器
cd /opt/resume-screening/deploy
docker compose down

# 回滚到指定版本（替换 tag）
docker tag resume-screening:rollback-YYYYMMDD-HHMM resume-screening:latest

# 重新启动
docker compose up -d
EOF
```

### 3.3 配置回滚

如果回滚代码仍无法恢复，可回退 git 版本后重新部署：

```bash
# 本地回退
git log --oneline -10
git checkout <commit-hash>

# 重新上传并部署
rsync -avz --exclude='.git' ./ root@82.156.87.244:/opt/resume-screening/
ssh root@82.156.87.244 "cd /opt/resume-screening/deploy && docker compose up -d --build"
```

---

## 四、运维命令速查

| 操作 | 命令 |
|------|------|
| 查看容器状态 | `docker compose -f /opt/resume-screening/deploy/docker-compose.yml ps` |
| 查看日志 | `docker logs -f --tail 100 resume-screening` |
| 重启容器 | `docker restart resume-screening` |
| 进入容器 | `docker exec -it resume-screening bash` |
| 健康检查 | `curl http://localhost:8000/api/health`（容器内） |
| 查看网络 | `docker network inspect football-edge_football-network` |

---

## 五、注意事项

1. **加密密钥**：`config/.key` 是 Fernet 对称加密密钥，丢失后所有已加密的 API Key 将无法解密。密钥存储在 Docker volume `resume-key` 中，不会随代码上传。
2. **网络共享**：容器接入 `football-edge_football-network` 外部网络，与智码足球项目共享。
3. **子路径部署**：前端页面 `<base href="/resume/server/">`，Nginx 代理 `/resume/server/` → `http://resume-screening:8000/`。
4. **CORS 配置**：生产环境 CORS 来源为 `https://zhimacoder.com`，通过环境变量 `CORS_ORIGINS` 控制。
5. **文件上传限制**：Nginx `client_max_body_size 50M`，支持批量上传简历。
