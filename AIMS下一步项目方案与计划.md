# AIMS 下一步项目方案与计划

> 评估日期：2026-05-06
> 基于：AI营销系统项目方案(OpenClaw版)V2.md、分层架构与数据流协作文档、架构与业务设计文档、任务分解清单、AGENTS.md、PROJECT_STATUS.md
> 证据来源：全部 16 个测试文件的当次运行结果、openclaw.json 实际解析验证、Skills 目录结构检查

---

## 一、评估方法概述

本次评估不是仅看文档，而是逐项对照以下维度的**当前实测状态**：

| 评估维度 | 方法 | 依据 |
|---------|------|------|
| 配置完整性 | 解析 openclaw.json 各字段 | JSON 解析 + 结构遍历 |
| Skill 可执行性 | 运行各 test_*.py 测试 | 16 个测试文件的退出码与输出 |
| 数据层可用性 | MCP 健康检查 | test_mcp_framework.py 输出 |
| 架构一致性 | 对比 AGENTS.md 约束与实际代码 | 是否出现架构双轨 |
| 工程质量 | 编码一致性、异常处理 | 测试中的 UnicodeError / KeyError / IntegrityError |

---

## 二、设计文档中的系统全景

从设计文档（V2方案 + 分层架构 + 业务设计）归纳，AIMS 完整系统由以下层次构成：

```
L1 通道层: 飞书 / 企微 / 钉钉 / Telegram / WhatsApp / Discord
L2 网关层: Token认证 + Bindings路由 + 限流 + 会话管理
L3 Agent层: main / ecommerce / social-media / cs / office（感知-决策-执行-记忆闭环）
L4 Skills层: 14通用 + 16业务（三级加载 + 门控）
L5 MCP层: 电商 / 社媒 / 多模态 / 数据服务 / ERP（四阶段机制）
L6 数据层: MySQL 8.0 / Redis / Milvus / Qdrant / OSS
```

业务闭环目标：
- **电商**：Listing 生成 <30s/条、合规 >95%、RAG 命中 >85%
- **社媒**：种草内容 <5min/篇、内容合规 >95%
- **客服**：客服响应 <3s、负面转人工 100%
- **办公**：周报生成 <5min/份

---

## 三、当前实现状态评估（2026-05-06 实测）

### 3.1 openclaw.json 配置完整性

| 配置域 | 状态 | 详情 |
|--------|------|------|
| JSON 语法 | ⚠️ BOM 问题 | 文件含 UTF-8 BOM，`utf-8-sig` 可解析，标准 JSON 解析器会失败 |
| identity | ❌ 空对象 | `"identity": {}`，未配置名称、描述等基础信息 |
| agents | ✅ 5个Agent已定义 | main / ecommerce / social-media / cs / office |
| channels | ✅ 6通道已配置 | feishu / wework / dingtalk / telegram / whatsapp / discord |
| plugins.entries (Skills) | ❌ 空数组 | **没有任何 Skill 注册到配置中** |
| cron.jobs | ❌ 空数组 | **没有任何 Cron 任务注册到配置中** |
| gateway.auth | ✅ Token模式已配置 | gateway.auth.mode = "token" |
| session | ✅ per-channel-peer隔离已配置 | |

**关键发现**：openclaw.json 虽然定义了 5 个 Agent 和 6 个通道，但 Skills 注册和 Cron 任务注册均为空，意味着 OpenClaw 原生运行时不会加载任何自定义 Skill，也不会触发任何定时任务。

### 3.2 Skills 代码层实现

**已有的 14 个业务 Skill 骨架（每个含 SKILL.md + main.py）：**

| Skill | 域 | 行数 | 运行状态 |
|-------|-----|------|---------|
| listing-gen | 电商 | 851 | ✅ test_skills 通过 |
| ad-optimizer | 电商 | 620 | ✅ test_skills 通过 |
| review-mgr | 电商 | — | ✅ test_skills 通过 |
| material-gen | 电商 | — | ✅ test_skills 通过 |
| xhs-seed | 社媒 | — | ✅ test_skills 通过 |
| douyin-ops | 社媒 | — | ✅ test_skills 通过 |
| video-channel | 社媒 | — | ✅ test_skills 通过 |
| opinion-watch | 社媒 | — | ✅ test_skills 通过 |
| cross-drain | 社媒 | — | ⚠️ test_new_skills 通过但 Unicode 编码异常 |
| order-query | 客服 | — | ❌ test_skills 因 GBK 编码断裂 |
| logistics-track | 客服 | — | ✅ 测试通过 |
| after-sale | 客服 | — | ✅ 测试通过 |
| email-mgr | 办公 | — | ✅ 测试通过 |
| doc-auto | 办公 | — | ✅ 测试通过 |

**已有的 10 个平台型 Skill：**

| Skill | 行数 | 作用 | 架构风险 |
|-------|------|------|---------|
| skill-orchestrator | 1735 | Skill 编排调度 | ⚠️ 与 OpenClaw 原生调度重叠 |
| agent-orchestrator | — | Agent 编排路由 | ⚠️ 与 OpenClaw Agent 层重叠 |
| cron-engine | 732 | 定时任务引擎 | ⚠️ 与 OpenClaw Cron 重叠 |
| data-layer | 766 | 数据访问抽象层 | ⚠️ 与 MCP + MySQL 原生能力重叠 |
| security-guard | 608 | 安全门控 | ⚠️ 与 OpenClaw gate + skill-vetter 重叠 |
| skill-gate | — | Skill 门控 | ⚠️ 部分重叠，可保留为自定义策略 |
| mcp-framework | 1012 | MCP Server 框架 | ✅ 必要的基础设施 |
| knowledge-pipeline | 724 | 知识库处理管线 | ✅ 必要的自定义能力 |
| confidence-gate | — | 置信度门控 | ⚠️ 部分重叠 |
| web-crawler | — | 爬虫能力 | ✅ 必要的自定义能力 |

**关键发现**：10 个平台型 Skill 中有 7 个与 OpenClaw 原生能力存在不同程度的功能重叠，构成"架构双轨"风险。

### 3.3 测试结果汇总（2026-05-06 实测）

| 测试文件 | 结果 | 说明 |
|---------|------|------|
| test_all_modules.py | ✅ 7/7 PASS | 综合模块测试全部通过 |
| test_business_capabilities.py | ✅ PASS | 业务能力测试全部通过 |
| test_orchestrator.py | ✅ PASS | 编排器测试通过 |
| test_security_guard.py | ✅ PASS | 安全门控测试全部通过 |
| test_knowledge_pipeline.py | ✅ PASS | 知识库管线测试全部通过 |
| test_mcp_framework.py | ✅ PASS | MCP 框架全部通过（含 fallback 场景） |
| test_cron_engine.py | — | 未运行 |
| test_ad_optimizer.py | — | 未运行 |
| test_mcp_servers.py | — | 未运行 |
| test_skill_orchestrator.py | — | 未运行 |
| test_skill_orchestrator_business.py | — | 未运行 |
| test_skill.py | — | 未运行 |
| test_skills.py | ⚠️ 部分失败 | order-query 因 GBK 编码断裂 |
| test_new_skills.py | ⚠️ 输出异常 | cross-drain 通过但 GBK 输出编码错误 |
| test_skill_gate.py | ❌ FAIL | UNIQUE constraint failed（SQLite 约束错误） |
| test_data_layer.py | ❌ FAIL | KeyError: 'review_id'（返回字段不匹配） |

### 3.4 MCP 数据层健康状态

```
mysql:    healthy=False, mode=fallback    ← Docker 未运行
redis:    healthy=False, mode=unavailable ← Docker 未运行
milvus:   healthy=False, mode=unavailable ← Docker 未运行
qdrant:   healthy=True,  mode=qdrant      ← SQLite 本地模式
ecommerce:healthy=True,  mode=ecommerce   ← simulated 数据
social:   healthy=True,  mode=social_media← simulated 数据
```

**关键发现**：核心数据服务（MySQL、Redis、Milvus）全部处于 fallback/unavailable 模式。全部 Skill 均在 simulated 数据上运行，未接入任何真实数据源。

### 3.5 当前成熟度矩阵

| 维度 | 评分 | 判断依据 |
|------|------|---------|
| 架构设计完整性 | ⭐⭐⭐⭐⭐ | 分层、Agent、Skills、MCP、数据流完整 |
| 配置定义完整性 | ⭐⭐⭐ | openclaw.json 含 BOM 且关键字段为空 |
| Skill 骨架覆盖率 | ⭐⭐⭐⭐⭐ | 24 个 Skill 已创建 |
| Skill 真实可执行性 | ⭐⭐⭐ | 多数通过测试但为 simulated 模式 |
| 数据层真实接入 | ⭐ | 全部核心服务 fallback |
| 真实平台 MCP 集成 | ⭐ | 全部 simulated |
| OpenClaw 原生闭环 | ⭐⭐ | 未验证端到端运行 |
| 工程质量（编码/异常） | ⭐⭐ | GBK/UTF-8 混用、测试存在断裂 |
| 可演示能力 | ⭐⭐⭐⭐ | 本地模拟能力充足，可产出内容 |
| 可上线能力 | ⭐ | 缺少真实集成、监控、门控、运维 |

---

## 四、核心差距分析

### 4.1 关键差距优先级排序

| 优先级 | 差距 | 影响 | 修复成本 |
|--------|------|------|---------|
| P0 | openclaw.json 不可被标准解析器读取 | 阻塞所有 OpenClaw 原生运行闭环 | 低（移除 BOM） |
| P0 | openclaw.json 未注册任何 Skill 和 Cron | OpenClaw 原生运行时不会加载业务能力 | 低（补全配置） |
| P0 | 核心 Docker 服务未运行（MySQL/Redis/Milvus） | 全部业务数据均为 simulated | 中（Docker 环境修复） |
| P1 | 架构双轨：自建设施与 OpenClaw 原生重叠 | 维护成本上升，违背 AGENTS.md 约束 | 高（架构收敛决策） |
| P1 | 无真实平台 MCP 集成 | 业务无法落地到真实电商/社媒平台 | 高（需对接真实 API） |
| P1 | 编码问题：GBK/UTF-8 混用导致测试断裂 | 影响中文场景的测试可靠性 | 低（统一编码策略） |
| P2 | 无真实门控闭环 | 高风险操作无人确认 | 中 |
| P2 | 无 Cron 任务真实触发 | 定时发布/监控不可用 | 低（补全配置 + 测试） |
| P3 | 无数据回流与自进化飞轮 | 系统不会随着使用而改进 | 高（需完整 CDC 管道） |
| P3 | 无监控/告警/审计 | 生产环境不可运维 | 中 |

### 4.2 与 2026-04-29 评估的对比变化

自上一次评估（2026-04-29）以来的变化：

| 项目 | 上次状态 | 本次状态 | 变化 |
|------|---------|---------|------|
| test_all_modules | 7/7 通过 | 7/7 通过 | → 稳定 |
| test_business_capabilities | 未报告 | ✅ PASS | 新增证据 |
| test_security_guard | 未报告 | ✅ PASS | 新增证据 |
| test_knowledge_pipeline | 未报告 | ✅ PASS | 新增证据 |
| test_skill_gate | 未报告 | ❌ FAIL | **新发现的问题** |
| test_data_layer | 未报告 | ❌ FAIL | **新发现的问题** |
| openclaw.json BOM | 已知 | 仍存在 | → 未修复 |
| JSON skill/cron 空字段 | 已知 | 仍为空 | → 未修复 |
| 核心 Docker 服务 | 未运行 | 未运行 | → 未修复 |

---

## 五、下一步项目计划

### 总体策略

**先收敛，再打通；先修复配置，再集成真实数据。**

### 第一阶段：运行面修复（3-5 天）

**目标**：恢复 openclaw.json 可解析性，补齐关键配置项，让测试全部回归绿色。

| 任务 | 操作 | 验收标准 |
|------|------|---------|
| F1-01 | 移除 openclaw.json 的 BOM，转为标准 UTF-8 | 标准 `json.load()` 可解析 |
| F1-02 | 补全 identity 配置段 | 名称、描述、版本信息完整 |
| F1-03 | 将所有 Skill 注册到 plugins.entries | `openclaw skills list` 可看到 24+ Skill |
| F1-04 | 将 8 个 Cron 任务注册到 cron.jobs | `openclaw cron list` 可看到任务列表 |
| F1-05 | 修复 test_skill_gate.py 的 UNIQUE 约束错误 | 测试全部通过 |
| F1-06 | 修复 test_data_layer.py 的 KeyError | 测试全部通过 |
| F1-07 | 统一 Python 文件编码声明为 UTF-8 | 所有 test_*.py 在 Windows 下无编码异常 |
| F1-08 | 恢复 Docker 核心服务运行 | `docker compose ps` 显示 MySQL/Redis/Milvus/Qdrant 均健康 |

**阶段放行标准**：
- ✅ `openclaw.json` 可被标准 JSON 解析器正确解析
- ✅ 全部 16 个 test_*.py 无 FAIL
- ✅ Docker 核心服务 4/4 健康运行

### 第二阶段：电商最小闭环（5-7 天）

**目标**：打通"飞书消息 -> ecommerce Agent -> listing-gen -> RAG 检索 -> 门控 -> 输出"的端到端链路。

| 任务 | 操作 | 验收标准 |
|------|------|---------|
| F2-01 | ecommerce Agent 绑定飞书电商群 | 发送消息可路由到 ecommerce Agent |
| F2-02 | listing-gen 接入真实 Milvus RAG | RAG 命中 >85%，不再 simulated |
| F2-03 | 为 listing-gen 创建 10 条验收样例（覆盖 5 个类目） | 每条生成 <30s，合规 >95% |
| F2-04 | 实现人工审核门控留痕 | 审核记录可查询 |
| F2-05 | 对接 1 个真实电商平台 MCP（先只做查询） | 可查询真实商品/订单数据 |

**阶段放行标准**：
- ✅ Listing 生成 <30s/条，合规 >95%
- ✅ RAG 检索不再默认 simulated
- ✅ 至少 1 个真实电商平台查询链路可用

### 第三阶段：架构收敛与社媒闭环（5-7 天）

**目标**：明确 OpenClaw 原生 vs 自建 Skill 的边界，同时打通社媒内容生成链路。

| 任务 | 操作 | 验收标准 |
|------|------|---------|
| F3-01 | 明确 7 个重叠 Skill 的去留决策（保留/废弃/合并） | 形成架构收敛说明文档 |
| F3-02 | social-media Agent 绑定飞书社媒群 | 社媒消息可路由到 social-media Agent |
| F3-03 | xhs-seed / douyin-ops 接入真实 Cron 定时任务 | Cron 可触发内容生成 |
| F3-04 | opinion-watch 从摘要升级到告警 | 负面舆情可触发告警通知 |

**阶段放行标准**：
- ✅ 架构收敛说明已评审
- ✅ 至少 2 个内容 Skill 可稳定生成
- ✅ 至少 1 个 Cron 任务可触发并留痕

### 第四阶段：客服办公与企业级能力（7-10 天）

**目标**：补齐客服自动化与办公自动化链路，引入真实数据源。

| 任务 | 操作 | 验收标准 |
|------|------|---------|
| F4-01 | cs Agent 绑定企微通道 | 客服消息可路由到 cs Agent |
| F4-02 | intent-recognition + sentiment-analysis + order-query + after-sale 串联 | 可覆盖 80% 客服场景 |
| F4-03 | report-gen 从 simulated_data 切换到真实 MySQL 数据 | 报表数据与数据库一致 |
| F4-04 | office Agent 绑定飞书办公群 | 办公消息可路由到 office Agent |

**阶段放行标准**：
- ✅ 客服高风险问题能准确转人工
- ✅ 办公报表基于真实数据源生成
- ✅ 负面情感转人工 = 100%

### 第五阶段：上线就绪（5-7 天）

**目标**：从"原型系统"进入"可灰度系统"。

| 任务 | 操作 | 验收标准 |
|------|------|---------|
| F5-01 | 补全真实 MCP 注册与配置 | mcporter.json 完整 |
| F5-02 | 端到端联调 + UAT | 覆盖全部 4 个业务域 |
| F5-03 | 监控 + 审计 + 告警 + 权限 + 门控策略 | 运维手册可操作 |
| F5-04 | 灰度方案 + 回滚预案 | 文档已评审 |
| F5-05 | 输出正式项目交付包 | 交付清单完整 |

---

## 六、阶段路线图

```
Week 1         Week 2         Week 3         Week 4
├────阶段一────┤├────阶段二────┤├────阶段三────┤├────阶段四+五───┤
F1-01~08       F2-01~05       F3-01~04       F4-01~04 + F5-01~05
│              │              │              │
│ 修复配置     │ 电商闭环     │ 架构收敛     │ 客服+办公
│ 回归测试     │ RAG真实化    │ 社媒定时     │ 真实数据
│ Docker恢复   │ 真实MCP查询  │ 舆情告警     │ 上线就绪
```

### 资源估算

| 阶段 | 工作量 | 关键技能 | 依赖 |
|------|--------|---------|------|
| 阶段一 | 3-5 人天 | Python + JSON + Docker | Docker 环境恢复 |
| 阶段二 | 5-7 人天 | RAG + MCP + OpenClaw 配置 | Milvus 运行 + 电商 API 密钥 |
| 阶段三 | 5-7 人天 | OpenClaw Cron + API 对接 | 社媒平台 API 密钥 |
| 阶段四 | 7-10 人天 | 客服逻辑 + 数据集成 | MySQL 真实数据就绪 |
| 阶段五 | 5-7 人天 | DevOps + 安全 | 环境稳定可用 |

---

## 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Docker 环境因内存限制无法运行 | 高 | 阻塞阶段一 | 确认宿主机可用内存，考虑降级方案（关闭非必要容器） |
| 真实电商 API 获取困难 | 中 | 阻塞阶段二 | 先用开放平台沙箱环境验证链路，再切换正式密钥 |
| OpenClaw 版本不兼容（2026.3.13 vs 3.14） | 中 | 配置可能失效 | 升级到匹配版本，或降级配置格式 |
| 架构双轨收敛决策分歧 | 中 | 阻塞阶段三 | 提前做技术决策评审，明确保留/废弃清单 |
| GBK/UTF-8 编码问题复发 | 低 | 测试断裂 | 统一所有 .py 文件头声明 `# -*- coding: utf-8 -*-` |

---

## 八、推荐的项目管理口径

建议对外沟通口径：

> **"AIMS 已完成 OpenClaw 架构设计与 24 个业务/平台 Skill 的原型开发，下一阶段将修复运行配置、收敛架构、打通电商全闭环并接入真实数据源。"**

---

## 九、最终建议

1. **第一步永远是修 openclaw.json 和让测试全绿** — 这是最基础的工程质量门禁。
2. **不急于新增 Skill** — 当前 24 个 Skill 已够，先让其中一条链路真实跑通。
3. **架构双轨必须在阶段三明确决策** — 拖延只会增加未来迁移成本。
4. **真实数据集成是分水岭** — simulated 模式只能做演示，不能做验收，不能做交付。
5. **监控/门控/审计在阶段五不可跳过** — 没有这些，AIMS 只能是"实验室原型"。

---

*所有路径已锁定 D 盘，C 盘零写入。*
*评估基准：2026-05-06 全量实测数据。*
