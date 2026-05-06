# Agent编排引擎

## 概述
Agent编排引擎是AIMS系统的核心，实现感知→决策→执行→记忆四模块Pipeline，负责消息的完整处理流程。

业务域与工具编排优先对齐项目根目录 `agents/*.json` 中声明的能力和工具映射；本 Skill 在运行时会据此补齐实际路由。
当请求明显属于多步骤业务闭环时，本 Skill 会优先调用 `skill-orchestrator` 执行工作流，而不是仅做单技能串联。

## 四模块架构

### 1. 感知模块 (Perception)
- 意图识别：基于关键词匹配识别用户意图
- 情感分析：检测用户情绪，判断是否需要转人工
- 实体提取：提取订单号、运单号、手机号、产品名等关键实体
- 知识检索：通过RAG检索相关知识，增强上下文理解

### 2. 决策模块 (Decision)
- 置信度评估：综合意图、情感、RAG、上下文四维计算置信度
- 动作决策：auto(自动执行) / confirm(确认后执行) / confirm_with_human(确认+人工) / human(转人工)
- 技能规划：根据意图匹配技能，支持多技能串联/并联执行
- Agent路由：将请求路由到对应的Agent（ecommerce/social-media/cs/office）

### 3. 执行模块 (Execution)
- 技能调度：调用匹配的技能，传递上下文和实体信息
- 顺序执行：技能按依赖关系依次执行，前序结果传递给后续技能
- 并行执行：无依赖的技能可并行执行，提升响应速度
- 结果聚合：收集所有技能执行结果，提取主结果

### 4. 记忆模块 (Memory)
- 会话持久化：将对话轮次、意图、情感、技能执行记录存入SQLite
- 上下文更新：维护对话上下文（实体、意图、情感、技能历史）
- 洞察提取：从执行结果中提取关键洞察（置信度、合规分数等）
- 历史查询：支持查询会话历史和Pipeline统计

## 支持的意图与技能映射

| 意图 | 技能 | Agent |
|------|------|-------|
| listing_generation/optimization | listing-gen | ecommerce |
| ad_optimization/budget/bidding | ad-optimizer | ecommerce |
| review_analysis/reply/alert | review-mgr | ecommerce |
| xhs_content/calendar/trend | xhs-seed | social-media |
| douyin_script/trend | douyin-ops | social-media |
| video_channel_script/distribution | video-channel | social-media |
| private_domain_drain/cross_platform_drain | cross-drain | social-media |
| presales | intent-recognition | cs |
| order_query/status | order-query | cs |
| logistics/tracking | logistics-track | cs |
| aftersale/refund/exchange/complaint | after-sale | cs |
| sentiment_analysis/emotion_handover | sentiment-analysis | cs |
| material_generation | material-gen | ecommerce |
| report_generation | report-gen | office |
| excel_visualization/data_visualization | excel-viz | office |
| email_management/reply/classification | email-mgr | office |
| document_automation/meeting_minutes | doc-auto | office |
| opinion_monitor | opinion-watch | social-media |

## API接口

### process - 处理消息
```json
{
  "action": "process",
  "message": "帮我查一下订单ORD20240101001",
  "context": {
    "user_id": "user123",
    "conversation_id": "conv-20240101-abc12345",
    "channel": "feishu",
    "customer_tier": "VIP"
  }
}
```

### get_conversation - 获取会话历史
```json
{
  "action": "get_conversation",
  "conversation_id": "conv-20240101-abc12345"
}
```

### get_stats - 获取Pipeline统计
```json
{
  "action": "get_stats",
  "hours": 24
}
```

### get_skill_registry - 获取技能注册表
```json
{
  "action": "get_skill_registry"
}
```

## 置信度门控

| 置信度 | 动作 | 说明 |
|--------|------|------|
| ≥0.85 | auto | 自动执行，无需确认 |
| 0.6-0.85 | confirm | 执行但需用户确认 |
| 0.4-0.6 | confirm_with_human | 执行但需人工确认 |
| <0.4 | human | 直接转人工处理 |

## 多技能编排策略

- **订单查询 + 物流追踪**：识别到运单号时自动追加logistics-track
- **售后 + 订单查询**：售后处理时自动查询关联订单
- **投诉/退款/售后 + 情感分析**：客服高风险场景追加 sentiment-analysis
- **经营报表 + 可视化**：报表生成后可继续调用 excel-viz 产出图表
- **办公闭环请求**：周报/图表/邮件/文档同时出现时升级为 `office_productivity_suite`
- **社媒闭环请求**：小红书/抖音/视频号/导流/舆情组合出现时升级为 `social_media_content_flywheel`
- **客服闭环请求**：订单+物流+售后/退款/投诉组合出现时升级为 `customer_service_resolution`
- **电商闭环请求**：Listing/素材/广告/经营分析组合出现时升级为 `ecommerce_operation_hub`
