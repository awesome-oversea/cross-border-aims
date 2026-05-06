# 技能编排器

## 概述
技能编排器负责多技能协同调用，支持工作流模板、上下文传递、条件执行和结果聚合。

## 核心能力

### 1. 工作流模板
预定义9种常用工作流，覆盖电商运营、社媒营销、客服、办公自动化四大业务域：

| 工作流 | 说明 | 步骤数 |
|--------|------|--------|
| full_listing_launch | 新品上架全流程 | 4步 |
| order_full_inquiry | 订单全链路查询 | 3步 |
| review_crisis_handling | 差评危机处理 | 4步 |
| social_media_campaign | 社媒营销活动 | 4步 |
| ad_full_optimization | 广告全链路优化 | 3步 |
| ecommerce_operation_hub | 电商经营闭环 | 5步 |
| social_media_content_flywheel | 社媒内容增长闭环 | 5步 |
| customer_service_resolution | 客服服务闭环 | 5步 |
| office_productivity_suite | 办公自动化闭环 | 4步 |

### 2. 上下文传递
- 前序技能的输出自动映射为后续技能的输入
- 支持input_mapping配置，灵活定义数据流转
- 全局参数贯穿整个工作流
- 支持 `@params.xxx` / `@context.xxx` / `@result:step_key.xxx` 形式的显式映射

### 3. 条件执行
- 根据条件决定是否执行某个步骤
- 内置条件：has_tracking / has_aftersale / has_negative / has_order_id / has_product / high_value_order / vip_customer
- 条件基于上下文和前序结果动态评估

### 4. 结果聚合
- 每种工作流有专属聚合器，生成结构化报告
- 包含summary、详细结果、推荐行动等
- 支持自定义聚合类型
- 聚合结果包含 `handoff` 字段，用于汇总人工审核/升级处理信号

## API接口

### execute_workflow - 执行预定义工作流
```json
{
  "action": "execute_workflow",
  "workflow_name": "full_listing_launch",
  "params": {
    "product_name": "蓝牙耳机",
    "platform": "amazon",
    "selling_points": ["降噪", "长续航", "蓝牙5.3"]
  },
  "context": {
    "user_id": "user123"
  }
}
```

### execute_custom - 执行自定义工作流
```json
{
  "action": "execute_custom",
  "steps": [
    {"skill": "order-query", "action": "query", "output_key": "order", "required": true},
    {"skill": "logistics-track", "action": "track", "output_key": "logistics", "condition": "has_tracking"}
  ],
  "params": {"order_id": "ORD20240101001"},
  "aggregation_type": "order_full_report"
}
```

### list_workflows - 列出可用工作流
```json
{"action": "list_workflows"}
```

### save_template - 保存自定义模板
```json
{
  "action": "save_template",
  "name": "my_workflow",
  "definition": {
    "name": "自定义工作流",
    "description": "...",
    "steps": [...],
    "aggregation": "default"
  }
}
```

### get_history - 获取执行历史
```json
{"action": "get_history", "limit": 20}
```

## 工作流详情

### full_listing_launch - 新品上架全流程
1. listing-gen → 生成Listing
2. material-gen → 生成素材（非必需）
3. ad-optimizer → 广告方案（非必需）
4. xhs-seed → 小红书种草（非必需）

### order_full_inquiry - 订单全链路查询
1. order-query → 查询订单（必需）
2. logistics-track → 物流追踪（条件：has_tracking）
3. after-sale → 售后状态（条件：has_aftersale）

### review_crisis_handling - 差评危机处理
1. review-mgr(analyze) → 评论分析（必需）
2. review-mgr(detect_alerts) → 差评预警
3. review-mgr(generate_reply) → 自动回复（条件：has_negative）
4. opinion-watch → 舆情监控

### social_media_campaign - 社媒营销活动
1. xhs-seed(generate) → 小红书种草（必需）
2. xhs-seed(calendar) → 内容日历
3. douyin-ops(generate) → 抖音脚本
4. opinion-watch → 舆情监控

### ad_full_optimization - 广告全链路优化
1. ad-optimizer(optimize) → 广告分析（必需）
2. ad-optimizer(budget) → 预算分配
3. listing-gen(optimize) → Listing优化建议

### ecommerce_operation_hub - 电商经营闭环
1. listing-gen(generate) → Listing 主稿（必需）
2. material-gen(generate) → 多平台素材 brief
3. ad-optimizer(optimize) → 广告优化建议
4. report-gen(generate) → 经营报表
5. excel-viz(visualize) → 图表看板

### social_media_content_flywheel - 社媒内容增长闭环
1. xhs-seed(generate) → 小红书种草笔记（必需）
2. douyin-ops(generate) → 抖音短视频脚本
3. video-channel(generate) → 视频号分发内容
4. cross-drain(cross_platform_strategy) → 跨平台导流策略
5. opinion-watch(monitor) → 内容上线后舆情巡检

### customer_service_resolution - 客服服务闭环
1. intent-recognition(analyze) → 咨询意图识别（必需）
2. order-query(query) → 订单摘要查询
3. logistics-track(track) → 物流追踪
4. after-sale(query) → 售后状态查询
5. sentiment-analysis(analyze) → 负面情绪升级判断

### office_productivity_suite - 办公自动化闭环
1. report-gen(generate) → 周报/经营报表（必需）
2. excel-viz(visualize) → 图表看板
3. doc-auto(summarize) → 文档摘要/复盘底稿
4. email-mgr(draft) → 邮件草稿
