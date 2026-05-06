import json
import os
import sqlite3
import hashlib
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawler.db")

PLATFORM_CONFIG = {
    "taobao": {"name": "淘宝/天猫", "target_types": ["product", "review", "sales"], "delay_range": [3, 8], "max_concurrent": 2},
    "jd": {"name": "京东", "target_types": ["product", "review", "price_history"], "delay_range": [2, 6], "max_concurrent": 3},
    "pdd": {"name": "拼多多", "target_types": ["product", "review", "activity"], "delay_range": [3, 7], "max_concurrent": 2},
    "xhs": {"name": "小红书", "target_types": ["note", "comment", "topic"], "delay_range": [4, 10], "max_concurrent": 1},
    "douyin": {"name": "抖音", "target_types": ["video", "comment", "trending"], "delay_range": [3, 8], "max_concurrent": 2},
    "1688": {"name": "1688", "target_types": ["supplier", "product", "price"], "delay_range": [2, 5], "max_concurrent": 3},
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS crawl_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            platform TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT DEFAULT '',
            keyword TEXT DEFAULT '',
            options TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            progress REAL DEFAULT 0,
            result_count INTEGER DEFAULT 0,
            error TEXT DEFAULT '',
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS crawl_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT DEFAULT '',
            data TEXT DEFAULT '{}',
            crawled_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS proxy_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy_url TEXT NOT NULL UNIQUE,
            proxy_type TEXT DEFAULT 'http',
            region TEXT DEFAULT '',
            speed_ms INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            last_check TEXT DEFAULT '',
            status TEXT DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS crawl_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            target_type TEXT NOT NULL,
            total_tasks INTEGER DEFAULT 0,
            success_tasks INTEGER DEFAULT 0,
            total_records INTEGER DEFAULT 0,
            avg_speed_ms INTEGER DEFAULT 0,
            date TEXT NOT NULL,
            UNIQUE(platform, target_type, date)
        )
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")
    for platform in PLATFORM_CONFIG:
        for ttype in PLATFORM_CONFIG[platform]["target_types"]:
            c.execute("SELECT id FROM crawl_stats WHERE platform=? AND target_type=? AND date=?", (platform, ttype, today))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO crawl_stats (platform, target_type, total_tasks, success_tasks, total_records, date) VALUES (?,?,?,?,?,?)",
                    (platform, ttype, random.randint(10, 50), random.randint(8, 45), random.randint(100, 500), today),
                )

    conn.commit()
    conn.close()


class WebCrawler:
    def __init__(self):
        init_db()
        self.ua_pool = USER_AGENTS.copy()

    def _generate_task_id(self, platform: str, target_type: str) -> str:
        ts = int(time.time())
        rand = random.randint(1000, 9999)
        return f"task-{platform}-{target_type}-{ts}-{rand}"

    def _get_random_ua(self) -> str:
        return random.choice(self.ua_pool)

    def _get_delay(self, platform: str) -> float:
        config = PLATFORM_CONFIG.get(platform, {})
        delay_range = config.get("delay_range", [3, 8])
        return random.uniform(delay_range[0], delay_range[1])

    def crawl(self, platform: str, target_type: str, target_id: str = "", options: Dict = None) -> Dict:
        if options is None:
            options = {}

        if platform not in PLATFORM_CONFIG:
            return {"success": False, "error": f"不支持的平台: {platform}"}

        if target_type not in PLATFORM_CONFIG[platform]["target_types"]:
            return {"success": False, "error": f"平台 {platform} 不支持目标类型: {target_type}"}

        task_id = self._generate_task_id(platform, target_type)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO crawl_tasks (task_id, platform, target_type, target_id, options, status, started_at, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (task_id, platform, target_type, target_id, json.dumps(options, ensure_ascii=False)[:500], "running", now, now),
        )
        conn.commit()
        conn.close()

        simulated_data = self._simulate_crawl(platform, target_type, target_id, options)

        now2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "UPDATE crawl_tasks SET status='completed', progress=100, result_count=?, completed_at=? WHERE task_id=?",
            (len(simulated_data), now2, task_id),
        )
        for item in simulated_data:
            c.execute(
                "INSERT INTO crawl_results (task_id, platform, target_type, target_id, data, crawled_at) VALUES (?,?,?,?,?,?)",
                (task_id, platform, target_type, target_id or item.get("id", ""), json.dumps(item, ensure_ascii=False, default=str)[:1000], now2),
            )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "task_id": task_id,
            "platform": platform,
            "target_type": target_type,
            "result_count": len(simulated_data),
            "data": simulated_data,
            "delay_used": self._get_delay(platform),
            "ua_used": self._get_random_ua()[:30] + "...",
            "mode": "simulated",
        }

    def _simulate_crawl(self, platform: str, target_type: str, target_id: str, options: Dict) -> List[Dict]:
        results = []
        count = int(options.get("max_results", 5))

        if target_type == "product":
            for i in range(count):
                results.append({
                    "id": f"{platform}_prod_{i+1:04d}",
                    "title": f"爬取商品{platform}-{i+1}",
                    "price": round(random.uniform(10, 500), 2),
                    "sales": random.randint(100, 10000),
                    "rating": round(random.uniform(3.5, 5.0), 1),
                    "review_count": random.randint(10, 500),
                })
        elif target_type == "review":
            max_reviews = int(options.get("max_reviews", 10))
            for i in range(min(max_reviews, 10)):
                results.append({
                    "id": f"{platform}_review_{i+1:04d}",
                    "content": f"这是第{i+1}条评论，商品质量不错，物流也很快。",
                    "rating": random.randint(3, 5),
                    "sentiment": random.choice(["positive", "neutral", "negative"]),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
        elif target_type in ("note", "video"):
            for i in range(count):
                results.append({
                    "id": f"{platform}_content_{i+1:04d}",
                    "title": f"热门内容{platform}-{i+1}",
                    "likes": random.randint(100, 50000),
                    "comments": random.randint(10, 5000),
                    "shares": random.randint(5, 2000),
                })
        elif target_type == "supplier":
            for i in range(count):
                results.append({
                    "id": f"supplier_{i+1:04d}",
                    "name": f"供应商{i+1}",
                    "moq": random.randint(10, 500),
                    "price_range": f"{random.randint(5, 50)}-{random.randint(50, 200)}",
                    "rating": round(random.uniform(3.0, 5.0), 1),
                })
        elif target_type == "trending":
            for i in range(count):
                results.append({
                    "keyword": f"热门关键词{i+1}",
                    "heat": random.randint(1000, 100000),
                    "trend": random.choice(["rising", "stable", "declining"]),
                })
        else:
            for i in range(count):
                results.append({"id": f"{target_type}_{i+1:04d}", "data": f"模拟数据{i+1}"})

        return results

    def crawl_batch(self, platform: str, target_type: str, target_ids: List[str], options: Dict = None) -> Dict:
        if options is None:
            options = {}

        results = []
        for tid in target_ids:
            r = self.crawl(platform, target_type, tid, options)
            if r["success"]:
                results.append({"target_id": tid, "task_id": r["task_id"], "result_count": r["result_count"]})

        return {
            "success": True,
            "platform": platform,
            "total_targets": len(target_ids),
            "completed": len(results),
            "results": results,
        }

    def crawl_search(self, platform: str, keyword: str, max_results: int = 20) -> Dict:
        if platform not in PLATFORM_CONFIG:
            return {"success": False, "error": f"不支持的平台: {platform}"}

        target_type = "product" if platform in ("taobao", "jd", "pdd", "1688") else "note"
        options = {"max_results": min(max_results, 50)}

        result = self.crawl(platform, target_type, "", {**options, "keyword": keyword})
        result["keyword"] = keyword
        return result

    def get_task_status(self, task_id: str) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM crawl_tasks WHERE task_id=?", (task_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        return {
            "success": True,
            "task_id": row["task_id"],
            "platform": row["platform"],
            "target_type": row["target_type"],
            "status": row["status"],
            "progress": row["progress"],
            "result_count": row["result_count"],
            "error": row["error"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }

    def list_tasks(self, status: str = None) -> Dict:
        conn = get_db()
        c = conn.cursor()
        if status:
            c.execute("SELECT * FROM crawl_tasks WHERE status=? ORDER BY created_at DESC LIMIT 50", (status,))
        else:
            c.execute("SELECT * FROM crawl_tasks ORDER BY created_at DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row["task_id"],
                "platform": row["platform"],
                "target_type": row["target_type"],
                "status": row["status"],
                "result_count": row["result_count"],
                "created_at": row["created_at"],
            })

        return {"total": len(tasks), "tasks": tasks}

    def get_proxy_status(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM proxy_pool WHERE status='active'")
        active = c.fetchone()["total"]
        c.execute("SELECT COUNT(*) as total FROM proxy_pool")
        total = c.fetchone()["total"]
        c.execute("SELECT region, COUNT(*) as count FROM proxy_pool WHERE status='active' GROUP BY region")
        regions = {row["region"] or "unknown": row["count"] for row in c.fetchall()}
        conn.close()

        return {
            "total_proxies": total,
            "active_proxies": active,
            "regions": regions,
            "ua_pool_size": len(self.ua_pool),
        }

    def get_crawl_stats(self) -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT platform, SUM(total_tasks) as tasks, SUM(success_tasks) as success, SUM(total_records) as records FROM crawl_stats GROUP BY platform")
        stats = {}
        for row in c.fetchall():
            stats[row["platform"]] = {
                "total_tasks": row["tasks"],
                "success_tasks": row["success"],
                "total_records": row["records"],
                "success_rate": round(row["success"] / max(row["tasks"], 1) * 100, 1),
            }
        conn.close()
        return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Web Crawler")
    parser.add_argument("--action", required=True)
    parser.add_argument("--platform", default="")
    parser.add_argument("--target_type", default="product")
    parser.add_argument("--target_id", default="")
    parser.add_argument("--target_ids", default="[]")
    parser.add_argument("--keyword", default="")
    parser.add_argument("--max_results", type=int, default=20)
    parser.add_argument("--options", default="{}")
    parser.add_argument("--task_id", default="")
    parser.add_argument("--status", default="")
    args = parser.parse_args()

    crawler = WebCrawler()

    if args.action == "crawl":
        options = json.loads(args.options)
        result = crawler.crawl(args.platform, args.target_type, args.target_id, options)
    elif args.action == "crawl_batch":
        target_ids = json.loads(args.target_ids)
        options = json.loads(args.options)
        result = crawler.crawl_batch(args.platform, args.target_type, target_ids, options)
    elif args.action == "crawl_search":
        result = crawler.crawl_search(args.platform, args.keyword, args.max_results)
    elif args.action == "get_task_status":
        result = crawler.get_task_status(args.task_id)
    elif args.action == "list_tasks":
        result = crawler.list_tasks(args.status or None)
    elif args.action == "get_proxy_status":
        result = crawler.get_proxy_status()
    elif args.action == "get_crawl_stats":
        result = crawler.get_crawl_stats()
    else:
        result = {"error": f"未知操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
