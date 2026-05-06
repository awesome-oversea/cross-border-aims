#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orders.db')

ORDER_STATUS_MAP = {
    "pending": {"label": "待付款", "color": "#fac858", "sort_order": 1},
    "paid": {"label": "已付款", "color": "#5470c6", "sort_order": 2},
    "processing": {"label": "处理中", "color": "#9a60b4", "sort_order": 3},
    "shipped": {"label": "已发货", "color": "#91cc75", "sort_order": 4},
    "delivered": {"label": "已送达", "color": "#30bf78", "sort_order": 5},
    "completed": {"label": "已完成", "color": "#73c0de", "sort_order": 6},
    "cancelled": {"label": "已取消", "color": "#ee6666", "sort_order": 7},
    "refunding": {"label": "退款中", "color": "#fc8452", "sort_order": 8},
}

STATUS_TRANSITIONS = {
    "pending": ["paid", "cancelled"],
    "paid": ["processing", "cancelled", "refunding"],
    "processing": ["shipped", "cancelled", "refunding"],
    "shipped": ["delivered", "refunding"],
    "delivered": ["completed", "refunding"],
    "completed": ["refunding"],
    "cancelled": [],
    "refunding": ["completed", "cancelled"],
}

STATUS_NEXT_STEP = {
    "pending": {"action": "付款", "description": "请尽快完成付款，超时订单将自动取消", "timeout_hours": 24},
    "paid": {"action": "等待发货", "description": "商家正在准备发货，预计1-2个工作日", "timeout_hours": 48},
    "processing": {"action": "备货中", "description": "商品正在打包，即将发货", "timeout_hours": 24},
    "shipped": {"action": "查看物流", "description": "商品已发出，可查看物流详情", "timeout_hours": 120},
    "delivered": {"action": "确认收货", "description": "商品已送达，请确认收货", "timeout_hours": 168},
    "completed": {"action": "评价", "description": "订单已完成，期待您的评价", "timeout_hours": None},
    "cancelled": {"action": "重新购买", "description": "订单已取消，可重新下单", "timeout_hours": None},
    "refunding": {"action": "查看退款", "description": "退款处理中，请耐心等待", "timeout_hours": 72},
}

PLATFORM_ORDER_RULES = {
    'amazon': {
        'name': 'Amazon',
        'order_id_prefix': 'AMZ',
        'auto_cancel_hours': 30,
        'return_window_days': 30,
        'feedback_window_days': 90,
    },
    'taobao': {
        'name': '淘宝',
        'order_id_prefix': 'TB',
        'auto_cancel_hours': 24,
        'return_window_days': 7,
        'feedback_window_days': 15,
    },
    'jd': {
        'name': '京东',
        'order_id_prefix': 'JD',
        'auto_cancel_hours': 24,
        'return_window_days': 7,
        'feedback_window_days': 30,
    },
    'pinduoduo': {
        'name': '拼多多',
        'order_id_prefix': 'PDD',
        'auto_cancel_hours': 24,
        'return_window_days': 7,
        'feedback_window_days': 15,
    },
    'shopee': {
        'name': 'Shopee',
        'order_id_prefix': 'SPE',
        'auto_cancel_hours': 24,
        'return_window_days': 7,
        'feedback_window_days': 15,
    },
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        platform TEXT DEFAULT 'amazon',
        status TEXT DEFAULT 'pending',
        buyer_phone TEXT,
        buyer_name TEXT,
        total_amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'CNY',
        shipping_address TEXT,
        tracking_number TEXT,
        created_at TEXT,
        updated_at TEXT,
        paid_at TEXT,
        shipped_at TEXT,
        completed_at TEXT,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        product_name TEXT,
        sku TEXT,
        quantity INTEGER DEFAULT 1,
        unit_price REAL DEFAULT 0,
        subtotal REAL DEFAULT 0,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS order_timeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        status TEXT,
        description TEXT,
        operator TEXT DEFAULT 'system',
        created_at TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    )''')
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_order(order_id: str = "", phone: str = "", platform: str = "") -> Dict:
    conn = get_db_connection()
    c = conn.cursor()

    if order_id:
        c.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    elif phone:
        c.execute("SELECT * FROM orders WHERE buyer_phone = ? ORDER BY created_at DESC", (phone,))
    else:
        conn.close()
        return {"error": "需要提供order_id或phone"}

    rows = c.fetchall()
    if not rows:
        conn.close()
        return _generate_simulated_order(order_id, phone, platform)

    orders = []
    for row in rows:
        order = dict(row)
        c.execute("SELECT * FROM order_items WHERE order_id = ?", (order['order_id'],))
        items = [dict(i) for i in c.fetchall()]
        c.execute("SELECT * FROM order_timeline WHERE order_id = ? ORDER BY created_at", (order['order_id'],))
        timeline = [dict(t) for t in c.fetchall()]
        order['items'] = items
        order['timeline'] = timeline
        order['statusInfo'] = ORDER_STATUS_MAP.get(order['status'], {})
        order['nextStep'] = STATUS_NEXT_STEP.get(order['status'], {})
        orders.append(order)

    conn.close()
    return {"orders": orders, "source": "database"}


def _generate_simulated_order(order_id: str, phone: str, platform: str) -> Dict:
    if not order_id:
        prefix = PLATFORM_ORDER_RULES.get(platform, PLATFORM_ORDER_RULES['amazon'])['order_id_prefix']
        order_id = f"{prefix}{datetime.now().strftime('%Y%m%d')}{hash(phone) % 10000:04d}"

    status_list = list(ORDER_STATUS_MAP.keys())
    idx = int(order_id[-2:]) % len(status_list) if len(order_id) >= 2 else 0
    status = status_list[idx]

    items = [
        {"product_name": "智能手表 Pro", "sku": "SW-2024-001", "quantity": 1, "unit_price": 899, "subtotal": 899},
        {"product_name": "无线蓝牙耳机", "sku": "BT-2024-003", "quantity": 2, "unit_price": 199, "subtotal": 398},
    ]
    total = sum(i["subtotal"] for i in items)

    now = datetime.now()
    create_time = now - timedelta(days=int(order_id[-2:]) % 15)
    timeline = []
    status_order = ["pending", "paid", "processing", "shipped", "delivered", "completed"]
    current_idx = status_order.index(status) if status in status_order else 0
    for i in range(current_idx + 1):
        t = create_time + timedelta(hours=i * 8)
        timeline.append({
            "status": status_order[i],
            "description": STATUS_NEXT_STEP.get(status_order[i], {}).get("description", ""),
            "operator": "system",
            "created_at": t.strftime("%Y-%m-%d %H:%M:%S"),
        })

    order = {
        "order_id": order_id,
        "platform": platform or "amazon",
        "status": status,
        "statusInfo": ORDER_STATUS_MAP.get(status, {}),
        "nextStep": STATUS_NEXT_STEP.get(status, {}),
        "buyer_phone": phone or "138****8888",
        "total_amount": total,
        "currency": "CNY",
        "items": items,
        "timeline": timeline,
        "created_at": create_time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {"orders": [order], "source": "simulated"}


def batch_query_orders(order_ids: List[str] = None, statuses: List[str] = None,
                       platform: str = "", date_from: str = "", date_to: str = "",
                       page: int = 1, page_size: int = 20) -> Dict:
    conn = get_db_connection()
    c = conn.cursor()

    conditions = []
    params = []
    if order_ids:
        placeholders = ','.join(['?'] * len(order_ids))
        conditions.append(f"order_id IN ({placeholders})")
        params.extend(order_ids)
    if statuses:
        placeholders = ','.join(['?'] * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("created_at <= ?")
        params.append(date_to)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    c.execute(f"SELECT COUNT(*) FROM orders{where_clause}", params)
    total = c.fetchone()[0]

    offset = (page - 1) * page_size
    c.execute(f"SELECT * FROM orders{where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
              params + [page_size, offset])
    rows = c.fetchall()

    orders = []
    for row in rows:
        order = dict(row)
        c.execute("SELECT * FROM order_items WHERE order_id = ?", (order['order_id'],))
        order['items'] = [dict(i) for i in c.fetchall()]
        order['statusInfo'] = ORDER_STATUS_MAP.get(order['status'], {})
        orders.append(order)

    conn.close()

    status_summary = {}
    for o in orders:
        s = o.get('status', 'unknown')
        status_summary[s] = status_summary.get(s, 0) + 1

    return {
        "orders": orders,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": (total + page_size - 1) // page_size,
        },
        "statusSummary": status_summary,
        "source": "database" if total > 0 else "empty",
    }


def get_order_statistics(platform: str = "", days: int = 30) -> Dict:
    conn = get_db_connection()
    c = conn.cursor()

    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = [date_from]
    platform_condition = ""
    if platform:
        platform_condition = " AND platform = ?"
        params.append(platform)

    c.execute(f"SELECT status, COUNT(*) as count FROM orders WHERE created_at >= ?{platform_condition} GROUP BY status", params)
    status_counts = {row['status']: row['count'] for row in c.fetchall()}

    c.execute(f"SELECT COUNT(*) as total, SUM(total_amount) as revenue FROM orders WHERE created_at >= ? AND status != 'cancelled'{platform_condition}", params)
    row = c.fetchone()
    total_orders = row['total'] or 0
    total_revenue = row['revenue'] or 0

    c.execute(f"SELECT DATE(created_at) as date, COUNT(*) as count, SUM(total_amount) as revenue FROM orders WHERE created_at >= ?{platform_condition} GROUP BY DATE(created_at) ORDER BY date", params)
    daily_stats = [{"date": r['date'], "orders": r['count'], "revenue": r['revenue'] or 0} for r in c.fetchall()]

    conn.close()

    return {
        "period": f"近{days}天",
        "platform": platform or "全部",
        "totalOrders": total_orders,
        "totalRevenue": round(total_revenue, 2),
        "statusDistribution": status_counts,
        "dailyStats": daily_stats,
        "avgOrderValue": round(total_revenue / max(total_orders, 1), 2),
    }


def query_order_info(input_data: Dict) -> Dict:
    action = input_data.get('action', 'query')
    order_id = input_data.get('order_id', '')
    phone = input_data.get('phone', '')
    platform = input_data.get('platform', 'amazon')

    if action == 'query':
        if not order_id and not phone:
            return {"error": "需要提供order_id或phone"}
        result = query_order(order_id, phone, platform)
        orders = result.get('orders', [])
        if orders:
            order = orders[0]
            needs_human = order['status'] in ('refunding', 'cancelled')
            result["handoff"] = {
                "needsHumanReview": needs_human,
                "reason": "订单处于退款/取消状态，需人工确认" if needs_human else "",
                "confidence": 95.0 if result['source'] == 'database' else 60.0,
                "gate": "auto" if not needs_human else "notify",
            }
        return result

    elif action == 'batch_query':
        return batch_query_orders(
            order_ids=input_data.get('order_ids'),
            statuses=input_data.get('statuses'),
            platform=platform,
            date_from=input_data.get('date_from', ''),
            date_to=input_data.get('date_to', ''),
            page=input_data.get('page', 1),
            page_size=input_data.get('page_size', 20),
        )

    elif action == 'statistics':
        return get_order_statistics(platform, input_data.get('days', 30))

    else:
        return {"error": f"不支持的操作: {action}"}


def main():
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        print(json.dumps({'error': '无效的JSON输入'}, ensure_ascii=False))
        return

    init_db()
    result = query_order_info(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
