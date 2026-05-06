import json
import os
import sqlite3
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate.db")

GATE_REGISTRY = {
    "ecommerce": {
        "listing_gen": {"default_level": "low", "description": "Listing生成"},
        "listing_optimize": {"default_level": "low", "description": "Listing优化"},
        "data_query": {"default_level": "low", "description": "数据查询"},
        "report_gen": {"default_level": "low", "description": "报表生成"},
        "ad_monitor": {"default_level": "low", "description": "广告监控"},
        "ad_adjust_price": {"default_level": "medium", "description": "广告调价"},
        "ad_adjust_price_large": {"default_level": "high", "description": "广告大额调价(>20%)"},
        "review_reply": {"default_level": "medium", "description": "差评回复"},
        "material_publish": {"default_level": "medium", "description": "素材发布"},
        "product_delete": {"default_level": "high", "description": "删除商品"},
        "refund": {"default_level": "high", "description": "退款操作"},
        "price_change_over_20pct": {"default_level": "high", "description": "调价超过20%"},
    },
    "social-media": {
        "content_gen": {"default_level": "low", "description": "内容生成"},
        "compliance_check": {"default_level": "low", "description": "合规检测"},
        "social_data_query": {"default_level": "low", "description": "社媒数据查询"},
        "content_publish": {"default_level": "medium", "description": "内容发布"},
        "cron_publish": {"default_level": "medium", "description": "定时发布"},
        "drain_script": {"default_level": "medium", "description": "导流话术"},
        "sensitive_topic": {"default_level": "high", "description": "敏感话题"},
        "negative_opinion": {"default_level": "high", "description": "负面舆情处理"},
    },
    "cs": {
        "faq_reply": {"default_level": "low", "description": "FAQ回复"},
        "order_query": {"default_level": "low", "description": "订单查询"},
        "product_recommend": {"default_level": "low", "description": "商品推荐"},
        "after_sale_consult": {"default_level": "medium", "description": "售后咨询"},
        "resend_process": {"default_level": "medium", "description": "补发处理"},
        "refund_process": {"default_level": "high", "description": "退款处理"},
        "negative_sentiment": {"default_level": "high", "description": "负面情感转人工"},
        "low_confidence": {"default_level": "high", "description": "低置信度转人工"},
    },
    "office": {
        "report_gen": {"default_level": "low", "description": "报表生成"},
        "excel_viz": {"default_level": "low", "description": "Excel可视化"},
        "doc_process": {"default_level": "low", "description": "文档处理"},
        "meeting_minutes": {"default_level": "low", "description": "会议纪要"},
        "email_draft": {"default_level": "medium", "description": "邮件草拟"},
        "email_send": {"default_level": "high", "description": "邮件发送"},
        "sensitive_doc": {"default_level": "high", "description": "敏感文档处理"},
    },
}

LEVEL_PRIORITY = {"low": 0, "medium": 1, "high": 2}

LEVEL_THRESHOLDS = {
    "low": {"min_confidence": 0.9, "action": "auto_execute", "notify": False},
    "medium": {"min_confidence": 0.6, "action": "execute_and_notify", "notify": True},
    "high": {"min_confidence": 0.0, "action": "human_confirm", "notify": True},
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS gate_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            operation TEXT NOT NULL,
            default_level TEXT NOT NULL DEFAULT 'medium',
            conditions TEXT DEFAULT '[]',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gate_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_id TEXT NOT NULL UNIQUE,
            agent TEXT NOT NULL,
            operation TEXT NOT NULL,
            level TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            params TEXT DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT DEFAULT '',
            approved_by TEXT DEFAULT '',
            approved_at TEXT DEFAULT '',
            rejected_by TEXT DEFAULT '',
            rejected_at TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            resolved_at TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS gate_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            operation TEXT NOT NULL,
            level TEXT NOT NULL,
            channel TEXT DEFAULT 'feishu',
            sent_at TEXT NOT NULL,
            status TEXT DEFAULT 'sent'
        )
    """)

    for agent, ops in GATE_REGISTRY.items():
        for op_name, op_config in ops.items():
            c.execute(
                "SELECT id FROM gate_rules WHERE agent=? AND operation=?",
                (agent, op_name),
            )
            if not c.fetchone():
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute(
                    "INSERT INTO gate_rules (agent, operation, default_level, conditions, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (agent, op_name, op_config["default_level"], "[]", op_config["description"], now, now),
                )

    conn.commit()
    conn.close()


class SkillGate:
    def __init__(self):
        init_db()
        self.custom_conditions = self._load_conditions()

    def _load_conditions(self) -> Dict:
        conditions = {}
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT agent, operation, conditions FROM gate_rules")
        for row in c.fetchall():
            key = f"{row['agent']}:{row['operation']}"
            try:
                conditions[key] = json.loads(row["conditions"])
            except (json.JSONDecodeError, TypeError):
                conditions[key] = []
        conn.close()
        return conditions

    def evaluate(self, operation: str, agent: str, confidence: float = 1.0, context: Dict = None) -> Dict:
        if context is None:
            context = {}

        level = self._determine_level(agent, operation, confidence, context)
        threshold = LEVEL_THRESHOLDS[level]

        gate_id = f"gate-{datetime.now().strftime('%Y%m%d%H%M%S')}-{abs(hash(f'{agent}:{operation}')) % 10000:04d}"

        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO gate_records (gate_id, agent, operation, level, confidence, params, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (gate_id, agent, operation, level, confidence, json.dumps(context, ensure_ascii=False, default=str)[:500], threshold["action"], now),
        )
        conn.commit()
        conn.close()

        result = {
            "gate_id": gate_id,
            "operation": operation,
            "agent": agent,
            "level": level,
            "confidence": confidence,
            "action": threshold["action"],
            "notify": threshold["notify"],
            "allowed": level == "low",
            "message": self._get_message(level, operation, confidence),
        }

        if level == "high":
            result["allowed"] = False
            result["message"] = f"操作 [{operation}] 需要人工确认（置信度: {confidence:.1%}，门控级别: 高风险）"
        elif level == "medium":
            result["allowed"] = True
            result["message"] = f"操作 [{operation}] 已执行并通知运营（置信度: {confidence:.1%}，门控级别: 中风险）"

        return result

    def _determine_level(self, agent: str, operation: str, confidence: float, context: Dict) -> str:
        base_level = self._get_base_level(agent, operation)
        conditional_level = self._check_conditions(agent, operation, context)

        if conditional_level and LEVEL_PRIORITY.get(conditional_level, 0) > LEVEL_PRIORITY.get(base_level, 0):
            return conditional_level

        if confidence >= 0.9:
            return base_level
        elif confidence >= 0.6:
            if LEVEL_PRIORITY.get(base_level, 0) < LEVEL_PRIORITY["medium"]:
                return "medium"
            return base_level
        else:
            return "high"

    def _get_base_level(self, agent: str, operation: str) -> str:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT default_level FROM gate_rules WHERE agent=? AND operation=?", (agent, operation))
        row = c.fetchone()
        conn.close()
        if row:
            return row["default_level"]
        if operation in GATE_REGISTRY.get(agent, {}):
            return GATE_REGISTRY[agent][operation]["default_level"]
        return "medium"

    def _check_conditions(self, agent: str, operation: str, context: Dict) -> Optional[str]:
        key = f"{agent}:{operation}"
        conditions = self.custom_conditions.get(key, [])
        for cond in conditions:
            field = cond.get("field", "")
            operator = cond.get("operator", "==")
            value = cond.get("value")
            level = cond.get("level", "high")

            ctx_value = context.get(field)
            if ctx_value is None:
                continue

            matched = False
            if operator == ">" and ctx_value > value:
                matched = True
            elif operator == ">=" and ctx_value >= value:
                matched = True
            elif operator == "<" and ctx_value < value:
                matched = True
            elif operator == "<=" and ctx_value <= value:
                matched = True
            elif operator == "==" and ctx_value == value:
                matched = True
            elif operator == "!=" and ctx_value != value:
                matched = True
            elif operator == "in" and ctx_value in value:
                matched = True

            if matched:
                return level

        return None

    def check(self, operation: str, agent: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        confidence = params.pop("_confidence", 0.95)
        return self.evaluate(operation, agent, confidence, params)

    def approve(self, gate_id: str, approved_by: str, comment: str = "") -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM gate_records WHERE gate_id=?", (gate_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": f"门控记录 {gate_id} 不存在"}

        if row["status"] != "human_confirm":
            conn.close()
            return {"success": False, "error": f"门控记录状态为 {row['status']}，无需审批"}

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "UPDATE gate_records SET status='approved', approved_by=?, approved_at=?, comment=?, resolved_at=? WHERE gate_id=?",
            (approved_by, now, comment, now, gate_id),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "gate_id": gate_id,
            "operation": row["operation"],
            "agent": row["agent"],
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": now,
            "message": f"操作 [{row['operation']}] 已被 {approved_by} 批准执行",
        }

    def reject(self, gate_id: str, rejected_by: str, comment: str = "") -> Dict:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM gate_records WHERE gate_id=?", (gate_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": f"门控记录 {gate_id} 不存在"}

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "UPDATE gate_records SET status='rejected', rejected_by=?, rejected_at=?, comment=?, resolved_at=? WHERE gate_id=?",
            (rejected_by, now, comment, now, gate_id),
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "gate_id": gate_id,
            "operation": row["operation"],
            "agent": row["agent"],
            "status": "rejected",
            "rejected_by": rejected_by,
            "rejected_at": now,
            "message": f"操作 [{row['operation']}] 已被 {rejected_by} 拒绝",
        }

    def list_pending(self, agent: str = None) -> Dict:
        conn = get_db()
        c = conn.cursor()
        if agent:
            c.execute("SELECT * FROM gate_records WHERE status='human_confirm' AND agent=? ORDER BY created_at DESC", (agent,))
        else:
            c.execute("SELECT * FROM gate_records WHERE status='human_confirm' ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()

        pending = []
        for row in rows:
            pending.append({
                "gate_id": row["gate_id"],
                "agent": row["agent"],
                "operation": row["operation"],
                "level": row["level"],
                "confidence": row["confidence"],
                "params": json.loads(row["params"]) if row["params"] else {},
                "created_at": row["created_at"],
            })

        return {"total": len(pending), "pending": pending}

    def register(self, operation: str, agent: str, default_level: str = "medium", conditions: List = None, description: str = "") -> Dict:
        if conditions is None:
            conditions = []

        conn = get_db()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("SELECT id FROM gate_rules WHERE agent=? AND operation=?", (agent, operation))
        existing = c.fetchone()

        if existing:
            c.execute(
                "UPDATE gate_rules SET default_level=?, conditions=?, description=?, updated_at=? WHERE agent=? AND operation=?",
                (default_level, json.dumps(conditions, ensure_ascii=False), description, now, agent, operation),
            )
        else:
            c.execute(
                "INSERT INTO gate_rules (agent, operation, default_level, conditions, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (agent, operation, default_level, json.dumps(conditions, ensure_ascii=False), description, now, now),
            )

        conn.commit()
        conn.close()

        key = f"{agent}:{operation}"
        self.custom_conditions[key] = conditions

        return {
            "success": True,
            "operation": operation,
            "agent": agent,
            "default_level": default_level,
            "conditions_count": len(conditions),
            "message": f"门控规则 [{operation}] 已注册到 {agent} Agent，默认级别: {default_level}",
        }

    def get_stats(self) -> Dict:
        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) as total FROM gate_records")
        total = c.fetchone()["total"]

        c.execute("SELECT level, COUNT(*) as count FROM gate_records GROUP BY level")
        level_dist = {row["level"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT status, COUNT(*) as count FROM gate_records GROUP BY status")
        status_dist = {row["status"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT agent, COUNT(*) as count FROM gate_records GROUP BY agent")
        agent_dist = {row["agent"]: row["count"] for row in c.fetchall()}

        c.execute("SELECT COUNT(*) as total FROM gate_rules")
        rules_total = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as total FROM gate_records WHERE status='human_confirm'")
        pending_count = c.fetchone()["total"]

        conn.close()

        return {
            "total_records": total,
            "total_rules": rules_total,
            "pending_approvals": pending_count,
            "level_distribution": level_dist,
            "status_distribution": status_dist,
            "agent_distribution": agent_dist,
        }

    def _get_message(self, level: str, operation: str, confidence: float) -> str:
        if level == "low":
            return f"操作 [{operation}] 自动执行（置信度: {confidence:.1%}，门控级别: 低风险）"
        elif level == "medium":
            return f"操作 [{operation}] 执行并通知运营（置信度: {confidence:.1%}，门控级别: 中风险）"
        else:
            return f"操作 [{operation}] 需要人工确认（置信度: {confidence:.1%}，门控级别: 高风险）"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Skill Gate")
    parser.add_argument("--action", required=True)
    parser.add_argument("--operation", default="")
    parser.add_argument("--agent", default="")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--context", default="{}")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--gate_id", default="")
    parser.add_argument("--approved_by", default="")
    parser.add_argument("--rejected_by", default="")
    parser.add_argument("--comment", default="")
    parser.add_argument("--default_level", default="medium")
    parser.add_argument("--conditions", default="[]")
    parser.add_argument("--description", default="")
    args = parser.parse_args()

    gate = SkillGate()

    if args.action == "evaluate":
        context = json.loads(args.context)
        result = gate.evaluate(args.operation, args.agent, args.confidence, context)
    elif args.action == "check":
        params = json.loads(args.params)
        result = gate.check(args.operation, args.agent, params)
    elif args.action == "approve":
        result = gate.approve(args.gate_id, args.approved_by, args.comment)
    elif args.action == "reject":
        result = gate.reject(args.gate_id, args.rejected_by, args.comment)
    elif args.action == "list_pending":
        result = gate.list_pending(args.agent or None)
    elif args.action == "register":
        conditions = json.loads(args.conditions)
        result = gate.register(args.operation, args.agent, args.default_level, conditions, args.description)
    elif args.action == "get_stats":
        result = gate.get_stats()
    else:
        result = {"error": f"未知操作: {args.action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
