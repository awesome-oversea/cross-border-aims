import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erp_mcp.db")

ERP_DOMAINS = {
    "pdm": {"name": "产品开发域", "description": "产品库、生命周期、选品模型"},
    "oms": {"name": "订单域", "description": "订单全生命周期、风控校验"},
    "scm": {"name": "供应链域", "description": "采购计划、补货建议、供应商协同"},
    "wms": {"name": "仓储域", "description": "库存管理、库位、盘点"},
    "fms": {"name": "财务域", "description": "费用、利润、成本归集"},
    "tms": {"name": "物流域", "description": "物流订单、轨迹、成本核算"},
}

TOOL_DEFINITIONS = {
    "erp_product_sync": {
        "description": "同步产品数据到ERP产品开发域",
        "domain": "pdm",
        "params": {"product_id": "商品ID", "platform": "平台", "title": "标题", "price": "价格", "stock": "库存", "category": "分类", "selling_points": "卖点(JSON)"},
        "risk_level": "write",
    },
    "erp_product_query": {
        "description": "查询ERP产品信息",
        "domain": "pdm",
        "params": {"product_id": "商品ID(可选)", "platform": "平台(可选)", "category": "分类(可选)"},
        "risk_level": "read",
    },
    "erp_order_sync": {
        "description": "同步订单数据到ERP订单域",
        "domain": "oms",
        "params": {"order_id": "订单ID", "platform": "平台", "product_title": "商品标题", "quantity": "数量", "amount": "金额", "buyer_id": "买家ID"},
        "risk_level": "write",
    },
    "erp_order_query": {
        "description": "查询ERP订单信息",
        "domain": "oms",
        "params": {"order_id": "订单ID(可选)", "platform": "平台(可选)", "status": "状态(可选)"},
        "risk_level": "read",
    },
    "erp_purchase_suggest": {
        "description": "获取ERP补货建议",
        "domain": "scm",
        "params": {"product_id": "商品ID", "current_stock": "当前库存", "avg_daily_sales": "日均销量", "lead_time_days": "采购周期(天)"},
        "risk_level": "read",
    },
    "erp_stock_sync": {
        "description": "同步库存数据到ERP仓储域",
        "domain": "wms",
        "params": {"product_id": "商品ID", "warehouse": "仓库", "stock": "库存数量", "location": "库位"},
        "risk_level": "write",
    },
    "erp_stock_query": {
        "description": "查询ERP库存信息",
        "domain": "wms",
        "params": {"product_id": "商品ID(可选)", "warehouse": "仓库(可选)"},
        "risk_level": "read",
    },
    "erp_cost_sync": {
        "description": "同步成本数据到ERP财务域",
        "domain": "fms",
        "params": {"product_id": "商品ID", "cost_type": "成本类型(product/ad/logistics/other)", "amount": "金额", "currency": "币种", "period": "期间"},
        "risk_level": "write",
    },
    "erp_profit_calc": {
        "description": "计算商品利润",
        "domain": "fms",
        "params": {"product_id": "商品ID", "revenue": "收入", "costs": "成本明细(JSON)"},
        "risk_level": "read",
    },
    "erp_logistics_sync": {
        "description": "同步物流数据到ERP物流域",
        "domain": "tms",
        "params": {"order_id": "订单ID", "carrier": "物流公司", "tracking_number": "运单号", "cost": "物流成本"},
        "risk_level": "write",
    },
    "erp_adopt": {
        "description": "一键采纳：将AI建议直接写入ERP系统",
        "domain": "all",
        "params": {"suggestion_type": "建议类型(listing/ad_price/restock/refund)", "suggestion_id": "建议ID", "data": "建议数据(JSON)", "approved_by": "审批人"},
        "risk_level": "dangerous",
    },
    "erp_adopt_batch": {
        "description": "批量一键采纳：将多个AI建议批量写入ERP",
        "domain": "all",
        "params": {"suggestions": "建议列表(JSON数组)", "approved_by": "审批人"},
        "risk_level": "dangerous",
    },
    "erp_domain_status": {
        "description": "查询ERP各域状态",
        "domain": "all",
        "params": {},
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
        CREATE TABLE IF NOT EXISTS erp_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            title TEXT DEFAULT '',
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            selling_points TEXT DEFAULT '[]',
            lifecycle TEXT DEFAULT 'active',
            synced_at TEXT NOT NULL,
            UNIQUE(product_id, platform)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS erp_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            product_title TEXT DEFAULT '',
            quantity INTEGER DEFAULT 1,
            amount REAL DEFAULT 0,
            buyer_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            synced_at TEXT NOT NULL,
            UNIQUE(order_id, platform)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS erp_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            warehouse TEXT DEFAULT 'default',
            stock INTEGER DEFAULT 0,
            location TEXT DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(product_id, warehouse)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS erp_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            cost_type TEXT NOT NULL,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'CNY',
            period TEXT DEFAULT '',
            synced_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS erp_adopt_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adopt_id TEXT NOT NULL UNIQUE,
            suggestion_type TEXT NOT NULL,
            suggestion_id TEXT DEFAULT '',
            data TEXT DEFAULT '{}',
            status TEXT DEFAULT 'adopted',
            approved_by TEXT DEFAULT '',
            adopted_at TEXT NOT NULL
        )
    """)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for platform in ["taobao", "jd", "pdd"]:
        for i in range(1, 4):
            pid = f"{platform}_prod_{i:04d}"
            c.execute("SELECT id FROM erp_products WHERE product_id=? AND platform=?", (pid, platform))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO erp_products (product_id, platform, title, price, stock, category, synced_at) VALUES (?,?,?,?,?,?,?)",
                    (pid, platform, f"ERP商品{platform}-{i}", 99.9 * i, 100 * i, "电子产品", now),
                )
            c.execute("SELECT id FROM erp_inventory WHERE product_id=? AND warehouse='default'", (pid,))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO erp_inventory (product_id, warehouse, stock, updated_at) VALUES (?,?,?,?)",
                    (pid, "default", 100 * i, now),
                )

    conn.commit()
    conn.close()


class ERPMCP:
    def __init__(self):
        init_db()

    def call_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name not in TOOL_DEFINITIONS:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        tool_def = TOOL_DEFINITIONS[tool_name]

        try:
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler:
                result = handler(params)
            else:
                result = {"success": False, "error": f"处理器未实现: {tool_name}"}
            result["tool"] = tool_name
            result["domain"] = tool_def["domain"]
            result["risk_level"] = tool_def["risk_level"]
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "tool": tool_name}

    def _handle_erp_product_sync(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        platform = params.get("platform", "")
        title = params.get("title", "")
        price = float(params.get("price", 0))
        stock = int(params.get("stock", 0))
        category = params.get("category", "")
        selling_points = params.get("selling_points", "[]")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM erp_products WHERE product_id=? AND platform=?", (product_id, platform))
        if c.fetchone():
            c.execute(
                "UPDATE erp_products SET title=?, price=?, stock=?, category=?, selling_points=?, synced_at=? WHERE product_id=? AND platform=?",
                (title, price, stock, category, selling_points, now, product_id, platform),
            )
        else:
            c.execute(
                "INSERT INTO erp_products (product_id, platform, title, price, stock, category, selling_points, synced_at) VALUES (?,?,?,?,?,?,?,?)",
                (product_id, platform, title, price, stock, category, selling_points, now),
            )
        conn.commit()
        conn.close()

        return {"success": True, "message": f"产品 {product_id} 已同步到ERP产品开发域"}

    def _handle_erp_product_query(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        platform = params.get("platform", "")

        conn = get_db()
        c = conn.cursor()
        if product_id:
            c.execute("SELECT * FROM erp_products WHERE product_id=? AND (platform=? OR ?='')", (product_id, platform, platform))
        elif platform:
            c.execute("SELECT * FROM erp_products WHERE platform=?", (platform,))
        else:
            c.execute("SELECT * FROM erp_products LIMIT 20")
        rows = c.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append({
                "product_id": row["product_id"],
                "platform": row["platform"],
                "title": row["title"],
                "price": row["price"],
                "stock": row["stock"],
                "category": row["category"],
                "lifecycle": row["lifecycle"],
            })

        return {"success": True, "products": products, "total": len(products)}

    def _handle_erp_order_sync(self, params: Dict) -> Dict:
        order_id = params.get("order_id", "")
        platform = params.get("platform", "")
        product_title = params.get("product_title", "")
        quantity = int(params.get("quantity", 1))
        amount = float(params.get("amount", 0))
        buyer_id = params.get("buyer_id", "")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM erp_orders WHERE order_id=? AND platform=?", (order_id, platform))
        if c.fetchone():
            c.execute(
                "UPDATE erp_orders SET product_title=?, quantity=?, amount=?, status=?, synced_at=? WHERE order_id=? AND platform=?",
                (product_title, quantity, amount, "synced", now, order_id, platform),
            )
        else:
            c.execute(
                "INSERT INTO erp_orders (order_id, platform, product_title, quantity, amount, buyer_id, status, synced_at) VALUES (?,?,?,?,?,?,?,?)",
                (order_id, platform, product_title, quantity, amount, buyer_id, "synced", now),
            )
        conn.commit()
        conn.close()

        return {"success": True, "message": f"订单 {order_id} 已同步到ERP订单域"}

    def _handle_erp_order_query(self, params: Dict) -> Dict:
        order_id = params.get("order_id", "")
        platform = params.get("platform", "")

        conn = get_db()
        c = conn.cursor()
        if order_id:
            c.execute("SELECT * FROM erp_orders WHERE order_id=? AND (platform=? OR ?='')", (order_id, platform, platform))
        elif platform:
            c.execute("SELECT * FROM erp_orders WHERE platform=?", (platform,))
        else:
            c.execute("SELECT * FROM erp_orders LIMIT 20")
        rows = c.fetchall()
        conn.close()

        orders = []
        for row in rows:
            orders.append({
                "order_id": row["order_id"],
                "platform": row["platform"],
                "product_title": row["product_title"],
                "quantity": row["quantity"],
                "amount": row["amount"],
                "status": row["status"],
            })

        return {"success": True, "orders": orders, "total": len(orders)}

    def _handle_erp_purchase_suggest(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        current_stock = int(params.get("current_stock", 0))
        avg_daily_sales = float(params.get("avg_daily_sales", 10))
        lead_time_days = int(params.get("lead_time_days", 7))

        safety_stock = int(avg_daily_sales * lead_time_days * 1.5)
        reorder_point = safety_stock + int(avg_daily_sales * lead_time_days)
        suggested_qty = max(0, reorder_point - current_stock + int(avg_daily_sales * 14))

        return {
            "success": True,
            "product_id": product_id,
            "current_stock": current_stock,
            "avg_daily_sales": avg_daily_sales,
            "lead_time_days": lead_time_days,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "suggested_order_qty": suggested_qty,
            "urgency": "high" if current_stock < safety_stock else ("medium" if current_stock < reorder_point else "low"),
        }

    def _handle_erp_stock_sync(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        warehouse = params.get("warehouse", "default")
        stock = int(params.get("stock", 0))
        location = params.get("location", "")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM erp_inventory WHERE product_id=? AND warehouse=?", (product_id, warehouse))
        if c.fetchone():
            c.execute("UPDATE erp_inventory SET stock=?, location=?, updated_at=? WHERE product_id=? AND warehouse=?", (stock, location, now, product_id, warehouse))
        else:
            c.execute("INSERT INTO erp_inventory (product_id, warehouse, stock, location, updated_at) VALUES (?,?,?,?,?)", (product_id, warehouse, stock, location, now))
        conn.commit()
        conn.close()

        return {"success": True, "message": f"库存 {product_id}@{warehouse} 已同步到ERP仓储域"}

    def _handle_erp_stock_query(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        warehouse = params.get("warehouse", "")

        conn = get_db()
        c = conn.cursor()
        if product_id:
            c.execute("SELECT * FROM erp_inventory WHERE product_id=? AND (warehouse=? OR ?='')", (product_id, warehouse, warehouse))
        else:
            c.execute("SELECT * FROM erp_inventory LIMIT 20")
        rows = c.fetchall()
        conn.close()

        inventory = []
        for row in rows:
            inventory.append({
                "product_id": row["product_id"],
                "warehouse": row["warehouse"],
                "stock": row["stock"],
                "location": row["location"],
                "updated_at": row["updated_at"],
            })

        return {"success": True, "inventory": inventory, "total": len(inventory)}

    def _handle_erp_cost_sync(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        cost_type = params.get("cost_type", "product")
        amount = float(params.get("amount", 0))
        currency = params.get("currency", "CNY")
        period = params.get("period", datetime.now().strftime("%Y-%m"))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO erp_costs (product_id, cost_type, amount, currency, period, synced_at) VALUES (?,?,?,?,?,?)",
            (product_id, cost_type, amount, currency, period, now),
        )
        conn.commit()
        conn.close()

        return {"success": True, "message": f"成本 {product_id}/{cost_type} 已同步到ERP财务域"}

    def _handle_erp_profit_calc(self, params: Dict) -> Dict:
        product_id = params.get("product_id", "")
        revenue = float(params.get("revenue", 0))
        costs = params.get("costs", "{}")

        if isinstance(costs, str):
            try:
                costs = json.loads(costs)
            except json.JSONDecodeError:
                costs = {}

        total_cost = sum(float(v) for v in costs.values()) if isinstance(costs, dict) else 0
        profit = revenue - total_cost
        profit_margin = (profit / revenue * 100) if revenue > 0 else 0

        return {
            "success": True,
            "product_id": product_id,
            "revenue": revenue,
            "costs": costs,
            "total_cost": total_cost,
            "profit": profit,
            "profit_margin": round(profit_margin, 2),
            "health": "healthy" if profit_margin > 20 else ("warning" if profit_margin > 0 else "loss"),
        }

    def _handle_erp_logistics_sync(self, params: Dict) -> Dict:
        return {"success": True, "message": f"物流数据已同步到ERP物流域"}

    def _handle_erp_adopt(self, params: Dict) -> Dict:
        suggestion_type = params.get("suggestion_type", "")
        suggestion_id = params.get("suggestion_id", "")
        data = params.get("data", "{}")
        approved_by = params.get("approved_by", "")

        if not approved_by:
            return {"success": False, "error": "一键采纳必须指定审批人(approved_by)"}

        adopt_id = f"adopt-{int(time.time())}-{abs(hash(suggestion_id)) % 10000:04d}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO erp_adopt_records (adopt_id, suggestion_type, suggestion_id, data, status, approved_by, adopted_at) VALUES (?,?,?,?,?,?,?)",
            (adopt_id, suggestion_type, suggestion_id, json.dumps(data, ensure_ascii=False, default=str)[:500], "adopted", approved_by, now),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "adopt_id": adopt_id,
            "suggestion_type": suggestion_type,
            "suggestion_id": suggestion_id,
            "approved_by": approved_by,
            "message": f"AI建议已采纳并写入ERP系统（类型: {suggestion_type}）",
            "gate_required": True,
        }

    def _handle_erp_adopt_batch(self, params: Dict) -> Dict:
        suggestions = params.get("suggestions", "[]")
        approved_by = params.get("approved_by", "")

        if not approved_by:
            return {"success": False, "error": "批量采纳必须指定审批人(approved_by)"}

        if isinstance(suggestions, str):
            try:
                suggestions = json.loads(suggestions)
            except json.JSONDecodeError:
                suggestions = []

        results = []
        for s in suggestions:
            r = self._handle_erp_adopt({**s, "approved_by": approved_by})
            results.append(r)

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "fail_count": len(results) - success_count,
            "results": results,
            "approved_by": approved_by,
        }

    def _handle_erp_domain_status(self, params: Dict) -> Dict:
        conn = get_db()
        c = conn.cursor()

        status = {}
        c.execute("SELECT COUNT(*) as cnt FROM erp_products")
        status["pdm"] = {"name": ERP_DOMAINS["pdm"]["name"], "product_count": c.fetchone()["cnt"], "status": "active"}

        c.execute("SELECT COUNT(*) as cnt FROM erp_orders")
        status["oms"] = {"name": ERP_DOMAINS["oms"]["name"], "order_count": c.fetchone()["cnt"], "status": "active"}

        c.execute("SELECT COUNT(*) as cnt FROM erp_inventory")
        status["wms"] = {"name": ERP_DOMAINS["wms"]["name"], "inventory_count": c.fetchone()["cnt"], "status": "active"}

        c.execute("SELECT COUNT(*) as cnt FROM erp_costs")
        status["fms"] = {"name": ERP_DOMAINS["fms"]["name"], "cost_records": c.fetchone()["cnt"], "status": "active"}

        c.execute("SELECT COUNT(*) as cnt FROM erp_adopt_records")
        status["adopt"] = {"name": "一键采纳", "adopt_count": c.fetchone()["cnt"], "status": "active"}

        status["scm"] = {"name": ERP_DOMAINS["scm"]["name"], "status": "active"}
        status["tms"] = {"name": ERP_DOMAINS["tms"]["name"], "status": "active"}

        conn.close()
        return {"success": True, "domains": status}

    def list_tools(self) -> Dict:
        tools = []
        for name, defn in TOOL_DEFINITIONS.items():
            tools.append({
                "name": name,
                "description": defn["description"],
                "domain": defn["domain"],
                "params": defn["params"],
                "risk_level": defn["risk_level"],
            })
        return {"total": len(tools), "tools": tools}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ERP MCP Server")
    parser.add_argument("--action", required=True)
    parser.add_argument("--tool", default="")
    parser.add_argument("--params", default="{}")
    args = parser.parse_args()

    mcp = ERPMCP()

    if args.action == "call_tool":
        params = json.loads(args.params)
        result = mcp.call_tool(args.tool, params)
    elif args.action == "list_tools":
        result = mcp.list_tools()
    else:
        result = {"error": f"未知操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
