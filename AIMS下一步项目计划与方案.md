# AIMS下一步项目计划与方案

生成日期：2026-04-29

## 一、分析依据

本方案基于以下材料与仓库现状综合判断：

- `AI营销系统项目方案(OpenClaw版)V2.md`
- `AGENTS.md`
- `2026041501任务分解清单.md`
- `2026041501任务分解清单-验收标准.md`
- 当前仓库代码、配置、Skills、脚本、fixtures、测试与本地校验结果

本次分析结论不是只看文档，而是结合了实际校验结果：

- `scripts/p0/Invoke-AimsSkillCheck.ps1`：通过，说明核心 Skill 文档结构较完整。
- `scripts/p1/Invoke-AimsSkillScenarioCheck.ps1`：部分失败，说明业务场景覆盖不均衡。
- `scripts/p1/Invoke-AimsKnowledgeCollectionCheck.ps1`：通过，说明 RAG 离线知识集合产物已形成。
- `scripts/p0/Invoke-AimsPreflight.ps1 -SkipCompose`：失败，说明运行面仍有阻塞项。
- `test_skills.py`：13/13 通过，说明一批本地 Skill 已具备可执行原型能力。
- `test_new_skills.py`：`cross-drain`可运行，`rag-retrieval`因 Milvus 不可用回退为 simulated。

## 二、AIMS当前阶段判断

### 总体结论

AIMS 当前不是“空架子”，但也还不是“可上线 OpenClaw 营销中台”。

更准确的判断是：

**AIMS 已经具备 P0 基础设施 + P1/P2 业务原型 + 一批本地模拟底座能力，但尚未完成 OpenClaw 原生闭环打通。**

### 当前成熟度判断

| 维度 | 现状判断 | 结论 |
|------|------|------|
| 架构设计完整度 | 高 | 文档、分层、Agent、任务分解、验收标准都比较完整 |
| 本地代码原型能力 | 中高 | 业务 Skill、平台 Skill、脚本、知识库处理链都已有代码 |
| OpenClaw 原生运行面 | 中低 | 配置内容完整，但主配置当前不可直接作为稳定运行入口 |
| 真业务集成能力 | 低 | 大量能力仍依赖 simulated / fallback / SQLite |
| 可演示能力 | 中高 | 本地可做 Demo、生成内容、跑验证 |
| 可上线能力 | 低 | 真实通道、真实 MCP、真实数据、真实门控尚未闭环 |

## 三、AIMS现有代码能力分析

### 1. 已具备的代码能力

#### 1.1 平台与工程底座

- 已具备 `docker-compose.yml`、`.env.example`、`init.sql`、`openclaw.json`、`mcporter.json`、`SOUL.md`、`AGENTS.md` 等核心资产。
- 已具备五个 Agent 独立配置与五套 workspace。
- 已具备 P0/P1 脚本体系，覆盖环境初始化、预检、健康检查、Skill 校验、知识集合导出与检查。
- 已具备多环境落地痕迹：`docker/`、`helm/`、`k8s/`、`scripts/`、`fixtures/`、`data/knowledge`。

#### 1.2 业务 Skill 原型

已存在并可本地执行的业务 Skill 覆盖了四大业务域：

- 电商：`listing-gen`、`ad-optimizer`、`review-mgr`、`material-gen`
- 社媒：`xhs-seed`、`douyin-ops`、`video-channel`、`opinion-watch`、`cross-drain`
- 客服：`order-query`、`logistics-track`、`after-sale`、`intent-recognition`、`sentiment-analysis`、`confidence-gate`
- 办公：`report-gen`、`excel-viz`、`email-mgr`、`doc-auto`

#### 1.3 平台型 Skill 底座

仓库中已经出现一批平台型 Skill：

- `agent-orchestrator`
- `skill-orchestrator`
- `mcp-framework`
- `knowledge-pipeline`
- `cron-engine`
- `data-layer`
- `security-guard`
- `skill-gate`
- `web-crawler`
- `data-flywheel`

这说明项目已经从“只做业务 Skill”向“自建平台底座”演进，代码能力并不弱。

#### 1.4 测试与知识库工程能力

- Skill 结构检查已通过，说明自定义 Skill 规范化程度较好。
- 场景夹具、知识路由、知识集合计划、知识检索校验脚本已存在。
- 知识集合检查结果显示：已形成 6 个集合、480 条记录，说明 RAG 离线准备工作已做出成果。

### 2. 当前代码能力的主要问题

#### 2.1 运行面第一阻塞项：`openclaw.json` 当前不可稳定作为运行主配置

当前主配置存在两个关键问题：

- `openclaw.json` 当前不是合法 JSON，预检脚本无法解析。
- 配置中存在编码损坏文本，尤其在 `cron.jobs` 部分已经影响语法。

这意味着：

- 文档定义的 OpenClaw 原生运行入口还没有真正“稳定化”。
- 现有代码能力更多停留在“组件可执行”，而不是“整机可稳定启动”。

#### 2.2 架构开始出现“双轨化”

按照 `AGENTS.md` 约束，AIMS 应优先使用 OpenClaw 原生能力：

- Agent 编排由 OpenClaw Agent 层承担
- 定时任务由 OpenClaw Cron 承担
- 数据访问经 MCP 层承担

但当前代码中又额外实现了：

- `agent-orchestrator`
- `cron-engine`
- `data-layer`
- `security-guard`
- `skill-gate`

这会带来明显风险：

- 文档架构是一套
- 代码运行逻辑可能变成另一套
- 后续维护成本和认知成本都会上升

#### 2.3 大量能力仍停留在 simulated / fallback 层

当前代码大量具备“可跑原型”，但不是“真实生产链路”：

- `report-gen` 使用 `simulated_data`
- `rag-retrieval` 支持 simulated mode
- `mcp-framework` 在 MySQL / Redis / Milvus / Qdrant 不可用时大量 fallback
- 电商 / 社媒 / 多模态 / 爬虫接口中存在大量 simulated 返回
- `web-crawler` 当前是模拟抓取结果

因此当前代码更适合：

- 本地演示
- 结构验证
- Prompt / JSON 输出调试

而不适合直接作为生产业务闭环。

#### 2.4 测试证据仍偏“结构验证”，不足以支撑阶段放行

当前测试优势在于：

- 结构检查强
- 场景夹具齐
- 本地 smoke test 可跑

当前测试短板在于：

- 缺少真实通道联调证据
- 缺少真实 MCP 平台调用证据
- 缺少真实向量库在线命中证据
- 缺少真实门控、人工审核、数据回流证据

未覆盖 scenario 的 Skill 也较多，包括但不限于：

- `confidence-gate`
- `excel-viz`
- `intent-recognition`
- `multimodal-理解`
- `rag-retrieval`
- `report-gen`
- `sentiment-analysis`
- `smart-recommend`
- `system-monitor`
- `user-profile`

## 四、AIMS现有业务能力分析

### 1. 电商业务能力

#### 已具备

- Listing 生成与合规检查原型
- 广告指标分析与调价建议原型
- 评论情感分析与回复建议原型
- 素材 brief / 文案生成原型
- 经营报表生成原型

#### 尚未真正打通

- 真实淘宝 / 京东 / 拼多多 / Amazon 数据读取
- 真实广告调价执行
- 真实商品发布与编辑
- 真实订单 / 评价 / ERP 数据回流

#### 判断

电商域已经是当前 AIMS 最接近“最小闭环”的业务域，应作为下一阶段主攻方向。

### 2. 社媒业务能力

#### 已具备

- 小红书种草文案生成
- 抖音脚本生成
- 视频号内容生成
- 舆情摘要与告警原型
- 跨平台导流话术与策略原型

#### 尚未真正打通

- 真实账号内容发布
- 真实平台数据回收
- 真实评论监控
- 真实爬虫与反反爬能力

#### 判断

社媒域内容生成能力较强，但平台执行能力明显弱于内容生产能力。

### 3. 客服业务能力

#### 已具备

- 意图识别
- 情感识别
- 订单查询原型
- 物流查询原型
- 售后分流与门控原型

#### 尚未真正打通

- 真实 OMS / WMS / ERP 订单数据
- 真实转人工队列
- 真实 SLA 与消息回流
- 真实客服知识库联动

#### 判断

客服域已经有较完整的“识别-决策-处理”雏形，但仍是本地模拟客服，而不是企业微信可用客服系统。

### 4. 办公业务能力

#### 已具备

- 周报 / 日报 / 月报生成
- Excel 图表配置生成
- 邮件分类与回信草拟
- 文档整理与摘要
- 会议纪要类文档原型

#### 尚未真正打通

- 飞书文档、邮箱、审批流
- 真实经营数据源
- 自动分发与留痕

#### 判断

办公域适合最早做“内部提效 Demo”，但不适合当前阶段作为首个对外业务闭环。

## 五、关键差距与项目判断

### 当前最关键的五个差距

1. **运行配置差距**
   `openclaw.json` 当前不可稳定解析，阻塞 OpenClaw 原生运行闭环。

2. **原生架构差距**
   OpenClaw 原生能力与自建平台 Skill 存在重叠，架构开始发散。

3. **真实集成差距**
   业务 Skill 多数能“出结果”，但未接入真实平台 API / 真实数据库 / 真实向量库。

4. **验收证据差距**
   目前主要是结构性通过，还不能支撑 P1/P2 阶段验收放行。

5. **工程质量差距**
   编码损坏、配置不一致、脚本假设不一致、SQLite 运行文件混入仓库等问题需要清理。

### 项目阶段最终判断

如果严格对照《任务分解清单》和《验收标准》，AIMS 当前更接近：

**P0 已完成大部分准备，P1/P2 已完成原型开发，但尚未达到 P1 正式放行标准。**

## 六、下一步总体策略

### 核心策略

下一步不建议继续横向扩张新 Skill 或新平台能力，而应改为：

**先收敛，再打通；先原生闭环，再扩展增强。**

### 三条总原则

1. **OpenClaw 原生优先**
   先让 Gateway / Bindings / Agents / Skills / MCP / Cron 跑成一套，再决定哪些自建底座要保留。

2. **电商闭环优先**
   先打通一条“飞书电商群 -> ecommerce Agent -> listing-gen -> RAG -> 门控 -> 输出”的最小闭环。

3. **模拟能力降级为验证层**
   自建 `agent-orchestrator`、`cron-engine`、`data-layer`、`web-crawler` 等优先定位为本地模拟 / 回归验证层，而不是先替代 OpenClaw 主运行链路。

## 七、下一步项目计划

### 第一阶段：运行面修复与架构收敛（1-3天）

目标：让 AIMS 重新回到“可启动、可预检、可解释”的状态。

重点任务：

- 修复 `openclaw.json` 的 JSON 语法错误与编码问题
- 将 `sandbox.mode` 调整到符合 `AGENTS.md` 约束的模式
- 对齐 `openclaw.json`、`Invoke-AimsPreflight.ps1`、`.env.example` 的模型策略与启动假设
- 明确哪些平台型 Skill 是“实验层”，哪些是“正式运行层”
- 清理不应入库的运行期 `.db` / 临时产物 / 编码异常文件

阶段输出：

- 可解析、可预检的 `openclaw.json`
- 可执行的 P0 预检报告
- AIMS 运行架构收敛说明

放行标准：

- `Invoke-AimsPreflight.ps1 -SkipCompose` 通过
- `openclaw.json` 可被脚本和运行时正确解析
- 主配置与 AGENTS 约束不再冲突

### 第二阶段：电商最小闭环打通（3-7天）

目标：完成第一个真正可演示、可验证、可迭代的业务闭环。

优先闭环：

飞书电商群 -> `main/ecommerce` 路由 -> `listing-gen` -> `rag-retrieval` -> `confidence-gate` / humanizer -> 人工审核输出

重点任务：

- 打通 `ecommerce` Agent 与核心 Skill 调用顺序
- 将 `rag-retrieval` 从 simulated 模式推进到真实 Milvus / Qdrant 检索
- 为 `listing-gen` 增加 10 条真实验收样例
- 增加人工审核队列与门控留痕
- 至少接通 1 个真实电商平台 MCP 能力，哪怕只做到查询，不先做写操作

阶段输出：

- 电商闭环演示用例
- Listing 样例集
- P1 阶段证据包

放行标准：

- Listing 生成可稳定跑通
- 合规校验链可稳定输出
- RAG 检索不再默认 simulated
- 至少 1 个真实平台查询链路可用

### 第三阶段：社媒闭环与 Cron 接入（5-10天）

目标：把“内容生成”推进到“可计划执行”。

重点任务：

- 打通 `social-media` Agent 与 `xhs-seed` / `douyin-ops` / `video-channel`
- 将 `opinion-watch` 从摘要能力推进到告警能力
- 优先接通 1 个真实社媒平台 MCP 或发布接口
- 先做“生成 + 审核 + 定时触发 + 人工确认发布”，不急于全自动直发

阶段输出：

- 社媒内容日历
- 定时任务配置
- 社媒预发布闭环

放行标准：

- 至少 2 个内容 Skill 可稳定生成
- 至少 1 个 Cron 任务可触发并留痕
- 舆情监控结果可落日志或告警输出

### 第四阶段：客服与办公联动（7-12天）

目标：补齐内部运营协同链路。

重点任务：

- 客服侧打通 `intent-recognition` + `sentiment-analysis` + `order-query` + `after-sale`
- 办公侧打通 `report-gen` + `excel-viz` + `email-mgr` + `doc-auto`
- 引入真实经营数据，替换 `report-gen` 的 simulated_data
- 负面情绪与高风险售后必须具备明确转人工出口

阶段输出：

- 客服标准处理链
- 周报 / 日报 / 邮件草拟样例
- 人工接管规则

放行标准：

- 客服高风险问题能准确转人工
- 办公报表可基于真实数据源生成
- 办公输出可被飞书 / 邮件场景复用

### 第五阶段：上线准备与验收（5-7天）

目标：从“原型系统”进入“可灰度系统”。

重点任务：

- 补齐真实 MCP 注册与配置
- 完成端到端联调、UAT、灰度切换、回滚预案
- 补齐监控、审计、日志、告警、权限、门控策略
- 输出正式项目交付包

阶段输出：

- 全链路验收报告
- 上线清单
- 回滚预案
- 运维交接材料

## 八、下一步优先级清单

### P0：必须先做

- 修复 `openclaw.json`
- 统一 UTF-8 编码
- 对齐预检脚本与当前模型策略
- 明确平台型 Skill 的保留边界
- 打通一个真实电商闭环

### P1：紧随其后

- 真实 Milvus / Qdrant 在线接入
- 真实电商 / 社媒 MCP 至少各 1 个
- 人工审核 / 转人工机制留痕
- Cron 任务真实触发与执行留痕

### P2：可在闭环后扩展

- 自进化飞轮
- ERP 深度集成
- 多通道大规模接入
- 爬虫与反反爬增强
- 国产化部署完善

## 九、推荐的项目管理口径

建议对外不要再把当前 AIMS 表述为“即将上线的全功能营销中台”，而应表述为：

**“AIMS 已完成 OpenClaw 架构设计与多业务原型开发，下一阶段进入原生闭环打通和真实集成阶段。”**

这个表述更准确，也更利于资源、周期和验收预期管理。

## 十、最终建议

下一步最正确的路线不是继续加功能，而是：

**修配置、收架构、打一条真闭环、补真实集成、再做阶段放量。**

对 AIMS 来说，当前最有价值的不是“再新增多少 Skill”，而是尽快把电商闭环做成第一个可验证、可汇报、可复用的样板链路。

---

所有路径已锁定 D 盘，C 盘零写入。
