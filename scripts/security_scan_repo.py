import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SENSITIVE_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'API Key (sk-*)'),
    (r'aims-secret-token-2026', 'Hardcoded Gateway Token'),
    (r'aims@2026', 'Hardcoded Password'),
    (r'password["\s:=]+["\'][^"$\{]{6,}["\']', 'Hardcoded Password'),
    (r'apiKey["\s:=]+["\'][^"$\{]{10,}["\']', 'Hardcoded API Key'),
    (r'appSecret["\s:=]+["\'][^"$\{]{10,}["\']', 'Hardcoded App Secret'),
    (r'botToken["\s:=]+["\'][^"$\{]{10,}["\']', 'Hardcoded Bot Token'),
]

SKIP_DIRS = {'.venv', 'node_modules', '.git', '__pycache__', '_secrets_backup', '.generated',
              'mysql-data', 'redis-data', 'milvus-data', 'qdrant-data', 'minio-data',
              'data', 'logs', 'runtime', 'refrence', 'tmp', '.pip', '.clawhub',
              '.gradle', '.plan', 'coverage', 'htmlcov', '.tox', '.mypy_cache', '.ruff_cache',
              '知识库', 'env', 'fixtures', 'dashboard'}
SKIP_EXTENSIONS = {'.pyc', '.pyo', '.db', '.png', '.jpg', '.ico', '.woff', '.woff2', '.ttf', '.eot',
                   '.txt', '.pdf', '.docx', '.xlsx'}
SKIP_FILES = {'pdf_extract_output.txt', 'docx_extract_output.txt', 'ref_extract_book.md', 'ref_extract_super.md',
              'sanitize_secrets.py', 'security_scan_repo.py'}


def scan_file(filepath):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return issues

    for pattern, desc in SENSITIVE_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            issues.append({
                'file': os.path.relpath(filepath, PROJECT_DIR),
                'line': line_num,
                'type': desc,
                'match': match.group()[:50],
            })

    return issues


def main():
    print("=" * 60)
    print("AIMS 安全扫描 — 检查敏感信息泄露")
    print("=" * 60)

    all_issues = []

    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SKIP_EXTENSIONS:
                continue
            if f in SKIP_FILES:
                continue

            filepath = os.path.join(root, f)
            issues = scan_file(filepath)
            all_issues.extend(issues)

    if all_issues:
        print(f"\n[WARNING] Found {len(all_issues)} potential sensitive info leaks:\n")
        for issue in all_issues:
            print(f"  [{issue['type']}] {issue['file']}:{issue['line']}")
            print(f"    Match: {issue['match']}")
        print(f"\nPlease fix the above issues before committing to Git!")
        sys.exit(1)
    else:
        print("\n[PASS] No sensitive info leaks found. Safe to commit!")
        sys.exit(0)


if __name__ == "__main__":
    main()
