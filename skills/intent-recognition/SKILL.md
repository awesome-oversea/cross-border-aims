---
title: 客服意图识别
description: 智能识别客服场景中用户的咨询意图，包括售前咨询、订单查询、物流跟踪、售后处理、投诉建议等类型
version: 1.0.0
tags:
  - 客服
  - 意图识别
  - NLP
inputs:
  type: object
  properties:
    user_message:
      type: string
      description: 用户的消息文本
    history:
      type: array
      description: 对话历史记录
      items:
        type: object
        properties:
          role:
            type: string
          content:
            type: string
  required:
    - user_message

outputs:
  type: object
  properties:
    intent:
      type: string
      description: 识别到的意图类型
      enum:
        - presales        # 售前咨询
        - order_query     # 订单查询
        - logistics       # 物流咨询
        - aftersale       # 售后处理
        - complaint       # 投诉建议
        - refund          # 退款咨询
        - exchange        # 换货咨询
        - tracking        # 物流跟踪
        - general         # 一般咨询
        - unclear         # 无法识别
    intent_label:
      type: string
      description: 意图的中文标签
    confidence:
      type: number
      description: 置信度 0-1
    keywords:
      type: array
      description: 识别到的关键词
      items:
        type: string
    entities:
      type: object
      description: 识别的实体信息
      properties:
        order_id:
          type: string
          description: 订单号
        tracking_number:
          type: string
          description: 运单号
        product_name:
          type: string
          description: 商品名称
        phone:
          type: string
          description: 电话号码
    suggestions:
      type: array
      description: 建议的下一步操作
      items:
        type: string
    response_template:
      type: string
      description: 建议的回复模板
gate: low
---

# 客服意图识别 Skill

## 简介
本技能用于智能识别客服场景中用户的咨询意图，帮助客服系统快速准确地理解用户需求，并路由到对应的处理流程。

## 意图类型定义

| 意图 | 说明 | 关键词示例 |
|------|------|-----------|
| presales | 售前咨询 | 价格、规格、功能、发货、使用方法 |
| order_query | 订单查询 | 订单、什么时候到、发货没 |
| logistics | 物流咨询 | 物流、快递、到哪了、派送 |
| aftersale | 售后处理 | 维修、退货、换货、质保 |
| complaint | 投诉建议 | 投诉、差评、举报、反馈问题 |
| refund | 退款咨询 | 退款、钱什么时候退、退款进度 |
| exchange | 换货咨询 | 换货、换颜色、换型号 |
| tracking | 物流跟踪 | 查物流、看快递、运单号 |
| general | 一般咨询 | 一般问题、信息咨询 |
| unclear | 无法识别 | 模糊表述 |

## 识别流程

1. **关键词匹配**：基于预设关键词快速匹配
2. **上下文分析**：结合对话历史综合判断
3. **实体提取**：识别订单号、运单号、商品名称等
4. **置信度计算**：基于匹配程度计算置信度
5. **建议生成**：生成下一步操作建议

## 输出说明

- **confidence >= 0.8**：高置信度，直接执行对应流程
- **0.5 <= confidence < 0.8**：中置信度，回复前确认用户意图
- **confidence < 0.5**：低置信度，转人工处理

## 使用场景

适用于企业微信、飞书等渠道的客服系统，自动识别用户咨询类型并路由到对应技能处理。
