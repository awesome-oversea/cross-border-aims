---
title: 系统监控告警
description: 实时监控AIMS系统各组件运行状态，检测异常并触发告警通知，保障系统稳定运行
version: 1.0.0
tags:
  - 监控
  - 告警
  - 运维
  - 健康检查
inputs:
  type: object
  properties:
    action:
      type: string
      description: 操作类型
      enum:
        - health_check    # 健康检查
        - metrics         # 获取指标
        - alert_check     # 告警检测
        - alert_history   # 告警历史
        - component_status # 组件状态
    target:
      type: string
      description: 监控目标
      enum:
        - all             # 全部
        - gateway         # 网关
        - agents          # Agent服务
        - database        # 数据库
        - redis           # Redis缓存
        - milvus          # Milvus向量库
        - qdrant          # Qdrant向量库
        - minio           # 对象存储
outputs:
  type: object
  properties:
    status:
      type: string
      description: 系统状态
      enum: [healthy, warning, critical, unknown]
    components:
      type: array
      description: 各组件状态
      items:
        type: object
        properties:
          name: { type: string }
          status: { type: string }
          response_time: { type: number }
          uptime: { type: string }
          details: { type: object }
    alerts:
      type: array
      description: 活跃告警列表
      items:
        type: object
        properties:
          level: { type: string }
          component: { type: string }
          message: { type: string }
          timestamp: { type: string }
    metrics:
      type: object
      description: 系统指标
gate: low
---

# 系统监控告警 Skill

## 简介
实时监控AIMS系统各组件运行状态，检测异常并触发告警通知。

## 监控组件

| 组件 | 检查项 | 告警阈值 |
|------|--------|----------|
| Gateway | 响应时间、请求成功率 | RT>2s, 成功率<95% |
| Agents | 运行状态、内存占用 | 内存>80%, 崩溃 |
| MySQL | 连接数、慢查询、磁盘 | 连接>80%, 慢查询>10/min |
| Redis | 内存、命中率、连接数 | 内存>80%, 命中率<90% |
| Milvus | 查询延迟、索引状态 | 延迟>500ms |
| Qdrant | 查询延迟、集合状态 | 延迟>500ms |
| MinIO | 存储空间、上传成功率 | 空间>85% |

## 告警等级

| 等级 | 说明 | 通知方式 |
|------|------|----------|
| info | 信息通知 | 日志记录 |
| warning | 警告 | 飞书/企微通知 |
| critical | 严重 | 飞书+短信+电话 |

## 使用场景

适用于系统运维监控、Cron定时健康检查、故障排查等场景。
