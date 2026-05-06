#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import json
import sys
import os
import time
from datetime import datetime

SKILLS_DIR = "D:/Project/aims/skills"

test_cases = {
    "listing-gen": [
        {"name": "基础Listing生成", "input": {"product_name": "智能手表Pro", "category": "智能穿戴", "platform": "taobao"}},
        {"name": "空商品名处理", "input": {"product_name": "", "category": "智能穿戴", "platform": "taobao"}},
    ],
    "ad-optimizer": [
        {"name": "广告优化", "input": {"campaign_id": "CAMP001", "budget": 1000, "target_roas": 3.0}},
    ],
    "review-mgr": [
        {"name": "评论管理", "input": {"product_id": "P001", "action": "analyze", "reviews": [{"content": "非常好用", "rating": 5}, {"content": "一般般", "rating": 3}]}},
    ],
    "material-gen": [
        {"name": "素材生成", "input": {"product_name": "智能手表", "material_type": "banner", "style": "科技感"}},
    ],
    "after-sale": [
        {"name": "退款处理", "input": {"order_id": "ORD1234567890", "type": "refund", "reason": "商品质量问题"}},
        {"name": "换货处理", "input": {"order_id": "ORD9876543210", "type": "exchange", "reason": "尺寸不符"}},
    ],
    "xhs-seed": [
        {"name": "小红书种草", "input": {"product": "智能手表", "style": "种草笔记", "target_audience": "年轻女性"}},
    ],
    "douyin-ops": [
        {"name": "抖音运营", "input": {"product": "蓝牙耳机", "video_type": "short", "target_audience": "年轻人"}},
    ],
    "opinion-watch": [
        {"name": "舆情监控", "input": {"keywords": ["智能手表", "质量问题"], "platform": "all"}},
    ],
    "order-query": [
        {"name": "订单查询", "input": {"order_id": "ORD1234567890"}},
        {"name": "手机号查询", "input": {"phone": "13800138000"}},
    ],
    "logistics-track": [
        {"name": "物流跟踪", "input": {"tracking_number": "SF1234567890"}},
        {"name": "顺丰运单", "input": {"tracking_number": "SF1098765432"}},
    ],
    "doc-auto": [
        {"name": "文档自动化", "input": {"doc_type": "report", "title": "月度经营报告", "content": "本月销售额增长15%"}},
    ],
    "rag-retrieval": [
        {"name": "RAG检索", "input": {"query": "智能手表退货政策", "top_k": 3}},
    ],
    "cross-drain": [
        {"name": "跨平台导流", "input": {"source": "douyin", "target": "wechat", "content_type": "product"}},
    ],
    "email-mgr": [
        {"name": "邮件分类", "input": {"subject": "关于订单退款的问题", "body": "您好，我购买的商品有质量问题", "sender": "customer@example.com"}},
        {"name": "紧急邮件", "input": {"subject": "紧急：合同签署", "body": "请尽快签署合同", "sender": "partner@example.com"}},
    ],
    "video-channel": [
        {"name": "短视频脚本", "input": {"product": "智能手表", "audience": "young_female", "duration": 60}},
    ],
    "report-gen": [
        {"name": "日报生成", "input": {"report_type": "daily"}},
        {"name": "周报生成", "input": {"report_type": "weekly"}},
    ],
    "excel-viz": [
        {"name": "柱状图生成", "input": {"data": [{"name": "周一", "value": 120}, {"name": "周二", "value": 150}], "chart_type": "bar", "title": "日销量"}},
        {"name": "饼图生成", "input": {"data": [{"name": "A", "value": 30}, {"name": "B", "value": 70}], "chart_type": "pie", "title": "占比"}},
    ],
    "intent-recognition": [
        {"name": "订单意图", "input": {"user_message": "我想查一下我的订单什么时候能到", "history": []}},
        {"name": "投诉意图", "input": {"user_message": "我要投诉你们的服务太差了", "history": []}},
        {"name": "售前咨询", "input": {"user_message": "这个手表多少钱，有什么功能", "history": []}},
        {"name": "模糊意图", "input": {"user_message": "你好", "history": []}},
    ],
    "sentiment-analysis": [
        {"name": "负面情感", "input": {"user_message": "太失望了，等了这么久还没收到货", "history": [], "context": {"customer_tier": "普通"}}},
        {"name": "正面情感", "input": {"user_message": "非常满意，质量很好", "history": [], "context": {}}},
        {"name": "VIP负面", "input": {"user_message": "不满意这个服务", "history": [], "context": {"customer_tier": "VIP", "order_value": 8000}}},
    ],
    "confidence-gate": [
        {"name": "高置信度自动处理", "input": {"intent_result": {"intent": "order_query", "intent_label": "订单查询", "confidence": 0.9}, "sentiment_result": {"sentiment": "neutral", "sentiment_score": 0.0, "intensity": "low", "require_human": False}, "rag_result": {"hit": True, "confidence": 0.8}, "context": {}}},
        {"name": "低置信度转人工", "input": {"intent_result": {"intent": "unclear", "intent_label": "无法识别", "confidence": 0.2}, "sentiment_result": {"sentiment": "angry", "sentiment_score": -0.8, "intensity": "critical", "require_human": True}, "rag_result": {"hit": False, "confidence": 0.1}, "context": {"customer_tier": "VIP"}}},
    ],
    "user-profile": [
        {"name": "创建画像", "input": {"user_id": "TEST001", "action": "create", "data": {"name": "测试用户", "tier": "VIP"}}},
        {"name": "添加标签", "input": {"user_id": "TEST001", "action": "add_tag", "data": {"tag": "数码爱好者"}}},
        {"name": "记录交互", "input": {"user_id": "TEST001", "action": "record_interaction", "data": {"interaction_type": "purchase", "sentiment": "positive", "satisfaction": 5}}},
    ],
    "smart-recommend": [
        {"name": "个性化推荐", "input": {"user_id": "USER001", "user_profile": {"tags": ["数码爱好者"], "preferences": {"categories": ["智能穿戴"]}}, "recommendation_type": "personalized", "limit": 4}},
        {"name": "热门推荐", "input": {"recommendation_type": "popular", "limit": 6}},
        {"name": "关联推荐", "input": {"recommendation_type": "related", "context": {"product_id": "P001"}, "limit": 4}},
    ],
    "multimodal-理解": [
        {"name": "文本分析", "input": {"content_type": "text", "content": "这款智能手表非常好用，推荐购买！", "analysis_type": ["text_analysis", "sentiment"]}},
        {"name": "图片分析", "input": {"content_type": "image", "content": "https://example.com/image.jpg", "analysis_type": ["ocr", "object_detection"]}},
    ],
    "system-monitor": [
        {"name": "全系统健康检查", "input": {"action": "health_check", "target": "all"}},
        {"name": "网关状态检查", "input": {"action": "component_status", "target": "gateway"}},
    ],
}

def run_skill_test(skill_name, test_case):
    skill_path = os.path.join(SKILLS_DIR, skill_name, "main.py")
    if not os.path.exists(skill_path):
        return {"passed": False, "error": f"技能文件不存在: {skill_path}"}

    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, skill_path],
            input=json.dumps(test_case["input"], ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            text=False,
            timeout=30
        )
        elapsed = round((time.time() - start_time) * 1000, 2)

        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace")
            return {"passed": False, "error": error[:200], "elapsed_ms": elapsed}

        output = result.stdout.decode("utf-8", errors="replace").strip()
        try:
            data = json.loads(output)
            return {"passed": True, "elapsed_ms": elapsed, "output_keys": list(data.keys())[:5]}
        except json.JSONDecodeError:
            return {"passed": False, "error": f"输出不是有效JSON: {output[:100]}", "elapsed_ms": elapsed}

    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "执行超时(30s)", "elapsed_ms": 30000}
    except Exception as e:
        return {"passed": False, "error": str(e)[:200], "elapsed_ms": 0}

def main():
    print("=" * 60)
    print("AIMS 自动化测试框架")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skill_results = {}

    for skill_name, cases in test_cases.items():
        print(f"\n--- {skill_name} ({len(cases)}个用例) ---")
        skill_passed = 0
        skill_failed = 0

        for case in cases:
            total_tests += 1
            result = run_skill_test(skill_name, case)

            if result["passed"]:
                skill_passed += 1
                passed_tests += 1
                status = "PASS"
            else:
                skill_failed += 1
                failed_tests += 1
                status = "FAIL"

            elapsed = result.get("elapsed_ms", 0)
            print(f"  [{status}] {case['name']} ({elapsed}ms)")
            if not result["passed"]:
                print(f"         错误: {result.get('error', '未知')[:80]}")

        skill_results[skill_name] = {
            "total": len(cases),
            "passed": skill_passed,
            "failed": skill_failed,
            "pass_rate": round(skill_passed / len(cases) * 100, 1) if cases else 0
        }

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for skill, stats in skill_results.items():
        status_icon = "OK" if stats["failed"] == 0 else "!!"
        print(f"  [{status_icon}] {skill}: {stats['passed']}/{stats['total']} ({stats['pass_rate']}%)")

    print(f"\n总计: {total_tests}个用例")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {round(passed_tests / total_tests * 100, 1) if total_tests else 0}%")

    report = {
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "pass_rate": round(passed_tests / total_tests * 100, 1) if total_tests else 0,
        "skills": skill_results
    }

    report_path = os.path.join("D:/Project/aims/runtime/logs", f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n测试报告已保存: {report_path}")

    return 0 if failed_tests == 0 else 1

if __name__ == "__main__":
    sys.exit(main())