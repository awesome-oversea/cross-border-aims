---
name: web-crawler
version: 1.0.0
description: 电商/社媒数据爬虫 — 6大平台数据采集 + 反反爬策略
author: AIMS
tags: [crawler, scraping, data-collection]
---

# 电商/社媒数据爬虫

## 概述
实现6大平台数据采集能力，包括商品信息、评论数据、社媒内容、竞品分析等，配合反反爬策略确保稳定采集。

## 支持平台
1. **淘宝/天猫**：商品信息、评论、销量数据
2. **京东**：商品详情、价格走势、评论
3. **拼多多**：商品搜索、评论、活动数据
4. **小红书**：笔记内容、评论、热门话题
5. **抖音**：视频数据、评论、热门趋势
6. **1688**：供应商信息、批发价格、MOQ

## 反反爬策略
- 请求频率控制：随机延迟 2-8s
- User-Agent 轮换：维护 50+ UA 池
- Cookie 管理：自动登录和刷新
- IP 代理池：支持 HTTP/SOCKS5 代理
- 验证码处理：OCR 识别 + 人工辅助
- 数据缓存：避免重复采集

## API接口

### crawl - 执行爬取任务
```json
{"action": "crawl", "platform": "taobao", "target_type": "product", "target_id": "prod_001", "options": {"include_reviews": true, "max_reviews": 100}}
```

### crawl_batch - 批量爬取
```json
{"action": "crawl_batch", "platform": "jd", "target_type": "product", "target_ids": ["id1", "id2"], "options": {"delay_range": [3, 8]}}
```

### crawl_search - 搜索爬取
```json
{"action": "crawl_search", "platform": "xhs", "keyword": "护肤品推荐", "max_results": 50}
```

### get_task_status - 查询任务状态
```json
{"action": "get_task_status", "task_id": "task-xxx"}
```

### list_tasks - 列出爬取任务
```json
{"action": "list_tasks", "status": "completed"}
```

### get_proxy_status - 查询代理池状态
```json
{"action": "get_proxy_status"}
```
