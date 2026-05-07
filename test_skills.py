#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import subprocess

# Force UTF-8 output encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def uprint(text):
    """安全打印：处理Windows终端UTF-8编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + '\n').encode('utf-8'))


def test_skill(skill_name, input_data):
    """测试单个技能：通过subprocess调用技能main.py，验证JSON输出"""

    uprint(f"=== Testing {skill_name} ===")
    try:
        result = subprocess.run(
            [sys.executable, f"D:/Project/aims/skills/{skill_name}/main.py"],
            input=json.dumps(input_data, ensure_ascii=False).encode('utf-8'),
            capture_output=True,
            text=False
        )

        if result.returncode == 0:
            output = result.stdout.decode('utf-8', errors='replace').strip()
            try:
                data = json.loads(output)
                uprint(f"  PASS")
                summary = json.dumps(data, ensure_ascii=False, indent=2)[:200]
                uprint(f"  output: {summary}")
                return True
            except json.JSONDecodeError:
                uprint(f"  FAIL - invalid JSON: {output[:100]}")
                return False
        else:
            error = result.stderr.decode('utf-8', errors='replace')
            uprint(f"  FAIL: {error[:100]}")
            return False
    except Exception as e:
        uprint(f"  EXCEPTION: {e}")
        return False


def main():
    tests = [
        {"skill": "order-query", "input": {"order_id": "ORD1234567890"}},
        {"skill": "logistics-track", "input": {"tracking_number": "SF1234567890"}},
        {"skill": "after-sale", "input": {"order_id": "ORD1234567890", "type": "refund", "reason": "Item defect"}},
        {"skill": "email-mgr", "input": {"subject": "Refund request", "body": "I need a refund", "sender": "customer@test.com"}},
        {"skill": "video-channel", "input": {"product": "Smart Watch", "audience": "young_female", "duration": 60}},
        {"skill": "report-gen", "input": {"report_type": "daily"}},
        {"skill": "excel-viz", "input": {"data": [{"name": "Mon", "value": 120}, {"name": "Tue", "value": 150}], "chart_type": "bar", "title": "Sales"}},
        {"skill": "intent-recognition", "input": {"user_message": "Where is my order?", "history": []}},
        {"skill": "sentiment-analysis", "input": {"user_message": "Very disappointed, long wait", "history": []}},
        {"skill": "confidence-gate", "input": {"intent_result": {"intent": "order_query", "confidence": 0.85}, "sentiment_result": {"sentiment": "negative"}, "rag_result": {"hit": True}, "context": {}}},
        {"skill": "user-profile", "input": {"user_id": "USER001", "action": "create", "data": {"name": "Test User"}}},
        {"skill": "smart-recommend", "input": {"user_id": "USER001", "user_profile": {"tags": ["VIP"], "preferences": {"categories": ["Electronics"]}}, "recommendation_type": "personalized", "limit": 4}},
        {"skill": "multimodal-理解", "input": {"content_type": "text", "content": "Great product! 50% off today!", "analysis_type": ["text_analysis", "sentiment", "key_points"]}},
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test_skill(test["skill"], test["input"]):
            passed += 1
        else:
            failed += 1
        uprint("")

    uprint(f"=== Results ===")
    uprint(f"Passed: {passed}")
    uprint(f"Failed: {failed}")
    uprint(f"Rate: {(passed / (passed + failed)) * 100:.1f}%")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
