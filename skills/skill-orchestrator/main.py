import json
import os
import sys
import sqlite3
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflow.db")

SKILL_BASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# 内置工作流模板：新品上架/订单全链路/差评危机/社媒活动/广告优化/电商闭环/社媒增长/客服闭环/办公自动化
WORKFLOW_TEMPLATES = {
    "full_listing_launch": {
        "name": "新品上架全流程",
        "description": "生成Listing + 素材 + 广告方案 + 小红书种草",
        "domain": "ecommerce",
        "agent": "ecommerce",
        "steps": [
            {"skill": "listing-gen", "action": "generate", "input_mapping": {}, "output_key": "listing", "required": True},
            {"skill": "material-gen", "action": "generate", "input_mapping": {"listing": "listing"}, "output_key": "materials", "required": False},
            {"skill": "ad-optimizer", "action": "optimize", "input_mapping": {"listing": "listing"}, "output_key": "ad_plan", "required": False},
            {"skill": "xhs-seed", "action": "generate", "input_mapping": {"listing": "listing"}, "output_key": "xhs_content", "required": False},
        ],
        "aggregation": "full_launch_report",
    },
    "order_full_inquiry": {
        "name": "订单全链路查询",
        "description": "查询订单 + 物流追踪 + 售后状态",
        "domain": "cs",
        "agent": "cs",
        "steps": [
            {"skill": "order-query", "action": "query", "input_mapping": {}, "output_key": "order", "required": True},
            {
                "skill": "logistics-track",
                "action": "track",
                "input_mapping": {"tracking_number": "@result:order.orders.0.tracking_number"},
                "output_key": "logistics",
                "required": False,
                "condition": "has_tracking",
            },
            {
                "skill": "after-sale",
                "action": "query",
                "input_mapping": {"order_id": "@result:order.orders.0.order_id"},
                "output_key": "aftersale",
                "required": False,
                "condition": "has_order_id",
            },
        ],
        "aggregation": "order_full_report",
    },
    "review_crisis_handling": {
        "name": "差评危机处理",
        "description": "评论分析 + 差评预警 + 自动回复 + 舆情监控",
        "domain": "ecommerce",
        "agent": "ecommerce",
        "steps": [
            {"skill": "review-mgr", "action": "analyze", "input_mapping": {}, "output_key": "review_analysis", "required": True},
            {"skill": "review-mgr", "action": "detect_alerts", "input_mapping": {"review_analysis": "review_analysis"}, "output_key": "alerts", "required": False},
            {"skill": "review-mgr", "action": "generate_reply", "input_mapping": {"review_analysis": "review_analysis"}, "output_key": "replies", "required": False, "condition": "has_negative"},
            {"skill": "opinion-watch", "action": "monitor", "input_mapping": {}, "output_key": "opinion", "required": False},
        ],
        "aggregation": "crisis_report",
    },
    "social_media_campaign": {
        "name": "社媒营销活动",
        "description": "小红书种草 + 抖音脚本 + 舆情监控",
        "domain": "social-media",
        "agent": "social-media",
        "steps": [
            {"skill": "xhs-seed", "action": "generate", "input_mapping": {}, "output_key": "xhs_content", "required": True},
            {"skill": "xhs-seed", "action": "calendar", "input_mapping": {}, "output_key": "xhs_calendar", "required": False},
            {"skill": "douyin-ops", "action": "generate", "input_mapping": {}, "output_key": "douyin_script", "required": False},
            {"skill": "opinion-watch", "action": "monitor", "input_mapping": {}, "output_key": "opinion", "required": False},
        ],
        "aggregation": "campaign_report",
    },
    "ad_full_optimization": {
        "name": "广告全链路优化",
        "description": "广告分析 + 预算分配 + 出价策略 + Listing优化建议",
        "domain": "ecommerce",
        "agent": "ecommerce",
        "steps": [
            {"skill": "ad-optimizer", "action": "optimize", "input_mapping": {}, "output_key": "ad_analysis", "required": True},
            {"skill": "ad-optimizer", "action": "budget", "input_mapping": {"ad_analysis": "ad_analysis"}, "output_key": "budget_plan", "required": False},
            {"skill": "listing-gen", "action": "optimize", "input_mapping": {"ad_analysis": "ad_analysis"}, "output_key": "listing_suggestions", "required": False},
        ],
        "aggregation": "ad_optimization_report",
    },
    "ecommerce_operation_hub": {
        "name": "电商经营闭环",
        "description": "Listing + 素材 + 广告优化 + 经营报表 + 图表看板",
        "domain": "ecommerce",
        "agent": "ecommerce",
        "steps": [
            {"skill": "listing-gen", "action": "generate", "output_key": "listing", "required": True},
            {"skill": "material-gen", "action": "generate", "output_key": "materials", "required": False, "condition": "has_product"},
            {"skill": "ad-optimizer", "action": "optimize", "output_key": "ad_analysis", "required": False, "condition": "has_ad_metrics"},
            {"skill": "report-gen", "action": "generate", "output_key": "report", "required": False, "params": {"report_type": "weekly"}},
            {
                "skill": "excel-viz",
                "action": "visualize",
                "input_mapping": {"report": "@result:report"},
                "output_key": "chart_board",
                "required": False,
            },
        ],
        "aggregation": "ecommerce_operations_report",
    },
    "social_media_content_flywheel": {
        "name": "社媒内容增长闭环",
        "description": "小红书 + 抖音 + 视频号 + 私域导流 + 舆情巡检",
        "domain": "social-media",
        "agent": "social-media",
        "steps": [
            {"skill": "xhs-seed", "action": "generate", "output_key": "xhs_content", "required": True},
            {"skill": "douyin-ops", "action": "generate", "output_key": "douyin_script", "required": False},
            {"skill": "video-channel", "action": "generate", "output_key": "video_channel_content", "required": False},
            {
                "skill": "cross-drain",
                "action": "cross_platform_strategy",
                "output_key": "drain_strategy",
                "required": False,
                "condition": "has_platform_pair",
            },
            {
                "skill": "opinion-watch",
                "action": "monitor",
                "input_mapping": {"content": "@result:xhs_content.fullContent"},
                "output_key": "opinion",
                "required": False,
                "condition": "has_opinion_content",
            },
        ],
        "aggregation": "social_media_flywheel_report",
    },
    "customer_service_resolution": {
        "name": "客服服务闭环",
        "description": "意图识别 + 订单查询 + 物流跟踪 + 售后查询 + 情绪升级",
        "domain": "cs",
        "agent": "cs",
        "steps": [
            {
                "skill": "intent-recognition",
                "action": "analyze",
                "input_mapping": {
                    "user_message": "@params.user_message",
                    "history": "@params.history",
                    "context": "@context",
                },
                "output_key": "intent",
                "required": True,
            },
            {
                "skill": "order-query",
                "action": "query",
                "input_mapping": {
                    "order_id": "@result:intent.entities.order_id",
                    "phone": "@result:intent.entities.phone_raw",
                },
                "output_key": "order",
                "required": False,
                "condition": "has_order_id",
            },
            {
                "skill": "logistics-track",
                "action": "track",
                "input_mapping": {
                    "tracking_number": "@result:intent.entities.tracking_number",
                    "order_id": "@result:order.orders.0.order_id",
                },
                "output_key": "logistics",
                "required": False,
                "condition": "has_tracking",
            },
            {
                "skill": "after-sale",
                "action": "query",
                "input_mapping": {
                    "order_id": "@result:order.orders.0.order_id",
                },
                "output_key": "aftersale",
                "required": False,
                "condition": "has_order_id",
            },
            {
                "skill": "sentiment-analysis",
                "action": "analyze",
                "input_mapping": {
                    "user_message": "@params.user_message",
                    "history": "@params.history",
                    "context": "@context",
                },
                "output_key": "sentiment",
                "required": False,
            },
        ],
        "aggregation": "customer_service_report",
    },
    "office_productivity_suite": {
        "name": "办公自动化闭环",
        "description": "周报/经营报表 + 图表看板 + 文档摘要 + 邮件草稿",
        "domain": "office",
        "agent": "office",
        "steps": [
            {
                "skill": "report-gen",
                "action": "generate",
                "output_key": "report",
                "required": True,
                "params": {"report_type": "weekly"},
            },
            {
                "skill": "excel-viz",
                "action": "visualize",
                "input_mapping": {"report": "@result:report"},
                "output_key": "chart_board",
                "required": False,
            },
            {
                "skill": "doc-auto",
                "action": "summarize",
                "input_mapping": {"report": "@result:report"},
                "output_key": "document",
                "required": False,
                "params": {"document_type": "summary"},
            },
            {
                "skill": "email-mgr",
                "action": "draft",
                "input_mapping": {
                    "report": "@result:report",
                    "document": "@result:document",
                },
                "output_key": "email",
                "required": False,
            },
        ],
        "aggregation": "office_productivity_report",
    },
}


def deep_get(data: Any, path: str, default=None):
    if path in ("", None):
        return data

    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit():
                return default
            index = int(part)
            if index < 0 or index >= len(current):
                return default
            current = current[index]
        else:
            return default

    return current


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return value
    return None


def compact_dict(values: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        result[key] = value
    return result


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS workflow_executions (
        execution_id TEXT PRIMARY KEY,
        workflow_name TEXT,
        status TEXT DEFAULT 'running',
        total_steps INTEGER DEFAULT 0,
        completed_steps INTEGER DEFAULT 0,
        failed_steps INTEGER DEFAULT 0,
        started_at TEXT,
        completed_at TEXT,
        duration_ms INTEGER DEFAULT 0,
        trigger_source TEXT DEFAULT 'manual',
        metadata TEXT DEFAULT '{}'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS workflow_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id TEXT,
        step_index INTEGER,
        skill_name TEXT,
        action TEXT,
        status TEXT DEFAULT 'pending',
        input_data TEXT,
        output_data TEXT,
        duration_ms INTEGER DEFAULT 0,
        error_message TEXT,
        started_at TEXT,
        completed_at TEXT,
        FOREIGN KEY (execution_id) REFERENCES workflow_executions(execution_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS workflow_templates (
        name TEXT PRIMARY KEY,
        definition TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class SkillInvoker:
    """技能调用器：通过subprocess调用技能main.py，按技能名自动构建输入参数"""

    def __init__(self):
        self.skill_cache = {}

    def invoke(self, skill_name: str, action: str, params: Dict, timeout: int = 90) -> Dict:
        skill_path = os.path.join(SKILL_BASE_PATH, skill_name, "main.py")
        if not os.path.exists(skill_path):
            return {"success": False, "error": f"技能 {skill_name} 不存在", "skill": skill_name}

        skill_input = self._build_input(skill_name, action, params)

        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, skill_path],
                input=json.dumps(skill_input, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            if result.returncode == 0 and result.stdout.strip():
                output = json.loads(result.stdout.strip())
                return {
                    "success": True,
                    "skill": skill_name,
                    "action": action,
                    "output": output,
                    "duration_ms": duration_ms,
                }
            else:
                error_msg = result.stderr[:500] if result.stderr else "执行失败"
                return {
                    "success": False,
                    "skill": skill_name,
                    "action": action,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "skill": skill_name,
                "action": action,
                "error": f"执行超时({timeout}s)",
                "duration_ms": duration_ms,
            }
        except json.JSONDecodeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "skill": skill_name,
                "action": action,
                "error": f"输出解析失败: {str(e)}",
                "duration_ms": duration_ms,
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "skill": skill_name,
                "action": action,
                "error": str(e),
                "duration_ms": duration_ms,
            }

    def _build_input(self, skill_name: str, action: str, params: Dict) -> Dict:
        normalized_name = skill_name.replace("-", "_")
        builder = getattr(self, f"_build_{normalized_name}_input", None)
        if builder:
            return builder(action, dict(params))

        base = {"action": action}
        base.update(params)
        return base

    def _build_listing_gen_input(self, action: str, params: Dict) -> Dict:
        base = {"action": action}
        base.update(params)
        return compact_dict(base)

    def _build_material_gen_input(self, action: str, params: Dict) -> Dict:
        base = {
            "action": action,
            "product_name": first_non_empty(params.get("product_name"), params.get("product")),
            "platform": first_non_empty(params.get("platform"), "amazon"),
            "material_type": first_non_empty(params.get("material_type"), "main_image"),
            "audience": first_non_empty(params.get("audience"), params.get("target_audience"), "泛人群"),
            "selling_points": first_non_empty(params.get("selling_points"), []),
        }
        base.update(params)
        return compact_dict(base)

    def _build_ad_optimizer_input(self, action: str, params: Dict) -> Dict:
        action_map = {
            "optimize": "full_analysis",
            "analyze": "health_check",
            "budget": "budget_allocation",
        }
        metrics = first_non_empty(params.get("metrics"), deep_get(params, "ad_analysis.metrics"), {})
        base = {
            "action": action_map.get(action, action),
            "platform": first_non_empty(params.get("platform"), "amazon"),
            "campaign_type": first_non_empty(params.get("campaign_type"), "sp"),
            "category": first_non_empty(params.get("category"), "electronics"),
            "metrics": metrics,
        }
        base.update(params)
        return compact_dict(base)

    def _build_report_gen_input(self, action: str, params: Dict) -> Dict:
        base = {
            "action": action,
            "report_type": first_non_empty(params.get("report_type"), self._infer_report_type(params), "weekly"),
            "date": params.get("date"),
            "platform": first_non_empty(params.get("platform"), "all"),
        }
        return compact_dict(base)

    def _build_excel_viz_input(self, action: str, params: Dict) -> Dict:
        report = first_non_empty(params.get("report"), deep_get(params, "report_data"))
        data = first_non_empty(params.get("data"), params.get("chart_data"))
        if not data:
            data = self._build_chart_dataset(report, params)

        title = first_non_empty(
            params.get("title"),
            self._build_chart_title(report, params.get("chart_type", "")),
            "经营数据图表",
        )
        chart_type = first_non_empty(params.get("chart_type"), self._infer_chart_type(data), "bar")

        base = {
            "action": action,
            "data": data,
            "chart_type": chart_type,
            "title": title,
            "operation": first_non_empty(params.get("operation"), "avg"),
        }
        return compact_dict(base)

    def _build_xhs_seed_input(self, action: str, params: Dict) -> Dict:
        base = {
            "action": action,
            "product_name": first_non_empty(params.get("product_name"), params.get("product"), params.get("topic")),
            "selling_points": first_non_empty(params.get("selling_points"), []),
            "target_audience": first_non_empty(params.get("target_audience"), params.get("audience"), "泛人群"),
            "note_type": first_non_empty(params.get("note_type"), "product"),
            "generate_calendar": action == "calendar" or bool(params.get("generate_calendar")),
        }
        base.update(params)
        return compact_dict(base)

    def _build_douyin_ops_input(self, action: str, params: Dict) -> Dict:
        base = {
            "action": action,
            "product_name": first_non_empty(params.get("product_name"), params.get("product"), params.get("topic")),
            "selling_points": first_non_empty(params.get("selling_points"), ["核心卖点突出", "适合短视频展示"]),
            "duration": first_non_empty(params.get("duration"), params.get("duration_seconds"), 35),
            "video_type": first_non_empty(params.get("video_type"), "product"),
            "target_audience": first_non_empty(params.get("target_audience"), params.get("audience"), "年轻人"),
            "features": first_non_empty(params.get("features"), []),
        }
        base.update(params)
        return compact_dict(base)

    def _build_video_channel_input(self, action: str, params: Dict) -> Dict:
        topic = first_non_empty(params.get("topic"), params.get("product_name"), params.get("product"))
        base = {
            "action": action,
            "topic": topic,
            "product": first_non_empty(params.get("product"), params.get("product_name"), topic),
            "audience": first_non_empty(params.get("audience"), params.get("target_audience"), "general"),
            "duration": first_non_empty(params.get("duration"), params.get("duration_seconds"), 45),
            "style": first_non_empty(params.get("style"), "friendly"),
        }
        base.update(params)
        return compact_dict(base)

    def _build_cross_drain_input(self, action: str, params: Dict) -> Dict:
        normalized_action = action if action in {
            "analyze_platform",
            "generate_strategy",
            "generate_content",
            "check_compliance",
            "cross_platform_strategy",
        } else "cross_platform_strategy"

        if normalized_action == "cross_platform_strategy":
            platforms = params.get("platforms") or self._infer_platforms(params)
            return compact_dict({
                "action": normalized_action,
                "platforms": platforms,
                "content_type": first_non_empty(params.get("content_type"), "product"),
            })

        if normalized_action == "generate_strategy":
            platform = first_non_empty(params.get("platform"), params.get("sourcePlatform"), "xiaohongshu")
            return compact_dict({
                "action": normalized_action,
                "platform": self._normalize_platform(platform),
                "content_type": first_non_empty(params.get("content_type"), "product"),
            })

        if normalized_action == "generate_content":
            platform = first_non_empty(params.get("platform"), params.get("sourcePlatform"), "xiaohongshu")
            return compact_dict({
                "action": normalized_action,
                "platform": self._normalize_platform(platform),
                "template_type": first_non_empty(params.get("template_type"), "comment"),
                "custom_text": first_non_empty(params.get("custom_text"), params.get("content"), ""),
            })

        return compact_dict({"action": normalized_action, **params})

    def _build_opinion_watch_input(self, action: str, params: Dict) -> Dict:
        content = first_non_empty(
            params.get("content"),
            params.get("fullContent"),
            self._compose_social_content(params),
        )
        base = {
            "action": action,
            "content": content,
            "brand_words": first_non_empty(params.get("brand_words"), params.get("keywords"), []),
        }
        base.update(params)
        return compact_dict(base)

    def _build_order_query_input(self, action: str, params: Dict) -> Dict:
        order_id = first_non_empty(
            params.get("order_id"),
            params.get("orderNo"),
            deep_get(params, "intent.entities.order_id"),
            deep_get(params, "order.orders.0.order_id"),
        )
        phone = first_non_empty(
            params.get("phone"),
            params.get("phone_raw"),
            deep_get(params, "intent.entities.phone_raw"),
        )

        base = {
            "action": first_non_empty(action, "query"),
            "order_id": order_id,
            "phone": phone,
            "platform": first_non_empty(params.get("platform"), "amazon"),
        }
        base.update(params)
        return compact_dict(base)

    def _build_logistics_track_input(self, action: str, params: Dict) -> Dict:
        tracking_number = first_non_empty(
            params.get("tracking_number"),
            params.get("trackingNo"),
            deep_get(params, "intent.entities.tracking_number"),
            deep_get(params, "order.orders.0.tracking_number"),
            deep_get(params, "order.orders.0.trackingNumber"),
        )
        base = {
            "action": first_non_empty(action, "track"),
            "tracking_number": tracking_number,
            "origin": first_non_empty(params.get("origin"), "CN"),
            "destination": params.get("destination", ""),
            "cross_border": bool(params.get("cross_border", False)),
        }
        base.update(params)
        return compact_dict(base)

    def _build_after_sale_input(self, action: str, params: Dict) -> Dict:
        order_id = first_non_empty(
            params.get("order_id"),
            params.get("orderNo"),
            deep_get(params, "order.orders.0.order_id"),
            deep_get(params, "intent.entities.order_id"),
        )
        base = {
            "action": first_non_empty(action, "query"),
            "order_id": order_id,
            "aftersale_id": first_non_empty(params.get("aftersale_id"), params.get("afterSaleId")),
            "type": first_non_empty(params.get("type"), params.get("afterSaleType")),
            "reason_category": first_non_empty(params.get("reason_category"), "quality"),
            "reason_detail": first_non_empty(params.get("reason_detail"), params.get("issue"), ""),
            "refund_amount": params.get("refund_amount", 0),
            "evidence": first_non_empty(params.get("evidence"), []),
            "buyer_id": first_non_empty(params.get("buyer_id"), params.get("customer_id"), ""),
        }
        base.update(params)
        return compact_dict(base)

    def _build_intent_recognition_input(self, action: str, params: Dict) -> Dict:
        return {
            "user_message": first_non_empty(params.get("user_message"), params.get("message"), ""),
            "history": first_non_empty(params.get("history"), []),
            "context": first_non_empty(params.get("context"), {}),
        }

    def _build_sentiment_analysis_input(self, action: str, params: Dict) -> Dict:
        return {
            "user_message": first_non_empty(params.get("user_message"), params.get("message"), ""),
            "history": first_non_empty(params.get("history"), []),
            "context": first_non_empty(params.get("context"), {}),
        }

    def _build_email_mgr_input(self, action: str, params: Dict) -> Dict:
        subject = first_non_empty(params.get("subject"), self._build_email_subject(params))
        body = first_non_empty(params.get("body"), self._build_email_body(params))
        base = {
            "subject": subject,
            "body": body,
            "sender": first_non_empty(params.get("sender"), params.get("senderRole"), ""),
            "attachments": first_non_empty(params.get("attachments"), []),
        }
        return compact_dict(base)

    def _build_doc_auto_input(self, action: str, params: Dict) -> Dict:
        content = first_non_empty(
            params.get("content"),
            params.get("sourceMaterial"),
            self._build_document_content(params),
        )
        metadata = dict(params.get("metadata", {}))
        if params.get("title"):
            metadata.setdefault("title", params.get("title"))
        if params.get("date"):
            metadata.setdefault("date", params.get("date"))

        base = {
            "content": content,
            "document_type": first_non_empty(params.get("document_type"), params.get("documentType"), "summary"),
            "metadata": metadata,
        }
        return compact_dict(base)

    def _compose_social_content(self, params: Dict) -> str:
        content_parts = []
        if params.get("fullContent"):
            content_parts.append(params["fullContent"])
        if deep_get(params, "xhs_content.fullContent"):
            content_parts.append(deep_get(params, "xhs_content.fullContent"))
        title_options = deep_get(params, "video_channel_content.title_options", []) or []
        if title_options:
            content_parts.append(" / ".join(title_options[:2]))
        script_segments = deep_get(params, "video_channel_content.script.segments", []) or []
        if script_segments:
            lines = [segment.get("content", "") for segment in script_segments[:3] if segment.get("content")]
            if lines:
                content_parts.append(" ".join(lines))
        return "\n".join(part for part in content_parts if part)

    def _build_chart_dataset(self, report: Any, params: Dict) -> List[Dict]:
        if isinstance(report, dict):
            sections = report.get("sections", [])
            for section in sections:
                rows = section.get("data")
                if not isinstance(rows, list) or not rows:
                    continue

                mapped_rows = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue

                    if "label" in row and "value" in row:
                        numeric = self._to_number(row.get("value"))
                        if numeric is not None:
                            mapped_rows.append({"name": row["label"], "value": numeric})
                    elif "day" in row and "orders" in row:
                        mapped_rows.append({"name": row["day"], "value": row["orders"]})
                    elif "date" in row and "orders" in row:
                        mapped_rows.append({"name": row["date"], "value": row["orders"]})
                    elif "category" in row and "sales" in row:
                        mapped_rows.append({"name": row["category"], "value": row["sales"]})
                    elif "platform" in row and "share" in row:
                        mapped_rows.append({"name": row["platform"], "value": row["share"]})

                if mapped_rows:
                    return mapped_rows

        metrics = params.get("metrics", {})
        if isinstance(metrics, dict) and metrics:
            dataset = []
            for key, value in metrics.items():
                numeric = self._to_number(value)
                if numeric is not None:
                    dataset.append({"name": key, "value": numeric})
            if dataset:
                return dataset

        return [
            {"name": "样本1", "value": 1},
            {"name": "样本2", "value": 2},
            {"name": "样本3", "value": 3},
        ]

    def _build_chart_title(self, report: Any, chart_type: str) -> str:
        if isinstance(report, dict) and report.get("title"):
            return f"{report['title']} - 图表"
        if chart_type == "line":
            return "趋势图"
        return "经营看板"

    def _infer_chart_type(self, data: List[Dict]) -> str:
        if not isinstance(data, list) or not data:
            return "bar"
        if any(item.get("name") in {"周一", "周二", "周三", "周四", "周五", "周六", "周日"} for item in data if isinstance(item, dict)):
            return "line"
        return "bar"

    def _build_document_content(self, params: Dict) -> str:
        report = params.get("report", {})
        if not isinstance(report, dict):
            return ""

        lines = []
        if report.get("title"):
            lines.append(report["title"])
        for insight in report.get("insights", [])[:4]:
            lines.append(f"- 洞察：{insight}")
        for recommendation in report.get("recommendations", [])[:4]:
            lines.append(f"- 建议：{recommendation}")
        return "\n".join(lines)

    def _build_email_subject(self, params: Dict) -> str:
        report = params.get("report", {})
        if isinstance(report, dict) and report.get("title"):
            return f"{report['title']} 摘要"
        return "自动生成的业务摘要"

    def _build_email_body(self, params: Dict) -> str:
        document = params.get("document", {})
        report = params.get("report", {})

        lines = ["您好，以下为自动整理的摘要：", ""]
        if isinstance(report, dict):
            for insight in report.get("insights", [])[:3]:
                lines.append(f"- {insight}")
        if isinstance(document, dict):
            summary = deep_get(document, "document.summary")
            if summary:
                lines.extend(["", "文档摘要：", summary])
        lines.extend(["", "请审阅。"])
        return "\n".join(lines)

    def _infer_platforms(self, params: Dict) -> List[str]:
        platforms = params.get("platforms", [])
        if platforms:
            return [self._normalize_platform(platform) for platform in platforms if self._normalize_platform(platform)]

        candidates = [
            params.get("sourcePlatform"),
            params.get("targetPlatform"),
            params.get("platform"),
        ]
        normalized = []
        for candidate in candidates:
            platform = self._normalize_platform(candidate)
            if platform and platform not in normalized:
                normalized.append(platform)

        return normalized or ["xiaohongshu", "video-channel"]

    def _normalize_platform(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None

        normalized = str(value).strip().lower()
        aliases = {
            "xhs": "xiaohongshu",
            "小红书": "xiaohongshu",
            "douyin": "douyin",
            "抖音": "douyin",
            "video-channel": "video-channel",
            "video_channel": "video-channel",
            "视频号": "video-channel",
            "kuaishou": "kuaishou",
            "快手": "kuaishou",
        }
        return aliases.get(normalized, normalized if normalized in {"xiaohongshu", "douyin", "video-channel", "kuaishou"} else None)

    def _infer_report_type(self, params: Dict) -> str:
        text = " ".join(str(value) for key, value in params.items() if key in {"message", "user_message", "report_type", "title"})
        if "月" in text or "monthly" in text.lower():
            return "monthly"
        if "日" in text or "daily" in text.lower():
            return "daily"
        return "weekly"

    def _to_number(self, value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = value.replace("¥", "").replace(",", "").replace("%", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None


class ConditionEvaluator:
    """条件评估器：判断工作流步骤的执行条件（是否有物流单号/订单ID/负面评论等）"""

    def __init__(self):
        self.conditions = {
            "has_tracking": self._has_tracking,
            "has_aftersale": self._has_aftersale,
            "has_negative": self._has_negative,
            "has_order_id": self._has_order_id,
            "has_product": self._has_product,
            "high_value_order": self._high_value_order,
            "vip_customer": self._vip_customer,
            "has_ad_metrics": self._has_ad_metrics,
            "has_platform_pair": self._has_platform_pair,
            "has_opinion_content": self._has_opinion_content,
        }

    def evaluate(self, condition: str, context: Dict, step_results: Dict) -> bool:
        if not condition:
            return True

        evaluator = self.conditions.get(condition)
        if evaluator:
            return evaluator(context, step_results)

        return True

    def _has_tracking(self, context: Dict, step_results: Dict) -> bool:
        return bool(
            context.get("tracking_number")
            or context.get("trackingNo")
            or deep_get(context, "entities.tracking_number")
            or deep_get(step_results, "intent.output.entities.tracking_number")
            or deep_get(step_results, "order.output.orders.0.tracking_number")
            or deep_get(step_results, "order.output.orders.0.trackingNumber")
        )

    def _has_aftersale(self, context: Dict, step_results: Dict) -> bool:
        return bool(
            context.get("aftersale_id")
            or context.get("afterSaleId")
            or deep_get(step_results, "aftersale.output.records.0.aftersale_id")
            or deep_get(step_results, "order.output.orders.0.aftersale_id")
            or deep_get(step_results, "order.output.orders.0.has_aftersale")
        )

    def _has_negative(self, context: Dict, step_results: Dict) -> bool:
        analysis_result = step_results.get("review_analysis", {})
        output = analysis_result.get("output", {})
        if isinstance(output, dict):
            sentiment = output.get("sentiment", "")
            negative_rate = output.get("negative_rate", 0)
            return sentiment in ["negative", "angry"] or negative_rate > 0.3
        return False

    def _has_order_id(self, context: Dict, step_results: Dict) -> bool:
        return bool(
            context.get("order_id")
            or context.get("orderNo")
            or deep_get(context, "entities.order_id")
            or deep_get(step_results, "intent.output.entities.order_id")
            or deep_get(step_results, "order.output.orders.0.order_id")
        )

    def _has_product(self, context: Dict, step_results: Dict) -> bool:
        return bool(
            context.get("product_name")
            or context.get("product")
            or context.get("topic")
            or deep_get(context, "entities.product_name")
        )

    def _high_value_order(self, context: Dict, step_results: Dict) -> bool:
        return context.get("order_value", 0) > 5000

    def _vip_customer(self, context: Dict, step_results: Dict) -> bool:
        return context.get("customer_tier") == "VIP"

    def _has_ad_metrics(self, context: Dict, step_results: Dict) -> bool:
        metrics = context.get("metrics", {})
        if isinstance(metrics, dict) and metrics:
            return True
        return any(key in context for key in ("acos", "ctr", "cvr", "roas", "spend", "revenue"))

    def _has_platform_pair(self, context: Dict, step_results: Dict) -> bool:
        platforms = context.get("platforms", [])
        if isinstance(platforms, list) and len(platforms) >= 1:
            return True
        return bool(context.get("sourcePlatform") or context.get("targetPlatform"))

    def _has_opinion_content(self, context: Dict, step_results: Dict) -> bool:
        return bool(
            context.get("content")
            or context.get("fullContent")
            or deep_get(step_results, "xhs_content.output.fullContent")
            or deep_get(step_results, "video_channel_content.output.title_options.0")
            or deep_get(step_results, "douyin_script.output.script.0.line")
        )


class ResultAggregator:
    """结果聚合器：按工作流类型聚合各步骤输出，生成结构化报告"""

    def __init__(self):
        self.aggregators = {
            "full_launch_report": self._full_launch_report,
            "order_full_report": self._order_full_report,
            "crisis_report": self._crisis_report,
            "campaign_report": self._campaign_report,
            "ad_optimization_report": self._ad_optimization_report,
            "ecommerce_operations_report": self._ecommerce_operations_report,
            "social_media_flywheel_report": self._social_media_flywheel_report,
            "customer_service_report": self._customer_service_report,
            "office_productivity_report": self._office_productivity_report,
            "default": self._default_aggregation,
        }

    def aggregate(self, aggregation_type: str, step_results: Dict, context: Dict) -> Dict:
        aggregator = self.aggregators.get(aggregation_type, self.aggregators["default"])
        return aggregator(step_results, context)

    def _full_launch_report(self, step_results: Dict, context: Dict) -> Dict:
        listing = self._safe_output(step_results, "listing")
        materials = self._safe_output(step_results, "materials")
        ad_plan = self._safe_output(step_results, "ad_plan")
        xhs_content = self._safe_output(step_results, "xhs_content")

        return {
            "type": "full_launch_report",
            "summary": {
                "listing_generated": bool(listing),
                "materials_generated": bool(materials),
                "ad_plan_generated": bool(ad_plan),
                "xhs_content_generated": bool(xhs_content),
                "total_steps_completed": sum(1 for v in step_results.values() if v.get("success")),
                "total_steps_attempted": len(step_results),
            },
            "listing": listing,
            "materials": materials,
            "ad_plan": ad_plan,
            "xhs_content": xhs_content,
            "recommendations": self._generate_launch_recommendations(listing, ad_plan, xhs_content),
        }

    def _order_full_report(self, step_results: Dict, context: Dict) -> Dict:
        raw_order = self._safe_output(step_results, "order")
        order = self._normalize_order(raw_order)
        logistics = self._safe_output(step_results, "logistics")
        aftersale = self._normalize_aftersale(self._safe_output(step_results, "aftersale"))

        return {
            "type": "order_full_report",
            "summary": {
                "order_found": bool(order),
                "logistics_available": bool(logistics),
                "aftersale_exists": bool(aftersale),
            },
            "order": order,
            "logistics": logistics,
            "aftersale": aftersale,
            "next_actions": self._generate_order_next_actions(order, logistics, aftersale),
            "handoff": self._collect_handoffs(step_results),
        }

    def _crisis_report(self, step_results: Dict, context: Dict) -> Dict:
        analysis = self._safe_output(step_results, "review_analysis")
        alerts = self._safe_output(step_results, "alerts")
        replies = self._safe_output(step_results, "replies")
        opinion = self._safe_output(step_results, "opinion")

        return {
            "type": "crisis_report",
            "severity": self._assess_crisis_severity(analysis, alerts),
            "review_analysis": analysis,
            "alerts": alerts,
            "suggested_replies": replies,
            "opinion_status": opinion,
            "recommended_actions": self._generate_crisis_actions(analysis, alerts),
            "handoff": self._collect_handoffs(step_results),
        }

    def _campaign_report(self, step_results: Dict, context: Dict) -> Dict:
        xhs = self._safe_output(step_results, "xhs_content")
        calendar = self._safe_output(step_results, "xhs_calendar")
        douyin = self._safe_output(step_results, "douyin_script")
        opinion = self._safe_output(step_results, "opinion")

        return {
            "type": "campaign_report",
            "summary": {
                "xhs_content_ready": bool(xhs),
                "calendar_ready": bool(calendar),
                "douyin_script_ready": bool(douyin),
                "opinion_monitoring": bool(opinion),
            },
            "xhs_content": xhs,
            "xhs_calendar": calendar,
            "douyin_script": douyin,
            "opinion_status": opinion,
            "handoff": self._collect_handoffs(step_results),
        }

    def _ad_optimization_report(self, step_results: Dict, context: Dict) -> Dict:
        analysis = self._safe_output(step_results, "ad_analysis")
        budget = self._safe_output(step_results, "budget_plan")
        listing_suggestions = self._safe_output(step_results, "listing_suggestions")

        return {
            "type": "ad_optimization_report",
            "ad_analysis": analysis,
            "budget_plan": budget,
            "listing_suggestions": listing_suggestions,
            "priority_actions": self._generate_ad_priority_actions(analysis, budget),
            "handoff": self._collect_handoffs(step_results),
        }

    def _ecommerce_operations_report(self, step_results: Dict, context: Dict) -> Dict:
        listing = self._safe_output(step_results, "listing")
        materials = self._safe_output(step_results, "materials")
        ad_analysis = self._safe_output(step_results, "ad_analysis")
        report = self._safe_output(step_results, "report")
        chart_board = self._safe_output(step_results, "chart_board")

        recommendations = []
        if listing:
            recommendations.append("Listing 已产出，先做合规审核再进入上架发布。")
        if materials:
            recommendations.append("素材已准备，可按平台尺寸要求进入设计与投放。")
        if ad_analysis:
            recommendations.extend(self._generate_ad_priority_actions(ad_analysis, {}))
        if report:
            recommendations.append("经营报表已生成，建议同步到周会或晨会复盘。")
        if chart_board:
            recommendations.append("图表看板可直接复用到经营汇报或日报大屏。")

        return {
            "type": "ecommerce_operations_report",
            "summary": {
                "listing_ready": bool(listing),
                "materials_ready": bool(materials),
                "ad_analysis_ready": bool(ad_analysis),
                "report_ready": bool(report),
                "chart_ready": bool(chart_board),
            },
            "deliverables": {
                "listing": listing,
                "materials": materials,
                "ad_analysis": ad_analysis,
                "report": report,
                "chart_board": chart_board,
            },
            "recommendations": recommendations or ["建议补齐商品资料后重新生成完整经营链路。"],
            "handoff": self._collect_handoffs(step_results),
        }

    def _social_media_flywheel_report(self, step_results: Dict, context: Dict) -> Dict:
        xhs_content = self._safe_output(step_results, "xhs_content")
        douyin_script = self._safe_output(step_results, "douyin_script")
        video_channel_content = self._safe_output(step_results, "video_channel_content")
        drain_strategy = self._safe_output(step_results, "drain_strategy")
        opinion = self._safe_output(step_results, "opinion")

        return {
            "type": "social_media_flywheel_report",
            "summary": {
                "xhs_ready": bool(xhs_content),
                "douyin_ready": bool(douyin_script),
                "video_channel_ready": bool(video_channel_content),
                "cross_drain_ready": bool(drain_strategy),
                "opinion_watch_ready": bool(opinion),
            },
            "content_matrix": {
                "xhs": self._first_title(xhs_content),
                "douyin": deep_get(douyin_script, "video_title"),
                "video_channel": first_non_empty(
                    deep_get(video_channel_content, "title_options.0"),
                    deep_get(video_channel_content, "title"),
                ),
            },
            "distribution": {
                "cross_drain": drain_strategy,
                "opinion_watch": opinion,
            },
            "recommendations": [
                "优先发布小红书和视频号版本，复用同一主题素材做平台差异化改写。",
                "私域导流建议保留人工审核，避免导流词触发平台风控。",
                "舆情监控结果应接入定时巡检，形成内容发布后的复盘闭环。",
            ],
            "handoff": self._collect_handoffs(step_results),
        }

    def _customer_service_report(self, step_results: Dict, context: Dict) -> Dict:
        intent = self._safe_output(step_results, "intent")
        order = self._normalize_order(self._safe_output(step_results, "order"))
        logistics = self._safe_output(step_results, "logistics")
        aftersale = self._normalize_aftersale(self._safe_output(step_results, "aftersale"))
        sentiment = self._safe_output(step_results, "sentiment")
        handoff = self._collect_handoffs(step_results)

        next_actions = []
        if order:
            next_actions.extend(self._generate_order_next_actions(order, logistics, aftersale))
        if isinstance(sentiment, dict) and sentiment.get("require_human"):
            next_actions.append(sentiment.get("transfer_reason") or "检测到负面情绪，建议转人工。")
        if aftersale:
            next_actions.append("售后记录已命中，可直接进入退款/退换货流程确认。")
        if not next_actions:
            next_actions.append("建议继续补充订单号、物流单号或售后证据。")

        return {
            "type": "customer_service_report",
            "summary": {
                "intent": intent.get("intent"),
                "intent_label": intent.get("intent_label"),
                "order_found": bool(order),
                "logistics_found": bool(logistics),
                "aftersale_found": bool(aftersale),
                "require_human": handoff["needs_human_review"],
            },
            "intent": intent,
            "order": order,
            "logistics": logistics,
            "aftersale": aftersale,
            "sentiment": sentiment,
            "next_actions": next_actions,
            "handoff": handoff,
        }

    def _office_productivity_report(self, step_results: Dict, context: Dict) -> Dict:
        report = self._safe_output(step_results, "report")
        chart_board = self._safe_output(step_results, "chart_board")
        document = self._safe_output(step_results, "document")
        email = self._safe_output(step_results, "email")

        return {
            "type": "office_productivity_report",
            "summary": {
                "report_ready": bool(report),
                "chart_ready": bool(chart_board),
                "document_ready": bool(document),
                "email_ready": bool(email),
            },
            "report_title": report.get("title") if isinstance(report, dict) else "",
            "document_summary": deep_get(document, "document.summary"),
            "email_subject": email.get("subject"),
            "deliverables": {
                "report": report,
                "chart_board": chart_board,
                "document": document,
                "email": email,
            },
            "recommendations": [
                "图表可直接贴入周报或经营复盘材料。",
                "文档摘要建议由业务负责人补充结论和责任人。",
                "邮件草稿默认只起草不发送，保留人工审批。",
            ],
            "handoff": self._collect_handoffs(step_results),
        }

    def _default_aggregation(self, step_results: Dict, context: Dict) -> Dict:
        return {
            "type": "default",
            "results": {key: val.get("output", {}) for key, val in step_results.items() if val.get("success")},
            "errors": {key: val.get("error", "") for key, val in step_results.items() if not val.get("success")},
            "summary": {
                "total_steps": len(step_results),
                "successful_steps": sum(1 for v in step_results.values() if v.get("success")),
                "failed_steps": sum(1 for v in step_results.values() if not v.get("success")),
            },
            "handoff": self._collect_handoffs(step_results),
        }

    def _generate_launch_recommendations(self, listing, ad_plan, xhs_content) -> List[str]:
        recs = []
        if listing:
            recs.append("Listing已生成，建议先进行合规检查后再上架")
        if ad_plan:
            recs.append("广告方案已生成，建议从小预算开始测试")
        if xhs_content:
            recs.append("小红书内容已生成，建议按照内容日历定时发布")
        if not recs:
            recs.append("建议先完成Listing生成，再进行后续步骤")
        return recs

    def _generate_order_next_actions(self, order, logistics, aftersale) -> List[str]:
        actions = []
        if order:
            status = order.get("status", "") if isinstance(order, dict) else ""
            if status in ["pending", "pending_payment"]:
                actions.append("订单待支付，建议提醒买家完成付款")
            elif status == "shipped":
                actions.append("订单已发货，可提供物流追踪信息")
            elif status == "completed":
                actions.append("订单已完成，可邀请买家评价")
        if logistics:
            progress = logistics.get("progress", 0) if isinstance(logistics, dict) else 0
            if progress < 50:
                actions.append("物流进度较慢，建议关注配送状态")
        if aftersale:
            actions.append("存在售后记录，建议优先处理售后问题")
        if not actions:
            actions.append("订单查询完成，如需进一步帮助请告知")
        return actions

    def _assess_crisis_severity(self, analysis, alerts) -> str:
        if isinstance(alerts, dict) and alerts.get("critical_alerts"):
            return "critical"
        if isinstance(analysis, dict):
            sentiment = analysis.get("sentiment", "")
            if sentiment in ["angry"]:
                return "high"
            if sentiment in ["negative"]:
                return "medium"
        return "low"

    def _generate_crisis_actions(self, analysis, alerts) -> List[str]:
        actions = []
        if isinstance(alerts, dict) and alerts.get("critical_alerts"):
            actions.append("检测到严重差评危机，建议立即启动危机公关流程")
        actions.append("对所有差评进行分类处理，优先处理高影响力差评")
        actions.append("准备标准化的差评回复模板")
        actions.append("持续监控舆情动态，及时响应新差评")
        return actions

    def _generate_ad_priority_actions(self, analysis, budget) -> List[str]:
        actions = []
        if isinstance(analysis, dict):
            acos = analysis.get("acos", 0) or deep_get(analysis, "metrics.acos") or 0
            if acos > 35:
                actions.append(f"ACOS偏高({acos:.1f}%)，建议降低无效关键词出价")
            elif acos < 15:
                actions.append(f"ACOS优秀({acos:.1f}%)，可适当增加预算扩大曝光")
        if isinstance(budget, dict):
                actions.append("预算分配方案已生成，建议按周调整")
        if not actions:
            actions.append("广告数据分析完成，建议持续优化关键词和出价策略")
        return actions

    def _safe_output(self, step_results: Dict, key: str) -> Dict:
        result = step_results.get(key, {})
        if isinstance(result, dict):
            return result.get("output", {}) if result.get("success") else {}
        return {}

    def _normalize_order(self, order_output: Dict) -> Dict:
        if not isinstance(order_output, dict):
            return {}
        if order_output.get("orders"):
            return order_output["orders"][0]
        return order_output

    def _normalize_aftersale(self, aftersale_output: Dict) -> Dict:
        if not isinstance(aftersale_output, dict):
            return {}
        if aftersale_output.get("records"):
            return aftersale_output["records"][0]
        return aftersale_output

    def _collect_handoffs(self, step_results: Dict) -> Dict:
        review_reasons = []
        max_confidence = None

        for result in step_results.values():
            if not isinstance(result, dict) or not result.get("success"):
                continue
            handoff = deep_get(result, "output.handoff")
            if not isinstance(handoff, dict):
                continue
            if handoff.get("needsHumanReview"):
                reason = handoff.get("reason")
                if reason:
                    review_reasons.append(reason)
            confidence = handoff.get("confidence")
            if isinstance(confidence, (int, float)):
                if max_confidence is None or confidence < max_confidence:
                    max_confidence = confidence

        return {
            "needs_human_review": bool(review_reasons),
            "reasons": review_reasons,
            "lowest_confidence": max_confidence,
        }

    def _first_title(self, payload: Dict) -> str:
        if not isinstance(payload, dict):
            return ""
        titles = payload.get("titles", [])
        if titles and isinstance(titles[0], dict):
            return titles[0].get("title", "")
        return payload.get("title", "")


class WorkflowEngine:
    """工作流引擎：编排多步骤业务闭环，支持条件执行/参数传递/执行持久化"""

    def __init__(self):
        self.invoker = SkillInvoker()
        self.condition_eval = ConditionEvaluator()
        self.aggregator = ResultAggregator()
        init_db()

    def execute_workflow(self, workflow_name: str, params: Dict, context: Dict = None) -> Dict:
        if context is None:
            context = {}
        runtime_context = self._merge_context(params, context)

        template = WORKFLOW_TEMPLATES.get(workflow_name)
        if not template:
            custom_template = self._load_custom_template(workflow_name)
            if custom_template:
                template = custom_template
            else:
                return {"success": False, "error": f"工作流 {workflow_name} 不存在"}

        execution_id = f"wf-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(str(params)) % 10000:04d}"
        start_time = time.time()

        self._save_execution_start(execution_id, workflow_name, len(template["steps"]))

        step_results = {}
        completed_steps = 0
        failed_steps = 0
        step_details = []

        for i, step in enumerate(template["steps"]):
            condition = step.get("condition", "")
            if condition and not self.condition_eval.evaluate(condition, runtime_context, step_results):
                step_details.append({
                    "step_index": i,
                    "skill": step["skill"],
                    "action": step["action"],
                    "status": "skipped",
                    "reason": f"条件 {condition} 不满足",
                })
                self._save_step(execution_id, i, step, "skipped", None, None, 0, f"条件 {condition} 不满足")
                continue

            step_params = dict(step.get("params", {}))
            step_params.update(params)
            resolved_inputs = self._resolve_input_mapping(step.get("input_mapping", {}), params, step_results, runtime_context)
            step_params.update(resolved_inputs)

            step_start = time.time()
            result = self.invoker.invoke(step["skill"], step["action"], step_params)
            step_duration = int((time.time() - step_start) * 1000)

            output_key = step.get("output_key", step["skill"])
            step_results[output_key] = result

            if result["success"]:
                completed_steps += 1
                self._save_step(execution_id, i, step, "success", step_params, result.get("output"), step_duration)
            else:
                failed_steps += 1
                self._save_step(execution_id, i, step, "failed", step_params, None, step_duration, result.get("error", ""))
                if step.get("required", False):
                    self._save_execution_end(execution_id, "failed", completed_steps, failed_steps, int((time.time() - start_time) * 1000))
                    return {
                        "success": False,
                        "execution_id": execution_id,
                        "workflow": workflow_name,
                        "error": f"必需步骤 {step['skill']} 执行失败: {result.get('error', '')}",
                        "completed_steps": completed_steps,
                        "failed_steps": failed_steps,
                        "step_results": step_results,
                    }

            step_details.append({
                "step_index": i,
                "skill": step["skill"],
                "action": step["action"],
                "status": "success" if result["success"] else "failed",
                "duration_ms": step_duration,
                "output_key": output_key,
            })

        aggregation_type = template.get("aggregation", "default")
        aggregated = self.aggregator.aggregate(aggregation_type, step_results, runtime_context)

        total_duration = int((time.time() - start_time) * 1000)
        self._save_execution_end(execution_id, "completed", completed_steps, failed_steps, total_duration)

        return {
            "success": True,
            "execution_id": execution_id,
            "workflow": workflow_name,
            "workflow_name": template["name"],
            "domain": template.get("domain", ""),
            "agent": template.get("agent", ""),
            "total_steps": len(template["steps"]),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": len(template["steps"]) - completed_steps - failed_steps,
            "duration_ms": total_duration,
            "step_details": step_details,
            "step_results": step_results,
            "aggregated_result": aggregated,
        }

    def execute_custom(self, steps: List[Dict], params: Dict, context: Dict = None, aggregation_type: str = "default") -> Dict:
        if context is None:
            context = {}
        runtime_context = self._merge_context(params, context)

        execution_id = f"custom-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        start_time = time.time()

        step_results = {}
        completed_steps = 0
        failed_steps = 0
        step_details = []

        for i, step in enumerate(steps):
            skill_name = step.get("skill", "")
            action = step.get("action", "process")
            condition = step.get("condition", "")
            required = step.get("required", False)
            output_key = step.get("output_key", skill_name)

            if condition and not self.condition_eval.evaluate(condition, runtime_context, step_results):
                step_details.append({
                    "step_index": i,
                    "skill": skill_name,
                    "action": action,
                    "status": "skipped",
                    "reason": f"条件 {condition} 不满足",
                })
                continue

            step_params = dict(step.get("params", {}))
            step_params.update(params)
            resolved_inputs = self._resolve_input_mapping(step.get("input_mapping", {}), params, step_results, runtime_context)
            step_params.update(resolved_inputs)

            result = self.invoker.invoke(skill_name, action, step_params)
            step_results[output_key] = result

            if result["success"]:
                completed_steps += 1
            else:
                failed_steps += 1
                if required:
                    return {
                        "success": False,
                        "execution_id": execution_id,
                        "error": f"必需步骤 {skill_name} 执行失败",
                        "step_results": step_results,
                    }

            step_details.append({
                "step_index": i,
                "skill": skill_name,
                "action": action,
                "status": "success" if result["success"] else "failed",
                "output_key": output_key,
            })

        aggregated = self.aggregator.aggregate(aggregation_type, step_results, runtime_context)
        total_duration = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "execution_id": execution_id,
            "workflow": "custom",
            "total_steps": len(steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "duration_ms": total_duration,
            "step_details": step_details,
            "step_results": step_results,
            "aggregated_result": aggregated,
        }

    def _resolve_input_mapping(self, mapping: Dict, params: Dict, step_results: Dict, context: Dict) -> Dict:
        resolved = {}
        for target_key, source_ref in mapping.items():
            value = self._resolve_source_ref(source_ref, params, step_results, context)
            if value is not None:
                resolved[target_key] = value
        return resolved

    def _resolve_source_ref(self, source_ref: Any, params: Dict, step_results: Dict, context: Dict):
        if not isinstance(source_ref, str):
            return source_ref

        if source_ref == "@params":
            return params
        if source_ref == "@context":
            return context
        if source_ref.startswith("@params."):
            return deep_get(params, source_ref[len("@params."):])
        if source_ref.startswith("@context."):
            return deep_get(context, source_ref[len("@context."):])
        if source_ref.startswith("@result:"):
            path = source_ref[len("@result:"):]
            step_key, _, remainder = path.partition(".")
            result = step_results.get(step_key, {})
            if not result.get("success"):
                return None
            output = result.get("output", {})
            return deep_get(output, remainder) if remainder else output

        if source_ref in step_results:
            result = step_results[source_ref]
            if result.get("success") and isinstance(result.get("output"), dict):
                return result["output"]
            return None
        if source_ref in params:
            return params[source_ref]
        if source_ref in context:
            return context[source_ref]
        return None

    def _merge_context(self, params: Dict, context: Dict) -> Dict:
        runtime_context = dict(params or {})
        runtime_context.update(context or {})
        return runtime_context

    def _load_custom_template(self, name: str) -> Optional[Dict]:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT definition FROM workflow_templates WHERE name = ?", (name,))
            row = c.fetchone()
            conn.close()
            if row:
                return json.loads(row["definition"])
            return None
        except Exception:
            return None

    def save_custom_template(self, name: str, definition: Dict) -> Dict:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            def_json = json.dumps(definition, ensure_ascii=False)
            c.execute(
                "INSERT OR REPLACE INTO workflow_templates (name, definition, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (name, def_json, now, now),
            )
            conn.commit()
            conn.close()
            return {"success": True, "message": f"工作流模板 {name} 已保存"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_workflows(self) -> Dict:
        built_in = [
            {
                "name": name,
                "display_name": tmpl["name"],
                "description": tmpl["description"],
                "domain": tmpl.get("domain", ""),
                "agent": tmpl.get("agent", ""),
                "steps_count": len(tmpl["steps"]),
                "skills": [step["skill"] for step in tmpl["steps"]],
                "type": "built-in",
            }
            for name, tmpl in WORKFLOW_TEMPLATES.items()
        ]

        custom = []
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT name, definition FROM workflow_templates")
            for row in c.fetchall():
                try:
                    defn = json.loads(row["definition"])
                    custom.append({
                        "name": row["name"],
                        "display_name": defn.get("name", row["name"]),
                        "description": defn.get("description", ""),
                        "steps_count": len(defn.get("steps", [])),
                        "type": "custom",
                    })
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

        return {
            "built_in": built_in,
            "custom": custom,
            "total": len(built_in) + len(custom),
        }

    def get_execution_history(self, limit: int = 20) -> List[Dict]:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "SELECT execution_id, workflow_name, status, total_steps, completed_steps, failed_steps, started_at, completed_at, duration_ms FROM workflow_executions ORDER BY started_at DESC LIMIT ?",
                (limit,),
            )
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def _save_execution_start(self, execution_id: str, workflow_name: str, total_steps: int):
        try:
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO workflow_executions (execution_id, workflow_name, status, total_steps, started_at) VALUES (?, ?, ?, ?, ?)",
                (execution_id, workflow_name, "running", total_steps, now),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _save_execution_end(self, execution_id: str, status: str, completed: int, failed: int, duration_ms: int):
        try:
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "UPDATE workflow_executions SET status = ?, completed_steps = ?, failed_steps = ?, completed_at = ?, duration_ms = ? WHERE execution_id = ?",
                (status, completed, failed, now, duration_ms, execution_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _save_step(self, execution_id: str, step_index: int, step: Dict, status: str, input_data, output_data, duration_ms: int, error_msg: str = ""):
        try:
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT INTO workflow_steps (execution_id, step_index, skill_name, action, status, input_data, output_data, duration_ms, error_message, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    execution_id,
                    step_index,
                    step.get("skill", ""),
                    step.get("action", ""),
                    status,
                    json.dumps(input_data, ensure_ascii=False, default=str)[:2000] if input_data else "",
                    json.dumps(output_data, ensure_ascii=False, default=str)[:2000] if output_data else "",
                    duration_ms,
                    error_msg,
                    now,
                    now,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


def main():
    input_data = json.loads(sys.stdin.read())

    action = input_data.get("action", "list_workflows")
    engine = WorkflowEngine()

    if action == "execute_workflow":
        workflow_name = input_data.get("workflow_name", "")
        params = input_data.get("params", {})
        context = input_data.get("context", {})
        result = engine.execute_workflow(workflow_name, params, context)

    elif action == "execute_custom":
        steps = input_data.get("steps", [])
        params = input_data.get("params", {})
        context = input_data.get("context", {})
        aggregation_type = input_data.get("aggregation_type", "default")
        result = engine.execute_custom(steps, params, context, aggregation_type)

    elif action == "list_workflows":
        result = engine.list_workflows()

    elif action == "save_template":
        name = input_data.get("name", "")
        definition = input_data.get("definition", {})
        result = engine.save_custom_template(name, definition)

    elif action == "get_history":
        limit = input_data.get("limit", 20)
        result = {"executions": engine.get_execution_history(limit)}

    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
