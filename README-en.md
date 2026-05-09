<div align="center">

# AIMS — AI-Powered Full-Stack Marketing System

**An AI-Driven Integrated Marketing Platform for Cross-Border E-Commerce**

[![Architecture](https://img.shields.io/badge/Architecture-DDD%20%2B%20EventDriven-blue)]()
[![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20Next.js-green)]()
[![AI](https://img.shields.io/badge/AI-MultiAgent%20%2B%20RAG-orange)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

中文 | [English](./README-en.md)

</div>

---

## Why This Project

The cross-border e-commerce industry is shifting from "labor-intensive" to "AI-driven." A mid-sized e-commerce team typically manages **5+ platforms, 3+ social channels, 24/7 customer service, and supply chain coordination** — high labor costs, slow response, and severe data silos.

AIMS is not just another chatbot. It's a **production-ready, operable, and evolvable** AI marketing system that gives a 10-person team the operational capacity of 50.

### Core Business Value

| Scenario | Pain Point | AIMS Solution |
|----------|-----------|---------------|
| Listing Generation | Manual writing is slow; multi-platform adaptation is hard | AI generation + compliance check + one-click publish |
| Ad Optimization | Bidding relies on experience; ROI fluctuates | AI bidding suggestions + confidence gating + effect tracking |
| Social Seeding | Content creation is slow; platform rules change frequently | AI copywriting + compliance detection + scheduled posting |
| Customer Service | Repetitive questions; slow handling of negative sentiment | Intent recognition + sentiment analysis + auto-escalation |
| Supply Chain | Inaccurate demand forecasting; frequent stockouts/overstock | AI replenishment + ERP one-click adoption + effect tracing |
| Data Analysis | Scattered reports; delayed decisions | Auto daily/weekly reports + KPI dashboard + anomaly alerts |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client / Channel Layer                       │
│   Feishu (Ecom/Social) │ WeCom (CS) │ DingTalk │ Telegram │ WA    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     API Gateway (Token Auth)                        │
│              OpenClaw Engine · Routing · Session · Heartbeat        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      Multi-Agent Collaboration Layer                │
│                                                                     │
│  ┌─────────┐  ┌───────────┐  ┌────────┐  ┌──────────┐  ┌────────┐ │
│  │  Main   │  │ Ecommerce │  │ Social │  │   CS     │  │ Office │ │
│  │ Router  │  │ Operations│  │ Media  │  │ Service  │  │  Auto   │ │
│  └────┬────┘  └─────┬─────┘  └───┬────┘  └────┬─────┘  └───┬────┘ │
│       │             │            │             │             │      │
│  ┌────▼─────────────▼────────────▼─────────────▼─────────────▼───┐ │
│  │         Perception → Decision → Execution → Memory            │ │
│  │     Intent Recog · Confidence Gate · Skill Orch · Session     │ │
│  └──────────────────────────┬────────────────────────────────────┘ │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│                     Skill Layer (30+ Skills)                        │
│                                                                     │
│  E-Commerce: listing-gen │ ad-optimizer │ review-mgr │ material   │
│  Social:     xhs-seed │ douyin-ops │ video-channel │ opinion     │
│  CS:         order-query │ logistics-track │ after-sale │ intent   │
│  Office:     report-gen │ excel-viz │ email-mgr │ meeting        │
│  System:     cron-engine │ skill-gate │ security │ data-flywheel  │
│  Data:       web-crawler │ knowledge-pipeline │ rag-retrieval     │
└──────────────────────────┬────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                    MCP Server Integration Layer                     │
│                                                                    │
│  E-Commerce: taobao-mcp │ jd-mcp │ pdd-mcp                       │
│  Social:     xhs-mcp │ douyin-mcp │ wechat-mcp                   │
│  Multimodal: dall-e-mcp │ whisper-mcp │ tts-mcp │ vision-mcp     │
│  ERP:        erp-mcp (PDM/OMS/SCM/WMS/FMS/TMS + One-click Adopt) │
│  Infra:      mysql-mcp │ redis-mcp │ milvus-mcp │ qdrant-mcp     │
└──────────────────────────┬────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                   Data & Infrastructure Layer                       │
│                                                                    │
│  MySQL 8.0 │ Redis 7.x │ Milvus 2.x │ Qdrant │ MinIO │ Etcd     │
│  Elasticsearch │ Kafka │ RocketMQ │ Ollama (Local LLM)            │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Data Flywheel & Self-Evolution                  │  │
│  │  CDC Pipeline → Feature Update → Vector Sync → Effect Track │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Highlights

### 1. Multi-Agent Collaboration

Each Agent defines an independent **Perception-Decision-Execution-Memory** pipeline — not simple prompt routing:

| Agent | Perception | Decision | Execution | Memory |
|-------|-----------|----------|-----------|--------|
| **Main** | Global messages, system events | Intent classification → routing | General QA, cross-domain coordination | Global session, policy cache |
| **Ecommerce** | Product/ad/review requests | Platform rules + RAG + confidence | 5 core e-commerce skills | Product DB, knowledge results |
| **Social** | Content/opinion/traffic requests | Platform norms + publishing strategy | 5 social media skills | Template DB, publish history |
| **CS** | Pre-sale/after-sale/complaints | Sentiment + intent classification | Order/logistics/after-sale skills | User profiles, ticket records |
| **Office** | Report/doc/email requests | Template matching + data fill | Report/Excel/meeting skills | Template DB, report history |

### 2. Three-Tier Skill Gating

Not all AI operations should execute automatically. AIMS implements risk-based gating:

```
Low Risk    (listing generation, data queries)      → Auto-execute
Medium Risk (ad price adjustment ≤20%, publishing)   → Execute + notify ops
High Risk   (refund approval, ad price change >20%)  → Require human confirmation
```

### 3. MCP Server Standardized Integration

Using Model Context Protocol for standardized external system integration with a four-stage protocol:

```
Intent Recognition → Capability Negotiation → Standardized Call → Execution Feedback
```

### 4. ERP One-Click Adoption Loop

AI Suggestion → Gate Review → Human Approval → Write to ERP → Effect Tracking:

```
AI Replenishment Suggestion → [Gate: Medium] → Ops Confirmation → ERP Purchase Order → 7-day Effect Tracing
```

### 5. Data Flywheel & Self-Evolution

```
Business Data → CDC Pipeline → Feature Extraction → Vector Update → Knowledge Enhancement
     ↑                                                                   │
     └──────── Effect Tracking ← Adoption ← AI Suggestion ← RAG ←──────┘
```

---

## Tech Stack

### Backend (Python Cloud-Native)

| Category | Technology | Notes |
|----------|-----------|-------|
| Framework | FastAPI + Pydantic v2 + SQLAlchemy 2.x (async) | Async high-performance |
| AI Engine | OpenClaw | Multi-Agent orchestration |
| LLM | DeepSeek / Moonshot / GLM-4 / Ollama (local) | Multi-model hot-swap |
| Vector DB | Milvus 2.x + Qdrant | Dual-engine RAG |
| RDBMS | MySQL 8.0 (asyncmy) | Per-service database |
| Cache | Redis 7.x (aioredis) | Session / features / rate limiting |
| Object Storage | MinIO (S3-compatible) | Images / docs / models |
| Message Queue | Kafka + RocketMQ | Event-driven + transactional messages |
| Search | Elasticsearch 8.x | Logs / product search |
| Stream Processing | PyFlink / Faust | Real-time data processing |
| CDC | Canal → Kafka | MySQL binlog real-time capture |
| Scheduling | Cron Engine + APScheduler | Scheduled publishing / reports / monitoring |

### Frontend

| Category | Technology |
|----------|-----------|
| Framework | Next.js 14+ (App Router) + React 18+ + TypeScript |
| UI | Ant Design 5.x |
| Package Manager | pnpm |

### Infrastructure

| Category | Technology |
|----------|-----------|
| Containerization | Docker + Docker Compose |
| Orchestration | Kubernetes + Helm |
| CI/CD | GitHub Actions |
| Logging | EFK (Elasticsearch + Fluentd + Kibana) |
| Monitoring | Prometheus + Grafana |
| Local LLM | Ollama (Qwen2.5 / Qwen3.5) |

---

## Project Structure

```
aims/
├── agents/                    # Agent definitions (5)
├── skills/                    # Skill modules (30+)
│   ├── listing-gen/           # Listing generation & optimization
│   ├── ad-optimizer/          # Ad bidding optimization
│   ├── xhs-seed/              # Xiaohongshu seeding
│   ├── mcp-framework/         # MCP Server framework
│   │   ├── ecom_mcp.py        # E-commerce platform MCP
│   │   ├── social_mcp.py      # Social media platform MCP
│   │   ├── multimodal_mcp.py  # Multimodal AI MCP
│   │   └── erp_mcp.py         # ERP integration MCP
│   ├── agent-orchestrator/    # Agent orchestration engine
│   ├── skill-gate/            # Skill gating mechanism
│   ├── cron-engine/           # Cron job engine
│   ├── knowledge-pipeline/    # RAG knowledge pipeline
│   ├── data-flywheel/         # Data flywheel & self-evolution
│   ├── web-crawler/           # Web crawler (6 platforms)
│   ├── security-guard/        # Security & compliance
│   └── ...                    # More skills
├── workspace-*/               # Agent workspaces (SOUL.md)
├── fixtures/                  # Seed data & knowledge base
├── helm/aims/                 # Kubernetes Helm Charts
├── k8s/                       # K8s native configs
├── scripts/                   # Ops scripts (PowerShell)
├── .github/workflows/         # CI/CD pipelines
├── docker-compose.yml         # Dev environment orchestration
├── openclaw.json              # Core system configuration
├── mcporter.json              # MCP Server registry
└── .env.example               # Environment variable template
```

---

## 30+ Skills Catalog

### E-Commerce Operations (5)

| Skill | Function | AI Enhancement |
|-------|----------|---------------|
| `listing-gen` | Multi-platform listing, SEO, compliance | AI title/keyword/description |
| `ad-optimizer` | Ad bidding, ROI analysis, budget allocation | AI bidding strategy |
| `review-mgr` | Review monitoring, sentiment, auto-reply | AI sentiment + reply generation |
| `material-gen` | Product image/detail page material | AI image generation + copy |
| `report-gen` | Business daily/weekly/monthly reports | AI data insights |

### Social Media Marketing (5)

| Skill | Function | AI Enhancement |
|-------|----------|---------------|
| `xhs-seed` | Xiaohongshu seeding content | AI copywriting + compliance |
| `douyin-ops` | Douyin short video scripts | AI script generation |
| `video-channel` | WeChat Video Channel distribution | AI scheduling optimization |
| `opinion-watch` | Public opinion monitoring | AI sentiment analysis |
| `cross-drain` | Private domain traffic strategy | AI channel analysis |

### Customer Service (4)

| Skill | Function | AI Enhancement |
|-------|----------|---------------|
| `order-query` | Multi-platform order lookup | AI intent recognition |
| `logistics-track` | Logistics tracking | AI anomaly alerts |
| `after-sale` | Return/refund processing | AI risk assessment |
| `intent-recognition` | CS intent classification | AI intent classification |

### Office Automation (5)

| Skill | Function | AI Enhancement |
|-------|----------|---------------|
| `report-gen` | Daily/weekly/monthly reports | AI auto-generation |
| `excel-viz` | Excel data visualization | AI chart recommendations |
| `email-mgr` | Email management | AI template filling |
| `doc-auto` | Document processing | AI format conversion |
| `meeting-minutes` | Meeting minutes | AI transcription |

### System Capabilities (8)

| Skill | Function |
|-------|----------|
| `agent-orchestrator` | Agent orchestration (Perception-Decision-Execution-Memory) |
| `skill-orchestrator` | Skill orchestration (workflow engine) |
| `skill-gate` | Three-tier gating (low/medium/high risk) |
| `cron-engine` | Cron job engine (8 built-in jobs) |
| `knowledge-pipeline` | RAG knowledge pipeline (6 knowledge categories) |
| `data-flywheel` | Data flywheel & self-evolution |
| `security-guard` | Security & compliance (content moderation / injection prevention / rate limiting / audit) |
| `system-monitor` | System monitoring & alerting |

### Data Collection (3)

| Skill | Function |
|-------|----------|
| `web-crawler` | 6-platform web crawler (anti-blocking strategies) |
| `rag-retrieval` | RAG vector retrieval |
| `data-layer` | Data access layer |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop (optional, for infrastructure)
- 8GB+ RAM (16GB+ for local LLM)

### 1. Clone

```bash
git clone https://github.com/your-username/aims.git
cd aims
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys (at least one LLM provider)
```

### 3. Start Infrastructure

```bash
# Docker (recommended)
docker compose up -d mysql redis milvus qdrant etcd minio

# Or use local scripts
./scripts/p0/Initialize-AimsEnv.ps1
```

### 4. Start System

```bash
# Option A: Docker Compose full stack
docker compose up -d

# Option B: Local development
./start-aims.bat
```

### 5. Verify

```bash
# Health check
curl http://localhost:18789/health

# Test skill
python -m skills.listing-gen.main --action generate --product "bluetooth earbuds"
```

---

## Deployment

### Development (Local Windows)

```
Developer Machine → OpenClaw (local) → MySQL/Redis/Milvus (Docker)
```

### Testing (Docker Compose)

Full stack orchestration via `docker-compose.yml` including OpenClaw, MySQL, Redis, Milvus, Qdrant, Etcd, and MinIO.

### Production (Kubernetes + Helm)

```bash
helm install aims ./helm/aims/ \
  -f ./helm/aims/values.yaml \
  -f ./helm/aims/values.prod.yaml \
  -f ./helm/aims/values.prod.shared.yaml
```

---

## Security Design

| Layer | Measures |
|-------|---------|
| Authentication | Gateway Token + OAuth2 (planned) |
| Authorization | Skill gating (low/medium/high risk tiers) |
| Data Protection | .env excluded from VCS, parameterized queries |
| Content Safety | Sensitive word filtering, superlative detection, platform compliance |
| Injection Prevention | Prompt injection detection, input sanitization |
| Rate Limiting | Sliding window algorithm, per-Agent/Skill granularity |
| Audit | Full operation logging, traceable |
| Credentials | SHA256 hashed storage, periodic rotation |

---

## Technical Decision Records

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent Orchestration | OpenClaw | Native multi-agent support, integrated Skill/MCP/Cron |
| Primary LLM | DeepSeek | Strong Chinese capability, cost-effective, stable API |
| Vector DB | Milvus + Qdrant | Milvus for performance, Qdrant for lightweight use cases |
| Transactional Messages | RocketMQ | Half-message + callback for payment/inventory consistency |
| Data Pipeline | Canal + Kafka | MySQL binlog real-time capture, no Python code changes needed |
| Gating Strategy | Three-tier | Balances automation efficiency with business safety |
| ERP Integration | MCP + One-click Adopt | Standardized protocol, human approval loop, traceable effects |

---

## Roadmap

- [x] **P0** — Foundation (OpenClaw + 5 Agents + Channel Integration)
- [x] **P1** — Core Skills (30+ Skills + MCP Servers)
- [x] **P2** — System Capabilities (Gating/Orchestration/Security/Monitoring)
- [x] **P3** — AI Enhancement (RAG/Sentiment/Recommendation/Multimodal)
- [x] **P4** — Data Loop (CDC/Flywheel/Crawler/ERP Integration)
- [ ] **P5** — Frontend Console (Next.js management interface)
- [ ] **P6** — Production Readiness (Load testing / Canary / Multi-tenant / SLA)

---

## License

[MIT License](./LICENSE)

---

<div align="center">

**AIMS — Making AI the Super-Colleague for Every E-Commerce Professional**

</div>
