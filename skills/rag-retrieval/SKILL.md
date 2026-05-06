---
name: rag-retrieval
title: 电商RAG知识库检索
version: 1.0.0
description: 电商领域RAG知识库检索服务，支持商品知识、广告优化、平台规则等内容的向量检索
author: AIMS Team
category: knowledge
tags: [rag, retrieval, knowledge-base, ecommerce]
enabled: true
runtime: python
main: main.py
gateway:
  enabled: true
  allowedChannels:
    - feishu
    - wework
  rateLimit: 100/min
safety:
  level: low
  audit: false
  requiresApproval: false
---

## 功能说明

本技能提供电商领域知识库的向量检索能力，支持：
- 商品知识检索
- 广告优化建议检索
- 平台规则检索
- 竞品分析数据检索
- 行业报告检索

## 输入参数

### 检索操作 (retrieve)
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 "retrieve" |
| query | string | 是 | 检索查询词 |
| top_k | int | 否 | 返回结果数量，默认5 |
| category | string | 否 | 分类过滤 |

### 导入操作 (import)
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 "import" |
| document.id | string | 是 | 文档ID |
| document.title | string | 是 | 文档标题 |
| document.content | string | 是 | 文档内容 |
| document.category | string | 否 | 文档分类 |
| document.source | string | 否 | 文档来源 |

### 统计操作 (stats)
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 固定为 "stats" |

## 输出格式

### 检索结果
```json
{
  "success": true,
  "query": "查询词",
  "results": [
    {
      "score": 0.85,
      "content": "知识内容片段...",
      "title": "文档标题",
      "category": "分类",
      "source": "来源",
      "chunk_index": 0,
      "total_chunks": 5
    }
  ],
  "count": 5
}
```

## 门控规则

- 低风险操作，自动执行
- 支持飞书、企微渠道访问
- 限流：100次/分钟

## 依赖

- pymilvus >= 2.4.0
- sentence-transformers >= 2.2.0

## 使用示例

```json
{
  "action": "retrieve",
  "query": "亚马逊广告ACOS优化策略",
  "top_k": 3,
  "category": "ad-optimizer"
}
```