# 知识管道

## 概述
知识管道负责RAG知识库的内容扩充、知识导入、检索和防幻觉机制。包含6类跨境电商领域知识库和完整的知识管理能力。

## 6类知识库

| 类别 | Key | 说明 | 文档数 |
|------|-----|------|--------|
| 跨境电商运营 | cross_border_ops | 亚马逊/Shopify/TikTok运营策略 | 5 |
| 平台规则与政策 | platform_rules | 各平台规则、合规要求 | 4 |
| 产品开发与选品 | product_dev | 选品方法论、生命周期管理 | 4 |
| 广告投放与优化 | advertising | 亚马逊/Facebook/Google广告 | 4 |
| 物流与仓储 | logistics_warehouse | FBA/海外仓/头程物流 | 4 |
| 财务与合规 | finance_compliance | 成本核算/税务/收款 | 4 |

## API接口

### import_builtin - 导入内置知识库
```json
{"action": "import_builtin"}
```

### import_document - 导入单篇文档
```json
{
  "action": "import_document",
  "title": "文档标题",
  "category": "cross_border_ops",
  "content": "文档内容...",
  "tags": ["标签1", "标签2"],
  "source": "manual"
}
```

### search - 知识检索
```json
{
  "action": "search",
  "query": "亚马逊ACOS优化",
  "top_k": 5,
  "category": "advertising"
}
```

### search_with_check - 检索+防幻觉检查
```json
{
  "action": "search_with_check",
  "query": "亚马逊ACOS优化",
  "response": "ACOS应该控制在25%-35%之间...",
  "top_k": 5
}
```

### stats - 知识库统计
```json
{"action": "stats"}
```

### list_categories - 列出知识类别
```json
{"action": "list_categories"}
```

## 防幻觉机制
- **来源覆盖率**：回答内容在知识来源中的覆盖比例(40%权重)
- **事实一致性**：回答与知识来源的语义匹配度(40%权重)
- **完整性**：检索结果与查询的相关性(20%权重)
- **风险等级**：high/medium/low 三级
- **置信度**：0-1分，低于0.5为高风险

## 文档分块策略
- 默认块大小：800字符
- 块重叠：100字符
- 按句子边界切分，保持语义完整性
