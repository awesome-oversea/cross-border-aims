import json
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def uprint(text):
    """安全打印：处理Windows终端UTF-8编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + '\n').encode('utf-8'))


def run_skill(skill_path, test_data, label):
    """运行单个技能测试：传入JSON数据到技能CLI，检查返回码并解析输出"""

    uprint(f"=== Testing {label} ===")
    result = subprocess.run(
        [sys.executable, skill_path],
        input=json.dumps(test_data, ensure_ascii=False).encode('utf-8'),
        capture_output=True,
        text=False
    )
    uprint(f"  Exit code: {result.returncode}")
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
    if stdout:
        try:
            output = json.loads(stdout)
            summary = json.dumps(output, ensure_ascii=False, indent=2)[:300]
            uprint(f"  Output: {summary}")
        except json.JSONDecodeError:
            uprint(f"  Raw: {stdout[:200]}")
    if stderr:
        uprint(f"  Stderr: {stderr[:200]}")
    return result.returncode == 0


def test_cross_drain():
    ok1 = run_skill("D:/Project/aims/skills/cross-drain/main.py",
                    {"action": "generate_strategy", "platform": "xiaohongshu", "content_type": "product"},
                    "cross-drain generate_strategy")
    ok2 = run_skill("D:/Project/aims/skills/cross-drain/main.py",
                    {"action": "cross_platform_strategy", "platforms": ["xiaohongshu", "douyin"], "content_type": "product"},
                    "cross-drain cross_platform")
    return ok1 and ok2


def test_rag_retrieval():
    ok1 = run_skill("D:/Project/aims/skills/rag-retrieval/main.py",
                    {"action": "stats"},
                    "rag-retrieval stats")
    ok2 = run_skill("D:/Project/aims/skills/rag-retrieval/main.py",
                    {"action": "retrieve", "query": "ACOS optimization", "top_k": 3},
                    "rag-retrieval retrieve")
    return ok1 and ok2


if __name__ == "__main__":
    ok = True
    ok &= test_cross_drain()
    ok &= test_rag_retrieval()
    uprint(f"\n=== Overall: {'ALL PASSED' if ok else 'SOME FAILED'} ===")
    sys.exit(0 if ok else 1)
