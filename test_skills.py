#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import sys

def test_skill(skill_name, input_data):
    print(f"=== 测试 {skill_name} ===")
    try:
        result = subprocess.run(
            ["python", f"D:/Project/aims/skills/{skill_name}/main.py"],
            input=json.dumps(input_data, ensure_ascii=False).encode('utf-8'),
            capture_output=True,
            text=False
        )
        
        if result.returncode == 0:
            output = result.stdout.decode('utf-8').strip()
            try:
                data = json.loads(output)
                print(f"✓ 成功")
                print(f"  输出: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
                return True
            except json.JSONDecodeError:
                print(f"✗ 输出不是有效的JSON: {output[:100]}")
                return False
        else:
            error = result.stderr.decode('utf-8')
            print(f"✗ 失败: {error[:100]}")
            return False
    except Exception as e:
        print(f"✗ 异常: {str(e)}")
        return False

def main():
    tests = [
        {
            "skill": "order-query",
            "input": {"order_id": "ORD1234567890"}
        },
        {
            "skill": "logistics-track",
            "input": {"tracking_number": "SF1234567890"}
        },
        {
            "skill": "after-sale",
            "input": {"order_id": "ORD1234567890", "type": "refund", "reason": "商品质量问题"}
        },
        {
            "skill": "email-mgr",
            "input": {"subject": "关于订单退款的问题", "body": "您好，我购买的商品有质量问题，需要退款。请尽快处理，谢谢！", "sender": "customer@example.com"}
        },
        {
            "skill": "video-channel",
            "input": {"product": "智能手表", "audience": "young_female", "duration": 60}
        },
        {
            "skill": "report-gen",
            "input": {"report_type": "daily"}
        },
        {
            "skill": "excel-viz",
            "input": {"data": [{"name": "周一", "value": 120}, {"name": "周二", "value": 150}, {"name": "周三", "value": 180}], "chart_type": "bar", "title": "日销量统计"}
        },
        {
            "skill": "intent-recognition",
            "input": {"user_message": "我想查一下我的订单什么时候能到", "history": []}
        },
        {
            "skill": "sentiment-analysis",
            "input": {"user_message": "太失望了，等了这么久还没收到货，质量也差", "history": [], "context": {"customer_tier": "普通", "order_value": 899}}
        },
        {
            "skill": "confidence-gate",
            "input": {
                "intent_result": {"intent": "order_query", "intent_label": "订单查询", "confidence": 0.85},
                "sentiment_result": {"sentiment": "negative", "sentiment_score": -0.4, "intensity": "medium", "require_human": False},
                "rag_result": {"hit": True, "confidence": 0.75},
                "context": {"customer_tier": "普通", "order_value": 500}
            }
        },
        {
            "skill": "user-profile",
            "input": {"user_id": "USER001", "action": "create", "data": {"name": "张三", "phone": "13800138000", "tier": "VIP"}}
        },
        {
            "skill": "smart-recommend",
            "input": {"user_id": "USER001", "user_profile": {"tags": ["数码爱好者", "VIP"], "preferences": {"categories": ["智能穿戴", "音频设备"]}}, "recommendation_type": "personalized", "limit": 4}
        },
        {
            "skill": "multimodal-理解",
            "input": {"content_type": "text", "content": "这款智能手表非常好用，推荐购买！限时优惠8折起，活动时间2026年5月1日-5月31日", "analysis_type": ["text_analysis", "sentiment", "key_points"]}
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test_skill(test["skill"], test["input"]):
            passed += 1
        else:
            failed += 1
        print()
    
    print(f"=== 测试结果 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"成功率: {(passed / (passed + failed)) * 100:.1f}%")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())