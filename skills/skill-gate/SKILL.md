---
name: skill-gate
version: 1.0.0
description: Skill门控机制 — 低风险自动执行/中风险执行并通知/高风险人工确认
author: AIMS
tags: [gate, security, control]
---

# Skill 门控机制

## 概述
实现 Skill 操作的三级门控策略，确保高风险操作必须人工确认，中风险操作执行并通知，低风险操作自动执行。

## 门控级别定义

| 级别 | 置信度 | 决策 | 通知 | 示例 |
|------|--------|------|------|------|
| low | ≥90% | 自动执行 | 无 | Listing生成、数据查询、日报生成 |
| medium | 60%-90% | 执行并通知 | 运营人员 | 广告调价、内容发布、差评回复 |
| high | <60% | 人工确认 | 必须确认后执行 | 退款、删除商品、大额调价 |

## 操作门控注册表

### 电商运营（ecommerce Agent）
- listing_gen → low
- listing_optimize → low
- data_query → low
- report_gen → low
- ad_monitor → low
- ad_adjust_price → medium
- ad_adjust_price_large → high
- review_reply → medium
- material_publish → medium
- product_delete → high
- refund → high
- price_change_over_20pct → high

### 社媒营销（social-media Agent）
- content_gen → low
- compliance_check → low
- social_data_query → low
- content_publish → medium
- cron_publish → medium
- drain_script → medium
- sensitive_topic → high
- negative_opinion → high

### 客服自动化（cs Agent）
- faq_reply → low
- order_query → low
- product_recommend → low
- after_sale_consult → medium
- resend_process → medium
- refund_process → high
- negative_sentiment → high
- low_confidence → high

### 办公自动化（office Agent）
- report_gen → low
- excel_viz → low
- doc_process → low
- meeting_minutes → low
- email_draft → medium
- email_send → high
- sensitive_doc → high

## API接口

### evaluate - 评估操作门控级别
```json
{"action": "evaluate", "operation": "refund_process", "agent": "cs", "confidence": 0.55, "context": {"order_value": 500}}
```

### register - 注册新操作门控规则
```json
{"action": "register", "operation": "new_operation", "agent": "ecommerce", "default_level": "medium", "conditions": [{"field": "amount", "operator": ">", "value": 1000, "level": "high"}]}
```

### check - 检查操作是否允许执行
```json
{"action": "check", "operation": "ad_adjust_price", "agent": "ecommerce", "params": {"price_change_pct": 25}}
```

### approve - 人工确认批准
```json
{"action": "approve", "gate_id": "gate-xxx", "approved_by": "admin", "comment": "确认执行"}
```

### reject - 人工确认拒绝
```json
{"action": "reject", "gate_id": "gate-xxx", "rejected_by": "admin", "comment": "风险过高"}
```

### list_pending - 列出待确认操作
```json
{"action": "list_pending", "agent": "ecommerce"}
```

### get_stats - 获取门控统计
```json
{"action": "get_stats"}
```
