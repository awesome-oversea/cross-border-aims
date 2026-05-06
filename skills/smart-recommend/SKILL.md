---
title: 智能推荐系统
description: 基于用户画像、行为数据和商品特征，提供个性化商品推荐和营销建议
version: 1.0.0
tags:
  - 推荐系统
  - 个性化推荐
  - 协同过滤
  - 用户画像
inputs:
  type: object
  properties:
    user_id:
      type: string
      description: 用户ID
    user_profile:
      type: object
      description: 用户画像数据
    context:
      type: object
      description: 上下文信息（当前浏览商品、场景等）
    recommendation_type:
      type: string
      description: 推荐类型
      enum:
        - personalized     # 个性化推荐
        - related          # 关联推荐
        - popular          # 热门推荐
        - new_arrivals     # 新品推荐
        - complementary    # 互补推荐
        - cross_sell       # 交叉销售
    limit:
      type: integer
      description: 推荐数量
      default: 6
outputs:
  type: object
  properties:
    recommendations:
      type: array
      description: 推荐商品列表
      items:
        type: object
        properties:
          product_id: { type: string }
          name: { type: string }
          category: { type: string }
          price: { type: number }
          image: { type: string }
          rating: { type: number }
          sales: { type: number }
          reason: { type: string }
          confidence: { type: number }
    strategy:
      type: string
      description: 推荐策略说明
    explanation:
      type: string
      description: 推荐理由解释
gate: low
---

# 智能推荐系统 Skill

## 简介
本技能基于用户画像、历史行为和商品特征，实现多维度智能推荐，支持多种推荐策略。

## 推荐策略

| 策略 | 说明 | 应用场景 |
|------|------|----------|
| personalized | 个性化推荐 | 首页推荐、用户专属推荐 |
| related | 关联推荐 | 商品详情页、猜你喜欢 |
| popular | 热门推荐 | 热销榜单、人气商品 |
| new_arrivals | 新品推荐 | 新品上市、首发专区 |
| complementary | 互补推荐 | 搭配购买、配件推荐 |
| cross_sell | 交叉销售 | 基于订单的关联推荐 |

## 推荐算法

1. **基于用户画像**：根据用户标签、偏好进行推荐
2. **协同过滤**：基于相似用户行为推荐
3. **内容推荐**：基于商品特征相似度推荐
4. **规则引擎**：基于业务规则的推荐

## 使用场景

适用于电商首页、商品详情页、订单完成页等场景的个性化推荐。
