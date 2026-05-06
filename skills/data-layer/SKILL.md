# 数据层

## 概述
8张核心数据表 + ETL回流管道 + 数据质量检查，覆盖会话/用户/商品/订单/评论/内容/定时任务/知识库全业务数据。

## 8张核心数据表

| 表名 | 说明 | 核心字段 |
|------|------|----------|
| sessions | 会话记录 | session_id, channel, user_id, agent_name, message, reply, intent |
| users | 用户信息 | user_id, channel, external_id, name, role, preferences |
| products | 商品信息 | product_id, platform, title, price, category, bsr_rank |
| orders | 订单数据 | order_id, platform, order_no, amount, status, tracking_number |
| reviews | 评论数据 | review_id, platform, product_id, content, sentiment, rating |
| contents | 内容记录 | content_id, type, platform, title, status, views, likes |
| cron_jobs | 定时任务 | job_id, name, cron_expr, agent, skill, enabled |
| knowledge_docs | 知识库文档 | doc_id, category, title, content, tags, vector_id |

## ETL回流管道

| 管道名 | 说明 | 调度 |
|--------|------|------|
| order_sync | 订单数据同步 | 每小时 |
| product_sync | 商品数据同步 | 每日 |
| review_sync | 评论数据同步 | 每6小时 |
| content_analytics | 内容数据聚合 | 每小时 |
| session_analytics | 会话数据聚合 | 实时 |

## API接口

### stats - 数据表统计
```json
{"action": "stats"}
```

### query - 查询数据
```json
{"action": "query", "table": "orders", "conditions": {"platform": "taobao"}, "limit": 10}
```

### insert_order - 插入订单
```json
{"action": "insert_order", "data": {"platform": "taobao", "order_no": "TB20260429001", "amount": 199.9}}
```

### run_etl - 执行ETL管道
```json
{"action": "run_etl", "pipeline": "order_sync"}
```

### quality_check - 数据质量检查
```json
{"action": "quality_check"}
```
