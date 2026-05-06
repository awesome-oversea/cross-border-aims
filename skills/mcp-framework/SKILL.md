# MCP Server框架

## 概述
MCP Server框架提供统一的数据访问适配层，封装MySQL/Redis/Milvus/Qdrant等数据源的访问能力，为所有技能提供标准化的数据操作接口。

## 支持的数据源

### MySQL适配器
| 工具 | 说明 | 风险级别 |
|------|------|----------|
| mysql_query | 执行SQL查询 | read |
| mysql_execute | 执行写操作 | write |
| mysql_list_tables | 列出所有表 | read |
| mysql_describe_table | 查看表结构 | read |
| mysql_insert | 插入数据 | write |
| mysql_update | 更新数据 | write |

### Redis适配器
| 工具 | 说明 | 风险级别 |
|------|------|----------|
| redis_get | 获取键值 | read |
| redis_set | 设置键值 | write |
| redis_delete | 删除键 | write |
| redis_hget | 获取Hash字段 | read |
| redis_hset | 设置Hash字段 | write |
| redis_hgetall | 获取Hash所有字段 | read |
| redis_list_push | 向列表推入值 | write |
| redis_list_range | 获取列表范围 | read |
| redis_keys | 搜索匹配键 | read |
| redis_ttl | 获取过期时间 | read |
| redis_incr | 递增计数器 | write |

### Milvus适配器
| 工具 | 说明 | 风险级别 |
|------|------|----------|
| milvus_search | 向量搜索 | read |
| milvus_insert | 插入向量数据 | write |
| milvus_list_collections | 列出集合 | read |
| milvus_get_collection_stats | 集合统计 | read |

### Qdrant适配器
| 工具 | 说明 | 风险级别 |
|------|------|----------|
| qdrant_search | 向量搜索 | read |
| qdrant_list_collections | 列出集合 | read |

## API接口

### call_tool - 调用MCP工具
```json
{
  "action": "call_tool",
  "tool_name": "redis_get",
  "params": {"key": "user:123:profile"}
}
```

### health_check - 健康检查
```json
{"action": "health_check"}
```

### list_tools - 列出可用工具
```json
{"action": "list_tools", "server_name": "redis"}
```

### get_history - 获取调用历史
```json
{"action": "get_history", "limit": 50}
```

## 容错机制
- MySQL不可用时自动降级到本地SQLite
- Redis不可用时返回fallback标记
- Milvus/Qdrant不可用时返回空结果
- 所有调用记录日志，便于排查问题
