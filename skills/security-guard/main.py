import json
import os
import re
import sqlite3
import sys
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "security.db")

SENSITIVE_WORDS = {
    "politics": ["政治敏感词1", "政治敏感词2"],
    "violence": ["暴力", "凶杀", "恐怖袭击"],
    "pornography": ["色情", "裸体"],
    "gambling": ["赌博", "博彩", "下注"],
    "fraud": ["诈骗", "传销", "非法集资"],
    "drug": ["毒品", "大麻", "海洛因"],
    "discrimination": ["种族歧视", "性别歧视"],
}

PLATFORM_RULES = {
    "taobao": {
        "name": "淘宝/天猫",
        "max_title_length": 60,
        "max_desc_length": 500,
        "forbidden_words": ["最", "第一", "国家级", "世界级", "最佳", "最优", "顶级", "极品", "绝对"],
        "required_fields": ["title", "price", "images"],
        "image_rules": {"min_count": 5, "max_size_mb": 5, "formats": ["jpg", "png", "webp"]},
    },
    "jd": {
        "name": "京东",
        "max_title_length": 45,
        "max_desc_length": 500,
        "forbidden_words": ["最", "第一", "国家级", "世界级", "最佳", "顶级", "唯一"],
        "required_fields": ["title", "price", "images", "brand"],
        "image_rules": {"min_count": 6, "max_size_mb": 5, "formats": ["jpg", "png"]},
    },
    "pdd": {
        "name": "拼多多",
        "max_title_length": 60,
        "max_desc_length": 500,
        "forbidden_words": ["最", "第一", "国家级", "最佳", "顶级", "极品"],
        "required_fields": ["title", "price", "images"],
        "image_rules": {"min_count": 3, "max_size_mb": 5, "formats": ["jpg", "png", "webp"]},
    },
    "xhs": {
        "name": "小红书",
        "max_title_length": 20,
        "max_desc_length": 1000,
        "forbidden_words": ["最", "第一", "国家级", "微信", "加我", "私聊", "转账", "购买链接"],
        "required_fields": ["title", "content", "images"],
        "image_rules": {"min_count": 3, "max_size_mb": 20, "formats": ["jpg", "png", "webp"]},
    },
    "douyin": {
        "name": "抖音",
        "max_title_length": 30,
        "max_desc_length": 300,
        "forbidden_words": ["最", "第一", "国家级", "微信", "加我", "私聊", "转账"],
        "required_fields": ["title", "video"],
        "image_rules": {"min_count": 1, "max_size_mb": 50, "formats": ["jpg", "png"]},
    },
}

INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
    r"(?i)forget\s+(everything|all|previous)",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)pretend\s+(to\s+be|you\s+are)",
    r"(?i)system\s*:\s*",
    r"(?i)jailbreak",
    r"(?i)dan\s+mode",
    r"(?i)developer\s+mode",
    r"(?i)override\s+(safety|security|rules)",
    r"(?i)bypass\s+(filter|check|restriction)",
    r"(?i)reveal\s+(your|the)\s+(prompt|instructions|system)",
    r"(?i)output\s+your\s+(instructions|prompt|rules)",
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS security_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_type TEXT NOT NULL,
        input_text TEXT,
        result TEXT,
        risk_level TEXT DEFAULT 'low',
        details TEXT,
        checked_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS credential_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        credential_key TEXT UNIQUE NOT NULL,
        credential_hash TEXT NOT NULL,
        credential_type TEXT DEFAULT 'api_key',
        description TEXT,
        rotation_days INTEGER DEFAULT 90,
        last_rotated TEXT,
        expires_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS access_control (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        resource TEXT NOT NULL,
        action TEXT NOT NULL,
        allowed INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT NOT NULL,
        endpoint TEXT,
        request_count INTEGER DEFAULT 0,
        window_start TEXT,
        window_seconds INTEGER DEFAULT 60,
        max_requests INTEGER DEFAULT 100,
        UNIQUE(identifier, endpoint)
    )""")
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class ContentModerator:
    def __init__(self):
        self.sensitive_words = SENSITIVE_WORDS
        self.platform_rules = PLATFORM_RULES

    def check_sensitive_words(self, text: str) -> Dict:
        if not text:
            return {"safe": True, "found": [], "categories": [], "risk_level": "low"}

        found = []
        categories = set()

        for category, words in self.sensitive_words.items():
            for word in words:
                if word in text:
                    found.append({"word": word, "category": category})
                    categories.add(category)

        risk_level = "low"
        if len(found) > 0:
            if any(c in ["politics", "violence", "drug"] for c in categories):
                risk_level = "high"
            elif any(c in ["pornography", "fraud"] for c in categories):
                risk_level = "high"
            else:
                risk_level = "medium"

        return {
            "safe": len(found) == 0,
            "found": found,
            "categories": list(categories),
            "risk_level": risk_level,
            "total_matches": len(found),
        }

    def check_platform_compliance(self, content: Dict, platform: str) -> Dict:
        rules = self.platform_rules.get(platform)
        if not rules:
            return {"compliant": True, "platform": platform, "message": "平台规则未配置，默认通过"}

        violations = []

        title = content.get("title", "")
        if len(title) > rules["max_title_length"]:
            violations.append({
                "field": "title",
                "issue": f"标题超长: {len(title)}>{rules['max_title_length']}",
                "severity": "medium",
            })

        desc = content.get("description", content.get("content", ""))
        if desc and len(desc) > rules["max_desc_length"]:
            violations.append({
                "field": "description",
                "issue": f"描述超长: {len(desc)}>{rules['max_desc_length']}",
                "severity": "medium",
            })

        for word in rules["forbidden_words"]:
            if word in title or word in desc:
                violations.append({
                    "field": "content",
                    "issue": f"包含违禁词: {word}",
                    "severity": "high",
                })

        for field in rules["required_fields"]:
            if field not in content or not content[field]:
                violations.append({
                    "field": field,
                    "issue": f"缺少必填字段: {field}",
                    "severity": "medium",
                })

        images = content.get("images", [])
        if isinstance(images, list):
            img_rules = rules.get("image_rules", {})
            if len(images) < img_rules.get("min_count", 0):
                violations.append({
                    "field": "images",
                    "issue": f"图片数量不足: {len(images)}<{img_rules.get('min_count', 0)}",
                    "severity": "low",
                })

        return {
            "compliant": len(violations) == 0,
            "platform": platform,
            "platform_name": rules["name"],
            "violations": violations,
            "violation_count": len(violations),
            "high_severity_count": sum(1 for v in violations if v["severity"] == "high"),
        }

    def check_content(self, text: str, platform: str = None, content: Dict = None) -> Dict:
        sensitive_result = self.check_sensitive_words(text)

        platform_result = None
        if platform and content:
            platform_result = self.check_platform_compliance(content, platform)

        overall_safe = sensitive_result["safe"]
        if platform_result and not platform_result["compliant"]:
            overall_safe = False

        risk_level = sensitive_result["risk_level"]
        if platform_result and platform_result["high_severity_count"] > 0:
            risk_level = "high"

        recommendation = "内容安全，可以发布"
        if not overall_safe:
            if risk_level == "high":
                recommendation = "内容存在高风险问题，禁止发布，需人工审核"
            elif risk_level == "medium":
                recommendation = "内容存在中风险问题，建议修改后发布"
            else:
                recommendation = "内容存在低风险问题，可以发布但建议优化"

        result = {
            "safe": overall_safe,
            "risk_level": risk_level,
            "sensitive_check": sensitive_result,
            "platform_check": platform_result,
            "recommendation": recommendation,
        }

        self._log_audit("content_check", text[:200], result, risk_level)

        return result

    def _log_audit(self, check_type: str, input_text: str, result: Dict, risk_level: str):
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT INTO security_audit_logs (check_type, input_text, result, risk_level, details, checked_at) VALUES (?, ?, ?, ?, ?, ?)",
                (check_type, input_text, json.dumps(result, ensure_ascii=False, default=str)[:500], risk_level, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


class PromptInjectionDetector:
    def __init__(self):
        self.patterns = INJECTION_PATTERNS

    def detect(self, text: str) -> Dict:
        if not text:
            return {"safe": True, "matches": [], "risk_level": "low"}

        matches = []
        for pattern in self.patterns:
            found = re.findall(pattern, text)
            if found:
                matches.append({"pattern": pattern, "matches": found})

        risk_level = "low"
        if len(matches) >= 3:
            risk_level = "high"
        elif len(matches) >= 1:
            risk_level = "medium"

        result = {
            "safe": len(matches) == 0,
            "matches": matches,
            "match_count": len(matches),
            "risk_level": risk_level,
            "recommendation": "输入安全" if len(matches) == 0 else "检测到潜在注入攻击，建议拒绝或清洗输入",
        }

        self._log_audit("injection_check", text[:200], result, risk_level)

        return result

    def sanitize(self, text: str) -> Dict:
        detection = self.detect(text)
        sanitized = text

        if not detection["safe"]:
            for match_info in detection["matches"]:
                for match_text in match_info["matches"]:
                    if isinstance(match_text, tuple):
                        match_text = match_text[0] if match_text else ""
                    if isinstance(match_text, str) and match_text:
                        sanitized = sanitized.replace(match_text, "[FILTERED]")

        return {
            "original_safe": detection["safe"],
            "sanitized_text": sanitized,
            "removed_count": sum(len(m["matches"]) for m in detection["matches"]),
            "risk_level": detection["risk_level"],
        }

    def _log_audit(self, check_type: str, input_text: str, result: Dict, risk_level: str):
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute(
                "INSERT INTO security_audit_logs (check_type, input_text, result, risk_level, details, checked_at) VALUES (?, ?, ?, ?, ?, ?)",
                (check_type, input_text, json.dumps(result, ensure_ascii=False, default=str)[:500], risk_level, "", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


class CredentialManager:
    def __init__(self):
        self._secret_key = os.environ.get("AIMS_SECRET_KEY", "aims-default-secret-key-change-in-production")

    def store_credential(self, key: str, value: str, description: str = "", credential_type: str = "api_key", rotation_days: int = 90) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        value_hash = hashlib.sha256(value.encode()).hexdigest()
        encrypted = self._encrypt(value)

        try:
            c.execute(
                "INSERT INTO credential_store (credential_key, credential_hash, credential_type, description, rotation_days, last_rotated, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (key, value_hash, credential_type, description, rotation_days, now, (datetime.now() + __import__("datetime").timedelta(days=rotation_days)).strftime("%Y-%m-%d %H:%M:%S"), now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "key": key, "stored": True}
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE credential_store SET credential_hash=?, rotation_days=?, last_rotated=?, expires_at=?, updated_at=? WHERE credential_key=?",
                (value_hash, rotation_days, now, (datetime.now() + __import__("datetime").timedelta(days=rotation_days)).strftime("%Y-%m-%d %H:%M:%S"), now, key),
            )
            conn.commit()
            conn.close()
            return {"success": True, "key": key, "rotated": True}

    def verify_credential(self, key: str, value: str) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT credential_hash, expires_at FROM credential_store WHERE credential_key=?", (key,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"valid": False, "error": "凭证不存在"}

        value_hash = hashlib.sha256(value.encode()).hexdigest()
        if value_hash != row["credential_hash"]:
            return {"valid": False, "error": "凭证不匹配"}

        if row["expires_at"]:
            expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expires:
                return {"valid": False, "error": "凭证已过期", "expired_at": row["expires_at"]}

        return {"valid": True}

    def list_credentials(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT credential_key, credential_type, description, rotation_days, last_rotated, expires_at FROM credential_store")
        creds = [dict(row) for row in c.fetchall()]
        conn.close()

        now = datetime.now()
        for cred in creds:
            if cred["expires_at"]:
                expires = datetime.strptime(cred["expires_at"], "%Y-%m-%d %H:%M:%S")
                cred["days_until_expiry"] = (expires - now).days
                cred["status"] = "expired" if expires < now else "active"
            else:
                cred["status"] = "active"

        return {"success": True, "credentials": creds, "total": len(creds)}

    def delete_credential(self, key: str) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM credential_store WHERE credential_key=?", (key,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "key": key, "deleted": affected > 0}

    def _encrypt(self, value: str) -> str:
        return hashlib.sha256((value + self._secret_key).encode()).hexdigest()


class RateLimiter:
    def __init__(self):
        pass

    def check_rate(self, identifier: str, endpoint: str = "default", max_requests: int = 100, window_seconds: int = 60) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now()

        c.execute("SELECT * FROM rate_limits WHERE identifier=? AND endpoint=?", (identifier, endpoint))
        row = c.fetchone()

        if row:
            window_start = datetime.strptime(row["window_start"], "%Y-%m-%d %H:%M:%S")
            elapsed = (now - window_start).total_seconds()

            if elapsed > row["window_seconds"]:
                c.execute(
                    "UPDATE rate_limits SET request_count=1, window_start=?, max_requests=?, window_seconds=? WHERE identifier=? AND endpoint=?",
                    (now.strftime("%Y-%m-%d %H:%M:%S"), max_requests, window_seconds, identifier, endpoint),
                )
                conn.commit()
                conn.close()
                return {"allowed": True, "remaining": max_requests - 1, "reset_at": (now + timedelta(seconds=window_seconds)).strftime("%Y-%m-%d %H:%M:%S")}
            else:
                new_count = row["request_count"] + 1
                if new_count > row["max_requests"]:
                    conn.commit()
                    conn.close()
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "retry_after": int(window_seconds - elapsed),
                        "limit": row["max_requests"],
                        "current": new_count,
                    }
                c.execute("UPDATE rate_limits SET request_count=? WHERE identifier=? AND endpoint=?", (new_count, identifier, endpoint))
                conn.commit()
                conn.close()
                return {"allowed": True, "remaining": row["max_requests"] - new_count, "reset_at": (window_start + timedelta(seconds=row["window_seconds"])).strftime("%Y-%m-%d %H:%M:%S")}
        else:
            c.execute(
                "INSERT INTO rate_limits (identifier, endpoint, request_count, window_start, window_seconds, max_requests) VALUES (?, ?, 1, ?, ?, ?)",
                (identifier, endpoint, now.strftime("%Y-%m-%d %H:%M:%S"), window_seconds, max_requests),
            )
            conn.commit()
            conn.close()
            return {"allowed": True, "remaining": max_requests - 1, "reset_at": (now + timedelta(seconds=window_seconds)).strftime("%Y-%m-%d %H:%M:%S")}


class SecurityGuard:
    def __init__(self):
        init_db()
        self.content_moderator = ContentModerator()
        self.injection_detector = PromptInjectionDetector()
        self.credential_manager = CredentialManager()
        self.rate_limiter = RateLimiter()

    def full_check(self, text: str, platform: str = None, content: Dict = None, identifier: str = "default") -> Dict:
        content_result = self.content_moderator.check_content(text, platform, content)
        injection_result = self.injection_detector.detect(text)
        rate_result = self.rate_limiter.check_rate(identifier, "full_check")

        overall_safe = content_result["safe"] and injection_result["safe"] and rate_result["allowed"]

        risk_level = "low"
        if content_result["risk_level"] == "high" or injection_result["risk_level"] == "high":
            risk_level = "high"
        elif content_result["risk_level"] == "medium" or injection_result["risk_level"] == "medium":
            risk_level = "medium"

        return {
            "safe": overall_safe,
            "risk_level": risk_level,
            "content_check": content_result,
            "injection_check": injection_result,
            "rate_check": rate_result,
            "recommendation": content_result["recommendation"] if not content_result["safe"] else injection_result["recommendation"],
        }

    def get_audit_logs(self, limit: int = 50) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM security_audit_logs ORDER BY checked_at DESC LIMIT ?", (limit,))
        logs = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"success": True, "logs": logs, "total": len(logs)}

    def get_security_stats(self) -> Dict:
        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) as total FROM security_audit_logs")
        total_checks = c.fetchone()["total"]

        c.execute("SELECT risk_level, COUNT(*) as count FROM security_audit_logs GROUP BY risk_level")
        risk_distribution = {row["risk_level"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT check_type, COUNT(*) as count FROM security_audit_logs GROUP BY check_type")
        check_types = {row["check_type"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT COUNT(*) as total FROM credential_store")
        total_creds = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as total FROM credential_store WHERE expires_at < ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        expired_creds = c.fetchone()["total"]

        conn.close()

        return {
            "success": True,
            "total_checks": total_checks,
            "risk_distribution": risk_distribution,
            "check_types": check_types,
            "total_credentials": total_creds,
            "expired_credentials": expired_creds,
        }


def main():
    input_data = json.loads(sys.stdin.read())
    action = input_data.get("action", "full_check")
    guard = SecurityGuard()

    if action == "full_check":
        result = guard.full_check(
            input_data.get("text", ""),
            input_data.get("platform"),
            input_data.get("content"),
            input_data.get("identifier", "default"),
        )
    elif action == "content_check":
        result = guard.content_moderator.check_content(
            input_data.get("text", ""),
            input_data.get("platform"),
            input_data.get("content"),
        )
    elif action == "sensitive_check":
        result = guard.content_moderator.check_sensitive_words(input_data.get("text", ""))
    elif action == "platform_check":
        result = guard.content_moderator.check_platform_compliance(
            input_data.get("content", {}),
            input_data.get("platform", ""),
        )
    elif action == "injection_check":
        result = guard.injection_detector.detect(input_data.get("text", ""))
    elif action == "injection_sanitize":
        result = guard.injection_detector.sanitize(input_data.get("text", ""))
    elif action == "store_credential":
        result = guard.credential_manager.store_credential(
            input_data.get("key", ""),
            input_data.get("value", ""),
            input_data.get("description", ""),
            input_data.get("type", "api_key"),
            input_data.get("rotation_days", 90),
        )
    elif action == "verify_credential":
        result = guard.credential_manager.verify_credential(
            input_data.get("key", ""),
            input_data.get("value", ""),
        )
    elif action == "list_credentials":
        result = guard.credential_manager.list_credentials()
    elif action == "delete_credential":
        result = guard.credential_manager.delete_credential(input_data.get("key", ""))
    elif action == "rate_check":
        result = guard.rate_limiter.check_rate(
            input_data.get("identifier", ""),
            input_data.get("endpoint", "default"),
            input_data.get("max_requests", 100),
            input_data.get("window_seconds", 60),
        )
    elif action == "audit_logs":
        result = guard.get_audit_logs(input_data.get("limit", 50))
    elif action == "stats":
        result = guard.get_security_stats()
    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
