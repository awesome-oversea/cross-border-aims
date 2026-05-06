---
title: 客服置信度门控
description: 综合评估意图识别置信度、情感分析结果、知识库检索匹配度，决定自动处理或转人工的门控机制
version: 1.0.0
tags:
  - 客服
  - 置信度
  - 门控
  - 决策
inputs:
  type: object
  properties:
    intent_result:
      type: object
      description: 意图识别结果
      properties:
        intent: { type: string }
        intent_label: { type: string }
        confidence: { type: number }
        keywords: { type: array }
        entities: { type: object }
    sentiment_result:
      type: object
      description: 情感分析结果
      properties:
        sentiment: { type: string }
        sentiment_score: { type: number }
        intensity: { type: string }
        require_human: { type: boolean }
        priority_level: { type: string }
    rag_result:
      type: object
      description: 知识库检索结果
      properties:
        hit: { type: boolean }
        confidence: { type: number }
        content: { type: string }
        source: { type: string }
    context:
      type: object
      description: 业务上下文
      properties:
        customer_tier: { type: string }
        order_value: { type: number }
        previous_complaints: { type: number }
        customer_duration: { type: number }
outputs:
  type: object
  properties:
    decision:
      type: string
      description: 处理决策
      enum:
        - auto           # 自动处理
        - confirm        # 确认后处理
        - human          # 转人工
    confidence:
      type: number
      description: 综合置信度 0-1
    confidence_breakdown:
      type: object
      description: 各维度置信度详情
    risk_level:
      type: string
      description: 风险等级
      enum:
        - low
        - medium
        - high
        - critical
    processing_mode:
      type: string
      description: 处理模式
    action:
      type: string
      description: 建议的后续动作
    message:
      type: string
      description: 决策说明
gate: medium
---

# 客服置信度门控 Skill

## 简介
本技能是客服自动化的核心决策模块，通过综合评估多个维度的置信度，决定是自动处理还是转人工处理。遵循**AGENTS.md**中的门控机制定义。

## 门控等级定义

| 风险等级 | 综合置信度 | 处理模式 | 说明 |
|----------|-----------|----------|------|
| low | >= 0.85 | 自动执行 | 高置信度，直接自动处理 |
| medium | 0.6-0.85 | 执行并通知 | 中置信度，执行后通知人工 |
| high | 0.4-0.6 | 确认后执行 | 低置信度，需人工确认 |
| critical | < 0.4 | 强制转人工 | 极低置信度，强制转人工 |

## 置信度权重配置

| 维度 | 权重 | 说明 |
|------|------|------|
| 意图识别 | 0.40 | 核心输入的理解程度 |
| 情感分析 | 0.25 | 用户情绪稳定性 |
| 知识库匹配 | 0.25 | RAG检索结果质量 |
| 业务上下文 | 0.10 | 客户价值和历史记录 |

## 决策矩阵

### 自动处理条件（decision: auto）
满足以下全部条件：
- 意图识别置信度 >= 0.7
- 情感不是 angry/disappointed 或强度 <= medium
- 知识库匹配置信度 >= 0.6
- 风险等级 != critical

### 转人工条件（decision: human）
满足以下任一条件：
- 综合置信度 < 0.4
- 情感强度 = critical
- 情感 require_human = true
- 连续3轮置信度下降
- VIP客户 + 置信度 < 0.7
- 高价值订单 + 情感负面

### 确认后处理（decision: confirm）
不满足自动处理，但也不满足转人工条件。

## 输出说明

- **decision**: 最终决策
- **confidence**: 0-1的综合置信度
- **confidence_breakdown**: 各维度详细置信度
- **risk_level**: 低/中/高/危险
- **processing_mode**: 建议的处理模式
- **action**: 具体操作建议

## 使用场景

适用于企业微信、飞书等渠道的客服系统，作为核心决策引擎，决定每条用户消息的处理路径。
