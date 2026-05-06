#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import subprocess
import sys
from datetime import datetime

PROJECT_DIR = "D:/Project/aims"
SKILLS_DIR = os.path.join(PROJECT_DIR, "skills")

PERFORMANCE_TARGETS = {
    "listing_gen_time_ms": 30000,
    "ad_optimize_time_ms": 15000,
    "review_analysis_time_ms": 10000,
    "order_query_time_ms": 3000,
    "logistics_track_time_ms": 3000,
    "intent_recognition_time_ms": 2000,
    "sentiment_analysis_time_ms": 2000,
    "confidence_gate_time_ms": 1000,
    "recommend_time_ms": 5000,
    "rag_retrieval_time_ms": 5000,
    "report_gen_time_ms": 10000,
}

def benchmark_skill(skill_name, input_data, iterations=3):
    skill_path = os.path.join(SKILLS_DIR, skill_name, "main.py")
    if not os.path.exists(skill_path):
        return {"skill": skill_name, "error": "文件不存在", "avg_ms": 0}

    times = []
    for i in range(iterations):
        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, skill_path],
                input=json.dumps(input_data, ensure_ascii=False).encode("utf-8"),
                capture_output=True,
                text=False,
                timeout=60
            )
            elapsed = (time.time() - start) * 1000

            if result.returncode == 0:
                times.append(elapsed)
            else:
                return {"skill": skill_name, "error": result.stderr.decode("utf-8", errors="replace")[:100], "avg_ms": 0}
        except subprocess.TimeoutExpired:
            return {"skill": skill_name, "error": "执行超时", "avg_ms": 60000}
        except Exception as e:
            return {"skill": skill_name, "error": str(e)[:100], "avg_ms": 0}

    avg_ms = sum(times) / len(times) if times else 0
    min_ms = min(times) if times else 0
    max_ms = max(times) if times else 0

    return {
        "skill": skill_name,
        "avg_ms": round(avg_ms, 2),
        "min_ms": round(min_ms, 2),
        "max_ms": round(max_ms, 2),
        "iterations": iterations,
        "times": [round(t, 2) for t in times]
    }

def analyze_skill_complexity(skill_name):
    skill_path = os.path.join(SKILLS_DIR, skill_name, "main.py")
    if not os.path.exists(skill_path):
        return {"skill": skill_name, "lines": 0, "functions": 0, "imports": 0}

    with open(skill_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = len(content.split("\n"))
    functions = len([l for l in content.split("\n") if l.strip().startswith("def ")])
    imports = len([l for l in content.split("\n") if l.strip().startswith("import ") or l.strip().startswith("from ")])
    code_lines = len([l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")])
    comment_lines = len([l for l in content.split("\n") if l.strip().startswith("#")])

    return {
        "skill": skill_name,
        "total_lines": lines,
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "functions": functions,
        "imports": imports,
        "complexity_score": round(functions * 2 + imports + code_lines / 50, 1)
    }

def check_skill_optimization(skill_name):
    skill_path = os.path.join(SKILLS_DIR, skill_name, "main.py")
    if not os.path.exists(skill_path):
        return []

    with open(skill_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    suggestions = []

    if "import json" in content and content.count("json.dumps") > 3:
        suggestions.append({"type": "performance", "message": "频繁调用json.dumps，考虑缓存序列化结果"})

    if content.count("for ") > 5 and "list(" not in content:
        suggestions.append({"type": "performance", "message": "多层循环未使用列表推导式，可优化性能"})

    if "time.sleep" in content:
        suggestions.append({"type": "performance", "message": "使用time.sleep阻塞，考虑异步处理"})

    if len(content) > 500 and "class " not in content:
        suggestions.append({"type": "maintainability", "message": "代码较长但未使用类封装，建议重构"})

    if "except:" in content or "except Exception" in content:
        suggestions.append({"type": "reliability", "message": "使用宽泛异常捕获，建议指定具体异常类型"})

    if "print(" in content and '__main__' not in content:
        suggestions.append({"type": "quality", "message": "使用print输出调试信息，建议使用logging模块"})

    if not suggestions:
        suggestions.append({"type": "info", "message": "代码质量良好，无需优化"})

    return suggestions

def generate_performance_report():
    print("=" * 60)
    print("AIMS 性能优化报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    benchmark_tests = [
        ("listing-gen", {"product_name": "智能手表", "category": "智能穿戴", "platform": "taobao"}),
        ("ad-optimizer", {"campaign_id": "CAMP001", "budget": 1000, "target_roas": 3.0}),
        ("order-query", {"order_id": "ORD1234567890"}),
        ("logistics-track", {"tracking_number": "SF1234567890"}),
        ("intent-recognition", {"user_message": "我想查一下订单", "history": []}),
        ("sentiment-analysis", {"user_message": "非常满意", "history": [], "context": {}}),
        ("confidence-gate", {"intent_result": {"intent": "order_query", "confidence": 0.85}, "sentiment_result": {"sentiment": "neutral", "sentiment_score": 0.0, "intensity": "low", "require_human": False}, "rag_result": {"hit": True, "confidence": 0.75}, "context": {}}),
        ("smart-recommend", {"recommendation_type": "popular", "limit": 6}),
        ("report-gen", {"report_type": "daily"}),
    ]

    print("\n[1] 技能性能基准测试")
    print("-" * 40)
    benchmark_results = []
    for skill_name, input_data in benchmark_tests:
        result = benchmark_skill(skill_name, input_data)
        benchmark_results.append(result)
        if "error" in result and result.get("avg_ms", 0) == 0:
            print(f"  {skill_name}: ERROR - {result.get('error', '')[:50]}")
        else:
            print(f"  {skill_name}: {result['avg_ms']}ms (min:{result['min_ms']}ms, max:{result['max_ms']}ms)")

    print("\n[2] 技能代码复杂度分析")
    print("-" * 40)
    complexity_results = []
    skill_dirs = [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d)) and os.path.exists(os.path.join(SKILLS_DIR, d, "main.py"))]
    for skill_name in sorted(skill_dirs):
        complexity = analyze_skill_complexity(skill_name)
        complexity_results.append(complexity)
        print(f"  {skill_name}: {complexity['total_lines']}行, {complexity['functions']}函数, 复杂度{complexity['complexity_score']}")

    print("\n[3] 优化建议")
    print("-" * 40)
    optimization_results = {}
    for skill_name in sorted(skill_dirs):
        suggestions = check_skill_optimization(skill_name)
        optimization_results[skill_name] = suggestions
        if any(s["type"] != "info" for s in suggestions):
            print(f"  {skill_name}:")
            for s in suggestions:
                if s["type"] != "info":
                    print(f"    [{s['type']}] {s['message']}")

    print("\n" + "=" * 60)
    print("性能优化总结")
    print("=" * 60)

    avg_response_time = sum(r["avg_ms"] for r in benchmark_results if r.get("avg_ms", 0) > 0) / max(1, len([r for r in benchmark_results if r.get("avg_ms", 0) > 0]))
    total_lines = sum(c["total_lines"] for c in complexity_results)
    total_functions = sum(c["functions"] for c in complexity_results)

    print(f"  平均响应时间: {avg_response_time:.1f}ms")
    f"  总代码行数: {total_lines}"
    print(f"  总函数数: {total_functions}")
    print(f"  技能总数: {len(skill_dirs)}")
    print(f"  需优化技能: {len([k for k, v in optimization_results.items() if any(s['type'] != 'info' for s in v)])}")

    report = {
        "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": benchmark_results,
        "complexity": complexity_results,
        "optimizations": optimization_results,
        "summary": {
            "avg_response_time_ms": round(avg_response_time, 2),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "skill_count": len(skill_dirs),
            "needs_optimization": len([k for k, v in optimization_results.items() if any(s["type"] != "info" for s in v)])
        }
    }

    report_path = os.path.join(PROJECT_DIR, "runtime/logs", f"perf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n性能报告已保存: {report_path}")

    return 0

if __name__ == "__main__":
    sys.exit(generate_performance_report())