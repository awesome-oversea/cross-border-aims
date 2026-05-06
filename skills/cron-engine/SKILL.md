# Cron定时任务引擎

## 概述
OpenClaw原生Cron调度引擎，8个内置定时任务覆盖日报/发布/监控/刷新，支持自定义任务扩展。

## 8个内置定时任务

| 任务名 | Cron表达式 | 说明 | Agent | Skill |
|--------|-----------|------|-------|-------|
| daily-ai-report | `0 9 * * *` | 每天9:00推送AI行业日报 | office | report-gen |
| xhs-daily-publish | `0 10 * * *` | 每天10:00自动发布小红书种草内容 | social-media | xhs-seed |
| douyin-daily-publish | `0 11 * * *` | 每天11:00自动发布抖音内容 | social-media | douyin-ops |
| video-channel-publish | `0 14 * * *` | 每天14:00自动发布视频号内容 | social-media | video-channel |
| weekly-report | `0 18 * * 5` | 每周五18:00生成运营周报 | office | report-gen |
| opinion-monitor | `*/10 * * * *` | 每10分钟监控社媒评论舆情 | social-media | opinion-watch |
| token-refresh | `0 */1 * * *` | 每小时刷新电商平台access_token | ecommerce | listing-gen |
| team-daily-report | `0 8 * * *` | 每天8:00生成团队日报 | office | report-gen |

## API接口

### init_builtin - 初始化内置任务
```json
{"action": "init_builtin"}
```

### list_jobs - 列出所有任务
```json
{"action": "list_jobs"}
```

### trigger_job - 手动触发任务
```json
{"action": "trigger_job", "name": "daily-ai-report"}
```

### add_job - 添加自定义任务
```json
{
  "action": "add_job",
  "job_config": {
    "name": "custom-report",
    "display_name": "自定义报表",
    "cron_expr": "0 8 * * 1-5",
    "description": "工作日8:00生成报表",
    "agent": "office",
    "skill": "report-gen",
    "action": "generate_custom_report",
    "params": {"report_type": "custom"},
    "channel": "feishu",
    "target": "office_group"
  }
}
```

### validate_cron - 验证Cron表达式
```json
{"action": "validate_cron", "expr": "0 9 * * *"}
```

### stats - 执行统计
```json
{"action": "stats"}
```

## Cron表达式格式
```
┌──────── 分钟 (0-59)
│ ┌────── 小时 (0-23)
│ │ ┌──── 日 (1-31)
│ │ │ ┌── 月 (1-12)
│ │ │ │ ┌ 星期 (0-6, 0=周日)
│ │ │ │ │
* * * * *
```

支持: `*` 任意值, `,` 列表, `-` 范围, `/` 步长
