# AIMS 本地依赖与 WSL 迁移规范

## 原则

- 所有模型、缓存、市场技能下载缓存、pip/npm 缓存、数据库和向量库持久化数据默认放在 `D:\aitools`。
- 项目目录 `D:\Project\aims` 只保留源码、配置、业务资料和轻量生成文件，不再承载基础设施数据卷。
- 能通过 WSL + Docker Compose 运行的链路优先走 WSL 路径，方便后续迁移到 Linux。
- Docker Compose 默认使用 `pull_policy: never` 和 `--pull never`，避免频繁拉镜像；缺失镜像必须显式一次性准备。

## Windows 路径

`.env` 默认路径：

```env
AIMS_TOOLS_ROOT=D:/aitools
AIMS_LOCAL_STORAGE_ROOT=D:/aitools/aims
AIMS_OLLAMA_DATA_DIR=D:/aitools/aims/ollama
AIMS_LOCAL_MODEL_CACHE_DIR=D:/aitools/aims/model-cache
AIMS_MYSQL_DATA_DIR=D:/aitools/aims/mysql
AIMS_REDIS_DATA_DIR=D:/aitools/aims/redis
AIMS_MINIO_DATA_DIR=D:/aitools/aims/minio
AIMS_MILVUS_DATA_DIR=D:/aitools/aims/milvus
AIMS_QDRANT_DATA_DIR=D:/aitools/aims/qdrant
AIMS_CLAWHUB_CACHE_DIR=D:/aitools/clawhub-cache
AIMS_NPM_CACHE_DIR=D:/aitools/npm-cache
AIMS_PIP_CACHE_DIR=D:/aitools/pip-cache
```

初始化或修复目录：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Initialize-AimsLocalStorage.ps1
```

验证依赖策略：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsDependencyPolicyCheck.ps1
```

## WSL 路径

WSL 运行时会生成 `.generated/.env.wsl`，把 Windows 路径映射为：

```env
AIMS_TOOLS_ROOT=/mnt/d/aitools
AIMS_LOCAL_STORAGE_ROOT=/mnt/d/aitools/aims
AIMS_OLLAMA_DATA_DIR=/mnt/d/aitools/aims/ollama
AIMS_LOCAL_MODEL_CACHE_DIR=/mnt/d/aitools/aims/model-cache
AIMS_MYSQL_DATA_DIR=/mnt/d/aitools/aims/mysql
AIMS_REDIS_DATA_DIR=/mnt/d/aitools/aims/redis
AIMS_MINIO_DATA_DIR=/mnt/d/aitools/aims/minio
AIMS_MILVUS_DATA_DIR=/mnt/d/aitools/aims/milvus
AIMS_QDRANT_DATA_DIR=/mnt/d/aitools/aims/qdrant
```

只生成并检查 WSL 命令，不启动服务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Start-AimsWslCompose.ps1 -UseLocalLlm -StartGateway -DryRun
```

检查 WSL Docker 前置条件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsWslDockerCheck.ps1
```

WSL 启动本地 Ollama 与 OpenClaw 网关：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Start-AimsWslCompose.ps1 -UseLocalLlm -StartGateway
```

WSL 同时启动基础设施：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Start-AimsWslCompose.ps1 -UseLocalLlm -IncludeInfra -StartGateway
```

## 缓存约束

- ClawHub/npm：`Install-AimsMarketSkills.ps1` 会把 `npx` 缓存设到 `AIMS_NPM_CACHE_DIR`，并设置 `CLAWHUB_CACHE_DIR`。
- pip：`Install-AimsRagDependencies.ps1` 和本地模型缓存初始化都会使用 `AIMS_PIP_CACHE_DIR`。
- CPU 模型缓存：`cpu-model-cache-init` 不再执行 Docker build；它使用预置 `AIMS_PYTHON_IMAGE`，运行时用 `/pip-cache` 挂载 `D:\aitools\pip-cache`。
- 模型资产：HuggingFace、reranker、Whisper 等缓存写入 `AIMS_LOCAL_MODEL_CACHE_DIR`。

## 镜像约束

当前默认镜像变量：

```env
AIMS_OPENCLAW_IMAGE=ghcr.io/openclaw/openclaw:latest
AIMS_OLLAMA_IMAGE=ollama/ollama:latest
AIMS_PYTHON_IMAGE=python:3.11-slim
```

这些镜像不会被脚本反复自动拉取。若本地缺失，需要人工确认后一次性拉取或改成 Docker Desktop 中已有的本地 tag。

## 回归检查

每次改动 Docker、依赖安装或技能市场相关脚本后，至少运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsPreflight.ps1 -SkipCompose
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsDependencyPolicyCheck.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Start-AimsWslCompose.ps1 -UseLocalLlm -StartGateway -DryRun
```

启动服务前先盘点本地镜像，不拉取：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsDockerImageInventory.ps1 -UseLocalLlm
```

如果 Windows Docker CLI 不稳定，改从 WSL 内盘点：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Project\aims\scripts\p0\Invoke-AimsDockerImageInventory.ps1 -UseLocalLlm -UseWsl
```

`-UseWsl` 要求 WSL 发行版内可以执行 `docker`。如果提示 `The command 'docker' could not be found`，需要在 Docker Desktop 中开启对应 WSL distro 的 integration，或在 WSL 内安装并连接 Docker Engine。

如有 `FAIL`，只处理缺失镜像。可以把 `AIMS_OPENCLAW_IMAGE`、`AIMS_OLLAMA_IMAGE`、`AIMS_PYTHON_IMAGE` 改成本机已有 tag，或者在人工确认后一次性拉取。
