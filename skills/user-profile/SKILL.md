---
title: 用户画像记录
description: 记录和维护客户画像，包括基本信息、行为特征、交互历史、偏好标签等，用于个性化服务和精准营销
version: 1.0.0
tags:
  - 客服
  - 用户画像
  - 个性化
  - 数据记录
inputs:
  type: object
  properties:
    user_id:
      type: string
      description: 用户ID
    action:
      type: string
      description: 操作类型
      enum:
        - get         # 获取画像
        - create      # 创建画像
        - update      # 更新画像
        - add_tag     # 添加标签
        - remove_tag  # 移除标签
        - record_interaction  # 记录交互
    data:
      type: object
      description: 操作数据
      properties:
        name: { type: string }
        phone: { type: string }
        tier: { type: string }
        tags: { type: array }
        preferences: { type: object }
        interaction_summary: { type: string }
outputs:
  type: object
  properties:
    success:
      type: boolean
      description: 操作是否成功
    user_profile:
      type: object
      description: 用户画像数据
    message:
      type: string
      description: 操作说明
gate: low
---

# 用户画像记录 Skill

## 简介
本技能用于记录和维护客户画像，支持个性化服务和精准营销。画像数据包括基本信息、购买行为、交互历史、偏好标签等维度。

## 操作类型

| 操作 | 说明 | 必需字段 |
|------|------|---------|
| get | 获取用户画像 | user_id |
| create | 创建新画像 | user_id, name |
| update | 更新画像信息 | user_id, data |
| add_tag | 添加用户标签 | user_id, tag |
| remove_tag | 移除用户标签 | user_id, tag |
| record_interaction | 记录交互 | user_id, interaction |

## 画像数据结构

```json
{
  "user_id": "USER001",
  "name": "张三",
  "phone": "13800138000",
  "tier": "VIP",
  "tags": ["高价值", "数码爱好者", "复购用户"],
  "preferences": {
    "categories": ["智能手表", "蓝牙耳机"],
    "price_range": "1000-3000",
    "brands": ["华为", "苹果"]
  },
  "interaction_count": 15,
  "last_interaction": "2026-04-28 10:30:00",
  "satisfaction_history": [4, 5, 4, 5, 5],
  "complaint_count": 0,
  "total_orders": 8,
  "total_spend": 15680,
  "avg_order_value": 1960,
  "created_at": "2025-01-15 14:20:00",
  "updated_at": "2026-04-28 10:30:00"
}
```

## 标签分类

| 标签类型 | 示例标签 |
|----------|---------|
| 价值分层 | 高价值, 中价值, 低价值, VIP |
| 品类偏好 | 数码爱好者, 美妆达人, 母婴用户 |
| 行为特征 | 复购用户, 沉默用户, 活跃用户 |
| 风险标识 | 投诉风险, 流失风险, 羊毛党 |

## 使用场景

适用于客服系统、销售CRM、精准营销等场景，支持个性化推荐和服务。
