---
title: 多模态内容理解
description: 支持图片、视频、文本等多种媒体类型的内容分析和理解，提取关键信息和语义
version: 1.0.0
tags:
  - 多模态
  - 内容理解
  - 图片分析
  - OCR
  - 视频分析
inputs:
  type: object
  properties:
    content_type:
      type: string
      description: 内容类型
      enum:
        - image       # 图片
        - video       # 视频
        - text        # 文本
        - mixed       # 混合内容
    content:
      type: string
      description: 内容数据（图片URL、视频URL或文本内容）
    analysis_type:
      type: array
      description: 分析类型
      items:
        type: string
        enum:
          - ocr              # 光学字符识别
          - object_detection # 物体检测
          - scene_recognition # 场景识别
          - text_analysis    # 文本分析
          - sentiment        # 情感分析
          - key_points       # 关键点提取
          - brand_detection  # 品牌检测
          - logo_detection   # Logo检测
outputs:
  type: object
  properties:
    content_type:
      type: string
      description: 内容类型
    analysis_results:
      type: array
      description: 分析结果列表
      items:
        type: object
        properties:
          type: { type: string }
          confidence: { type: number }
          data: { type: object }
    summary:
      type: string
      description: 内容摘要
    keywords:
      type: array
      description: 关键词列表
      items:
        type: string
    entities:
      type: object
      description: 识别的实体
gate: low
---

# 多模态内容理解 Skill

## 简介
本技能支持图片、视频、文本等多种媒体类型的内容分析和理解，提取关键信息和语义。

## 分析能力

| 分析类型 | 说明 | 输出示例 |
|----------|------|----------|
| ocr | 光学字符识别 | 识别图片中的文字内容 |
| object_detection | 物体检测 | 识别图片中的物体及其位置 |
| scene_recognition | 场景识别 | 识别图片/视频的场景类型 |
| text_analysis | 文本分析 | 分析文本内容、主题分类 |
| sentiment | 情感分析 | 分析内容情感倾向 |
| key_points | 关键点提取 | 提取内容的核心要点 |
| brand_detection | 品牌检测 | 识别内容中的品牌信息 |
| logo_detection | Logo检测 | 识别内容中的Logo |

## 使用场景

适用于社媒内容分析、商品图片理解、视频内容分析等场景。
