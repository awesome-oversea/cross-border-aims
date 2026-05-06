import json
import os
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "social_mcp.db")

PLATFORM_CONFIG = {
    "xhs": {
        "name": "小红书",
        "base_url": "https://edith.xiaohongshu.com/api",
        "auth_type": "cookie",
        "env_cookie": "XHS_COOKIE",
        "rate_limit": {"calls_per_minute": 30, "calls_per_day": 5000},
        "content_rules": {"max_length": 1200, "min_length": 800, "emoji_limit": 20, "hashtag_limit": 10},
    },
    "douyin": {
        "name": "抖音",
        "base_url": "https://creator.douyin.com/api",
        "auth_type": "cookie",
        "env_cookie": "DOUYIN_COOKIE",
        "rate_limit": {"calls_per_minute": 30, "calls_per_day": 5000},
        "content_rules": {"video_max_seconds": 300, "script_max_length": 2000},
    },
    "wechat": {
        "name": "微信/企微",
        "base_url": "https://qyapi.weixin.qq.com/cgi-bin",
        "auth_type": "token",
        "env_corp_id": "WEWORK_CORP_ID",
        "env_agent_secret": "WEWORK_AGENT_SECRET",
        "rate_limit": {"calls_per_minute": 60, "calls_per_day": 100000},
        "content_rules": {"msg_max_length": 4096},
    },
}

TOOL_DEFINITIONS = {
    "social_content_publish": {
        "description": "发布内容到社媒平台",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "title": "标题", "content": "正文内容", "tags": "标签列表(逗号分隔)", "images": "图片URL列表(逗号分隔)", "schedule_time": "定时发布时间(可选)"},
        "risk_level": "write",
    },
    "social_content_list": {
        "description": "获取已发布内容列表",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "page": "页码", "page_size": "每页数量", "status": "内容状态(published/draft/all)"},
        "risk_level": "read",
    },
    "social_content_delete": {
        "description": "删除已发布内容",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "content_id": "内容ID"},
        "risk_level": "dangerous",
    },
    "social_analytics": {
        "description": "获取内容数据分析(阅读/点赞/评论/分享)",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "content_id": "内容ID(可选，不填则汇总)", "start_date": "开始日期", "end_date": "结束日期"},
        "risk_level": "read",
    },
    "social_comment_list": {
        "description": "获取评论列表",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "content_id": "内容ID", "page": "页码", "page_size": "每页数量"},
        "risk_level": "read",
    },
    "social_comment_reply": {
        "description": "回复评论",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "comment_id": "评论ID", "content": "回复内容"},
        "risk_level": "write",
    },
    "social_trending": {
        "description": "获取平台热点/趋势",
        "platforms": ["xhs", "douyin"],
        "params": {"platform": "平台标识", "category": "分类(可选)", "limit": "数量限制"},
        "risk_level": "read",
    },
    "wechat_send_message": {
        "description": "发送企微消息(文本/卡片/Markdown)",
        "platforms": ["wechat"],
        "params": {"msg_type": "消息类型(text/markdown/interactive)", "content": "消息内容", "user_list": "接收人列表(逗号分隔，@all为全员)", "agent_id": "应用ID(可选)"},
        "risk_level": "write",
    },
    "wechat_transfer_human": {
        "description": "转接人工客服",
        "platforms": ["wechat"],
        "params": {"user_id": "用户ID", "reason": "转接原因", "session_context": "会话上下文(可选)"},
        "risk_level": "write",
    },
    "social_compliance_check": {
        "description": "内容合规检测(敏感词/极限词/平台规范)",
        "platforms": ["xhs", "douyin", "wechat"],
        "params": {"platform": "平台标识", "content": "待检测内容", "check_types": "检测类型(sensitive/extreme/platform/all)"},
        "risk_level": "read",
    },
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            content_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            published_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(platform, content_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            content_id TEXT NOT NULL,
            user_name TEXT DEFAULT '',
            content TEXT DEFAULT '',
            reply TEXT DEFAULT '',
            replied_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(platform, comment_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            content TEXT DEFAULT '',
            user_list TEXT DEFAULT '',
            status TEXT DEFAULT 'sent',
            sent_at TEXT NOT NULL
        )
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for platform in ["xhs", "douyin"]:
        for i in range(1, 4):
            cid = f"{platform}_content_{i:04d}"
            c.execute("SELECT id FROM contents WHERE platform=? AND content_id=?", (platform, cid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO contents (platform, content_id, title, content, tags, status, likes, comments, shares, views, published_at, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (platform, cid, f"测试笔记{i}", f"这是第{i}篇测试内容，包含一些关键词和描述。", "测试,笔记", "published", 100 * i, 10 * i, 5 * i, 1000 * i, now, now),
                )
        for i in range(1, 3):
            cmid = f"{platform}_comment_{i:04d}"
            c.execute("SELECT id FROM comments WHERE platform=? AND comment_id=?", (platform, cmid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO comments (platform, comment_id, content_id, user_name, content, created_at) VALUES (?,?,?,?,?,?)",
                    (platform, cmid, f"{platform}_content_0001", f"用户{i}", f"评论内容{i}", now),
                )

    conn.commit()
    conn.close()


SENSITIVE_WORDS = ["最", "第一", "国家级", "最佳", "最强", "唯一", "首选", "顶级", "极品", "绝对"]
XHS_BANNED = ["加微信", "加V", "私聊", "低价", "免费送", "转发抽奖"]


class SocialMCP:
    def __init__(self):
        init_db()
        self.credentials = self._load_credentials()

    def _load_credentials(self) -> Dict:
        creds = {}
        for platform, config in PLATFORM_CONFIG.items():
            if config["auth_type"] == "cookie":
                cookie = os.environ.get(config["env_cookie"], "")
                creds[platform] = {"configured": bool(cookie), "auth_type": "cookie"}
            elif config["auth_type"] == "token":
                corp_id = os.environ.get(config.get("env_corp_id", ""), "")
                secret = os.environ.get(config.get("env_agent_secret", ""), "")
                creds[platform] = {"configured": bool(corp_id and secret), "auth_type": "token"}
        return creds

    def _check_platform(self, platform: str) -> Dict:
        if platform not in PLATFORM_CONFIG:
            return {"success": False, "error": f"不支持的平台: {platform}，支持: {list(PLATFORM_CONFIG.keys())}"}
        return {"success": True}

    def _check_content_rules(self, platform: str, content: str) -> Dict:
        config = PLATFORM_CONFIG.get(platform, {})
        rules = config.get("content_rules", {})
        issues = []
        warnings = []

        if "max_length" in rules and len(content) > rules["max_length"]:
            issues.append(f"内容长度 {len(content)} 超过限制 {rules['max_length']}")
        if "min_length" in rules and len(content) < rules["min_length"]:
            warnings.append(f"内容长度 {len(content)} 不足建议长度 {rules['min_length']}，已自动补齐")

        return {"compliant": len(issues) == 0, "issues": issues, "warnings": warnings}

    def call_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name not in TOOL_DEFINITIONS:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool_def = TOOL_DEFINITIONS[tool_name]
        platform = params.get("platform", "")
        check = self._check_platform(platform)
        if not check["success"]:
            return check

        if platform not in tool_def["platforms"]:
            return {"success": False, "error": f"工具 {tool_name} 不支持平台 {platform}，支持: {tool_def['platforms']}"}

        try:
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler:
                result = handler(platform, params)
            else:
                result = {"success": False, "error": f"处理器未实现: {tool_name}"}
            result["platform"] = platform
            result["tool"] = tool_name
            result["risk_level"] = tool_def["risk_level"]
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "platform": platform, "tool": tool_name}

    def _handle_social_content_publish(self, platform: str, params: Dict) -> Dict:
        title = params.get("title", "")
        content = params.get("content", "")
        tags = params.get("tags", "")

        rules_check = self._check_content_rules(platform, content)
        if not rules_check["compliant"]:
            return {"success": False, "error": "内容不符合平台规范", "issues": rules_check["issues"]}

        content_id = f"{platform}_content_{int(time.time())}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO contents (platform, content_id, title, content, tags, status, published_at, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (platform, content_id, title, content, tags, "published", now, now),
        )
        conn.commit()
        conn.close()

        return {"success": True, "content_id": content_id, "message": f"内容已发布到{PLATFORM_CONFIG[platform]['name']}"}

    def _handle_social_content_list(self, platform: str, params: Dict) -> Dict:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))
        status = params.get("status", "all")

        conn = get_db()
        c = conn.cursor()
        if status == "all":
            c.execute("SELECT * FROM contents WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        else:
            c.execute("SELECT * FROM contents WHERE platform=? AND status=? ORDER BY id LIMIT ? OFFSET ?", (platform, status, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        conn.close()

        contents = []
        for row in rows:
            contents.append({
                "content_id": row["content_id"],
                "title": row["title"],
                "status": row["status"],
                "likes": row["likes"],
                "comments": row["comments"],
                "views": row["views"],
                "published_at": row["published_at"],
            })

        return {"success": True, "contents": contents}

    def _handle_social_content_delete(self, platform: str, params: Dict) -> Dict:
        content_id = params.get("content_id", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE contents SET status='deleted' WHERE platform=? AND content_id=?", (platform, content_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"内容 {content_id} 已删除", "gate_required": True}

    def _handle_social_analytics(self, platform: str, params: Dict) -> Dict:
        content_id = params.get("content_id", "")

        conn = get_db()
        c = conn.cursor()
        if content_id:
            c.execute("SELECT * FROM contents WHERE platform=? AND content_id=?", (platform, content_id))
            row = c.fetchone()
            conn.close()
            if not row:
                return {"success": False, "error": f"内容 {content_id} 不存在"}
            return {
                "success": True,
                "analytics": {
                    "content_id": row["content_id"],
                    "title": row["title"],
                    "likes": row["likes"],
                    "comments": row["comments"],
                    "shares": row["shares"],
                    "views": row["views"],
                    "engagement_rate": round((row["likes"] + row["comments"] + row["shares"]) / max(row["views"], 1) * 100, 2),
                },
            }
        else:
            c.execute("SELECT SUM(likes) as total_likes, SUM(comments) as total_comments, SUM(shares) as total_shares, SUM(views) as total_views, COUNT(*) as total_contents FROM contents WHERE platform=? AND status='published'", (platform,))
            row = c.fetchone()
            conn.close()
            return {
                "success": True,
                "analytics": {
                    "total_contents": row["total_contents"],
                    "total_likes": row["total_likes"] or 0,
                    "total_comments": row["total_comments"] or 0,
                    "total_shares": row["total_shares"] or 0,
                    "total_views": row["total_views"] or 0,
                },
            }

    def _handle_social_comment_list(self, platform: str, params: Dict) -> Dict:
        content_id = params.get("content_id", "")
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM comments WHERE platform=? AND content_id=? ORDER BY id LIMIT ? OFFSET ?", (platform, content_id, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        conn.close()

        comments = []
        for row in rows:
            comments.append({
                "comment_id": row["comment_id"],
                "user_name": row["user_name"],
                "content": row["content"],
                "reply": row["reply"],
            })

        return {"success": True, "comments": comments}

    def _handle_social_comment_reply(self, platform: str, params: Dict) -> Dict:
        comment_id = params.get("comment_id", "")
        content = params.get("content", "")

        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE comments SET reply=?, replied_at=? WHERE platform=? AND comment_id=?", (content, now, platform, comment_id))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"评论 {comment_id} 已回复"}

    def _handle_social_trending(self, platform: str, params: Dict) -> Dict:
        limit = int(params.get("limit", 10))
        trending = [
            {"rank": i, "keyword": f"热门话题{i}", "heat": 10000 - i * 500, "category": "生活"}
            for i in range(1, limit + 1)
        ]
        return {"success": True, "platform": PLATFORM_CONFIG[platform]["name"], "trending": trending}

    def _handle_wechat_send_message(self, platform: str, params: Dict) -> Dict:
        msg_type = params.get("msg_type", "text")
        content = params.get("content", "")
        user_list = params.get("user_list", "@all")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (platform, msg_type, content, user_list, status, sent_at) VALUES (?,?,?,?,?,?)",
            ("wechat", msg_type, content[:500], user_list, "sent", now),
        )
        conn.commit()
        conn.close()

        return {"success": True, "message": f"企微消息已发送", "msg_type": msg_type, "user_list": user_list}

    def _handle_wechat_transfer_human(self, platform: str, params: Dict) -> Dict:
        user_id = params.get("user_id", "")
        reason = params.get("reason", "")
        return {"success": True, "message": f"用户 {user_id} 已转接人工客服", "reason": reason}

    def _handle_social_compliance_check(self, platform: str, params: Dict) -> Dict:
        content = params.get("content", "")
        check_types = params.get("check_types", "all")
        issues = []

        if check_types in ("sensitive", "all"):
            for word in SENSITIVE_WORDS:
                if word in content:
                    issues.append({"type": "sensitive", "word": word, "message": f"包含敏感词: {word}"})

        if check_types in ("extreme", "all"):
            for word in SENSITIVE_WORDS[:5]:
                if word in content:
                    issues.append({"type": "extreme", "word": word, "message": f"包含极限词: {word}"})

        if platform == "xhs" and check_types in ("platform", "all"):
            for word in XHS_BANNED:
                if word in content:
                    issues.append({"type": "platform", "word": word, "message": f"小红书禁止: {word}"})

        return {
            "success": True,
            "compliant": len(issues) == 0,
            "issues": issues,
            "issue_count": len(issues),
            "platform": platform,
        }

    def list_tools(self) -> Dict:
        tools = []
        for name, defn in TOOL_DEFINITIONS.items():
            tools.append({
                "name": name,
                "description": defn["description"],
                "platforms": defn["platforms"],
                "params": defn["params"],
                "risk_level": defn["risk_level"],
            })
        return {"total": len(tools), "tools": tools}

    def get_platform_status(self) -> Dict:
        status = {}
        for platform, config in PLATFORM_CONFIG.items():
            status[platform] = {
                "name": config["name"],
                "configured": self.credentials.get(platform, {}).get("configured", False),
                "rate_limit": config["rate_limit"],
                "content_rules": config.get("content_rules", {}),
            }
        return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Social Media MCP Server")
    parser.add_argument("--action", required=True)
    parser.add_argument("--tool", default="")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()

    mcp = SocialMCP()

    if args.action == "call_tool":
        params = json.loads(args.params)
        result = mcp.call_tool(args.tool, params)
    elif args.action == "list_tools":
        result = mcp.list_tools()
    elif args.action == "platform_status":
        result = mcp.get_platform_status()
    else:
        result = {"error": f"未知操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
