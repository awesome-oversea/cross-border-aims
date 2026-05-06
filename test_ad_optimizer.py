#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
sys.path.insert(0, "D:/Project/aims/skills/ad-optimizer")

from main import optimize_advertising

# 测试数据
test_data = {
    "platform": "amazon",
    "shop": "Test Shop",
    "campaign_type": "sponsored",
    "time_range": "last_7_days",
    "impressions": 10000,
    "clicks": 200,
    "spend": 400.0,
    "conversions": 10,
    "acos": 40.0,
    "ctr": 2.0,
    "cvr": 5.0,
    "roas": 2.5,
    "target_acos": 30.0,
    "target_roas": 3.0,
    "keywords": [
        {"name": "wireless headphones", "acos": 25.0, "conversions": 5},
        {"name": "bluetooth earphones", "acos": 55.0, "spend": 60.0, "conversions": 0},
        {"name": "best headphones", "acos": 35.0, "conversions": 3}
    ]
}

# 调用技能
result = optimize_advertising(test_data)

# 输出结果
print("=== 广告优化测试结果 ===")
print(json.dumps(result, ensure_ascii=False, indent=2))