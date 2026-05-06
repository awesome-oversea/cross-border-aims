---
name: data-flywheel
version: 1.0.0
description: 数据回流与自进化飞轮 — CDC管道+特征更新+向量更新
author: AIMS
tags: [data, flywheel, cdc, evolution]
---

# 数据回流与自进化飞轮

## 概述
实现数据回流闭环，将业务数据自动回流到知识库和特征库，驱动AI模型持续进化。

## 核心组件
1. **CDC管道**：监听MySQL binlog变更，实时捕获数据变更
2. **特征更新**：从业务数据提取特征，更新用户画像和商品特征
3. **向量更新**：将新数据向量化后写入Milvus/Qdrant知识库
4. **效果追踪**：追踪AI建议采纳率和效果，反馈优化

## 自进化飞轮
数据采集 → 特征提取 → 模型优化 → 建议生成 → 采纳执行 → 效果追踪 → 数据回流

## API接口

### start_cdc - 启动CDC管道
```json
{"action": "start_cdc", "tables": ["products", "orders", "reviews"], "batch_size": 100}
```

### sync_features - 同步特征数据
```json
{"action": "sync_features", "feature_type": "user_profile", "entity_id": "user_001"}
```

### sync_vectors - 同步向量数据
```json
{"action": "sync_vectors", "collection": "ecom_rules", "source_table": "products", "batch_size": 50}
```

### track_adoption - 追踪建议采纳
```json
{"action": "track_adoption", "suggestion_type": "listing", "suggestion_id": "sug-001", "adopted": true, "effect": {"ctr": 0.05, "conversion": 0.02}}
```

### get_flywheel_status - 获取飞轮状态
```json
{"action": "get_flywheel_status"}
```
