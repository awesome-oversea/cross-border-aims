import json
import os
import re
import sqlite3
import sys
import hashlib
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aims_data.db")

TABLE_DEFINITIONS = {
    "sessions": {
        "description": "会话记录表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "session_id TEXT UNIQUE NOT NULL",
            "channel TEXT NOT NULL",
            "user_id TEXT NOT NULL",
            "agent_name TEXT DEFAULT 'main'",
            "message TEXT",
            "reply TEXT",
            "intent TEXT",
            "confidence REAL DEFAULT 0.0",
            "skill_used TEXT",
            "duration_ms INTEGER DEFAULT 0",
            "tokens_used INTEGER DEFAULT 0",
            "created_at TEXT NOT NULL",
        ],
        "indexes": ["session_id", "channel", "user_id", "agent_name", "created_at"],
    },
    "users": {
        "description": "用户信息表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "user_id TEXT UNIQUE NOT NULL",
            "channel TEXT NOT NULL",
            "external_id TEXT",
            "name TEXT",
            "avatar TEXT",
            "role TEXT DEFAULT 'user'",
            "preferences TEXT DEFAULT '{}'",
            "interaction_count INTEGER DEFAULT 0",
            "last_active_at TEXT",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["user_id", "channel", "external_id"],
    },
    "products": {
        "description": "商品信息表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "product_id TEXT UNIQUE NOT NULL",
            "platform TEXT NOT NULL",
            "sku_id TEXT",
            "title TEXT NOT NULL",
            "price REAL DEFAULT 0.0",
            "currency TEXT DEFAULT 'CNY'",
            "category TEXT",
            "subcategory TEXT",
            "selling_points TEXT",
            "description TEXT",
            "images TEXT DEFAULT '[]'",
            "status TEXT DEFAULT 'active'",
            "bsr_rank INTEGER DEFAULT 0",
            "review_count INTEGER DEFAULT 0",
            "rating REAL DEFAULT 0.0",
            "monthly_sales INTEGER DEFAULT 0",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["product_id", "platform", "category", "status"],
    },
    "orders": {
        "description": "订单数据表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "order_id TEXT UNIQUE NOT NULL",
            "platform TEXT NOT NULL",
            "order_no TEXT NOT NULL",
            "product_id TEXT",
            "product_title TEXT",
            "quantity INTEGER DEFAULT 1",
            "amount REAL DEFAULT 0.0",
            "currency TEXT DEFAULT 'CNY'",
            "status TEXT DEFAULT 'pending'",
            "buyer_id TEXT",
            "buyer_name TEXT",
            "shipping_address TEXT",
            "tracking_number TEXT",
            "logistics_status TEXT",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["order_id", "platform", "status", "buyer_id", "created_at"],
    },
    "reviews": {
        "description": "评论数据表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "review_id TEXT UNIQUE NOT NULL",
            "platform TEXT NOT NULL",
            "product_id TEXT NOT NULL",
            "order_id TEXT",
            "content TEXT NOT NULL",
            "rating INTEGER DEFAULT 5",
            "sentiment TEXT DEFAULT 'neutral'",
            "sentiment_score REAL DEFAULT 0.5",
            "replied INTEGER DEFAULT 0",
            "reply_content TEXT",
            "reviewer_name TEXT",
            "review_date TEXT",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["review_id", "platform", "product_id", "sentiment", "replied"],
    },
    "contents": {
        "description": "内容记录表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "content_id TEXT UNIQUE NOT NULL",
            "type TEXT NOT NULL",
            "platform TEXT NOT NULL",
            "title TEXT",
            "content TEXT",
            "tags TEXT DEFAULT '[]'",
            "status TEXT DEFAULT 'draft'",
            "published_at TEXT",
            "views INTEGER DEFAULT 0",
            "likes INTEGER DEFAULT 0",
            "comments INTEGER DEFAULT 0",
            "shares INTEGER DEFAULT 0",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["content_id", "type", "platform", "status"],
    },
    "cron_jobs": {
        "description": "定时任务表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "job_id TEXT UNIQUE NOT NULL",
            "name TEXT NOT NULL",
            "cron_expr TEXT NOT NULL",
            "agent TEXT DEFAULT 'main'",
            "skill TEXT",
            "action TEXT",
            "params TEXT DEFAULT '{}'",
            "channel TEXT DEFAULT 'feishu'",
            "target TEXT",
            "enabled INTEGER DEFAULT 1",
            "last_run TEXT",
            "next_run TEXT",
            "run_count INTEGER DEFAULT 0",
            "fail_count INTEGER DEFAULT 0",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["job_id", "name", "enabled"],
    },
    "knowledge_docs": {
        "description": "知识库文档表",
        "columns": [
            "id INTEGER PRIMARY KEY AUTOINCREMENT",
            "doc_id TEXT UNIQUE NOT NULL",
            "category TEXT NOT NULL",
            "title TEXT NOT NULL",
            "content TEXT NOT NULL",
            "tags TEXT DEFAULT '[]'",
            "source TEXT DEFAULT 'manual'",
            "vector_id TEXT",
            "char_count INTEGER DEFAULT 0",
            "chunk_count INTEGER DEFAULT 0",
            "access_count INTEGER DEFAULT 0",
            "relevance_score REAL DEFAULT 0.0",
            "status TEXT DEFAULT 'active'",
            "created_at TEXT NOT NULL",
            "updated_at TEXT",
        ],
        "indexes": ["doc_id", "category", "source", "status"],
    },
}

ETL_PIPELINES = {
    "order_sync": {
        "name": "订单数据同步",
        "source": "ecommerce_api",
        "target": "orders",
        "schedule": "every_hour",
        "description": "从电商平台API同步订单数据",
    },
    "product_sync": {
        "name": "商品数据同步",
        "source": "ecommerce_api",
        "target": "products",
        "schedule": "daily",
        "description": "从电商平台API同步商品数据",
    },
    "review_sync": {
        "name": "评论数据同步",
        "source": "ecommerce_api",
        "target": "reviews",
        "schedule": "every_6_hours",
        "description": "从电商平台API同步评论数据",
    },
    "content_analytics": {
        "name": "内容数据聚合",
        "source": "social_media_api",
        "target": "contents",
        "schedule": "hourly",
        "description": "从社媒API聚合内容互动数据",
    },
    "session_analytics": {
        "name": "会话数据聚合",
        "source": "openclaw_logs",
        "target": "sessions",
        "schedule": "realtime",
        "description": "实时记录OpenClaw会话数据",
    },
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for table_name, table_def in TABLE_DEFINITIONS.items():
        columns_sql = ", ".join(table_def["columns"])
        c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})")

        for idx_col in table_def.get("indexes", []):
            idx_name = f"idx_{table_name}_{idx_col}"
            try:
                c.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({idx_col})")
            except sqlite3.OperationalError:
                pass

    c.execute("""CREATE TABLE IF NOT EXISTS etl_pipeline_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pipeline_name TEXT NOT NULL,
        execution_id TEXT NOT NULL,
        status TEXT DEFAULT 'running',
        records_processed INTEGER DEFAULT 0,
        records_inserted INTEGER DEFAULT 0,
        records_updated INTEGER DEFAULT 0,
        records_failed INTEGER DEFAULT 0,
        started_at TEXT,
        completed_at TEXT,
        duration_ms INTEGER DEFAULT 0,
        error_message TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS data_quality_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        check_type TEXT NOT NULL,
        check_result TEXT,
        issues_found INTEGER DEFAULT 0,
        checked_at TEXT
    )""")

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_id(prefix: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = random.randint(1000, 9999)
    return f"{prefix}{ts}{rand}" if prefix else f"{ts}{rand}"


class DataManager:
    def __init__(self):
        init_db()

    def insert_session(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        session_id = data.get("session_id", generate_id("sess-"))
        try:
            c.execute(
                "INSERT INTO sessions (session_id, channel, user_id, agent_name, message, reply, intent, confidence, skill_used, duration_ms, tokens_used, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, data.get("channel", ""), data.get("user_id", ""), data.get("agent_name", "main"), data.get("message", ""), data.get("reply", ""), data.get("intent", ""), data.get("confidence", 0.0), data.get("skill_used", ""), data.get("duration_ms", 0), data.get("tokens_used", 0), now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "session_id": session_id}
        except sqlite3.IntegrityError:
            conn.close()
            return {"success": False, "error": "session_id已存在"}

    def insert_user(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_id = data.get("user_id", generate_id("user-"))
        try:
            c.execute(
                "INSERT INTO users (user_id, channel, external_id, name, avatar, role, preferences, interaction_count, last_active_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, data.get("channel", ""), data.get("external_id", ""), data.get("name", ""), data.get("avatar", ""), data.get("role", "user"), json.dumps(data.get("preferences", {}), ensure_ascii=False), data.get("interaction_count", 0), now, now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "user_id": user_id}
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE users SET name=?, last_active_at=?, interaction_count=interaction_count+1, updated_at=? WHERE user_id=?",
                (data.get("name", ""), now, now, user_id),
            )
            conn.commit()
            conn.close()
            return {"success": True, "user_id": user_id, "updated": True}

    def insert_product(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        product_id = data.get("product_id", generate_id("prod-"))
        try:
            c.execute(
                "INSERT INTO products (product_id, platform, sku_id, title, price, currency, category, subcategory, selling_points, description, images, status, bsr_rank, review_count, rating, monthly_sales, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (product_id, data.get("platform", ""), data.get("sku_id", ""), data.get("title", ""), data.get("price", 0.0), data.get("currency", "CNY"), data.get("category", ""), data.get("subcategory", ""), data.get("selling_points", ""), data.get("description", ""), json.dumps(data.get("images", []), ensure_ascii=False), data.get("status", "active"), data.get("bsr_rank", 0), data.get("review_count", 0), data.get("rating", 0.0), data.get("monthly_sales", 0), now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "product_id": product_id}
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE products SET title=?, price=?, category=?, selling_points=?, bsr_rank=?, review_count=?, rating=?, monthly_sales=?, updated_at=? WHERE product_id=?",
                (data.get("title", ""), data.get("price", 0.0), data.get("category", ""), data.get("selling_points", ""), data.get("bsr_rank", 0), data.get("review_count", 0), data.get("rating", 0.0), data.get("monthly_sales", 0), now, product_id),
            )
            conn.commit()
            conn.close()
            return {"success": True, "product_id": product_id, "updated": True}

    def insert_order(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        order_id = data.get("order_id", generate_id("ord-"))
        try:
            c.execute(
                "INSERT INTO orders (order_id, platform, order_no, product_id, product_title, quantity, amount, currency, status, buyer_id, buyer_name, shipping_address, tracking_number, logistics_status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, data.get("platform", ""), data.get("order_no", ""), data.get("product_id", ""), data.get("product_title", ""), data.get("quantity", 1), data.get("amount", 0.0), data.get("currency", "CNY"), data.get("status", "pending"), data.get("buyer_id", ""), data.get("buyer_name", ""), data.get("shipping_address", ""), data.get("tracking_number", ""), data.get("logistics_status", ""), now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "order_id": order_id}
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE orders SET status=?, tracking_number=?, logistics_status=?, updated_at=? WHERE order_id=?",
                (data.get("status", "pending"), data.get("tracking_number", ""), data.get("logistics_status", ""), now, order_id),
            )
            conn.commit()
            conn.close()
            return {"success": True, "order_id": order_id, "updated": True}

    def insert_review(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        review_id = data.get("review_id", generate_id("rev-"))
        try:
            c.execute(
                "INSERT INTO reviews (review_id, platform, product_id, order_id, content, rating, sentiment, sentiment_score, replied, reply_content, reviewer_name, review_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (review_id, data.get("platform", ""), data.get("product_id", ""), data.get("order_id", ""), data.get("content", ""), data.get("rating", 5), data.get("sentiment", "neutral"), data.get("sentiment_score", 0.5), 0, None, data.get("reviewer_name", ""), data.get("review_date", now), now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "review_id": review_id}
        except sqlite3.IntegrityError:
            conn.close()
            return {"success": False, "error": "review_id已存在"}

    def insert_content(self, data: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        content_id = data.get("content_id", generate_id("cnt-"))
        try:
            c.execute(
                "INSERT INTO contents (content_id, type, platform, title, content, tags, status, published_at, views, likes, comments, shares, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (content_id, data.get("type", "post"), data.get("platform", ""), data.get("title", ""), data.get("content", ""), json.dumps(data.get("tags", []), ensure_ascii=False), data.get("status", "draft"), data.get("published_at"), data.get("views", 0), data.get("likes", 0), data.get("comments", 0), data.get("shares", 0), now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "content_id": content_id}
        except sqlite3.IntegrityError:
            c.execute(
                "UPDATE contents SET views=?, likes=?, comments=?, shares=?, status=?, updated_at=? WHERE content_id=?",
                (data.get("views", 0), data.get("likes", 0), data.get("comments", 0), data.get("shares", 0), data.get("status", "draft"), now, content_id),
            )
            conn.commit()
            conn.close()
            return {"success": True, "content_id": content_id, "updated": True}

    def query_table(self, table_name: str, conditions: Dict = None, limit: int = 20, offset: int = 0) -> Dict:
        if table_name not in TABLE_DEFINITIONS:
            return {"success": False, "error": f"表 {table_name} 不存在"}

        conn = get_db()
        c = conn.cursor()

        if conditions:
            where_parts = []
            params = []
            for key, value in conditions.items():
                if isinstance(value, list):
                    placeholders = ",".join(["?"] * len(value))
                    where_parts.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                elif isinstance(value, str) and "%" in value:
                    where_parts.append(f"{key} LIKE ?")
                    params.append(value)
                else:
                    where_parts.append(f"{key} = ?")
                    params.append(value)

            where_clause = " AND ".join(where_parts)
            c.execute(f"SELECT * FROM {table_name} WHERE {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?", params + [limit, offset])
        else:
            c.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))

        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"success": True, "table": table_name, "data": rows, "count": len(rows)}

    def get_table_stats(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        stats = {}

        for table_name in TABLE_DEFINITIONS:
            c.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = c.fetchone()["count"]
            stats[table_name] = {"count": count, "description": TABLE_DEFINITIONS[table_name]["description"]}

        conn.close()
        return {"success": True, "tables": stats, "total_tables": len(stats)}

    def get_table_schema(self, table_name: str) -> Dict:
        if table_name not in TABLE_DEFINITIONS:
            return {"success": False, "error": f"表 {table_name} 不存在"}

        conn = get_db()
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table_name})")
        columns = [dict(row) for row in c.fetchall()]
        conn.close()

        return {
            "success": True,
            "table": table_name,
            "description": TABLE_DEFINITIONS[table_name]["description"],
            "columns": columns,
            "indexes": TABLE_DEFINITIONS[table_name].get("indexes", []),
        }


class ETLPipeline:
    def __init__(self, data_manager: DataManager = None):
        self.data_manager = data_manager or DataManager()

    def run_pipeline(self, pipeline_name: str) -> Dict:
        pipeline = ETL_PIPELINES.get(pipeline_name)
        if not pipeline:
            return {"success": False, "error": f"管道 {pipeline_name} 不存在"}

        execution_id = generate_id("etl-")
        start_time = time.time()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO etl_pipeline_logs (pipeline_name, execution_id, status, started_at) VALUES (?, ?, ?, ?)",
            (pipeline_name, execution_id, "running", now),
        )
        conn.commit()

        try:
            result = self._execute_pipeline(pipeline_name, pipeline)

            duration = int((time.time() - start_time) * 1000)
            c.execute(
                "UPDATE etl_pipeline_logs SET status=?, records_processed=?, records_inserted=?, records_updated=?, records_failed=?, completed_at=?, duration_ms=? WHERE execution_id=?",
                ("completed", result.get("processed", 0), result.get("inserted", 0), result.get("updated", 0), result.get("failed", 0), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, execution_id),
            )
            conn.commit()
            conn.close()

            return {
                "success": True,
                "execution_id": execution_id,
                "pipeline": pipeline_name,
                "duration_ms": duration,
                **result,
            }

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            c.execute(
                "UPDATE etl_pipeline_logs SET status=?, error_message=?, completed_at=?, duration_ms=? WHERE execution_id=?",
                ("failed", str(e), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), duration, execution_id),
            )
            conn.commit()
            conn.close()
            return {"success": False, "execution_id": execution_id, "error": str(e)}

    def _execute_pipeline(self, pipeline_name: str, pipeline: Dict) -> Dict:
        if pipeline_name == "order_sync":
            return self._sync_orders()
        elif pipeline_name == "product_sync":
            return self._sync_products()
        elif pipeline_name == "review_sync":
            return self._sync_reviews()
        elif pipeline_name == "content_analytics":
            return self._sync_content_analytics()
        elif pipeline_name == "session_analytics":
            return self._sync_session_analytics()
        return {"processed": 0, "inserted": 0, "updated": 0, "failed": 0}

    def _sync_orders(self) -> Dict:
        platforms = ["taobao", "jd", "pdd"]
        inserted = 0
        updated = 0

        for platform in platforms:
            for i in range(3):
                order_no = f"{platform.upper()}{datetime.now().strftime('%Y%m%d')}{random.randint(10000, 99999)}"
                result = self.data_manager.insert_order({
                    "order_id": f"ord-{platform}-{order_no}",
                    "platform": platform,
                    "order_no": order_no,
                    "product_title": f"测试商品-{platform}-{i+1}",
                    "quantity": random.randint(1, 5),
                    "amount": round(random.uniform(50, 500), 2),
                    "status": random.choice(["pending", "shipped", "delivered"]),
                    "buyer_name": f"买家{random.randint(1, 100)}",
                })
                if result.get("success"):
                    if result.get("updated"):
                        updated += 1
                    else:
                        inserted += 1

        return {"processed": len(platforms) * 3, "inserted": inserted, "updated": updated, "failed": 0}

    def _sync_products(self) -> Dict:
        categories = ["电子产品", "家居用品", "服装", "美妆"]
        inserted = 0
        updated = 0

        for cat in categories:
            result = self.data_manager.insert_product({
                "product_id": f"prod-sync-{cat}-{datetime.now().strftime('%Y%m%d')}",
                "platform": "taobao",
                "title": f"热销{cat}商品",
                "price": round(random.uniform(30, 300), 2),
                "category": cat,
                "bsr_rank": random.randint(1, 1000),
                "review_count": random.randint(10, 500),
                "rating": round(random.uniform(3.5, 5.0), 1),
                "monthly_sales": random.randint(100, 5000),
            })
            if result.get("success"):
                if result.get("updated"):
                    updated += 1
                else:
                    inserted += 1

        return {"processed": len(categories), "inserted": inserted, "updated": updated, "failed": 0}

    def _sync_reviews(self) -> Dict:
        sentiments = ["positive", "neutral", "negative"]
        inserted = 0

        for i in range(5):
            sentiment = random.choice(sentiments)
            rating = {"positive": 5, "neutral": 3, "negative": 1}[sentiment]
            result = self.data_manager.insert_review({
                "review_id": f"rev-sync-{datetime.now().strftime('%Y%m%d')}-{i}",
                "platform": "taobao",
                "product_id": f"prod-sync-电子产品-{datetime.now().strftime('%Y%m%d')}",
                "content": f"用户评价内容{i+1}",
                "rating": rating,
                "sentiment": sentiment,
                "sentiment_score": round(random.uniform(0.1, 0.9), 2),
                "reviewer_name": f"用户{random.randint(1, 50)}",
            })
            if result.get("success"):
                inserted += 1

        return {"processed": 5, "inserted": inserted, "updated": 0, "failed": 0}

    def _sync_content_analytics(self) -> Dict:
        platforms = ["xhs", "douyin"]
        inserted = 0
        updated = 0

        for platform in platforms:
            result = self.data_manager.insert_content({
                "content_id": f"cnt-sync-{platform}-{datetime.now().strftime('%Y%m%d')}",
                "type": "post",
                "platform": platform,
                "title": f"{platform}热门内容",
                "status": "published",
                "views": random.randint(100, 10000),
                "likes": random.randint(10, 1000),
                "comments": random.randint(5, 200),
                "shares": random.randint(0, 100),
            })
            if result.get("success"):
                if result.get("updated"):
                    updated += 1
                else:
                    inserted += 1

        return {"processed": len(platforms), "inserted": inserted, "updated": updated, "failed": 0}

    def _sync_session_analytics(self) -> Dict:
        channels = ["feishu", "wework", "dingtalk"]
        agents = ["ecommerce", "social-media", "cs"]
        inserted = 0

        for i in range(3):
            result = self.data_manager.insert_session({
                "session_id": f"sess-sync-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                "channel": random.choice(channels),
                "user_id": f"user-{random.randint(1, 50)}",
                "agent_name": random.choice(agents),
                "message": f"测试消息{i+1}",
                "reply": f"测试回复{i+1}",
                "intent": random.choice(["query_product", "query_order", "manage_ad"]),
                "confidence": round(random.uniform(0.6, 1.0), 2),
                "duration_ms": random.randint(100, 3000),
            })
            if result.get("success"):
                inserted += 1

        return {"processed": 3, "inserted": inserted, "updated": 0, "failed": 0}

    def get_pipeline_logs(self, limit: int = 20) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM etl_pipeline_logs ORDER BY started_at DESC LIMIT ?", (limit,))
        logs = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"success": True, "logs": logs, "total": len(logs)}

    def list_pipelines(self) -> Dict:
        return {"success": True, "pipelines": ETL_PIPELINES, "total": len(ETL_PIPELINES)}

    def run_data_quality_check(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        issues = []

        for table_name in TABLE_DEFINITIONS:
            c.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            count = c.fetchone()["count"]

            c.execute(f"PRAGMA table_info({table_name})")
            columns = [row["name"] for row in c.fetchall()]

            for col in columns:
                try:
                    c.execute(f"SELECT COUNT(*) as null_count FROM {table_name} WHERE {col} IS NULL")
                    null_count = c.fetchone()["null_count"]
                    if null_count > 0 and count > 0:
                        null_pct = round(null_count / count * 100, 1)
                        if null_pct > 50:
                            issues.append({"table": table_name, "column": col, "issue": f"空值率{null_pct}%", "severity": "high"})
                except sqlite3.OperationalError:
                    pass

            try:
                id_col = columns[0] if columns else "id"
                c.execute(f"SELECT COUNT(*) as dup_count FROM (SELECT {id_col}, COUNT(*) as cnt FROM {table_name} GROUP BY {id_col} HAVING cnt > 1)")
                dup_count = c.fetchone()["dup_count"]
                if dup_count > 0:
                    issues.append({"table": table_name, "issue": f"存在{dup_count}条重复记录", "severity": "medium"})
            except sqlite3.OperationalError:
                pass

            c.execute(
                "INSERT INTO data_quality_checks (table_name, check_type, check_result, issues_found, checked_at) VALUES (?, ?, ?, ?, ?)",
                (table_name, "comprehensive", "pass" if not any(i["table"] == table_name for i in issues) else "issues_found", sum(1 for i in issues if i["table"] == table_name), now),
            )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "checked_at": now,
            "tables_checked": len(TABLE_DEFINITIONS),
            "total_issues": len(issues),
            "issues": issues,
            "overall_quality": "good" if len(issues) == 0 else "needs_attention",
        }


def main():
    input_data = json.loads(sys.stdin.read())
    action = input_data.get("action", "stats")
    dm = DataManager()
    etl = ETLPipeline(dm)

    if action == "stats":
        result = dm.get_table_stats()
    elif action == "schema":
        result = dm.get_table_schema(input_data.get("table", ""))
    elif action == "query":
        result = dm.query_table(
            input_data.get("table", ""),
            input_data.get("conditions"),
            input_data.get("limit", 20),
            input_data.get("offset", 0),
        )
    elif action == "insert_session":
        result = dm.insert_session(input_data.get("data", {}))
    elif action == "insert_user":
        result = dm.insert_user(input_data.get("data", {}))
    elif action == "insert_product":
        result = dm.insert_product(input_data.get("data", {}))
    elif action == "insert_order":
        result = dm.insert_order(input_data.get("data", {}))
    elif action == "insert_review":
        result = dm.insert_review(input_data.get("data", {}))
    elif action == "insert_content":
        result = dm.insert_content(input_data.get("data", {}))
    elif action == "run_etl":
        result = etl.run_pipeline(input_data.get("pipeline", ""))
    elif action == "list_pipelines":
        result = etl.list_pipelines()
    elif action == "etl_logs":
        result = etl.get_pipeline_logs(input_data.get("limit", 20))
    elif action == "quality_check":
        result = etl.run_data_quality_check()
    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
