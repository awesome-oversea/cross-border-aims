---
title: 情感识别与转人工
description: 智能识别用户情感倾向，检测负面情绪并触发人工客服转接，保障高风险客户的服务质量
version: 1.0.0
tags:
  - 客服
  - 情感分析
  - 负面检测
  - 转人工
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
          sentiment:
            type: string
    context:
      type: object
      description: 附加上下文信息
      properties:
        customer_tier:
          type: string
          description: 客户等级（VIP/普通）
        order_value:
          type: number
          description: 订单金额
        previous_complaints:
          type: number
          description: 历史投诉次数
outputs:
  type: object
  properties:
    sentiment:
      type: string
      description: 情感分类
      enum:
        - positive      # 正面积极
        - neutral       # 中性平淡
        - negative      # 负面不满
        - angry         # 愤怒激动
        - anxious       # 焦虑担忧
        - disappointed  # 失望沮丧
    sentiment_score:
      type: number
      description: 情感得分 -1到1（负值表示负面）
    sentiment_label:
      type: string
      description: 情感中文标签
    emotion_keywords:
      type: array
      description: 识别到的情感关键词
      items:
        type: string
    intensity:
      type: string
      description: 情感强度
      enum:
        - low
        - medium
        - high
        - critical
    require_human:
      type: boolean
      description: 是否需要转人工
    transfer_reason:
      type: string
      description: 转人工原因
    priority_level:
      type: string
      description: 处理优先级
      enum:
        - low
        - normal
        - high
        - urgent
        - critical
    suggested_response:
      type: string
      description: 建议的回复策略
gate: medium
---

# 情感识别与转人工 Skill

## 简介
本技能通过自然语言处理技术分析用户消息的情感倾向，识别负面情绪和敏感表达。当检测到高风险情感信号时，自动触发人工客服转接机制，确保客户满意度。

## 情感分类体系

| 情感类型 | 说明 | 典型关键词 |
|----------|------|-----------|
| positive | 正面积极 | 感谢、满意、很好、太棒了、喜欢 |
| neutral | 中性平淡 | 好的、了解、知道了、嗯 |
| negative | 负面不满 | 不满意、失望、不好、差、太慢了 |
| angry | 愤怒激动 | 生气、恼火、发火、太过分了、投诉 |
| anxious | 焦虑担忧 | 担心、着急、急死了、什么时候能到 |
| disappointed | 失望沮丧 | 失望、绝望、不抱希望了、算了 |

## 情感强度定义

| 强度 | 说明 | 判断标准 |
|------|------|----------|
| low | 轻度负面 | 单一负面词，置信度低 |
| medium | 中度负面 | 多个负面词，情感得分-0.3到-0.6 |
| high | 高度负面 | 强烈负面词组合，情感得分-0.6到-0.8 |
| critical | 极度负面 | 极端词汇+投诉威胁，情感得分<-0.8 |

## 转人工触发条件

满足以下任一条件时，触发转人工：
1. **情感强度 = critical**（极度负面）
2. **连续3轮对话情感得分 < -0.5**
3. **检测到投诉/举报意图**
4. **VIP客户 + 情感得分 < -0.3**
5. **订单金额 > 5000元 + 情感得分 < -0.4**

## 优先级映射

- **critical** → 优先级：critical（立即转人工）
- **angry + high** → 优先级：urgent（紧急转人工）
- **disappointed + high** → 优先级：high（优先转人工）
- **negative + medium** → 优先级：normal（可自动处理）
- **neutral/positive** → 优先级：low（正常流程）

## 使用场景

适用于企业微信、飞书等渠道的客服系统，实时监控用户情感状态，保障服务质量。
