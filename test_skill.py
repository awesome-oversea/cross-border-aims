#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
sys.path.insert(0, "D:/Project/aims/skills/listing-gen")

from main import generate_listing

# 测试数据
test_data = {
    "platform": "amazon",
    "site": "US",
    "language": "en-US",
    "product_name": "Wireless Bluetooth Headphones",
    "category": "Electronics",
    "features": ["Noise Cancelling", "40 Hours Battery Life", "Waterproof IPX5"],
    "specs": {"Color": "Black", "Weight": "180g"},
    "material": "ABS Plastic"
}

# 调用技能
result = generate_listing(test_data)

# 输出结果
print("=== 测试结果 ===")
print(json.dumps(result, ensure_ascii=False, indent=2))