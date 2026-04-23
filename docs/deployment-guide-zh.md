# ScienceClaw 本地部署教程

本文档帮助你从零开始完成 ScienceClaw 的本地化部署。

ScienceClaw 是一个基于 LangChain DeepAgents 和 AIO Sandbox 构建的个人研究 AI 助手，提供 1,900+ 科学工具、多格式文档生成、网页搜索与爬取以及技能/工具扩展系统，所有功能均在 Docker 容器中本地运行。

---

## 目录

- [前置要求](#前置要求)
- [部署方式选择](#部署方式选择)
- [方式一：预构建镜像部署（推荐）](#方式一预构建镜像部署推荐)
- [方式二：国内镜像加速源码构建](#方式二国内镜像加速源码构建)
- [方式三：标准源码构建（海外用户/开发者）](#方式三标准源码构建海外用户开发者)
- [环境变量配置详解](#环境变量配置详解)
- [端口与服务一览](#端口与服务一览)
- [常用运维命令](#常用运维命令)
- [卸载](#卸载)
- [常见问题排查](#常见问题排查)

---

## 前置要求

### 硬件要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 8 GB | 16 GB+ |
| 磁盘 | 20 GB 可用空间 | 40 GB+（含数据和日志） |

### 软件要求

- **Docker** >= 24.0
- **Docker Compose** >= 2.20（随 Docker Desktop 自动安装）
- **Git**（用于克隆仓库）

#### 安装 Docker

=== "Ubuntu / Debian"

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录使 docker 组生效
```

=== "CentOS / RHEL"

```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
```

=== "macOS"

下载安装 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)。

=== "Windows"

下载安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)。需启用 WSL 2。

安装完成后验证：

```bash
docker --version
docker compose version
```

### LLM API Key

ScienceClaw 需要一个大语言模型的 API Key 才能工作。默认使用 DeepSeek，也支持任何 OpenAI 兼容接口（如 OpenAI、通义千问、Kimi 等）。

- DeepSeek API Key：前往 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取
- 其他兼容接口：准备对应的 API Key 和 Base URL 即可

---

## 部署方式选择

| 方式 | 适合人群 | 构建时间 | 命令 |
|------|---------|---------|------|
| **预构建镜像（推荐）** | 普通用户，快速体验 | ~5 分钟（下载镜像） | `docker-compose-release.yml` |
| **国内镜像加速构建** | 国内开发者，需自定义 | ~20-40 分钟 | `docker-compose-china.yml` |
| **标准源码构建** | 海外用户/项目贡献者 | ~20-40 分钟 | `docker-compose.yml` |

---

## 方式一：预构建镜像部署（推荐）

使用预构建的 Docker 镜像，无需编译，适合大多数用户。

### 第 1 步：克隆仓库

```bash
git clone https://github.com/your-org/ScienceClaw.git
cd ScienceClaw
```

### 第 2 步：配置环境变量

在项目根目录创建 `.env` 文件：

```bash
cat > .env << 'EOF'
# === 必填 ===
API_KEY=your-deepseek-api-key-here

# === 可选 ===
# 如果使用非 DeepSeek 的模型，取消注释并修改以下配置
# API_BASE=https://api.deepseek.com/v1
# MODEL_NAME=deepseek-chat
# TEMPERATURE=0.7
# MAX_TOKENS=2000

# === 资源限制（可选） ===
# SANDBOX_MEM_LIMIT=8g
# SANDBOX_CPUS=4
EOF
```

> **重要**：将 `your-deepseek-api-key-here` 替换为你的实际 API Key。

### 第 3 步：启动服务

```bash
docker compose -f docker-compose-release.yml up -d --pull always
```

首次运行会拉取所有镜像，约需 3-5 分钟（取决于网络速度）。

### 第 4 步：验证部署

检查所有服务是否正常运行：

```bash
docker compose -f docker-compose-release.yml ps
```

所有服务状态应为 `running` 或 `healthy`。

在浏览器中访问：

- **前端界面**：[http://localhost:5173](http://localhost:5173)
- 默认登录账号：`admin`
- 默认登录密码：`admin123`

> **安全提示**：首次登录后请及时修改默认密码。

---

## 方式二：国内镜像加速源码构建

从源码构建，但使用华为云 SWR 镜像加速依赖下载。适合需要二次开发或自定义的用户。

### 第 1 步：克隆仓库

```bash
git clone https://github.com/your-org/ScienceClaw.git
cd ScienceClaw
```

### 第 2 步：配置环境变量

与方式一相同，在项目根目录创建 `.env` 文件：

```bash
cat > .env << 'EOF'
API_KEY=your-deepseek-api-key-here
EOF
```

### 第 3 步：构建并启动

```bash
docker compose -f docker-compose-china.yml up -d --build
```

> **注意**：首次构建需要下载依赖并编译，sandbox 镜像较大（含 Playwright 浏览器），整体构建时间约 20-40 分钟。后续重新构建会利用缓存，速度更快。

### 第 4 步：验证部署

```bash
docker compose -f docker-compose-china.yml ps
```

访问 [http://localhost:5173](http://localhost:5173)，使用 `admin` / `admin123` 登录。

---

## 方式三：标准源码构建（海外用户/开发者）

不使用国内镜像加速，直接从 Docker Hub 和 PyPI/NPM 拉取依赖。

```bash
git clone https://github.com/your-org/ScienceClaw.git
cd ScienceClaw

# 配置 API Key
echo "API_KEY=your-api-key-here" > .env

# 构建并启动
docker compose up -d --build
```

---

## 环境变量配置详解

环境变量通过项目根目录的 `.env` 文件配置。Docker Compose 会自动读取该文件。

### 基础配置

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `API_KEY` | **是** | 无 | LLM API 密钥 |
| `API_BASE` | 否 | `https://api.deepseek.com/v1` | LLM API 地址 |
| `MODEL_NAME` | 否 | `deepseek-chat` | 模型名称 |
| `TEMPERATURE` | 否 | `0.7` | 生成温度（0-1） |
| `MAX_TOKENS` | 否 | `2000` | 最大生成 token 数 |

### 资源限制

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SANDBOX_MEM_LIMIT` | `8g` | 沙箱容器内存上限 |
| `SANDBOX_CPUS` | `4` | 沙箱容器 CPU 核数 |

### 飞书/Lark 集成（可选）

| 变量 | 说明 |
|------|------|
| `LARK_APP_ID` | 飞书应用 ID |
| `LARK_APP_SECRET` | 飞书应用密钥 |

### 切换到其他 LLM 提供商示例

**使用 OpenAI：**

```env
API_KEY=sk-your-openai-key
API_BASE=https://api.openai.com/v1
MODEL_NAME=gpt-4o
```

**使用通义千问：**

```env
API_KEY=sk-your-qwen-key
API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus
```

**使用 Kimi：**

```env
API_KEY=your-moonshot-key
API_BASE=https://api.moonshot.cn/v1
MODEL_NAME=moonshot-v1-8k
```

### 完整 `.env` 模板

```env
# ================================
# ScienceClaw 环境变量配置
# ================================

# --- LLM 配置（必填） ---
API_KEY=your-api-key-here

# --- LLM 可选配置 ---
# API_BASE=https://api.deepseek.com/v1
# MODEL_NAME=deepseek-chat
# TEMPERATURE=0.7
# MAX_TOKENS=2000

# --- 日志级别 ---
# LOG_LEVEL=INFO

# --- 沙箱资源限制 ---
# SANDBOX_MEM_LIMIT=8g
# SANDBOX_CPUS=4

# --- 任务调度 ---
# DISPLAY_TIMEZONE=Asia/Shanghai
# TASK_SERVICE_API_KEY=

# --- 飞书/Lark 集成 ---
# LARK_APP_ID=
# LARK_APP_SECRET=
```

---

## 端口与服务一览

ScienceClaw 由 10 个 Docker 服务组成，启动后各服务占用以下端口：

| 服务 | 主机端口 | 说明 | 用户是否需要关注 |
|------|---------|------|----------------|
| **frontend** | **5173** | Web 前端界面 | **是 — 浏览器访问入口** |
| **backend** | 12001 | 后端 API 服务 | 一般不需要直接访问 |
| **sandbox** | 18080 | 代码执行沙箱 | 不需要 |
| **websearch** | 8068 | 搜索/爬取服务 | 不需要 |
| **scheduler_api** | 12002 | 任务调度 API | 不需要 |
| **mongo** | 27014 | MongoDB 数据库 | 数据库管理时可能需要 |
| **searxng** | 26080 | 元搜索引擎 | 不需要 |
| **redis** | 无（仅内部） | 消息队列 | 不需要 |
| **celery_worker** | 无（仅内部） | 异步任务执行 | 不需要 |
| **celery_beat** | 无（仅内部） | 定时任务调度 | 不需要 |

日常使用只需通过浏览器访问 `http://localhost:5173` 即可。

---

## 常用运维命令

以下命令均需在项目根目录执行。使用国内加速或标准构建的用户，请将命令中的 `docker-compose-release.yml` 替换为对应的 compose 文件。

为方便，可设置别名：

```bash
# 根据你的部署方式选择一条执行
export COMPOSE_FILE=docker-compose-release.yml        # 预构建镜像
# export COMPOSE_FILE=docker-compose-china.yml         # 国内加速
# export COMPOSE_FILE=docker-compose.yml               # 标准构建
```

设置后，后续命令可省略 `-f` 参数。

### 查看服务状态

```bash
docker compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f celery_worker
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启单个服务
docker compose restart backend
```

### 停止服务

```bash
# 停止所有服务（保留数据）
docker compose down
```

### 更新升级

**预构建镜像用户：**

```bash
# 拉取最新镜像并重启
docker compose -f docker-compose-release.yml pull
docker compose -f docker-compose-release.yml up -d
```

**源码构建用户：**

```bash
# 拉取最新代码并重新构建
git pull
docker compose up -d --build
```

### 数据备份

MongoDB 数据存储在 Docker 命名卷 `scienceclaw_mongo_data` 中。

```bash
# 备份数据库
docker compose exec mongo mongodump --out /tmp/backup
docker compose cp mongo:/tmp/backup ./mongodb-backup

# 恢复数据库
docker compose cp ./mongodb-backup mongo:/tmp/backup
docker compose exec mongo mongorestore /tmp/backup
```

用户工作区文件存储在项目根目录的 `workspace/` 目录中，直接备份该目录即可。

---

## 卸载

### 停止并移除容器

```bash
docker compose down
```

### 清理数据卷（会删除所有数据）

```bash
docker compose down -v
```

### 清理镜像

```bash
docker compose down --rmi all
```

### 完全清理

```bash
# 删除所有 ScienceClaw 相关容器、卷和镜像
docker compose down -v --rmi all
# 删除项目目录
rm -rf /path/to/ScienceClaw
```

---

## 常见问题排查

### 1. 端口被占用

**现象**：启动时报 `port is already allocated` 错误。

**解决**：修改 docker-compose 文件中对应服务的端口映射，或停止占用端口的其他程序。

```bash
# 查看端口占用（以 5173 为例）
lsof -i :5173        # macOS / Linux
netstat -tunlp | grep 5173  # Linux
```

### 2. 内存不足

**现象**：容器频繁重启，日志中出现 OOM（Out of Memory）错误。

**解决**：
- 确保 Docker 至少分配了 8 GB 内存（Docker Desktop → Settings → Resources）
- 降低沙箱内存限制：在 `.env` 中设置 `SANDBOX_MEM_LIMIT=4g`

### 3. 镜像拉取慢或失败

**现象**：`docker pull` 超时或速度极慢。

**解决**：
- 国内用户使用 `docker-compose-china.yml` 或 `docker-compose-release.yml`（镜像托管在华为云 SWR）
- 配置 Docker 镜像加速器：编辑 `/etc/docker/daemon.json`（Linux）或 Docker Desktop 设置

```json
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

### 4. API Key 无效

**现象**：对话时提示 API 错误或认证失败。

**解决**：
- 检查 `.env` 文件中 `API_KEY` 是否正确
- 如果使用自定义 API 地址，确认 `API_BASE` 格式正确（需包含 `/v1` 后缀）
- 重启后端服务使配置生效：`docker compose restart backend`

### 5. 构建时间过长

**现象**：源码构建耗时超过 40 分钟。

**解决**：
- sandbox 镜像需要安装 Playwright 浏览器，体积较大（约 2-3 GB），属于正常现象
- 使用预构建镜像（`docker-compose-release.yml`）可跳过构建步骤
- 确保网络通畅，Docker BuildKit 缓存正常工作

### 6. 搜索功能不工作

**现象**：AI 无法执行网页搜索。

**解决**：
- 检查 websearch 和 searxng 服务是否正常运行：`docker compose ps`
- 查看搜索服务日志：`docker compose logs websearch`、`docker compose logs searxng`
- 如果在国内网络环境，Google 搜索引擎可能需要代理配置

### 7. 文件上传失败（413 错误）

**现象**：上传文件时提示 413 Request Entity Too Large。

**解决**：前端 nginx 已配置 `client_max_body_size 100m`。如果使用反向代理（如宿主机 nginx），需要在代理层也添加对应配置。

### 8. 数据库连接失败

**现象**：后端日志显示 MongoDB 连接错误。

**解决**：
- 确认 mongo 服务正常：`docker compose ps mongo`
- 等待 mongo 完全启动（首次启动需要初始化，约 10-20 秒）
- 重启后端：`docker compose restart backend`

---

## 获取帮助

- **GitHub Issues**：提交 Bug 报告或功能建议
- **项目文档**：查看仓库中的 README 获取更多功能介绍
