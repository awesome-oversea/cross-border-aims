import json
import subprocess
import sys

def test_cross_drain():
    print("=== 测试 cross-drain 技能 ===")
    
    test_data = {
        "action": "generate_strategy",
        "platform": "xiaohongshu",
        "content_type": "product"
    }
    
    result = subprocess.run(
        [sys.executable, "D:/Project/aims/skills/cross-drain/main.py"],
        input=json.dumps(test_data, ensure_ascii=False),
        encoding='utf-8',
        capture_output=True
    )
    
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        try:
            output = json.loads(result.stdout)
            print("输出结果:")
            print(json.dumps(output, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(f"输出: {result.stdout}")
    if result.stderr:
        print(f"错误: {result.stderr}")
    
    print("\n=== 测试跨平台策略 ===")
    test_data2 = {
        "action": "cross_platform_strategy",
        "platforms": ["xiaohongshu", "douyin", "video-channel"],
        "content_type": "product"
    }
    
    result2 = subprocess.run(
        [sys.executable, "D:/Project/aims/skills/cross-drain/main.py"],
        input=json.dumps(test_data2, ensure_ascii=False),
        encoding='utf-8',
        capture_output=True
    )
    
    print(f"Exit code: {result2.returncode}")
    if result2.stdout:
        try:
            output = json.loads(result2.stdout)
            print("输出结果:")
            print(json.dumps(output, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(f"输出: {result2.stdout}")
    if result2.stderr:
        print(f"错误: {result2.stderr}")

def test_rag_retrieval():
    print("\n=== 测试 rag-retrieval 技能 ===")
    
    test_data = {
        "action": "stats"
    }
    
    result = subprocess.run(
        [sys.executable, "D:/Project/aims/skills/rag-retrieval/main.py"],
        input=json.dumps(test_data, ensure_ascii=False),
        encoding='utf-8',
        capture_output=True
    )
    
    print(f"Exit code: {result.returncode}")
    if result.stdout:
        try:
            output = json.loads(result.stdout)
            print("输出结果:")
            print(json.dumps(output, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(f"输出: {result.stdout}")
    if result.stderr:
        print(f"错误: {result.stderr}")
    
    print("\n=== 测试检索功能 ===")
    test_data2 = {
        "action": "retrieve",
        "query": "亚马逊广告ACOS优化策略",
        "top_k": 3
    }
    
    result2 = subprocess.run(
        [sys.executable, "D:/Project/aims/skills/rag-retrieval/main.py"],
        input=json.dumps(test_data2, ensure_ascii=False),
        encoding='utf-8',
        capture_output=True
    )
    
    print(f"Exit code: {result2.returncode}")
    if result2.stdout:
        try:
            output = json.loads(result2.stdout)
            print("输出结果:")
            print(json.dumps(output, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(f"输出: {result2.stdout}")
    if result2.stderr:
        print(f"错误: {result2.stderr}")

if __name__ == "__main__":
    test_cross_drain()
    test_rag_retrieval()