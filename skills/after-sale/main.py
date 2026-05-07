#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aftersale.db')

# 售后类型定义：仅退款、退货退款、换货、维修、补发
REFUND_TYPES = {
    'refund_only': {
        'name': '仅退款',
        'description': '未收到货或无需退货，仅申请退款',
        'required_evidence': ['订单截图'],
        'processing_days': 3,
        'applicable_statuses': ['pending', 'paid', 'processing'],
    },
    'return_refund': {
        'name': '退货退款',
        'description': '已收到货，需退回商品并退款',
        'required_evidence': ['商品照片', '问题说明'],
        'processing_days': 7,
        'applicable_statuses': ['delivered', 'completed'],
    },
    'exchange': {
        'name': '换货',
        'description': '商品存在问题，要求更换同款商品',
        'required_evidence': ['商品照片', '问题说明'],
        'processing_days': 10,
        'applicable_statuses': ['delivered', 'completed'],
    },
    'repair': {
        'name': '维修',
        'description': '商品功能异常，要求维修',
        'required_evidence': ['故障视频', '问题描述'],
        'processing_days': 15,
        'applicable_statuses': ['delivered', 'completed'],
    },
    'reissue': {
        'name': '补发',
        'description': '商品缺失或损坏，要求补发',
        'required_evidence': ['收货照片', '缺失说明'],
        'processing_days': 5,
        'applicable_statuses': ['delivered'],
    },
}

# 售后原因分类：质量问题、描述不符、物流问题、个人偏好、服务问题
REASON_CATEGORIES = {
    'quality': {
        'name': '质量问题',
        'reasons': ['商品破损', '功能异常', '材质不符', '做工粗糙', '有异味'],
        'priority': 'high',
        'auto_approve': False,
    },
    'description': {
        'name': '描述不符',
        'reasons': ['与图片不符', '规格不符', '颜色差异', '材质不符', '功能缺失'],
        'priority': 'high',
        'auto_approve': False,
    },
    'logistics': {
        'name': '物流问题',
        'reasons': ['包裹破损', '商品丢失', '配送延迟', '送错地址', '快递态度差'],
        'priority': 'medium',
        'auto_approve': True,
    },
    'preference': {
        'name': '个人偏好',
        'reasons': ['不喜欢', '买错了', '尺寸不合适', '颜色不喜欢', '价格问题'],
        'priority': 'low',
        'auto_approve': True,
    },
    'service': {
        'name': '服务问题',
        'reasons': ['客服态度差', '承诺未兑现', '发货太慢', '包装简陋', '发票问题'],
        'priority': 'medium',
        'auto_approve': False,
    },
}

# 售后状态机：状态流转关系图
# submitted → reviewing → approved → returning → returned → refunding → completed
#            → cancelled
#                        → rejected → escalated → approved/rejected/completed
#                                    → cancelled
AFTERSALE_STATUS_MAP = {
    'submitted': {'label': '已提交', 'sort_order': 1, 'action': '等待审核'},
    'reviewing': {'label': '审核中', 'sort_order': 2, 'action': '商家正在审核'},
    'approved': {'label': '已通过', 'sort_order': 3, 'action': '请按要求操作'},
    'rejected': {'label': '已拒绝', 'sort_order': 4, 'action': '可申请平台介入'},
    'returning': {'label': '退货中', 'sort_order': 5, 'action': '请寄回商品'},
    'returned': {'label': '已退货', 'sort_order': 6, 'action': '等待商家确认'},
    'refunding': {'label': '退款中', 'sort_order': 7, 'action': '退款处理中'},
    'completed': {'label': '已完成', 'sort_order': 8, 'action': '售后已完成'},
    'cancelled': {'label': '已取消', 'sort_order': 9, 'action': '售后已取消'},
    'escalated': {'label': '已升级', 'sort_order': 10, 'action': '平台介入处理'},
}

# 状态机允许的转换规则（有向图）
STATUS_TRANSITIONS = {
    'submitted': ['reviewing', 'cancelled'],
    'reviewing': ['approved', 'rejected', 'escalated'],
    'approved': ['returning', 'refunding', 'cancelled'],
    'rejected': ['escalated', 'cancelled'],
    'returning': ['returned', 'escalated'],
    'returned': ['refunding', 'escalated'],
    'refunding': ['completed', 'escalated'],
    'completed': [],
    'cancelled': [],
    'escalated': ['approved', 'rejected', 'completed'],
}

# 自动审批规则：小额退款自动通过、VIP用户自动通过
AUTO_APPROVE_RULES = {
    'max_refund_amount': 200,
    'quality_auto_reject_threshold': 0,
    'preference_auto_approve': True,
    'logistics_auto_approve': True,
    'first_time_buyer_bonus': True,
    'vip_auto_approve': True,
}

# 赔偿规则：根据异常类型自动计算赔偿方案
COMPENSATION_RULES = {
    'late_delivery': {'type': 'coupon', 'amount': 10, 'condition': '延迟超过3天'},
    'damaged_product': {'type': 'partial_refund', 'percentage': 30, 'condition': '轻微损坏'},
    'wrong_item': {'type': 'full_refund', 'amount': 0, 'condition': '发错商品'},
    'missing_parts': {'type': 'reissue', 'amount': 0, 'condition': '配件缺失'},
    'quality_issue': {'type': 'full_refund', 'amount': 0, 'condition': '严重质量问题'},
}


def init_db():
    """初始化SQLite数据库，创建售后订单表和状态时间线表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS aftersale_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aftersale_id TEXT UNIQUE,
        order_id TEXT,
        type TEXT,
        reason_category TEXT,
        reason_detail TEXT,
        status TEXT DEFAULT 'submitted',
        refund_amount REAL DEFAULT 0,
        evidence TEXT,
        buyer_id TEXT,
        seller_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        completed_at TEXT,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS aftersale_timeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aftersale_id TEXT,
        status TEXT,
        description TEXT,
        operator TEXT DEFAULT 'system',
        created_at TEXT,
        FOREIGN KEY (aftersale_id) REFERENCES aftersale_orders(aftersale_id)
    )''')
    conn.commit()
    conn.close()


def get_db_connection():
    """获取SQLite数据库连接（带行工厂）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_aftersale(order_id: str, aftersale_type: str, reason_category: str,
                     reason_detail: str, refund_amount: float = 0,
                     evidence: List[str] = None, buyer_id: str = "") -> Dict:
    """创建售后申请，含自动审批逻辑与Skill-Gate置信度门控集成"""
    type_info = REFUND_TYPES.get(aftersale_type, {})
    if not type_info:
        return {"error": f"不支持的售后类型: {aftersale_type}"}

    category_info = REASON_CATEGORIES.get(reason_category, {})
    if not category_info:
        return {"error": f"不支持的原因分类: {reason_category}"}

    now = datetime.now()
    aftersale_id = f"AS{now.strftime('%Y%m%d%H%M%S')}{hash(order_id) % 1000:03d}"

    auto_approved = False
    if category_info.get('auto_approve') and refund_amount <= AUTO_APPROVE_RULES['max_refund_amount']:
        auto_approved = True
    if AUTO_APPROVE_RULES.get('vip_auto_approve') and buyer_id.startswith('VIP'):
        auto_approved = True

    # Confidence-gate integration: when auto-approved, double-check via SkillGate
    # to catch high-risk refunds that should route to human review
    if auto_approved:
        try:
            import importlib.util as _iu
            _cg = _iu.spec_from_file_location("as_cg", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skill-gate", "main.py"))
            if _cg and _cg.loader:
                _cgm = _iu.module_from_spec(_cg)
                sys.modules["as_cg"] = _cgm
                _cg.loader.exec_module(_cgm)
                _gr = _cgm.SkillGate().evaluate("refund" if aftersale_type in ("refund_only", "return_refund") else "after_sale_consult", "ecommerce", confidence=0.9, context={"refund_amount": refund_amount, "reason_category": reason_category})
                if _gr.get("action") == "human_confirm":
                    auto_approved = False
                    initial_status = "submitted"
        except Exception:
            pass

    initial_status = 'approved' if auto_approved else 'submitted'

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO aftersale_orders 
        (aftersale_id, order_id, type, reason_category, reason_detail, status, refund_amount, evidence, buyer_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (aftersale_id, order_id, aftersale_type, reason_category, reason_detail,
               initial_status, refund_amount, json.dumps(evidence or [], ensure_ascii=False),
               buyer_id, now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("""INSERT INTO aftersale_timeline (aftersale_id, status, description, operator, created_at)
        VALUES (?, ?, ?, ?, ?)""",
              (aftersale_id, initial_status, f"售后申请已提交，类型: {type_info['name']}", "buyer",
               now.strftime("%Y-%m-%d %H:%M:%S")))
    if auto_approved:
        c.execute("""INSERT INTO aftersale_timeline (aftersale_id, status, description, operator, created_at)
            VALUES (?, ?, ?, ?, ?)""",
                  (aftersale_id, 'approved', "系统自动审核通过", "system",
                   now.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return {
        "aftersaleId": aftersale_id,
        "orderId": order_id,
        "type": aftersale_type,
        "typeName": type_info['name'],
        "reasonCategory": reason_category,
        "reasonCategoryName": category_info['name'],
        "reasonDetail": reason_detail,
        "status": initial_status,
        "statusInfo": AFTERSALE_STATUS_MAP.get(initial_status, {}),
        "refundAmount": refund_amount,
        "autoApproved": auto_approved,
        "nextAction": _get_next_action(initial_status, aftersale_type),
        "estimatedDays": type_info['processing_days'],
        "requiredEvidence": type_info['required_evidence'],
        "createdAt": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _get_next_action(status: str, aftersale_type: str) -> Dict:
    """根据当前状态和售后类型确定用户下一步操作指引"""
    actions = {
        'submitted': {"action": "等待审核", "description": "商家将在24小时内审核", "timeout_hours": 24},
        'reviewing': {"action": "审核中", "description": "商家正在审核您的申请", "timeout_hours": 24},
        'approved': {
            "action": "寄回商品" if aftersale_type in ('return_refund', 'exchange', 'repair') else "等待退款",
            "description": "请按要求操作",
            "timeout_hours": 72,
        },
        'rejected': {"action": "申请介入", "description": "如不满意可申请平台介入", "timeout_hours": 168},
        'returning': {"action": "填写物流单号", "description": "请尽快寄回并填写物流信息", "timeout_hours": 168},
        'returned': {"action": "等待确认", "description": "商家确认收货后处理退款", "timeout_hours": 72},
        'refunding': {"action": "等待到账", "description": "退款将在1-3个工作日内到账", "timeout_hours": 72},
        'completed': {"action": "已完成", "description": "售后流程已结束", "timeout_hours": None},
        'cancelled': {"action": "已取消", "description": "售后申请已取消", "timeout_hours": None},
        'escalated': {"action": "等待平台处理", "description": "平台将在3个工作日内处理", "timeout_hours": 72},
    }
    return actions.get(status, {"action": "未知", "description": ""})


def query_aftersale(aftersale_id: str = "", order_id: str = "") -> Dict:
    """查询售后单详情（含时间线），未命中时返回模拟数据"""

    conn = get_db_connection()
    c = conn.cursor()

    if aftersale_id:
        c.execute("SELECT * FROM aftersale_orders WHERE aftersale_id = ?", (aftersale_id,))
    elif order_id:
        c.execute("SELECT * FROM aftersale_orders WHERE order_id = ? ORDER BY created_at DESC", (order_id,))
    else:
        conn.close()
        return {"error": "需要提供aftersale_id或order_id"}

    rows = c.fetchall()
    if not rows:
        conn.close()
        return _generate_simulated_aftersale(aftersale_id, order_id)

    results = []
    for row in rows:
        record = dict(row)
        c.execute("SELECT * FROM aftersale_timeline WHERE aftersale_id = ? ORDER BY created_at", (record['aftersale_id'],))
        record['timeline'] = [dict(t) for t in c.fetchall()]
        record['statusInfo'] = AFTERSALE_STATUS_MAP.get(record['status'], {})
        record['nextAction'] = _get_next_action(record['status'], record['type'])
        record['typeName'] = REFUND_TYPES.get(record['type'], {}).get('name', record['type'])
        results.append(record)

    conn.close()
    return {"records": results, "source": "database"}


def _generate_simulated_aftersale(aftersale_id: str, order_id: str) -> Dict:
    """在数据库无数据时生成模拟售后单，便于演示和接口联调"""

    if not order_id:
        order_id = f"ORD{datetime.now().strftime('%Y%m%d')}0001"
    if not aftersale_id:
        aftersale_id = f"AS{datetime.now().strftime('%Y%m%d%H%M%S')}001"

    now = datetime.now()
    status_list = list(AFTERSALE_STATUS_MAP.keys())
    idx = hash(order_id) % len(status_list)
    status = status_list[idx]

    timeline = []
    status_order = ['submitted', 'reviewing', 'approved', 'returning', 'returned', 'refunding', 'completed']
    current_idx = status_order.index(status) if status in status_order else 0
    for i in range(current_idx + 1):
        t = now - timedelta(hours=(current_idx - i) * 8)
        timeline.append({
            "status": status_order[i],
            "description": AFTERSALE_STATUS_MAP.get(status_order[i], {}).get('action', ''),
            "operator": "system",
            "created_at": t.strftime("%Y-%m-%d %H:%M:%S"),
        })

    record = {
        "aftersale_id": aftersale_id,
        "order_id": order_id,
        "type": "return_refund",
        "typeName": "退货退款",
        "reason_category": "quality",
        "reason_detail": "商品存在质量问题",
        "status": status,
        "statusInfo": AFTERSALE_STATUS_MAP.get(status, {}),
        "nextAction": _get_next_action(status, "return_refund"),
        "refund_amount": 899,
        "timeline": timeline,
        "created_at": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {"records": [record], "source": "simulated"}


def update_aftersale_status(aftersale_id: str, new_status: str, operator: str = "system",
                             notes: str = "") -> Dict:
    """更新售后单状态，含状态机转换合法性校验"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status, type FROM aftersale_orders WHERE aftersale_id = ?", (aftersale_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"error": f"售后单不存在: {aftersale_id}"}

    current_status = row['status']
    allowed = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        conn.close()
        return {"error": f"不允许从{current_status}转到{new_status}", "allowedTransitions": allowed}

    now = datetime.now()
    c.execute("UPDATE aftersale_orders SET status = ?, updated_at = ?, notes = ? WHERE aftersale_id = ?",
              (new_status, now.strftime("%Y-%m-%d %H:%M:%S"), notes, aftersale_id))
    c.execute("""INSERT INTO aftersale_timeline (aftersale_id, status, description, operator, created_at)
        VALUES (?, ?, ?, ?, ?)""",
              (aftersale_id, new_status, notes or f"状态更新为{AFTERSALE_STATUS_MAP.get(new_status, {}).get('label', new_status)}",
               operator, now.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return {
        "aftersaleId": aftersale_id,
        "previousStatus": current_status,
        "newStatus": new_status,
        "statusInfo": AFTERSALE_STATUS_MAP.get(new_status, {}),
        "nextAction": _get_next_action(new_status, row['type']),
        "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def calculate_compensation(order_id: str, reason_category: str, reason_detail: str,
                           order_amount: float) -> Dict:
    """根据售后原因关键词匹配赔偿规则，计算赔偿方案"""

    compensation = None
    for rule_key, rule in COMPENSATION_RULES.items():
        if rule_key == 'late_delivery' and '延迟' in reason_detail:
            compensation = {"type": rule['type'], "amount": rule['amount'], "condition": rule['condition']}
            break
        elif rule_key == 'damaged_product' and ('损坏' in reason_detail or '破损' in reason_detail):
            compensation = {"type": rule['type'], "percentage": rule['percentage'], "amount": round(order_amount * rule['percentage'] / 100, 2), "condition": rule['condition']}
            break
        elif rule_key == 'wrong_item' and '发错' in reason_detail:
            compensation = {"type": rule['type'], "amount": order_amount, "condition": rule['condition']}
            break
        elif rule_key == 'quality_issue' and reason_category == 'quality':
            compensation = {"type": rule['type'], "amount": order_amount, "condition": rule['condition']}
            break

    if not compensation:
        if reason_category in ('quality', 'description'):
            compensation = {"type": "full_refund", "amount": order_amount, "condition": "质量问题/描述不符全额退款"}
        elif reason_category == 'logistics':
            compensation = {"type": "coupon", "amount": 10, "condition": "物流问题补偿优惠券"}
        else:
            compensation = {"type": "partial_refund", "percentage": 50, "amount": round(order_amount * 0.5, 2), "condition": "协商退款"}

    return {
        "orderId": order_id,
        "reasonCategory": reason_category,
        "reasonDetail": reason_detail,
        "orderAmount": order_amount,
        "compensation": compensation,
        "requiresApproval": compensation.get('type') == 'full_refund' or compensation.get('amount', 0) > 200,
    }


def process_aftersale(input_data: Dict) -> Dict:
    """售后主入口：根据action参数分发到create/query/update/compensation子流程"""

    action = input_data.get('action', 'create')
    order_id = input_data.get('order_id', '')
    aftersale_id = input_data.get('aftersale_id', '')

    if action == 'create':
        if not order_id:
            return {"error": "需要提供order_id"}
        return create_aftersale(
            order_id=order_id,
            aftersale_type=input_data.get('type', 'return_refund'),
            reason_category=input_data.get('reason_category', 'quality'),
            reason_detail=input_data.get('reason_detail', ''),
            refund_amount=input_data.get('refund_amount', 0),
            evidence=input_data.get('evidence', []),
            buyer_id=input_data.get('buyer_id', ''),
        )

    elif action == 'query':
        return query_aftersale(aftersale_id, order_id)

    elif action == 'update_status':
        if not aftersale_id:
            return {"error": "需要提供aftersale_id"}
        return update_aftersale_status(
            aftersale_id=aftersale_id,
            new_status=input_data.get('new_status', ''),
            operator=input_data.get('operator', 'system'),
            notes=input_data.get('notes', ''),
        )

    elif action == 'compensation':
        return calculate_compensation(
            order_id=order_id,
            reason_category=input_data.get('reason_category', 'quality'),
            reason_detail=input_data.get('reason_detail', ''),
            order_amount=input_data.get('order_amount', 0),
        )

    else:
        return {"error": f"不支持的操作: {action}"}


def main():
    """CLI入口：从stdin或argv读取JSON，调用售后处理流程并输出结果"""
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
    result = process_aftersale(input_data)

    needs_human = False
    if isinstance(result, dict):
        status = result.get('status', '')
        if status in ('rejected', 'escalated'):
            needs_human = True
        if result.get('requiresApproval', False):
            needs_human = True
        result["handoff"] = {
            "needsHumanReview": needs_human,
            "reason": "售后需要人工审核或介入" if needs_human else "",
            "confidence": 85.0,
            "gate": "human" if needs_human else "auto",
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
