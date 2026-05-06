# 安全合规与风控

## 概述
内容风控、凭证管理、防注入、限流、审计日志，保障系统安全合规。

## 核心模块

### 内容风控 (ContentModerator)
- 敏感词检测：7类敏感词库（政治/暴力/色情/赌博/欺诈/毒品/歧视）
- 平台合规检查：5个平台规则（淘宝/京东/拼多多/小红书/抖音）
- 违禁词检测、标题长度检查、必填字段校验

### 防注入 (PromptInjectionDetector)
- 12种注入模式检测
- 输入清洗/过滤
- 风险等级评估

### 凭证管理 (CredentialManager)
- API Key安全存储（SHA256哈希）
- 凭证轮换（默认90天）
- 过期检测
- 凭证验证

### 限流 (RateLimiter)
- 滑动窗口限流
- 可配置请求上限和时间窗口
- 剩余配额和重试时间

## API接口

### full_check - 完整安全检查
```json
{"action": "full_check", "text": "内容文本", "platform": "taobao"}
```

### content_check - 内容合规检查
```json
{"action": "content_check", "text": "商品标题", "platform": "taobao", "content": {"title": "...", "price": 99}}
```

### injection_check - 注入检测
```json
{"action": "injection_check", "text": "用户输入"}
```

### injection_sanitize - 注入清洗
```json
{"action": "injection_sanitize", "text": "用户输入"}
```

### store_credential - 存储凭证
```json
{"action": "store_credential", "key": "DEEPSEEK_API_KEY", "value": "sk-xxx", "description": "DeepSeek API密钥"}
```

### rate_check - 限流检查
```json
{"action": "rate_check", "identifier": "user-001", "max_requests": 100, "window_seconds": 60}
```
