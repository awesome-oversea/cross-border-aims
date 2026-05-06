import json
import os
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecom_mcp.db")

PLATFORM_CONFIG = {
    "taobao": {
        "name": "淘宝/天猫",
        "base_url": "https://eco.taobao.com/router",
        "auth_type": "oauth2",
        "env_app_key": "TAOBAO_APP_KEY",
        "env_app_secret": "TAOBAO_APP_SECRET",
        "env_session": "TAOBAO_SESSION_KEY",
        "rate_limit": {"calls_per_minute": 60, "calls_per_day": 50000},
    },
    "jd": {
        "name": "京东",
        "base_url": "https://api.jd.com/routerjson",
        "auth_type": "oauth2",
        "env_app_key": "JD_APP_KEY",
        "env_app_secret": "JD_APP_SECRET",
        "env_session": "JD_ACCESS_TOKEN",
        "rate_limit": {"calls_per_minute": 60, "calls_per_day": 100000},
    },
    "pdd": {
        "name": "拼多多",
        "base_url": "https://gw-api.pinduoduo.com/api/router",
        "auth_type": "oauth2",
        "env_app_key": "PDD_CLIENT_ID",
        "env_app_secret": "PDD_CLIENT_SECRET",
        "env_session": "PDD_ACCESS_TOKEN",
        "rate_limit": {"calls_per_minute": 100, "calls_per_day": 200000},
    },
}

TOOL_DEFINITIONS = {
    "ecom_product_list": {
        "description": "获取商品列表",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "page": "页码(默认1)", "page_size": "每页数量(默认20)", "status": "商品状态(onsale/offsale/all)"},
        "risk_level": "read",
    },
    "ecom_product_detail": {
        "description": "获取商品详情",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "product_id": "商品ID"},
        "risk_level": "read",
    },
    "ecom_product_update": {
        "description": "更新商品信息(标题/价格/库存)",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "product_id": "商品ID", "title": "新标题(可选)", "price": "新价格(可选)", "stock": "新库存(可选)"},
        "risk_level": "write",
    },
    "ecom_product_delete": {
        "description": "删除/下架商品",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "product_id": "商品ID"},
        "risk_level": "dangerous",
    },
    "ecom_order_list": {
        "description": "获取订单列表",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "page": "页码", "page_size": "每页数量", "status": "订单状态", "start_time": "开始时间", "end_time": "结束时间"},
        "risk_level": "read",
    },
    "ecom_order_detail": {
        "description": "获取订单详情",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "order_id": "订单ID"},
        "risk_level": "read",
    },
    "ecom_order_ship": {
        "description": "订单发货",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "order_id": "订单ID", "logistics_company": "物流公司", "tracking_number": "运单号"},
        "risk_level": "write",
    },
    "ecom_ad_campaign_list": {
        "description": "获取广告计划列表",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "page": "页码", "page_size": "每页数量"},
        "risk_level": "read",
    },
    "ecom_ad_campaign_update": {
        "description": "更新广告计划(预算/出价)",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "campaign_id": "计划ID", "budget": "日预算(可选)", "bid_price": "出价(可选)"},
        "risk_level": "write",
    },
    "ecom_review_list": {
        "description": "获取商品评价列表",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "product_id": "商品ID", "page": "页码", "page_size": "每页数量"},
        "risk_level": "read",
    },
    "ecom_review_reply": {
        "description": "回复商品评价",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "review_id": "评价ID", "content": "回复内容"},
        "risk_level": "write",
    },
    "ecom_refund_list": {
        "description": "获取退款/售后列表",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "status": "退款状态", "page": "页码", "page_size": "每页数量"},
        "risk_level": "read",
    },
    "ecom_refund_agree": {
        "description": "同意退款",
        "platforms": ["taobao", "jd", "pdd"],
        "params": {"platform": "平台标识", "refund_id": "退款ID"},
        "risk_level": "dangerous",
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
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            product_id TEXT NOT NULL,
            title TEXT NOT NULL,
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            status TEXT DEFAULT 'onsale',
            category TEXT DEFAULT '',
            sku_info TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(platform, product_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            order_id TEXT NOT NULL,
            buyer_id TEXT DEFAULT '',
            product_title TEXT DEFAULT '',
            quantity INTEGER DEFAULT 1,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            logistics_company TEXT DEFAULT '',
            tracking_number TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(platform, order_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            campaign_id TEXT NOT NULL,
            name TEXT NOT NULL,
            budget REAL DEFAULT 0,
            bid_price REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            cost REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(platform, campaign_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            review_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            content TEXT DEFAULT '',
            rating INTEGER DEFAULT 5,
            sentiment TEXT DEFAULT 'neutral',
            reply TEXT DEFAULT '',
            replied_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(platform, review_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            refund_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            amount REAL DEFAULT 0,
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(platform, refund_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            tool TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            risk_level TEXT DEFAULT 'read',
            status TEXT DEFAULT 'success',
            response_time_ms INTEGER DEFAULT 0,
            called_at TEXT NOT NULL
        )
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for platform in ["taobao", "jd", "pdd"]:
        for i in range(1, 6):
            pid = f"{platform}_prod_{i:04d}"
            c.execute("SELECT id FROM products WHERE platform=? AND product_id=?", (platform, pid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO products (platform, product_id, title, price, stock, status, category, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (platform, pid, f"测试商品{platform}-{i}", 99.9 * i, 100 * i, "onsale", "电子产品", now, now),
                )

        for i in range(1, 4):
            oid = f"{platform}_order_{i:04d}"
            c.execute("SELECT id FROM orders WHERE platform=? AND order_id=?", (platform, oid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO orders (platform, order_id, buyer_id, product_title, quantity, amount, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (platform, oid, f"buyer_{i:03d}", f"测试商品{platform}-{i}", i, 99.9 * i, "pending", now, now),
                )

        for i in range(1, 3):
            cid = f"{platform}_camp_{i:04d}"
            c.execute("SELECT id FROM ad_campaigns WHERE platform=? AND campaign_id=?", (platform, cid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO ad_campaigns (platform, campaign_id, name, budget, bid_price, status, impressions, clicks, cost, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (platform, cid, f"广告计划{platform}-{i}", 100 * i, 1.5 + i * 0.5, "active", 10000 * i, 500 * i, 50 * i, now, now),
                )

        for i in range(1, 4):
            rid = f"{platform}_review_{i:04d}"
            c.execute("SELECT id FROM reviews WHERE platform=? AND review_id=?", (platform, rid))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO reviews (platform, review_id, product_id, content, rating, sentiment, created_at) VALUES (?,?,?,?,?,?,?)",
                    (platform, rid, f"{platform}_prod_{i:04d}", f"这是第{i}条评价", 5 - (i - 1), "positive" if i <= 2 else "negative", now),
                )

    conn.commit()
    conn.close()


class EcomMCP:
    def __init__(self):
        init_db()
        self.credentials = self._load_credentials()

    def _load_credentials(self) -> Dict:
        creds = {}
        for platform, config in PLATFORM_CONFIG.items():
            app_key = os.environ.get(config["env_app_key"], "")
            app_secret = os.environ.get(config["env_app_secret"], "")
            session_key = os.environ.get(config["env_session"], "")
            creds[platform] = {
                "app_key": app_key,
                "app_secret_hash": hashlib.sha256(app_secret.encode()).hexdigest()[:16] if app_secret else "",
                "session_key": session_key,
                "configured": bool(app_key and app_secret),
            }
        return creds

    def _log_call(self, platform: str, tool: str, params: Dict, risk_level: str, status: str, response_time_ms: int):
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO api_call_logs (platform, tool, params, risk_level, status, response_time_ms, called_at) VALUES (?,?,?,?,?,?,?)",
            (platform, tool, json.dumps(params, ensure_ascii=False, default=str)[:500], risk_level, status, response_time_ms, now),
        )
        conn.commit()
        conn.close()

    def _check_platform(self, platform: str) -> Dict:
        if platform not in PLATFORM_CONFIG:
            return {"success": False, "error": f"不支持的平台: {platform}，支持: {list(PLATFORM_CONFIG.keys())}"}
        return {"success": True}

    def _check_write_permission(self, platform: str, risk_level: str) -> Dict:
        if risk_level == "dangerous":
            return {"success": True, "warning": "危险操作需要skill-gate人工确认", "gate_required": True}
        if risk_level == "write":
            if not self.credentials.get(platform, {}).get("configured"):
                return {"success": True, "warning": f"平台 {platform} 未配置API凭证，使用模拟模式", "mode": "simulated"}
        return {"success": True}

    def call_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name not in TOOL_DEFINITIONS:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool_def = TOOL_DEFINITIONS[tool_name]
        platform = params.get("platform", "")
        check = self._check_platform(platform)
        if not check["success"]:
            return check

        risk_level = tool_def["risk_level"]
        if risk_level in ("write", "dangerous"):
            perm = self._check_write_permission(platform, risk_level)
            if not perm["success"]:
                return perm

        start = time.time()
        try:
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler:
                result = handler(platform, params)
            else:
                result = self._handle_generic(platform, tool_name, params)

            elapsed = int((time.time() - start) * 1000)
            self._log_call(platform, tool_name, params, risk_level, "success", elapsed)
            result["platform"] = platform
            result["tool"] = tool_name
            result["risk_level"] = risk_level
            return result
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self._log_call(platform, tool_name, params, risk_level, "error", elapsed)
            return {"success": False, "error": str(e), "platform": platform, "tool": tool_name}

    def _handle_ecom_product_list(self, platform: str, params: Dict) -> Dict:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))
        status = params.get("status", "all")

        conn = get_db()
        c = conn.cursor()
        if status == "all":
            c.execute("SELECT * FROM products WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        else:
            c.execute("SELECT * FROM products WHERE platform=? AND status=? ORDER BY id LIMIT ? OFFSET ?", (platform, status, page_size, (page - 1) * page_size))

        rows = c.fetchall()
        c.execute("SELECT COUNT(*) as total FROM products WHERE platform=?", (platform,))
        total = c.fetchone()["total"]
        conn.close()

        products = []
        for row in rows:
            products.append({
                "product_id": row["product_id"],
                "title": row["title"],
                "price": row["price"],
                "stock": row["stock"],
                "status": row["status"],
                "category": row["category"],
            })

        return {"success": True, "total": total, "page": page, "page_size": page_size, "products": products}

    def _handle_ecom_product_detail(self, platform: str, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE platform=? AND product_id=?", (platform, product_id))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"商品 {product_id} 不存在"}

        return {
            "success": True,
            "product": {
                "product_id": row["product_id"],
                "title": row["title"],
                "price": row["price"],
                "stock": row["stock"],
                "status": row["status"],
                "category": row["category"],
                "sku_info": json.loads(row["sku_info"]) if row["sku_info"] else {},
            },
        }

    def _handle_ecom_product_update(self, platform: str, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE platform=? AND product_id=?", (platform, product_id))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": f"商品 {product_id} 不存在"}

        updates = []
        update_vals = []
        if "title" in params:
            updates.append("title=?")
            update_vals.append(params["title"])
        if "price" in params:
            updates.append("price=?")
            update_vals.append(float(params["price"]))
        if "stock" in params:
            updates.append("stock=?")
            update_vals.append(int(params["stock"]))

        if updates:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates.append("updated_at=?")
            update_vals.append(now)
            update_vals.extend([platform, product_id])
            c.execute(f"UPDATE products SET {', '.join(updates)} WHERE platform=? AND product_id=?", update_vals)
            conn.commit()

        conn.close()
        return {"success": True, "message": f"商品 {product_id} 已更新", "updated_fields": list(params.keys())}

    def _handle_ecom_product_delete(self, platform: str, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE products SET status='offsale', updated_at=? WHERE platform=? AND product_id=?", (now, platform, product_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"商品 {product_id} 已下架", "gate_required": True}

    def _handle_ecom_order_list(self, platform: str, params: Dict) -> Dict:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        c.execute("SELECT COUNT(*) as total FROM orders WHERE platform=?", (platform,))
        total = c.fetchone()["total"]
        conn.close()

        orders = []
        for row in rows:
            orders.append({
                "order_id": row["order_id"],
                "buyer_id": row["buyer_id"],
                "product_title": row["product_title"],
                "quantity": row["quantity"],
                "amount": row["amount"],
                "status": row["status"],
            })

        return {"success": True, "total": total, "page": page, "page_size": page_size, "orders": orders}

    def _handle_ecom_order_detail(self, platform: str, params: Dict) -> Dict:
        order_id = params.get("order_id", "")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE platform=? AND order_id=?", (platform, order_id))
        row = c.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"订单 {order_id} 不存在"}

        return {
            "success": True,
            "order": {
                "order_id": row["order_id"],
                "buyer_id": row["buyer_id"],
                "product_title": row["product_title"],
                "quantity": row["quantity"],
                "amount": row["amount"],
                "status": row["status"],
                "logistics_company": row["logistics_company"],
                "tracking_number": row["tracking_number"],
            },
        }

    def _handle_ecom_order_ship(self, platform: str, params: Dict) -> Dict:
        order_id = params.get("order_id", "")
        logistics_company = params.get("logistics_company", "")
        tracking_number = params.get("tracking_number", "")

        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "UPDATE orders SET status='shipped', logistics_company=?, tracking_number=?, updated_at=? WHERE platform=? AND order_id=?",
            (logistics_company, tracking_number, now, platform, order_id),
        )
        conn.commit()
        conn.close()

        return {"success": True, "message": f"订单 {order_id} 已发货", "logistics_company": logistics_company, "tracking_number": tracking_number}

    def _handle_ecom_ad_campaign_list(self, platform: str, params: Dict) -> Dict:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM ad_campaigns WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        conn.close()

        campaigns = []
        for row in rows:
            campaigns.append({
                "campaign_id": row["campaign_id"],
                "name": row["name"],
                "budget": row["budget"],
                "bid_price": row["bid_price"],
                "status": row["status"],
                "impressions": row["impressions"],
                "clicks": row["clicks"],
                "cost": row["cost"],
                "ctr": round(row["clicks"] / max(row["impressions"], 1) * 100, 2),
            })

        return {"success": True, "campaigns": campaigns}

    def _handle_ecom_ad_campaign_update(self, platform: str, params: Dict) -> Dict:
        campaign_id = params.get("campaign_id", "")
        conn = get_db()
        c = conn.cursor()

        updates = []
        update_vals = []
        if "budget" in params:
            updates.append("budget=?")
            update_vals.append(float(params["budget"]))
        if "bid_price" in params:
            updates.append("bid_price=?")
            update_vals.append(float(params["bid_price"]))

        if updates:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates.append("updated_at=?")
            update_vals.append(now)
            update_vals.extend([platform, campaign_id])
            c.execute(f"UPDATE ad_campaigns SET {', '.join(updates)} WHERE platform=? AND campaign_id=?", update_vals)
            conn.commit()

        conn.close()
        return {"success": True, "message": f"广告计划 {campaign_id} 已更新"}

    def _handle_ecom_review_list(self, platform: str, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))

        conn = get_db()
        c = conn.cursor()
        if product_id:
            c.execute("SELECT * FROM reviews WHERE platform=? AND product_id=? ORDER BY id LIMIT ? OFFSET ?", (platform, product_id, page_size, (page - 1) * page_size))
        else:
            c.execute("SELECT * FROM reviews WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        conn.close()

        reviews = []
        for row in rows:
            reviews.append({
                "review_id": row["review_id"],
                "product_id": row["product_id"],
                "content": row["content"],
                "rating": row["rating"],
                "sentiment": row["sentiment"],
                "reply": row["reply"],
            })

        return {"success": True, "reviews": reviews}

    def _handle_ecom_review_reply(self, platform: str, params: Dict) -> Dict:
        review_id = params.get("review_id", "")
        content = params.get("content", "")

        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE reviews SET reply=?, replied_at=? WHERE platform=? AND review_id=?", (content, now, platform, review_id))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"评价 {review_id} 已回复"}

    def _handle_ecom_refund_list(self, platform: str, params: Dict) -> Dict:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM refunds WHERE platform=? ORDER BY id LIMIT ? OFFSET ?", (platform, page_size, (page - 1) * page_size))
        rows = c.fetchall()
        conn.close()

        refunds = []
        for row in rows:
            refunds.append({
                "refund_id": row["refund_id"],
                "order_id": row["order_id"],
                "amount": row["amount"],
                "reason": row["reason"],
                "status": row["status"],
            })

        return {"success": True, "refunds": refunds}

    def _handle_ecom_refund_agree(self, platform: str, params: Dict) -> Dict:
        refund_id = params.get("refund_id", "")
        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE refunds SET status='agreed', updated_at=? WHERE platform=? AND refund_id=?", (now, platform, refund_id))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"退款 {refund_id} 已同意", "gate_required": True}

    def _handle_generic(self, platform: str, tool_name: str, params: Dict) -> Dict:
        return {"success": False, "error": f"工具 {tool_name} 处理器未实现"}

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
            }
        return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description="E-commerce MCP Server")
    parser.add_argument("--action", required=True)
    parser.add_argument("--tool", default="")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()

    mcp = EcomMCP()

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
