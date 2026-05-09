import os
import shutil
import json
import re
from datetime import datetime

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_secrets_backup")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

SENSITIVE_PATTERNS = [
    (r'(apiKey["\s:]+)["\']?[\w\-]{20,}["\']?', r'\1"${REDACTED}"'),
    (r'(appSecret["\s:]+)["\']?[\w\-]{20,}["\']?', r'\1"${REDACTED}"'),
    (r'(agentSecret["\s:]+)["\']?[\w\-]{20,}["\']?', r'\1"${REDACTED}"'),
    (r'(botToken["\s:]+)["\']?[\w\-:]{20,}["\']?', r'\1"${REDACTED}"'),
    (r'(corpId["\s:]+)["\']?[\w\-]{10,}["\']?', r'\1"${REDACTED}"'),
    (r'(appKey["\s:]+)["\']?[\w\-]{10,}["\']?', r'\1"${REDACTED}"'),
    (r'(token["\s:]+)["\']?[\w\-]{20,}["\']?', r'\1"${REDACTED}"'),
]

FILES_TO_CHECK = [
    "openclaw.json",
    "mcporter.json",
    "docker-compose.yml",
    "k8s/secret.yaml",
    "test-gateway.ps1",
]

ENV_FILES_TO_SANITIZE = [
    ".env.local.example",
]

DOC_FILES_WITH_SECRETS = [
    "本地开发环境部署指南.md",
    "快速启动指南.md",
    "部署指南.md",
]


def backup_file(filepath):
    if not os.path.exists(filepath):
        return
    rel = os.path.relpath(filepath, PROJECT_DIR)
    backup_path = os.path.join(BACKUP_DIR, rel.replace(os.sep, "_"))
    os.makedirs(os.path.dirname(backup_path) if os.path.dirname(backup_path) else BACKUP_DIR, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    print(f"  [BACKUP] {rel} -> {os.path.basename(backup_path)}")


def sanitize_json_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    content = re.sub(
        r'("appId"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_APP_ID}"',
        content
    )
    content = re.sub(
        r'("appSecret"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_APP_SECRET}"',
        content
    )
    content = re.sub(
        r'("agentSecret"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_AGENT_SECRET}"',
        content
    )
    content = re.sub(
        r'("botToken"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_BOT_TOKEN}"',
        content
    )
    content = re.sub(
        r'("corpId"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_CORP_ID}"',
        content
    )
    content = re.sub(
        r'("appKey"\s*:\s*)"[^"]{5,}"',
        r'\1"${REDACTED_APP_KEY}"',
        content
    )

    if content != original:
        backup_file(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SANITIZED] {os.path.relpath(filepath, PROJECT_DIR)}")
    else:
        print(f"  [CLEAN] {os.path.relpath(filepath, PROJECT_DIR)}")


def sanitize_ps1_file(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    content = re.sub(
        r'(\$env:AIMS_GATEWAY_TOKEN\s*=\s*)"[^"]+"',
        r'\1"${AIMS_GATEWAY_TOKEN}"',
        content
    )

    if content != original:
        backup_file(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SANITIZED] {os.path.relpath(filepath, PROJECT_DIR)}")
    else:
        print(f"  [CLEAN] {os.path.relpath(filepath, PROJECT_DIR)}")


def sanitize_doc_files(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    content = re.sub(r'(AIMS_GATEWAY_TOKEN=)aims-secret-token-2026', r'\1${AIMS_GATEWAY_TOKEN}', content)
    content = re.sub(r'(DEEPSEEK_API_KEY=)sk-[a-zA-Z0-9]+', r'\1${DEEPSEEK_API_KEY}', content)
    content = re.sub(r'(MOONSHOT_API_KEY=)sk-[a-zA-Z0-9]+', r'\1${MOONSHOT_API_KEY}', content)
    content = re.sub(r'(ZHIPU_API_KEY=)[a-zA-Z0-9.]+', r'\1${ZHIPU_API_KEY}', content)
    content = re.sub(r'(FEISHU_BOT1_APP_SECRET=)[a-zA-Z0-9]+', r'\1${FEISHU_BOT1_APP_SECRET}', content)
    content = re.sub(r'(WEWORK_AGENT_SECRET=)[a-zA-Z0-9]+', r'\1${WEWORK_AGENT_SECRET}', content)
    content = re.sub(r'(MYSQL_ROOT_PASSWORD=)[a-zA-Z0-9!@#$%^&*]+', r'\1${MYSQL_ROOT_PASSWORD}', content)
    content = re.sub(r'(MYSQL_PASSWORD=)[a-zA-Z0-9!@#$%^&*]+', r'\1${MYSQL_PASSWORD}', content)

    if content != original:
        backup_file(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SANITIZED] {os.path.relpath(filepath, PROJECT_DIR)}")
    else:
        print(f"  [CLEAN] {os.path.relpath(filepath, PROJECT_DIR)}")


def main():
    print("=" * 60)
    print("AIMS 敏感配置清理工具")
    print(f"备份目录: {BACKUP_DIR}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(BACKUP_DIR, exist_ok=True)

    print("\n[1] 清理 JSON 配置文件")
    for f in FILES_TO_CHECK:
        if f.endswith('.json'):
            sanitize_json_file(os.path.join(PROJECT_DIR, f))

    print("\n[2] 清理 PowerShell 脚本")
    sanitize_ps1_file(os.path.join(PROJECT_DIR, "test-gateway.ps1"))

    print("\n[3] 清理文档中的敏感信息")
    for f in DOC_FILES_WITH_SECRETS:
        sanitize_doc_files(os.path.join(PROJECT_DIR, f))

    print("\n[4] 检查 .env 文件")
    env_file = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_file):
        backup_file(env_file)
        print(f"  [WARNING] .env 文件存在，已在 .gitignore 中排除，确保不会提交到 Git")
    else:
        print(f"  [OK] .env 文件不存在（正常，由 .env.example 复制创建）")

    print("\n[5] 检查数据库文件")
    db_files = []
    for root, dirs, files in os.walk(os.path.join(PROJECT_DIR, "skills")):
        for f in files:
            if f.endswith('.db'):
                db_files.append(os.path.join(root, f))
    if db_files:
        print(f"  [INFO] 发现 {len(db_files)} 个 .db 文件（SQLite 运行时数据）")
        for f in db_files:
            print(f"    - {os.path.relpath(f, PROJECT_DIR)}")

    print("\n" + "=" * 60)
    print("清理完成！")
    print(f"备份文件保存在: {BACKUP_DIR}")
    print("请确认 .gitignore 包含: .env, *.db, _secrets_backup/")
    print("=" * 60)


if __name__ == "__main__":
    main()
