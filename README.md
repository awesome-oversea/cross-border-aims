<div align="center">

# AIMS — AI 全员营销系统

**面向跨境电商的 AI 驱动一体化营销平台**

[![Architecture](https://img.shields.io/badge/Architecture-DDD%20%2B%20EventDriven-blue)]()
[![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20Next.js-green)]()
[![AI](https://img.shields.io/badge/AI-MultiAgent%20%2B%20RAG-orange)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

[English](./README-en.md) | 中文

</div>

---

## 为什么做这个项目

跨境电商行业正经历从"人力密集"到"AI驱动"的转型。一个中型电商团队通常需要同时管理 **5+ 电商平台、3+ 社媒渠道、7×24 客服、供应链协同**——人力成本高、响应慢、数据孤岛严重。

AIMS 的目标不是做一个"聊天机器人"，而是构建一个 **可落地、可运营、可进化** 的 AI 全员营销系统，让 10 人团队拥有 50 人的运营能力。

### 核心业务价值

| 场景 | 痛点 | AIMS 方案 |
|------|------|-----------|
| Listing 生成 | 人工编写效率低、多平台适配难 | AI 生成 + 平台规则合规校验 + 一键发布 |
| 广告投放 | 出价策略依赖经验、ROI 波动大 | AI 出价建议 + 置信度门控 + 效果追踪闭环 |
| 社媒种草 | 内容产出慢、平台规则多变 | AI 种草文案 + 合规检测 + 定时发布 |
| 客服响应 | 重复问题多、负面情绪处理慢 | 意图识别 + 情感分析 + 负面自动转人工 |
| 供应链补货 | 需求预测不准、断货/积压频发 | AI 补货建议 + ERP 一键采纳 + 效果回溯 |
| 数据分析 | 报表分散、决策滞后 | 自动日报/周报 + KPI 看板 + 异常预警 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        客户端 / 通道层                               │
│   飞书(电商群/社媒群) │ 企业微信(客服) │ 钉钉 │ Telegram │ WhatsApp  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     API Gateway (Token Auth)                        │
│                   OpenClaw Engine · 路由 · 会话 · 心跳               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      Multi-Agent 协同层                              │
│                                                                     │
│  ┌─────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐  ┌────────┐ │
│  │  Main   │  │ Ecommerce │  │ Social │  │   CS     │  │ Office │ │
│  │ 总控路由 │  │ 电商运营   │  │ 社媒营销│  │ 客服售后 │  │ 办公   │ │
│  └────┬────┘  └─────┬─────┘  └───┬────┘  └────┬─────┘  └───┬────┘ │
│       │             │            │             │             │      │
│  ┌────▼─────────────▼────────────▼─────────────▼─────────────▼───┐ │
│  │              感知 → 决策 → 执行 → 记忆  Pipeline               │ │
│  │    意图识别  置信度门控  Skill编排  会话持久化                   │ │
│  └──────────────────────────┬────────────────────────────────────┘ │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│                     Skill 技能层 (30+ Skills)                       │
│                                                                     │
│  电商运营: listing-gen │ ad-optimizer │ review-mgr │ material-gen  │
│  社媒营销: xhs-seed │ douyin-ops │ video-channel │ opinion-watch  │
│  客服售后: order-query │ logistics-track │ after-sale │ intent      │
│  办公自动化: report-gen │ excel-viz │ email-mgr │ meeting-minutes │
│  系统能力: cron-engine │ skill-gate │ security-guard │ data-flywheel│
│  数据采集: web-crawler │ knowledge-pipeline │ rag-retrieval        │
└──────────────────────────┬────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                    MCP Server 对接层                                │
│                                                                    │
│  电商平台: taobao-mcp │ jd-mcp │ pdd-mcp                         │
│  社媒平台: xhs-mcp │ douyin-mcp │ wechat-mcp                     │
│  多模态AI: dall-e-mcp │ whisper-mcp │ tts-mcp │ vision-mcp       │
│  ERP闭环: erp-mcp (PDM/OMS/SCM/WMS/FMS/TMS + 一键采纳)          │
│  基础设施: mysql-mcp │ redis-mcp │ milvus-mcp │ qdrant-mcp       │
└──────────────────────────┬────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                      数据与基础设施层                                │
│                                                                    │
│  MySQL 8.0 │ Redis 7.x │ Milvus 2.x │ Qdrant │ MinIO │ Etcd     │
│  Elasticsearch │ Kafka │ RocketMQ │ Ollama (本地LLM)              │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              数据回流与自进化飞轮                              │  │
│  │  CDC管道 → 特征更新 → 向量同步 → 效果追踪 → 模型优化         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 架构设计亮点

### 1. Multi-Agent 协同架构

每个 Agent 独立定义 **感知-决策-执行-记忆** 四模块 Pipeline，而非简单的 prompt 路由：

| Agent | 感知 | 决策 | 执行 | 记忆 |
|-------|------|------|------|------|
| **Main** | 全局消息、系统事件 | 意图分类→路由分发 | 通用问答、跨域协调 | 全局会话、策略缓存 |
| **Ecommerce** | 商品/广告/评论请求 | 平台规则+RAG+置信度 | listing-gen等5大技能 | 商品库、知识检索结果 |
| **Social** | 内容/舆情/导流请求 | 平台规范+发布策略 | xhs-seed等5大技能 | 话术库、发布记录 |
| **CS** | 售前/售后/投诉 | 情感识别+意图分类 | 订单/物流/售后技能 | 用户画像、工单记录 |
| **Office** | 报表/文档/邮件请求 | 模板匹配+数据填充 | 周报/Excel/会议技能 | 模板库、历史报表 |

### 2. 三级 Skill 门控机制

不是所有 AI 操作都能自动执行。AIMS 实现了基于风险的分级门控：

```
低风险 (listing生成、数据查询)     → 自动执行
中风险 (广告调价≤20%、内容发布)    → 执行并通知运营
高风险 (退款审批、广告调价>20%)    → 必须人工确认
```

### 3. MCP Server 标准化对接

采用 Model Context Protocol 实现外部系统标准化对接，每个 MCP Server 遵循四阶段协议：

```
意图识别 → 能力协商 → 标准化调用 → 执行反馈
```

### 4. ERP 一键采纳闭环

AI 建议 → 门控审核 → 人工审批 → 写入 ERP → 效果追踪，形成完整闭环：

```
AI补货建议 → [门控:中风险] → 运营确认 → ERP采购单 → 7天后效果回溯
```

### 5. 数据回流与自进化飞轮

```
业务数据 → CDC管道 → 特征提取 → 向量更新 → 知识库增强
    ↑                                              │
    └────── 效果追踪 ← 采纳执行 ← AI建议 ← RAG检索 ←┘
```

---

## 技术栈

### 后端 (Python 云原生)

| 类别 | 技术选型 | 说明 |
|------|----------|------|
| 基础框架 | FastAPI + Pydantic v2 + SQLAlchemy 2.x (async) | 异步高性能 |
| AI 引擎 | OpenClaw | Multi-Agent 编排引擎 |
| LLM 接入 | DeepSeek / Moonshot / GLM-4 / Ollama (本地) | 多模型热切换 |
| 向量数据库 | Milvus 2.x + Qdrant | 双引擎 RAG |
| 关系数据库 | MySQL 8.0 (asyncmy) | 每服务独立库 |
| 缓存 | Redis 7.x (aioredis) | 会话/特征/限流 |
| 对象存储 | MinIO (S3 兼容) | 图片/文档/模型 |
| 消息队列 | Kafka + RocketMQ | 事件驱动 + 事务消息 |
| 搜索引擎 | Elasticsearch 8.x | 日志/商品搜索 |
| 流计算 | PyFlink / Faust | 实时数据处理 |
| 数据采集 | Canal → Kafka | Binlog CDC |
| 任务调度 | Cron Engine + APScheduler | 定时发布/报表/监控 |

### 前端

| 类别 | 技术选型 |
|------|----------|
| 框架 | Next.js 14+ (App Router) + React 18+ + TypeScript |
| UI | Ant Design 5.x |
| 包管理 | pnpm |

### 基础设施

| 类别 | 技术选型 |
|------|----------|
| 容器化 | Docker + Docker Compose |
| 编排 | Kubernetes + Helm |
| CI/CD | GitHub Actions |
| 日志 | EFK (Elasticsearch + Fluentd + Kibana) |
| 监控 | Prometheus + Grafana |
| 本地 LLM | Ollama (Qwen2.5 / Qwen3.5) |

---

## 项目结构

```
aims/
├── agents/                    # Agent 定义 (5个)
│   ├── main.json              # 总控路由 Agent
│   ├── ecommerce.json         # 电商运营 Agent
│   ├── social-media.json      # 社媒营销 Agent
│   ├── cs.json                # 客服售后 Agent
│   └── office.json            # 办公自动化 Agent
│
├── skills/                    # 技能模块 (30+)
│   ├── listing-gen/           # Listing 生成优化
│   ├── ad-optimizer/          # 广告投放优化
│   ├── xhs-seed/              # 小红书种草
│   ├── douyin-ops/            # 抖音运营
│   ├── review-mgr/            # 评论管理
│   ├── order-query/           # 订单查询
│   ├── logistics-track/       # 物流追踪
│   ├── after-sale/            # 售后处理
│   ├── report-gen/            # 报表生成
│   ├── mcp-framework/         # MCP Server 框架
│   │   ├── ecom_mcp.py        # 电商平台 MCP
│   │   ├── social_mcp.py      # 社媒平台 MCP
│   │   ├── multimodal_mcp.py  # 多模态 AI MCP
│   │   └── erp_mcp.py         # ERP 闭环 MCP
│   ├── agent-orchestrator/    # Agent 编排引擎
│   ├── skill-orchestrator/    # 技能编排器
│   ├── skill-gate/            # Skill 门控机制
│   ├── cron-engine/           # 定时任务引擎
│   ├── knowledge-pipeline/    # RAG 知识管道
│   ├── data-flywheel/         # 数据回流飞轮
│   ├── web-crawler/           # 数据爬虫
│   ├── security-guard/        # 安全合规
│   └── ...                    # 更多技能
│
├── workspace-*/               # Agent 工作空间 (SOUL.md)
├── fixtures/                  # 种子数据与知识库
│   ├── knowledge/             # 知识库种子
│   └── skills/                # 技能场景
│
├── helm/                      # Kubernetes Helm Charts
│   └── aims/                  # 生产级 Helm Chart
│       ├── templates/         # K8s 资源模板
│       └── values*.yaml       # 多环境配置
│
├── k8s/                       # K8s 原生配置
├── docker/                    # Docker 构建
├── scripts/                   # 运维脚本 (PowerShell)
│   ├── p0/                    # 基础设施脚本
│   └── p1/                    # 知识库脚本
│
├── .github/workflows/         # CI/CD 流水线
├── docker-compose.yml         # 开发环境编排
├── openclaw.json              # 系统核心配置
├── mcporter.json              # MCP Server 注册
├── SOUL.md                    # 主 Agent 人设
├── AGENTS.md                  # Agent 协同定义
└── .env.example               # 环境变量模板
```

---

## 30+ 技能清单

### 电商运营 (5)

| 技能 | 功能 | AI 增强 |
|------|------|---------|
| `listing-gen` | 多平台 Listing 生成、SEO 优化、合规校验 | AI 标题/关键词/描述生成 |
| `ad-optimizer` | 广告出价建议、ROI 分析、预算分配 | AI 出价策略优化 |
| `review-mgr` | 评论监控、情感分析、自动回复 | AI 情感识别 + 回复生成 |
| `material-gen` | 商品主图/详情页素材生成 | AI 图片生成 + 文案 |
| `report-gen` | 经营日报/周报/月报自动生成 | AI 数据洞察 |

### 社媒营销 (5)

| 技能 | 功能 | AI 增强 |
|------|------|---------|
| `xhs-seed` | 小红书种草笔记创作与发布 | AI 文案 + 合规检测 |
| `douyin-ops` | 抖音短视频脚本与运营 | AI 脚本生成 |
| `video-channel` | 视频号内容分发 | AI 排期优化 |
| `opinion-watch` | 舆情监控与预警 | AI 情感分析 |
| `cross-drain` | 私域导流策略 | AI 渠道分析 |

### 客服售后 (4)

| 技能 | 功能 | AI 增强 |
|------|------|---------|
| `order-query` | 多平台订单查询 | AI 意图识别 |
| `logistics-track` | 物流轨迹追踪 | AI 异常预警 |
| `after-sale` | 退货退款处理 | AI 风控评估 |
| `intent-recognition` | 客服意图识别 | AI 意图分类 |

### 办公自动化 (5)

| 技能 | 功能 | AI 增强 |
|------|------|---------|
| `report-gen` | 日报/周报/月报 | AI 自动生成 |
| `excel-viz` | Excel 数据可视化 | AI 图表推荐 |
| `email-mgr` | 邮件管理 | AI 模板填充 |
| `doc-auto` | 文档处理 | AI 格式转换 |
| `meeting-minutes` | 会议纪要 | AI 语音转写 |

### 系统能力 (8)

| 技能 | 功能 |
|------|------|
| `agent-orchestrator` | Agent 编排引擎 (感知-决策-执行-记忆) |
| `skill-orchestrator` | 技能编排器 (工作流引擎) |
| `skill-gate` | 三级门控机制 (低/中/高风险) |
| `cron-engine` | 定时任务引擎 (8个内置任务) |
| `knowledge-pipeline` | RAG 知识管道 (6类知识库) |
| `data-flywheel` | 数据回流与自进化飞轮 |
| `security-guard` | 安全合规 (内容风控/防注入/限流/审计) |
| `system-monitor` | 系统监控与告警 |

### 数据采集 (3)

| 技能 | 功能 |
|------|------|
| `web-crawler` | 6大平台数据爬虫 (反反爬策略) |
| `rag-retrieval` | RAG 向量检索 |
| `data-layer` | 数据访问层 |

---

## 快速开始

### 前置条件

- Python 3.11+
- Docker Desktop (可选，用于基础设施)
- 8GB+ RAM (本地 LLM 需要 16GB+)

### 1. 克隆项目

```bash
git clone https://github.com/your-username/aims.git
cd aims
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key (至少配置一个 LLM 提供商)
```

### 3. 启动基础设施

```bash
# Docker 方式 (推荐)
docker compose up -d mysql redis milvus qdrant etcd minio

# 或使用本地脚本
./scripts/p0/Initialize-AimsEnv.ps1
```

### 4. 启动系统

```bash
# 方式一: Docker Compose 全栈启动
docker compose up -d

# 方式二: 本地开发模式
./start-aims.bat
```

### 5. 验证

```bash
# 健康检查
curl http://localhost:18789/health

# 测试技能
python -m skills.listing-gen.main --action generate --product "蓝牙耳机"
```

---

## 部署架构

### 开发环境 (本地 Windows)

```
开发者机器 → OpenClaw (本地) → MySQL/Redis/Milvus (Docker)
```

### 测试环境 (Docker Compose)

```yaml
# docker-compose.yml 已包含完整服务编排
services:
  openclaw:    # AI 引擎
  mysql:       # 关系数据库
  redis:       # 缓存/会话
  milvus:      # 向量数据库
  qdrant:      # 向量数据库 (备选)
  etcd:        # Milvus 依赖
  minio:       # 对象存储
```

### 生产环境 (Kubernetes + Helm)

```bash
# 多环境 Values
helm install aims ./helm/aims/ \
  -f ./helm/aims/values.yaml \           # 基础配置
  -f ./helm/aims/values.prod.yaml \      # 生产覆盖
  -f ./helm/aims/values.prod.shared.yaml # 共享配置
```

---

## 安全设计

| 层面 | 措施 |
|------|------|
| 认证 | Gateway Token + OAuth2 (规划中) |
| 授权 | Skill 门控 (低/中/高风险分级) |
| 数据 | .env 敏感配置不入库、参数化查询 |
| 内容 | 敏感词过滤、极限词检测、平台合规校验 |
| 防注入 | Prompt 注入检测、输入清洗 |
| 限流 | 滑动窗口算法、按 Agent/Skill 粒度限流 |
| 审计 | 操作日志全量记录、可追溯 |
| 凭证 | SHA256 哈希存储、定期轮换 |

---

## 数据流

```
用户消息
  │
  ├─→ 飞书/企微/钉钉/Telegram
  │
  ▼
Gateway (Token Auth)
  │
  ▼
Main Agent (意图分类 + 路由)
  │
  ├──→ Ecommerce Agent ──→ listing-gen / ad-optimizer / review-mgr
  │                              │
  │                              ▼
  │                         Ecom MCP (淘宝/京东/拼多多)
  │                              │
  │                              ▼
  │                         ERP MCP (一键采纳闭环)
  │
  ├──→ Social Agent ────→ xhs-seed / douyin-ops / opinion-watch
  │                              │
  │                              ▼
  │                         Social MCP (小红书/抖音/微信)
  │
  ├──→ CS Agent ────────→ order-query / logistics-track / after-sale
  │                              │
  │                              ▼
  │                         情感分析 → 负面自动转人工
  │
  └──→ Office Agent ────→ report-gen / excel-viz / email-mgr
                                 │
                                 ▼
                            Cron Engine (定时推送)
```

---

## 技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 编排 | OpenClaw | 原生 Multi-Agent 支持、Skill/MCP/Cron 一体化 |
| 主 LLM | DeepSeek | 中文能力强、成本适中、API 稳定 |
| 向量数据库 | Milvus + Qdrant | Milvus 高性能、Qdrant 轻量级，按场景选型 |
| 事务消息 | RocketMQ | 半消息+回查，适合支付/库存强一致场景 |
| 数据管道 | Canal + Kafka | MySQL binlog 实时采集，Python 无需改造 |
| 门控策略 | 三级分级 | 平衡自动化效率与业务安全 |
| ERP 对接 | MCP + 一键采纳 | 标准化协议、人工审批闭环、效果可追溯 |

---

## 路线图

- [x] **P0** — 基础架构搭建 (OpenClaw + 5 Agent + 通道接入)
- [x] **P1** — 核心技能开发 (30+ Skills + MCP Server)
- [x] **P2** — 系统能力建设 (门控/编排/安全/监控)
- [x] **P3** — AI 增强能力 (RAG/情感/推荐/多模态)
- [x] **P4** — 数据闭环 (CDC/飞轮/爬虫/ERP集成)
- [ ] **P5** — 前端控制台 (Next.js 管理界面)
- [ ] **P6** — 生产化 (压测/灰度/多租户/SLA)

---

## 许可证

[MIT License](./LICENSE)

---

<div align="center">

**AIMS — 让 AI 成为每个电商人的超级同事**

</div>
