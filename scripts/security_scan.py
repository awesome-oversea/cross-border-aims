#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
from datetime import datetime

PROJECT_DIR = "D:/Project/aims"

SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', "API Key泄露"),
    (r'(?:secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', "密码泄露"),
    (r'(?:token|access[_-]?token)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', "Token泄露"),
    (r'(?:credential|auth)\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', "凭证泄露"),
    (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API Key"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "私钥泄露"),
]

SENSITIVE_FILES = [
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", ".pem", ".key",
    "credentials.json", "service-account.json"
]

REQUIRED_ENV_VARS = [
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPU_API_KEY",
    "AIMS_GATEWAY_TOKEN",
    "MYSQL_ROOT_PASSWORD",
    "REDIS_PASSWORD",
]

SECURITY_CHECKS = {
    "gateway_auth": {"description": "Gateway认证模式", "expected": "token"},
    "dm_policy": {"description": "DM策略", "expected": "pairing"},
    "sandbox_mode": {"description": "沙箱模式", "expected": "non-main"},
    "env_gitignore": {"description": ".env在.gitignore中", "expected": True},
    "no_hardcoded_secrets": {"description": "无硬编码密钥", "expected": True},
}

def scan_secrets(directory):
    findings = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules", "venv", ".venv"]]
        for filename in files:
            if filename.endswith((".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".md")):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    for pattern, desc in SECRET_PATTERNS:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            rel_path = os.path.relpath(filepath, directory)
                            findings.append({
                                "file": rel_path,
                                "type": desc,
                                "count": len(matches),
                                "severity": "high"
                            })
                except Exception:
                    pass
    return findings

def check_sensitive_files(directory):
    findings = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv"]]
        for filename in files:
            if filename in SENSITIVE_FILES:
                rel_path = os.path.relpath(os.path.join(root, filename), directory)
                findings.append({
                    "file": rel_path,
                    "type": "敏感文件",
                    "severity": "critical"
                })
    return findings

def check_gitignore(directory):
    gitignore_path = os.path.join(directory, ".gitignore")
    if not os.path.exists(gitignore_path):
        return {"check": "env_gitignore", "passed": False, "message": ".gitignore不存在"}

    with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if ".env" in content:
        return {"check": "env_gitignore", "passed": True, "message": ".env已在.gitignore中"}
    else:
        return {"check": "env_gitignore", "passed": False, "message": ".env未在.gitignore中"}

def check_openclaw_security(directory):
    config_path = os.path.join(directory, "openclaw.json")
    if not os.path.exists(config_path):
        return {"check": "openclaw_config", "passed": False, "message": "openclaw.json不存在"}

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    results = []

    auth_mode = config.get("gateway", {}).get("auth", {}).get("mode", "")
    results.append({
        "check": "gateway_auth",
        "passed": auth_mode == "token",
        "message": f"Gateway认证模式: {auth_mode} {'(合规)' if auth_mode == 'token' else '(不合规，应为token)'}"
    })

    channels = config.get("channels", {})
    dm_issues = []
    for channel_name, channel_config in channels.items():
        dm_policy = channel_config.get("dmPolicy", "")
        if dm_policy != "pairing":
            dm_issues.append(f"{channel_name}: {dm_policy}")

    results.append({
        "check": "dm_policy",
        "passed": len(dm_issues) == 0,
        "message": f"DM策略: {'全部合规' if not dm_issues else ', '.join(dm_issues)}"
    })

    sandbox_mode = config.get("agents", {}).get("defaults", {}).get("sandbox", {}).get("mode", "")
    results.append({
        "check": "sandbox_mode",
        "passed": sandbox_mode in ["non-main", "full"],
        "message": f"沙箱模式: {sandbox_mode}"
    })

    return results

def generate_security_report(directory):
    print("=" * 60)
    print("AIMS 安全扫描报告")
    print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"扫描目录: {directory}")
    print("=" * 60)

    all_findings = []
    all_checks = []

    print("\n[1] 密钥泄露扫描...")
    secret_findings = scan_secrets(directory)
    all_findings.extend(secret_findings)
    if secret_findings:
        print(f"  发现 {len(secret_findings)} 处潜在密钥泄露:")
        for f in secret_findings:
            print(f"    - {f['file']}: {f['type']} ({f['count']}处)")
    else:
        print("  未发现密钥泄露")

    print("\n[2] 敏感文件检查...")
    sensitive_findings = check_sensitive_files(directory)
    all_findings.extend(sensitive_findings)
    if sensitive_findings:
        print(f"  发现 {len(sensitive_findings)} 个敏感文件:")
        for f in sensitive_findings:
            print(f"    - {f['file']} ({f['type']})")
    else:
        print("  未发现敏感文件")

    print("\n[3] .gitignore检查...")
    gitignore_result = check_gitignore(directory)
    all_checks.append(gitignore_result)
    print(f"  {'PASS' if gitignore_result['passed'] else 'FAIL'}: {gitignore_result['message']}")

    print("\n[4] OpenClaw安全配置检查...")
    openclaw_results = check_openclaw_security(directory)
    if isinstance(openclaw_results, list):
        all_checks.extend(openclaw_results)
    else:
        all_checks.append(openclaw_results)
    for r in openclaw_results if isinstance(openclaw_results, list) else [openclaw_results]:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}: {r['message']}")

    critical_count = len([f for f in all_findings if f.get("severity") == "critical"])
    high_count = len([f for f in all_findings if f.get("severity") == "high"])
    failed_checks = len([c for c in all_checks if not c.get("passed", True)])

    print("\n" + "=" * 60)
    print("安全扫描总结")
    print("=" * 60)
    print(f"  严重问题: {critical_count}")
    print(f"  高危问题: {high_count}")
    print(f"  配置检查失败: {failed_checks}")
    print(f"  总体状态: {'SECURE' if critical_count == 0 and failed_checks == 0 else 'NEEDS ATTENTION'}")

    report = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directory": directory,
        "findings": all_findings,
        "checks": all_checks,
        "summary": {
            "critical": critical_count,
            "high": high_count,
            "failed_checks": failed_checks,
            "status": "secure" if critical_count == 0 and failed_checks == 0 else "needs_attention"
        }
    }

    report_path = os.path.join(directory, "runtime/logs", f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n安全报告已保存: {report_path}")

    return 0 if critical_count == 0 and failed_checks == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(generate_security_report(PROJECT_DIR))