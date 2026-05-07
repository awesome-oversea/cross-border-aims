import json
import os
import sys
import sqlite3
import subprocess
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SKILLS_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
AGENTS_ROOT = os.path.join(PROJECT_ROOT, "agents")
DB_PATH = os.path.join(BASE_DIR, "orchestrator.db")


def _skill_path(skill_name: str) -> str:
    return os.path.join(SKILLS_ROOT, skill_name, "main.py")


# 技能注册表：所有可用技能的路径、意图映射、所属域和描述
SKILL_REGISTRY = {
    "skill-orchestrator": {
        "path": _skill_path("skill-orchestrator"),
        "intents": ["workflow_orchestration", "business_workflow"],
        "domain": "main",
        "description": "业务工作流编排",
    },
    "listing-gen": {
        "path": _skill_path("listing-gen"),
        "intents": ["listing_generation", "listing_optimization"],
        "domain": "ecommerce",
        "description": "Listing智能生成与优化",
    },
    "ad-optimizer": {
        "path": _skill_path("ad-optimizer"),
        "intents": ["ad_optimization", "ad_budget", "ad_bidding"],
        "domain": "ecommerce",
        "description": "广告投放优化",
    },
    "review-mgr": {
        "path": _skill_path("review-mgr"),
        "intents": ["review_analysis", "review_reply", "review_alert"],
        "domain": "ecommerce",
        "description": "评论舆情管理",
    },
    "material-gen": {
        "path": _skill_path("material-gen"),
        "intents": ["material_generation", "image_generation"],
        "domain": "ecommerce",
        "description": "素材AIGC生成",
    },
    "xhs-seed": {
        "path": _skill_path("xhs-seed"),
        "intents": ["xhs_content", "xhs_calendar", "xhs_trend"],
        "domain": "social-media",
        "description": "小红书种草",
    },
    "douyin-ops": {
        "path": _skill_path("douyin-ops"),
        "intents": ["douyin_script", "douyin_trend"],
        "domain": "social-media",
        "description": "抖音运营",
    },
    "video-channel": {
        "path": _skill_path("video-channel"),
        "intents": ["video_channel_script", "video_channel_distribution"],
        "domain": "social-media",
        "description": "视频号内容分发",
    },
    "cross-drain": {
        "path": _skill_path("cross-drain"),
        "intents": ["private_domain_drain", "cross_platform_drain"],
        "domain": "social-media",
        "description": "跨平台私域导流",
    },
    "opinion-watch": {
        "path": _skill_path("opinion-watch"),
        "intents": ["opinion_monitor", "crisis_alert"],
        "domain": "social-media",
        "description": "舆情监控",
    },
    "intent-recognition": {
        "path": _skill_path("intent-recognition"),
        "intents": ["presales", "customer_intent_recognition"],
        "domain": "cs",
        "description": "客服意图识别",
    },
    "order-query": {
        "path": _skill_path("order-query"),
        "intents": ["order_query", "order_status"],
        "domain": "cs",
        "description": "订单查询",
    },
    "logistics-track": {
        "path": _skill_path("logistics-track"),
        "intents": ["logistics", "tracking"],
        "domain": "cs",
        "description": "物流追踪",
    },
    "after-sale": {
        "path": _skill_path("after-sale"),
        "intents": ["aftersale", "refund", "exchange", "complaint"],
        "domain": "cs",
        "description": "售后处理",
    },
    "sentiment-analysis": {
        "path": _skill_path("sentiment-analysis"),
        "intents": ["sentiment_analysis", "emotion_handover"],
        "domain": "cs",
        "description": "情感识别与转人工",
    },
    "report-gen": {
        "path": _skill_path("report-gen"),
        "intents": ["report_generation", "data_report"],
        "domain": "office",
        "description": "报表生成",
    },
    "excel-viz": {
        "path": _skill_path("excel-viz"),
        "intents": ["excel_visualization", "data_visualization"],
        "domain": "office",
        "description": "Excel数据可视化",
    },
    "email-mgr": {
        "path": _skill_path("email-mgr"),
        "intents": ["email_management", "email_reply", "email_classification"],
        "domain": "office",
        "description": "邮件管理",
    },
    "doc-auto": {
        "path": _skill_path("doc-auto"),
        "intents": ["document_automation", "meeting_minutes"],
        "domain": "office",
        "description": "文档自动化",
    },
    "rag-retrieval": {
        "path": _skill_path("rag-retrieval"),
        "intents": ["knowledge_retrieval"],
        "domain": "shared",
        "description": "RAG知识检索",
    },
}

INTENT_LABELS = {
    "workflow_orchestration": "业务工作流编排",
    "business_workflow": "业务闭环执行",
    "listing_generation": "Listing生成",
    "listing_optimization": "Listing优化",
    "ad_optimization": "广告优化",
    "ad_budget": "广告预算",
    "ad_bidding": "广告出价",
    "review_analysis": "评论分析",
    "review_reply": "评论回复",
    "review_alert": "差评预警",
    "xhs_content": "小红书种草",
    "xhs_calendar": "小红书排期",
    "xhs_trend": "小红书趋势",
    "douyin_script": "抖音脚本",
    "douyin_trend": "抖音趋势",
    "video_channel_script": "视频号脚本",
    "video_channel_distribution": "视频号分发",
    "private_domain_drain": "私域导流",
    "cross_platform_drain": "跨平台导流",
    "presales": "售前咨询",
    "customer_intent_recognition": "客服意图识别",
    "order_query": "订单查询",
    "order_status": "订单状态查询",
    "logistics": "物流咨询",
    "tracking": "物流跟踪",
    "aftersale": "售后处理",
    "refund": "退款咨询",
    "exchange": "换货咨询",
    "complaint": "投诉建议",
    "sentiment_analysis": "情感分析",
    "emotion_handover": "情绪转人工",
    "material_generation": "素材生成",
    "image_generation": "图片素材生成",
    "report_generation": "报表生成",
    "data_report": "经营分析报表",
    "excel_visualization": "Excel可视化",
    "data_visualization": "数据可视化",
    "email_management": "邮件管理",
    "email_reply": "邮件回复",
    "email_classification": "邮件分类",
    "document_automation": "文档自动化",
    "meeting_minutes": "会议纪要",
    "opinion_monitor": "舆情监控",
    "crisis_alert": "危机预警",
    "knowledge_retrieval": "知识检索",
    "general_greeting": "一般问候",
    "unclear": "无法识别",
}

# 意图关键词映射：将用户消息中的关键词匹配到具体意图
INTENT_KEYWORDS = {
    "listing_generation": ["listing", "标题", "产品描述", "五点描述", "上架", "生成listing"],
    "listing_optimization": ["优化listing", "标题优化", "关键词优化", "转化率低"],
    "ad_optimization": ["广告", "ACOS", "点击率", "转化率", "广告优化", "投放"],
    "ad_budget": ["广告预算", "预算分配", "出价", "调价"],
    "review_analysis": ["评论", "评价", "差评", "好评", "评论分析"],
    "review_reply": ["回复评论", "差评回复", "评价回复"],
    "review_alert": ["差评预警", "评论预警", "负面评价"],
    "xhs_content": ["小红书", "种草", "笔记", "种草笔记"],
    "xhs_calendar": ["内容日历", "发布计划", "小红书计划"],
    "douyin_script": ["抖音", "短视频", "脚本", "视频脚本"],
    "video_channel_script": ["视频号", "视频号脚本", "视频号内容", "社交裂变", "转发给家人"],
    "video_channel_distribution": ["视频号分发", "视频号发布", "视频号传播"],
    "private_domain_drain": ["私域导流", "导流", "企业微信", "评论区引导", "私聊领取", "引导私聊", "私域"],
    "cross_platform_drain": ["跨平台导流", "跨平台分发", "跨平台引流"],
    "presales": ["价格", "多少钱", "规格", "参数", "功能", "怎么用", "发货时间", "有货吗", "库存", "优惠", "正品"],
    "order_query": ["订单", "查订单", "订单号", "订单状态"],
    "logistics": ["物流", "快递", "到哪了", "配送"],
    "tracking": ["追踪", "运单", "物流查询"],
    "aftersale": ["售后", "退货", "换货", "维修"],
    "refund": ["退款", "退钱", "退款进度"],
    "exchange": ["换货", "换颜色", "换型号"],
    "complaint": ["投诉", "举报", "不满"],
    "sentiment_analysis": ["情感分析", "情绪识别", "负面情绪", "转人工", "安抚"],
    "material_generation": ["素材", "图片", "主图", "详情页"],
    "report_generation": ["报表", "周报", "日报", "月报", "数据报告", "经营分析"],
    "excel_visualization": ["excel", "excel图表", "图表", "柱状图", "折线图", "饼图", "可视化"],
    "data_visualization": ["数据可视化", "图形化", "仪表盘", "看板"],
    "email_management": ["邮件", "邮箱", "回复邮件", "邮件分类", "邮件草稿", "报价邮件"],
    "document_automation": ["文档", "摘要", "结构化", "整理文档", "方案整理"],
    "meeting_minutes": ["会议纪要", "会议记录", "会议总结", "纪要"],
    "opinion_monitor": ["舆情", "监控", "品牌舆情"],
    "knowledge_retrieval": ["知识", "查询", "规则", "政策"],
}

WORKFLOW_CATALOG = {
    "ecommerce_operation_hub": {
        "display_name": "电商经营闭环",
        "agent": "ecommerce",
        "domain": "ecommerce",
    },
    "social_media_content_flywheel": {
        "display_name": "社媒内容增长闭环",
        "agent": "social-media",
        "domain": "social-media",
    },
    "customer_service_resolution": {
        "display_name": "客服服务闭环",
        "agent": "cs",
        "domain": "cs",
    },
    "office_productivity_suite": {
        "display_name": "办公自动化闭环",
        "agent": "office",
        "domain": "office",
    },
}


def _normalize_tools(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _get_context_value(context: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in context and context.get(key) is not None:
            return context.get(key)
    return default


def _extract_product_candidate(message: str) -> Optional[str]:
    import re

    patterns = [
        r"产品(?:是|为)?[:：]?\s*([^\s，。,；;]{2,30})",
        r"关于([^\s，。,；;]{2,30})",
        r"适合([^\s，。,；;]{2,30})的",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _load_agent_profiles() -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(AGENTS_ROOT):
        return profiles

    for entry in sorted(os.listdir(AGENTS_ROOT)):
        if not entry.endswith(".json"):
            continue

        file_path = os.path.join(AGENTS_ROOT, entry)
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                profile = json.load(handle)
        except Exception:
            continue

        agent_id = profile.get("id") or os.path.splitext(entry)[0]
        profiles[agent_id] = profile

    return profiles


AGENT_PROFILES = _load_agent_profiles()
SKILL_TO_AGENT_MAP: Dict[str, str] = {}
SKILL_AGENT_CANDIDATES: Dict[str, List[str]] = {}
AGENT_ROUTING_KEYWORDS: Dict[str, List[str]] = {}

for agent_id, profile in AGENT_PROFILES.items():
    routing_keywords = profile.get("routing_rules", {}).get("keywords", [])
    AGENT_ROUTING_KEYWORDS[agent_id] = [
        str(keyword) for keyword in routing_keywords if str(keyword).strip()
    ]

    for capability in profile.get("capabilities", {}).values():
        if capability.get("enabled") is False:
            continue
        for skill_name in _normalize_tools(capability.get("tools", [])):
            if skill_name not in SKILL_REGISTRY:
                continue
            SKILL_AGENT_CANDIDATES.setdefault(skill_name, [])
            if agent_id not in SKILL_AGENT_CANDIDATES[skill_name]:
                SKILL_AGENT_CANDIDATES[skill_name].append(agent_id)

for skill_name, agent_ids in SKILL_AGENT_CANDIDATES.items():
    if len(agent_ids) == 1:
        only_agent = agent_ids[0]
        SKILL_TO_AGENT_MAP[skill_name] = only_agent
        if only_agent != "main":
            SKILL_REGISTRY[skill_name]["domain"] = only_agent

INTENT_TO_SKILL_MAP: Dict[str, str] = {}
for skill_name, skill_info in SKILL_REGISTRY.items():
    for intent in skill_info["intents"]:
        INTENT_TO_SKILL_MAP[intent] = skill_name

AGENT_DOMAIN_MAP = {
    "main": "main",
    "shared": "main",
}
for agent_id in AGENT_PROFILES:
    AGENT_DOMAIN_MAP[agent_id] = agent_id


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        user_id TEXT,
        agent_id TEXT DEFAULT 'main',
        channel TEXT DEFAULT 'default',
        status TEXT DEFAULT 'active',
        turn_count INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        metadata TEXT DEFAULT '{}'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        content TEXT,
        intent TEXT,
        confidence REAL DEFAULT 0,
        sentiment TEXT,
        skill_used TEXT,
        processing_time_ms INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS pipeline_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        turn_id TEXT,
        module TEXT,
        input_summary TEXT,
        output_summary TEXT,
        duration_ms INTEGER DEFAULT 0,
        status TEXT DEFAULT 'success',
        error_message TEXT,
        created_at TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS skill_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        turn_id TEXT,
        skill_name TEXT,
        skill_input TEXT,
        skill_output TEXT,
        execution_mode TEXT DEFAULT 'sync',
        duration_ms INTEGER DEFAULT 0,
        status TEXT DEFAULT 'success',
        error_message TEXT,
        created_at TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS context_store (
        key TEXT PRIMARY KEY,
        value TEXT,
        expires_at TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class PerceptionModule:
    """感知模块：意图识别 + 情感分析 + 实体提取 + RAG检索"""
    def __init__(self):
        self.name = "perception"

    def process(self, message: str, context: Dict) -> Dict:
        start_time = datetime.now()
        try:
            intent_result = self._recognize_intent(message, context)
            sentiment_result = self._analyze_sentiment(message, context)
            entities = self._extract_entities(message)
            rag_result = self._retrieve_knowledge(message, intent_result, context)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "module": self.name,
                "status": "success",
                "duration_ms": duration_ms,
                "intent": intent_result,
                "sentiment": sentiment_result,
                "entities": entities,
                "rag_context": rag_result,
                "original_message": message,
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "module": self.name,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
                "intent": {"intent": "unclear", "confidence": 0.3},
                "sentiment": {"sentiment": "neutral", "sentiment_score": 0.0},
                "entities": {},
                "rag_context": {"hit": False},
            }

    def _recognize_intent(self, message: str, context: Dict) -> Dict:
        text = message.lower()
        intent_scores = {}
        platform_bonuses = {
            "xhs_content": [("小红书", 2)],
            "xhs_calendar": [("小红书", 2)],
            "douyin_script": [("抖音", 2)],
            "video_channel_script": [("视频号", 2)],
            "video_channel_distribution": [("视频号", 2)],
            "private_domain_drain": [("企业微信", 1), ("私域", 1)],
            "cross_platform_drain": [("跨平台", 1)],
            "email_management": [("邮件", 1)],
            "report_generation": [("周报", 2), ("月报", 2), ("日报", 2), ("报表", 1)],
            "excel_visualization": [("excel", 1), ("图表", 1)],
            "meeting_minutes": [("会议纪要", 2)],
        }

        for intent, keywords in INTENT_KEYWORDS.items():
            score = 0
            matched = []
            for kw in keywords:
                if kw.lower() in text:
                    score += 1
                    matched.append(kw)
            if score > 0:
                intent_scores[intent] = {"score": score, "keywords": matched}

        for intent, bonuses in platform_bonuses.items():
            if intent not in intent_scores:
                continue
            for keyword, bonus in bonuses:
                if keyword.lower() in text:
                    intent_scores[intent]["score"] += bonus
                    if keyword not in intent_scores[intent]["keywords"]:
                        intent_scores[intent]["keywords"].append(keyword)

        if not intent_scores:
            if any(w in text for w in ["你好", "在吗", "请问", "咨询"]):
                return {
                    "intent": "general_greeting",
                    "intent_label": "一般问候",
                    "confidence": 0.6,
                    "keywords": [],
                    "skill": None,
                }
            return {
                "intent": "unclear",
                "intent_label": "无法识别",
                "confidence": 0.3,
                "keywords": [],
                "skill": None,
            }

        best_intent = max(intent_scores, key=lambda x: intent_scores[x]["score"])
        max_score = intent_scores[best_intent]["score"]
        confidence = min(0.95, 0.5 + max_score * 0.12)

        skill_name = INTENT_TO_SKILL_MAP.get(best_intent)

        return {
            "intent": best_intent,
            "intent_label": INTENT_LABELS.get(best_intent, "未知"),
            "confidence": round(confidence, 2),
            "keywords": intent_scores[best_intent]["keywords"],
            "skill": skill_name,
        }

    def _analyze_sentiment(self, message: str, context: Dict) -> Dict:
        text = message.lower()
        score = 0.0
        emotion_keywords = []

        negative_words = {
            "非常不满": -0.8, "极其失望": -0.8, "垃圾": -0.7, "骗子": -0.8,
            "投诉": -0.7, "退款": -0.4, "差评": -0.6, "太差": -0.6,
            "不满": -0.5, "失望": -0.5, "着急": -0.4, "慢": -0.3,
            "麻烦": -0.3, "不好": -0.4, "有问题": -0.3,
        }
        positive_words = {
            "非常满意": 0.8, "太棒了": 0.8, "感谢": 0.6, "谢谢": 0.5,
            "很好": 0.5, "不错": 0.4, "喜欢": 0.4, "好的": 0.1,
        }

        for word, weight in negative_words.items():
            if word in text:
                score += weight
                emotion_keywords.append(word)

        for word, weight in positive_words.items():
            if word in text:
                score += weight
                emotion_keywords.append(word)

        score = max(-1.0, min(1.0, score))

        if score >= 0.3:
            sentiment = "positive"
            sentiment_label = "正面"
        elif score >= -0.2:
            sentiment = "neutral"
            sentiment_label = "中性"
        elif score >= -0.5:
            sentiment = "negative"
            sentiment_label = "负面"
        else:
            sentiment = "angry"
            sentiment_label = "愤怒"

        require_human = score < -0.6 or "投诉" in text

        return {
            "sentiment": sentiment,
            "sentiment_score": round(score, 2),
            "sentiment_label": sentiment_label,
            "emotion_keywords": emotion_keywords[:5],
            "require_human": require_human,
        }

    def _extract_entities(self, message: str) -> Dict:
        import re
        entities = {}

        order_match = re.search(r'(?:订单号?)[：:]\s*([A-Za-z0-9]{8,20})', message, re.IGNORECASE)
        if not order_match:
            order_match = re.search(r'([A-Z]{2,4}\d{8,15})', message, re.IGNORECASE)
        if order_match:
            entities["order_id"] = order_match.group(1).upper()

        tracking_match = re.search(r'(SF\d{10,15})', message)
        if not tracking_match:
            tracking_match = re.search(r'(YT\d{10,15})', message)
        if not tracking_match:
            tracking_match = re.search(r'(\d{12,18})', message)
        if tracking_match:
            entities["tracking_number"] = tracking_match.group(1)

        phone_match = re.search(r'(1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4})', message)
        if phone_match:
            phone = re.sub(r'[\s\-]', '', phone_match.group(1))
            entities["phone"] = phone[:3] + "****" + phone[-4:]

        product_keywords = [
            "智能手表", "蓝牙耳机", "无线充电器", "手机壳", "数据线",
            "移动电源", "音箱", "平板", "笔记本", "键盘", "鼠标",
        ]
        for product in product_keywords:
            if product in message:
                entities["product_name"] = product
                break
        if "product_name" not in entities:
            candidate = _extract_product_candidate(message)
            if candidate:
                entities["product_name"] = candidate

        platform_keywords = {
            "亚马逊": "amazon", "淘宝": "taobao", "京东": "jd",
            "拼多多": "pdd", "小红书": "xiaohongshu", "抖音": "douyin",
            "视频号": "video-channel", "企业微信": "wework", "飞书": "feishu",
        }
        for kw, platform in platform_keywords.items():
            if kw in message:
                entities["platform"] = platform
                break

        return entities

    def _retrieve_knowledge(self, message: str, intent_result: Dict, context: Dict) -> Dict:
        if context.get("skip_rag"):
            return {"hit": False, "confidence": 0.0, "sources": []}

        intent = intent_result.get("intent", "")
        if intent in ["unclear", "general_greeting"]:
            return {"hit": False, "confidence": 0.0, "sources": []}

        category_map = {
            "listing_generation": "listing-gen",
            "listing_optimization": "listing-gen",
            "ad_optimization": "ad-optimizer",
            "ad_budget": "ad-optimizer",
            "review_analysis": "review-mgr",
            "presales": "cs",
            "order_query": "cs",
            "logistics": "cs",
            "aftersale": "cs",
            "refund": "cs",
            "report_generation": "office",
            "document_automation": "office",
        }

        category = category_map.get(intent)
        try:
            skill_path = SKILL_REGISTRY.get("rag-retrieval", {}).get("path")
            if skill_path and os.path.exists(skill_path):
                rag_input = json.dumps({
                    "action": "retrieve",
                    "query": message,
                    "top_k": 3,
                    "category": category,
                }, ensure_ascii=False)
                result = subprocess.run(
                    [sys.executable, skill_path],
                    input=rag_input,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                )
                if result.returncode == 0:
                    rag_data = json.loads(result.stdout.strip())
                    if rag_data.get("success") and rag_data.get("count", 0) > 0:
                        return {
                            "hit": True,
                            "confidence": 0.7,
                            "results": rag_data.get("results", []),
                            "sources": [r.get("title", "") for r in rag_data.get("results", [])],
                        }
        except Exception:
            pass

        return {"hit": False, "confidence": 0.3, "sources": []}


class DecisionModule:
    """决策模块：置信度评估 + 技能编排 + Agent路由"""
    def __init__(self):
        self.name = "decision"

    def process(self, perception_result: Dict, context: Dict) -> Dict:
        start_time = datetime.now()
        try:
            intent = perception_result.get("intent", {})
            sentiment = perception_result.get("sentiment", {})
            rag_context = perception_result.get("rag_context", {})

            decision = self._evaluate_confidence(intent, sentiment, rag_context, context)
            skill_plan = self._plan_skill_execution(intent, decision, perception_result, context)
            agent_routing = self._route_to_agent(intent, skill_plan, perception_result, context)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "module": self.name,
                "status": "success",
                "duration_ms": duration_ms,
                "decision": decision,
                "skill_plan": skill_plan,
                "agent_routing": agent_routing,
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "module": self.name,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
                "decision": {"action": "human", "confidence": 0.0},
                "skill_plan": {"skills": [], "mode": "none"},
                "agent_routing": {"agent_id": "main"},
            }

    def _evaluate_confidence(self, intent: Dict, sentiment: Dict, rag: Dict, context: Dict) -> Dict:
        intent_confidence = intent.get("confidence", 0.5)
        sentiment_score = sentiment.get("sentiment_score", 0.0)
        sentiment_require_human = sentiment.get("require_human", False)
        rag_confidence = rag.get("confidence", 0.3) if rag.get("hit") else 0.3

        sentiment_confidence = 1.0 - abs(sentiment_score)
        if sentiment.get("sentiment") in ["angry", "negative"]:
            sentiment_confidence *= 0.6

        context_score = 0.5
        if context.get("customer_tier") == "VIP":
            context_score += 0.2
        if context.get("order_value", 0) > 5000:
            context_score += 0.15
        context_confidence = max(0.0, min(1.0, context_score))

        overall = (
            intent_confidence * 0.40
            + sentiment_confidence * 0.25
            + rag_confidence * 0.25
            + context_confidence * 0.10
        )
        overall = max(0.0, min(1.0, overall))

        if overall >= 0.85:
            action = "auto"
            risk_level = "low"
        elif overall >= 0.6:
            action = "confirm"
            risk_level = "medium"
        elif overall >= 0.4:
            action = "confirm_with_human"
            risk_level = "high"
        else:
            action = "human"
            risk_level = "critical"

        if sentiment_require_human:
            action = "human"
            risk_level = "critical"

        if context.get("customer_tier") == "VIP" and overall < 0.7:
            action = "confirm_with_human"
            risk_level = "high"

        return {
            "action": action,
            "confidence": round(overall, 2),
            "risk_level": risk_level,
            "confidence_breakdown": {
                "intent": round(intent_confidence, 2),
                "sentiment": round(sentiment_confidence, 2),
                "rag": round(rag_confidence, 2),
                "context": round(context_confidence, 2),
            },
        }

    def _plan_skill_execution(self, intent: Dict, decision: Dict, perception: Dict, context: Dict) -> Dict:
        skill_name = intent.get("skill")
        action = decision.get("action", "human")

        if action == "human" or not skill_name:
            return {
                "skills": [],
                "mode": "none",
                "reason": "转人工处理" if action == "human" else "无匹配技能",
            }

        workflow_plan = self._match_workflow_plan(perception, context)
        if workflow_plan:
            return workflow_plan

        skill_info = SKILL_REGISTRY.get(skill_name)
        if not skill_info:
            return {
                "skills": [],
                "mode": "none",
                "reason": f"技能 {skill_name} 未注册",
            }

        skills = [{"name": skill_name, "domain": skill_info["domain"], "primary": True}]

        intent_type = intent.get("intent", "")
        sentiment = perception.get("sentiment", {}).get("sentiment", "")
        if intent_type == "order_query":
            entities = perception.get("entities", {})
            if entities.get("tracking_number"):
                skills.append({"name": "logistics-track", "domain": "cs", "primary": False})
        elif intent_type == "aftersale":
            skills.append({"name": "order-query", "domain": "cs", "primary": False})
        elif intent_type == "complaint":
            skills.append({"name": "review-mgr", "domain": "ecommerce", "primary": False})
        elif intent_type == "report_generation" and "excel-viz" in SKILL_REGISTRY:
            skills.append({"name": "excel-viz", "domain": "office", "primary": False})

        if (
            intent_type in ["complaint", "refund", "exchange", "aftersale", "logistics", "tracking", "order_query"]
            or sentiment in ["negative", "angry", "anxious", "disappointed"]
        ) and "sentiment-analysis" in SKILL_REGISTRY:
            if all(skill["name"] != "sentiment-analysis" for skill in skills):
                skills.append({"name": "sentiment-analysis", "domain": "cs", "primary": False})

        mode = "sequential"
        if len(skills) > 1:
            has_primary_dependency = any(not s["primary"] for s in skills)
            mode = "sequential" if has_primary_dependency else "parallel"

        return {
            "skills": skills,
            "mode": mode,
            "reason": f"匹配到 {len(skills)} 个技能，执行模式: {mode}",
        }

    def _match_workflow_plan(self, perception: Dict, context: Dict) -> Optional[Dict]:
        message = perception.get("original_message", "")
        entities = perception.get("entities", {})
        text = message.lower()

        def contains_any(words: List[str]) -> bool:
            return any(word.lower() in text for word in words)

        def count_groups(groups: List[List[str]]) -> int:
            return sum(1 for group in groups if contains_any(group))

        has_product = bool(
            entities.get("product_name")
            or _get_context_value(context, "product_name", "product", "topic")
            or _extract_product_candidate(message)
        )
        has_order = bool(entities.get("order_id") or _get_context_value(context, "order_id", "orderNo"))
        has_tracking = bool(entities.get("tracking_number") or _get_context_value(context, "tracking_number", "trackingNo"))

        office_groups = [
            ["周报", "日报", "月报", "报表", "经营分析"],
            ["图表", "可视化", "excel", "看板"],
            ["邮件", "报价邮件", "邮件草稿"],
            ["文档", "摘要", "会议纪要", "纪要"],
        ]
        if count_groups(office_groups) >= 2:
            return self._build_workflow_plan("office_productivity_suite")

        social_groups = [
            ["小红书"],
            ["抖音"],
            ["视频号"],
            ["导流", "私域", "企业微信"],
            ["舆情", "监控"],
        ]
        if count_groups(social_groups) >= 2 and has_product:
            return self._build_workflow_plan("social_media_content_flywheel")

        cs_groups = [
            ["订单", "订单号"],
            ["物流", "快递", "运单", "单号", "到哪了"],
            ["售后", "退款", "换货", "投诉"],
        ]
        if count_groups(cs_groups) >= 2 and (has_order or has_tracking):
            return self._build_workflow_plan("customer_service_resolution")

        ecommerce_groups = [
            ["listing", "上架"],
            ["素材", "主图", "详情页"],
            ["广告", "投放", "acos"],
            ["报表", "图表", "经营"],
        ]
        if count_groups(ecommerce_groups) >= 2 and has_product:
            return self._build_workflow_plan("ecommerce_operation_hub")

        return None

    def _build_workflow_plan(self, workflow_name: str) -> Dict:
        workflow = WORKFLOW_CATALOG[workflow_name]
        return {
            "skills": [
                {
                    "name": "skill-orchestrator",
                    "domain": workflow["domain"],
                    "primary": True,
                    "workflow_name": workflow_name,
                    "workflow_agent": workflow["agent"],
                }
            ],
            "mode": "workflow",
            "workflow": {
                "name": workflow_name,
                "display_name": workflow["display_name"],
                "agent": workflow["agent"],
                "domain": workflow["domain"],
            },
            "reason": f"识别为{workflow['display_name']}，交由 skill-orchestrator 执行业务闭环",
        }

    def _route_to_agent(self, intent: Dict, skill_plan: Dict, perception: Dict, context: Dict) -> Dict:
        workflow = skill_plan.get("workflow", {})
        if workflow.get("agent"):
            agent_id = workflow["agent"]
            return {
                "agent_id": agent_id,
                "reason": f"工作流 {workflow.get('display_name', workflow.get('name', ''))} 路由到 {agent_id} Agent",
            }

        skill_name = intent.get("skill")
        if skill_name:
            skill_info = SKILL_REGISTRY.get(skill_name, {})
            candidate_agents = SKILL_AGENT_CANDIDATES.get(skill_name, [])
            if skill_name in SKILL_TO_AGENT_MAP:
                agent_id = SKILL_TO_AGENT_MAP[skill_name]
            elif candidate_agents:
                message = perception.get("original_message", "")
                current_agent = context.get("current_agent")
                if current_agent in candidate_agents:
                    agent_id = current_agent
                else:
                    scored_candidates = []
                    for candidate_agent in candidate_agents:
                        keywords = AGENT_ROUTING_KEYWORDS.get(candidate_agent, [])
                        score = sum(1 for keyword in keywords if keyword and keyword in message)
                        scored_candidates.append((candidate_agent, score))

                    scored_candidates.sort(key=lambda item: item[1], reverse=True)
                    if scored_candidates and scored_candidates[0][1] > 0:
                        agent_id = scored_candidates[0][0]
                    else:
                        agent_id = AGENT_DOMAIN_MAP.get(skill_info.get("domain", "main"), "main")
            else:
                domain = skill_info.get("domain", "main")
                agent_id = AGENT_DOMAIN_MAP.get(domain, "main")
        else:
            message = perception.get("original_message", "")
            agent_id = context.get("current_agent", "main")
            for candidate_agent, keywords in AGENT_ROUTING_KEYWORDS.items():
                if any(keyword and keyword in message for keyword in keywords):
                    agent_id = candidate_agent
                    break

        return {
            "agent_id": agent_id,
            "reason": f"意图 {intent.get('intent', 'unknown')} 路由到 {agent_id} Agent",
        }


class ExecutionModule:
    """执行模块：按模式（串行/并行/工作流）调用技能并返回结果"""
    def __init__(self):
        self.name = "execution"

    def _skill_timeout(self, skill_name: str, skill_input: Dict) -> int:
        if skill_name == "skill-orchestrator":
            return 180

        timeout_map = {
            "listing-gen": 90,
            "xhs-seed": 60,
            "video-channel": 60,
            "doc-auto": 60,
            "report-gen": 45,
            "ad-optimizer": 45,
        }
        return timeout_map.get(skill_name, 30)

    def process(self, decision_result: Dict, perception_result: Dict, context: Dict) -> Dict:
        start_time = datetime.now()
        try:
            skill_plan = decision_result.get("skill_plan", {})
            decision = decision_result.get("decision", {})
            action = decision.get("action", "human")

            if action == "human":
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                return {
                    "module": self.name,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "action": "human_handover",
                    "results": [],
                    "message": "已转交人工客服处理",
                    "requires_human": True,
                }

            skills = skill_plan.get("skills", [])
            mode = skill_plan.get("mode", "none")

            if not skills:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                return {
                    "module": self.name,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "action": "no_skill",
                    "results": [],
                    "message": "无匹配技能，将使用通用回复",
                    "requires_human": False,
                }

            if mode == "parallel":
                results = self._execute_parallel(skills, perception_result, context)
            else:
                results = self._execute_sequential(skills, perception_result, context)

            primary_result = next((r for r in results if r.get("primary")), results[0] if results else {})

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "module": self.name,
                "status": "success",
                "duration_ms": duration_ms,
                "action": "skill_executed",
                "results": results,
                "primary_result": primary_result,
                "execution_mode": mode,
                "requires_human": action in ["confirm", "confirm_with_human"],
                "message": f"已执行 {len(results)} 个技能",
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "module": self.name,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
                "results": [],
                "requires_human": True,
            }

    def _execute_skill(self, skill_name: str, skill_input: Dict, is_primary: bool = True) -> Dict:
        skill_info = SKILL_REGISTRY.get(skill_name)
        if not skill_info:
            return {"skill": skill_name, "status": "error", "error": "技能未注册", "primary": is_primary}

        skill_path = skill_info.get("path")
        if not skill_path or not os.path.exists(skill_path):
            return {"skill": skill_name, "status": "error", "error": "技能文件不存在", "primary": is_primary}

        start_time = datetime.now()
        timeout = self._skill_timeout(skill_name, skill_input)
        try:
            input_json = json.dumps(skill_input, ensure_ascii=False)
            result = subprocess.run(
                [sys.executable, skill_path],
                input=input_json,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if result.returncode == 0:
                output = json.loads(result.stdout.strip()) if result.stdout.strip() else {}
                return {
                    "skill": skill_name,
                    "status": "success",
                    "output": output,
                    "duration_ms": duration_ms,
                    "primary": is_primary,
                }
            else:
                return {
                    "skill": skill_name,
                    "status": "error",
                    "error": result.stderr[:500] if result.stderr else "执行失败",
                    "duration_ms": duration_ms,
                    "primary": is_primary,
                }
        except subprocess.TimeoutExpired:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "skill": skill_name,
                "status": "error",
                "error": f"执行超时({timeout}s)",
                "duration_ms": duration_ms,
                "primary": is_primary,
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "skill": skill_name,
                "status": "error",
                "error": str(e),
                "duration_ms": duration_ms,
                "primary": is_primary,
            }

    def _get_context_value(self, context: Dict, *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in context and context.get(key) is not None:
                return context.get(key)
        return default

    def _coerce_numeric(self, value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace("¥", "").replace(",", "").replace("%", "").strip()
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _build_chart_dataset(self, context: Dict, prior_results: List[Dict]) -> List[Dict[str, Any]]:
        context_data = self._get_context_value(context, "data", "chart_data", default=[])
        if isinstance(context_data, list) and context_data:
            return context_data

        for result in prior_results or []:
            if result.get("skill") != "report-gen":
                continue

            report_output = result.get("output", {})
            for section in report_output.get("sections", []):
                dataset = []
                for item in section.get("data", []):
                    if not isinstance(item, dict):
                        continue

                    label = (
                        item.get("label")
                        or item.get("name")
                        or item.get("category")
                        or item.get("platform")
                        or item.get("day")
                        or item.get("week")
                    )
                    value = item.get("value")
                    if value is None:
                        value = item.get("sales", item.get("orders"))

                    numeric_value = self._coerce_numeric(value)
                    if label is None or numeric_value is None:
                        continue

                    dataset.append({"name": str(label), "value": numeric_value})

                if dataset:
                    return dataset

        return [
            {"name": "订单数", "value": 128},
            {"name": "营收", "value": 96},
            {"name": "访客", "value": 248},
        ]

    def _infer_platforms(self, message: str, context: Dict) -> List[str]:
        candidates = []
        known_pairs = [
            ("xiaohongshu", ["小红书", "xhs"]),
            ("douyin", ["抖音"]),
            ("video-channel", ["视频号"]),
            ("kuaishou", ["快手"]),
        ]

        for platform in self._get_context_value(context, "platforms", default=[]) or []:
            if isinstance(platform, str) and platform.strip():
                candidates.append(platform.strip())

        source_platform = self._get_context_value(context, "source_platform", "sourcePlatform")
        target_platform = self._get_context_value(context, "target_platform", "targetPlatform")
        for platform in [source_platform, target_platform]:
            if isinstance(platform, str) and platform.strip():
                candidates.append(platform.strip())

        for normalized, aliases in known_pairs:
            if any(alias in message for alias in aliases):
                candidates.append(normalized)

        unique_candidates = []
        for platform in candidates:
            if platform not in unique_candidates:
                unique_candidates.append(platform)

        return unique_candidates

    def _infer_report_type(self, message: str, context: Dict) -> str:
        report_type = self._get_context_value(context, "report_type", "reportType")
        if isinstance(report_type, str) and report_type.strip():
            return report_type.strip()
        if "月报" in message:
            return "monthly"
        if "周报" in message:
            return "weekly"
        return "daily"

    def _build_workflow_params(self, workflow_name: str, perception: Dict, context: Dict) -> Dict:
        entities = perception.get("entities", {})
        message = perception.get("original_message", "")
        product_name = (
            _get_context_value(context, "product_name", "product", "topic")
            or entities.get("product_name")
            or _extract_product_candidate(message)
        )
        platform = _get_context_value(context, "platform") or entities.get("platform")

        base = {
            "message": message,
            "user_message": message,
            "history": _get_context_value(context, "history", default=[]),
            "platform": platform,
            "product_name": product_name,
            "topic": _get_context_value(context, "topic", "subject") or product_name or message,
            "selling_points": _get_context_value(context, "selling_points", default=[]),
            "target_audience": _get_context_value(context, "target_audience", "audience"),
            "audience": _get_context_value(context, "audience", "target_audience"),
            "duration": _get_context_value(context, "duration", "durationSeconds"),
            "sourcePlatform": _get_context_value(context, "sourcePlatform", "source_platform"),
            "targetPlatform": _get_context_value(context, "targetPlatform", "target_platform"),
            "platforms": _get_context_value(context, "platforms", default=[]),
            "order_id": _get_context_value(context, "order_id", "orderNo") or entities.get("order_id"),
            "tracking_number": _get_context_value(context, "tracking_number", "trackingNo") or entities.get("tracking_number"),
            "report_type": self._infer_report_type(message, context),
            "date": _get_context_value(context, "date", default=datetime.now().strftime("%Y-%m-%d")),
            "subject": _get_context_value(context, "subject", default="AIMS 自动业务摘要"),
            "body": _get_context_value(context, "body", default=message),
            "content": _get_context_value(context, "content", default=message),
            "document_type": _get_context_value(context, "document_type", "documentType", default="summary"),
            "metrics": _get_context_value(context, "metrics", default={}),
            "campaign_type": _get_context_value(context, "campaign_type", "campaignType", default="sp"),
            "category": _get_context_value(context, "category", default="electronics"),
            "material_type": _get_context_value(context, "material_type", "materialType", default="main_image"),
        }

        if workflow_name == "customer_service_resolution":
            base["platform"] = base["platform"] or "jd"
        elif workflow_name == "office_productivity_suite":
            base["platform"] = base["platform"] or "all"
        elif workflow_name == "ecommerce_operation_hub":
            base["platform"] = base["platform"] or "amazon"

        return {key: value for key, value in base.items() if value is not None}

    def _build_skill_input(self, skill_def: Any, perception: Dict, context: Dict, prior_results: List[Dict] = None) -> Dict:
        if isinstance(skill_def, dict):
            skill_name = skill_def.get("name", "")
            workflow_name = skill_def.get("workflow_name", "")
        else:
            skill_name = str(skill_def)
            workflow_name = ""

        intent = perception.get("intent", {})
        entities = perception.get("entities", {})
        message = perception.get("original_message", "")
        sentiment = perception.get("sentiment", {})
        history = self._get_context_value(context, "history", default=[])

        base_input = {
            "action": self._infer_skill_action(skill_name, intent.get("intent", "")),
            "message": message,
            "intent": intent.get("intent", ""),
            "entities": entities,
            "context": context,
            "sentiment": sentiment,
        }

        if skill_name == "skill-orchestrator":
            return {
                "action": "execute_workflow",
                "workflow_name": workflow_name,
                "params": self._build_workflow_params(workflow_name, perception, context),
                "context": context,
            }

        if skill_name == "order-query":
            if entities.get("order_id"):
                base_input["action"] = "query"
                base_input["order_id"] = entities["order_id"]
            elif entities.get("phone"):
                base_input["action"] = "query_by_phone"
                base_input["phone"] = entities["phone"]
            else:
                base_input["action"] = "statistics"
        elif skill_name == "logistics-track":
            if entities.get("tracking_number"):
                base_input["action"] = "track"
                base_input["tracking_number"] = entities["tracking_number"]
            else:
                base_input["action"] = "track"
        elif skill_name == "after-sale":
            if intent.get("intent") == "refund":
                base_input["action"] = "create"
                base_input["aftersale_type"] = "refund_only"
            elif intent.get("intent") == "exchange":
                base_input["action"] = "create"
                base_input["aftersale_type"] = "exchange"
            else:
                base_input["action"] = "query"
        elif skill_name == "review-mgr":
            if intent.get("intent") == "review_reply":
                base_input["action"] = "generate_reply"
            elif intent.get("intent") == "review_alert":
                base_input["action"] = "detect_alerts"
            else:
                base_input["action"] = "analyze"
        elif skill_name == "listing-gen":
            base_input["action"] = "generate"
            if entities.get("product_name"):
                base_input["product_name"] = entities["product_name"]
            if entities.get("platform"):
                base_input["platform"] = entities["platform"]
        elif skill_name == "ad-optimizer":
            base_input["action"] = "optimize"
        elif skill_name == "xhs-seed":
            base_input["action"] = "generate"
        elif skill_name == "video-channel":
            base_input["action"] = "generate"
            base_input["product"] = self._get_context_value(context, "product", "product_name") or entities.get("product_name")
            base_input["topic"] = self._get_context_value(context, "topic", "subject") or base_input.get("product") or message
            base_input["audience"] = self._get_context_value(context, "audience", "target_audience", default="general")
            base_input["duration"] = int(self._get_context_value(context, "duration", "durationSeconds", default=60))
            base_input["style"] = self._get_context_value(context, "style", default="friendly")
        elif skill_name == "cross-drain":
            platforms = self._infer_platforms(message, context)
            if len(platforms) >= 2:
                base_input["action"] = "cross_platform_strategy"
                base_input["platforms"] = platforms[:2]
            else:
                base_input["action"] = "generate_strategy"
                base_input["platform"] = platforms[0] if platforms else "xiaohongshu"
            base_input["content_type"] = self._get_context_value(context, "content_type", "contentType", default="product")
        elif skill_name == "report-gen":
            base_input["action"] = "generate"
            base_input["report_type"] = self._infer_report_type(message, context)
            base_input["date"] = self._get_context_value(context, "date", default=datetime.now().strftime("%Y-%m-%d"))
            base_input["platform"] = self._get_context_value(context, "platform", default=entities.get("platform", "all"))
        elif skill_name == "excel-viz":
            base_input["action"] = "generate"
            base_input["data"] = self._build_chart_dataset(context, prior_results or [])
            base_input["chart_type"] = self._get_context_value(context, "chart_type", "chartType", default="bar")
            base_input["title"] = self._get_context_value(context, "title", default="AIMS 业务数据可视化")
            base_input["operation"] = self._get_context_value(context, "operation", default="sum")
        elif skill_name == "email-mgr":
            base_input["action"] = "classify"
            base_input["subject"] = self._get_context_value(context, "subject", default="AIMS 自动生成邮件草稿")
            base_input["body"] = self._get_context_value(context, "body", default=message)
            base_input["sender"] = self._get_context_value(context, "sender", "senderRole", default=context.get("user_id", "unknown"))
            base_input["attachments"] = self._get_context_value(context, "attachments", default=[])
        elif skill_name == "doc-auto":
            base_input["action"] = "automate"
            base_input["content"] = self._get_context_value(context, "content", default=message)
            base_input["document_type"] = self._get_context_value(context, "document_type", "documentType", default="summary")
            base_input["metadata"] = self._get_context_value(context, "metadata", default={})
        elif skill_name == "intent-recognition":
            base_input["action"] = "recognize"
            base_input["user_message"] = message
            base_input["history"] = history
        elif skill_name == "sentiment-analysis":
            base_input["action"] = "analyze"
            base_input["user_message"] = message
            base_input["history"] = history
            base_input["context"] = context
        elif skill_name == "rag-retrieval":
            base_input["action"] = "retrieve"
            base_input["query"] = message

        if prior_results:
            base_input["prior_results"] = [
                {"skill": r.get("skill"), "output": r.get("output", {})}
                for r in prior_results
                if r.get("status") == "success"
            ]

        return base_input

    def _infer_skill_action(self, skill_name: str, intent: str) -> str:
        action_map = {
            "listing-gen": "generate",
            "ad-optimizer": "optimize",
            "review-mgr": "analyze",
            "xhs-seed": "generate",
            "douyin-ops": "generate",
            "video-channel": "generate",
            "cross-drain": "generate_strategy",
            "intent-recognition": "recognize",
            "order-query": "query",
            "logistics-track": "track",
            "after-sale": "query",
            "sentiment-analysis": "analyze",
            "material-gen": "generate",
            "report-gen": "generate",
            "excel-viz": "generate",
            "email-mgr": "classify",
            "doc-auto": "automate",
            "opinion-watch": "monitor",
            "rag-retrieval": "retrieve",
        }
        return action_map.get(skill_name, "process")

    def _execute_sequential(self, skills: List[Dict], perception: Dict, context: Dict) -> List[Dict]:
        results = []
        for skill_def in skills:
            skill_name = skill_def["name"]
            is_primary = skill_def.get("primary", False)
            skill_input = self._build_skill_input(skill_def, perception, context, results)
            result = self._execute_skill(skill_name, skill_input, is_primary)
            results.append(result)
        return results

    def _execute_parallel(self, skills: List[Dict], perception: Dict, context: Dict) -> List[Dict]:
        results = []
        for skill_def in skills:
            skill_name = skill_def["name"]
            is_primary = skill_def.get("primary", False)
            skill_input = self._build_skill_input(skill_def, perception, context)
            result = self._execute_skill(skill_name, skill_input, is_primary)
            results.append(result)
        return results


class MemoryModule:
    """记忆模块：会话持久化 + 上下文更新 + 洞察提取"""
    def __init__(self):
        self.name = "memory"

    def process(self, execution_result: Dict, perception_result: Dict, decision_result: Dict, context: Dict) -> Dict:
        start_time = datetime.now()
        try:
            conversation_id = context.get("conversation_id", "")
            if conversation_id:
                self._save_conversation_turn(
                    conversation_id, perception_result, decision_result, execution_result, context
                )

            updated_context = self._update_context(context, perception_result, execution_result)

            insights = self._extract_insights(perception_result, execution_result)

            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "module": self.name,
                "status": "success",
                "duration_ms": duration_ms,
                "context_updated": True,
                "insights": insights,
                "conversation_id": conversation_id,
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return {
                "module": self.name,
                "status": "error",
                "duration_ms": duration_ms,
                "error": str(e),
                "context_updated": False,
            }

    def _save_conversation_turn(self, conversation_id: str, perception: Dict, decision: Dict, execution: Dict, context: Dict):
        try:
            conn = get_db_connection()
            c = conn.cursor()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute("SELECT turn_count FROM conversations WHERE conversation_id = ?", (conversation_id,))
            row = c.fetchone()
            if row:
                c.execute(
                    "UPDATE conversations SET turn_count = turn_count + 1, updated_at = ? WHERE conversation_id = ?",
                    (now, conversation_id),
                )
            else:
                c.execute(
                    "INSERT INTO conversations (conversation_id, user_id, agent_id, channel, status, turn_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (conversation_id, context.get("user_id", ""), context.get("agent_id", "main"), context.get("channel", "default"), "active", 1, now, now),
                )

            turn_id = f"{conversation_id}-{row[0] + 1 if row else 1}"

            c.execute(
                "INSERT INTO messages (conversation_id, role, content, intent, confidence, sentiment, skill_used, processing_time_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    "user",
                    perception.get("original_message", ""),
                    perception.get("intent", {}).get("intent", ""),
                    decision.get("decision", {}).get("confidence", 0),
                    perception.get("sentiment", {}).get("sentiment", ""),
                    ",".join([s["name"] for s in decision.get("skill_plan", {}).get("skills", [])]),
                    execution.get("duration_ms", 0),
                    now,
                ),
            )

            for module_name, module_result in [("perception", perception), ("decision", decision), ("execution", execution)]:
                c.execute(
                    "INSERT INTO pipeline_logs (conversation_id, turn_id, module, input_summary, output_summary, duration_ms, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        conversation_id,
                        turn_id,
                        module_name,
                        json.dumps({"message": perception.get("original_message", "")}, ensure_ascii=False)[:500],
                        json.dumps(module_result, ensure_ascii=False, default=str)[:500],
                        module_result.get("duration_ms", 0),
                        module_result.get("status", "success"),
                        now,
                    ),
                )

            for skill_result in execution.get("results", []):
                c.execute(
                    "INSERT INTO skill_executions (conversation_id, turn_id, skill_name, skill_input, skill_output, execution_mode, duration_ms, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        conversation_id,
                        turn_id,
                        skill_result.get("skill", ""),
                        "",
                        json.dumps(skill_result.get("output", {}), ensure_ascii=False, default=str)[:1000],
                        execution.get("execution_mode", "sync"),
                        skill_result.get("duration_ms", 0),
                        skill_result.get("status", "success"),
                        now,
                    ),
                )

            conn.commit()
            conn.close()
        except Exception:
            pass

    def _update_context(self, context: Dict, perception: Dict, execution: Dict) -> Dict:
        entities = perception.get("entities", {})
        if entities:
            if "entities" not in context:
                context["entities"] = {}
            context["entities"].update(entities)

        intent = perception.get("intent", {})
        if intent.get("intent"):
            context["last_intent"] = intent["intent"]
            context["last_intent_confidence"] = intent.get("confidence", 0)

        sentiment = perception.get("sentiment", {})
        if sentiment.get("sentiment"):
            context["last_sentiment"] = sentiment["sentiment"]

        results = execution.get("results", [])
        if results:
            context["last_skills_used"] = [r.get("skill") for r in results if r.get("status") == "success"]

        context["last_interaction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return context

    def _extract_insights(self, perception: Dict, execution: Dict) -> Dict:
        insights = {
            "intent_identified": perception.get("intent", {}).get("intent") != "unclear",
            "skill_executed": len(execution.get("results", [])) > 0,
            "skill_success": all(r.get("status") == "success" for r in execution.get("results", [])),
            "requires_human": execution.get("requires_human", False),
        }

        primary_result = execution.get("primary_result", {})
        if primary_result.get("status") == "success" and primary_result.get("output"):
            output = primary_result["output"]
            if isinstance(output, dict):
                if "confidence" in output:
                    insights["result_confidence"] = output["confidence"]
                if "compliance_score" in output:
                    insights["compliance_score"] = output["compliance_score"]

        return insights

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "SELECT role, content, intent, confidence, sentiment, skill_used, created_at FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            )
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in reversed(rows)]
        except Exception:
            return []

    def get_context(self, key: str) -> Optional[str]:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT value, expires_at FROM context_store WHERE key = ?", (key,))
            row = c.fetchone()
            conn.close()
            if row:
                if row["expires_at"]:
                    expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
                    if expires < datetime.now():
                        return None
                return row["value"]
            return None
        except Exception:
            return None

    def set_context(self, key: str, value: str, ttl_seconds: int = 3600):
        try:
            conn = get_db_connection()
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            expires = (datetime.now() + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%d %H:%M:%S")
            c.execute(
                "INSERT OR REPLACE INTO context_store (key, value, expires_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (key, value, expires, now, now),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


class AgentOrchestrator:
    """Agent编排器：感知→决策→执行→记忆四阶段流水线，协调多技能协作"""
    def __init__(self):
        self.perception = PerceptionModule()
        self.decision = DecisionModule()
        self.execution = ExecutionModule()
        self.memory = MemoryModule()
        init_db()

    def process(self, message: str, context: Dict = None) -> Dict:
        if context is None:
            context = {}

        pipeline_start = datetime.now()
        conversation_id = context.get("conversation_id", self._generate_conversation_id(context))
        context["conversation_id"] = conversation_id

        perception_result = self.perception.process(message, context)

        decision_result = self.decision.process(perception_result, context)

        execution_result = self.execution.process(decision_result, perception_result, context)

        memory_result = self.memory.process(execution_result, perception_result, decision_result, context)

        total_duration = int((datetime.now() - pipeline_start).total_seconds() * 1000)

        response = self._compose_response(
            perception_result, decision_result, execution_result, memory_result, context
        )

        pipeline_result = {
            "conversation_id": conversation_id,
            "pipeline": {
                "total_duration_ms": total_duration,
                "modules": {
                    "perception": {
                        "status": perception_result.get("status"),
                        "duration_ms": perception_result.get("duration_ms", 0),
                    },
                    "decision": {
                        "status": decision_result.get("status"),
                        "duration_ms": decision_result.get("duration_ms", 0),
                    },
                    "execution": {
                        "status": execution_result.get("status"),
                        "duration_ms": execution_result.get("duration_ms", 0),
                    },
                    "memory": {
                        "status": memory_result.get("status"),
                        "duration_ms": memory_result.get("duration_ms", 0),
                    },
                },
            },
            "perception": perception_result,
            "decision": decision_result,
            "execution": execution_result,
            "memory": memory_result,
            "response": response,
            "context": context,
        }

        return pipeline_result

    def _generate_conversation_id(self, context: Dict) -> str:
        user_id = context.get("user_id", "anonymous")
        channel = context.get("channel", "default")
        now = datetime.now()
        raw = f"{user_id}-{channel}-{now.strftime('%Y%m%d')}"
        hash_val = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"conv-{now.strftime('%Y%m%d')}-{hash_val}"

    def _compose_response(self, perception: Dict, decision: Dict, execution: Dict, memory: Dict, context: Dict) -> Dict:
        intent = perception.get("intent", {})
        sentiment = perception.get("sentiment", {})
        decision_info = decision.get("decision", {})
        action = decision_info.get("action", "human")

        if action == "human":
            return {
                "type": "human_handover",
                "message": self._generate_human_handover_message(perception, decision_info),
                "reason": decision_info.get("risk_level", "unknown"),
                "confidence": decision_info.get("confidence", 0),
                "requires_human": True,
            }

        primary_result = execution.get("primary_result", {})
        if primary_result.get("status") == "success":
            output = primary_result.get("output", {})
            return {
                "type": "skill_result",
                "message": self._format_skill_output(primary_result.get("skill", ""), output, intent),
                "skill": primary_result.get("skill"),
                "confidence": decision_info.get("confidence", 0),
                "requires_confirmation": action in ["confirm", "confirm_with_human"],
                "data": output,
            }

        if execution.get("action") == "no_skill":
            return {
                "type": "general_response",
                "message": self._generate_general_response(perception),
                "confidence": decision_info.get("confidence", 0),
            }

        return {
            "type": "error",
            "message": "处理过程中出现错误，请稍后重试或联系人工客服",
            "confidence": 0,
            "requires_human": True,
        }

    def _generate_human_handover_message(self, perception: Dict, decision: Dict) -> str:
        intent_label = perception.get("intent", {}).get("intent_label", "")
        sentiment_label = perception.get("sentiment", {}).get("sentiment_label", "")
        risk_level = decision.get("risk_level", "")

        if risk_level == "critical":
            return f"检测到您的{sentiment_label}情绪，为了更好地为您服务，已为您转接人工客服，请稍候。"
        elif risk_level == "high":
            return f"关于{intent_label}的问题，为了确保准确处理，已为您转接专业客服。"
        else:
            return f"您的问题需要人工确认，已为您转接客服，请稍候。"

    def _format_skill_output(self, skill_name: str, output: Dict, intent: Dict) -> str:
        if not output:
            return "技能执行完成，但未返回结果。"

        if skill_name == "order-query":
            if "order" in output:
                order = output["order"]
                return f"订单查询结果：订单号 {order.get('order_id', '')}，状态 {order.get('status_label', order.get('status', ''))}，金额 {order.get('total_amount', 0)} 元"
            elif "statistics" in output:
                stats = output["statistics"]
                return f"订单统计：总订单 {stats.get('total_orders', 0)} 笔，总金额 {stats.get('total_amount', 0)} 元"
            return "订单查询完成。"

        if skill_name == "logistics-track":
            if "progress" in output:
                return f"物流追踪：当前进度 {output.get('progress', 0)}%，状态 {output.get('current_status', '查询中')}"
            return "物流查询完成。"

        if skill_name == "after-sale":
            if "aftersaleId" in output:
                return f"售后申请已创建：{output.get('aftersaleId', '')}，类型 {output.get('typeName', '')}，状态 {output.get('status', '')}"
            return "售后处理完成。"

        if skill_name == "listing-gen":
            if "title" in output:
                return f"Listing生成完成：标题 {output.get('title', '')[:50]}..."
            return "Listing生成完成。"

        if skill_name == "ad-optimizer":
            return "广告优化建议已生成。"

        if skill_name == "review-mgr":
            if "sentiment_summary" in output:
                return f"评论分析完成：{output.get('sentiment_summary', '')}"
            return "评论分析完成。"

        if skill_name == "xhs-seed":
            titles = output.get("titles", [])
            if titles and isinstance(titles[0], dict):
                return f"小红书笔记生成完成：{titles[0].get('title', '')[:50]}..."
            return "小红书内容生成完成。"

        if skill_name == "video-channel":
            title_options = output.get("title_options", [])
            if title_options:
                return f"视频号内容草稿已生成：{title_options[0][:50]}..."
            return "视频号内容生成完成。"

        if skill_name == "cross-drain":
            if output.get("strategies"):
                return f"跨平台导流策略已生成，覆盖 {output.get('total_platforms', 0)} 个平台。"
            if output.get("platform_name"):
                return f"{output.get('platform_name', '')} 导流策略已生成。"
            return "私域导流策略已生成。"

        if skill_name == "report-gen":
            if "title" in output:
                return f"经营报表已生成：{output.get('title', '')}"
            return "经营报表已生成。"

        if skill_name == "excel-viz":
            chart_type = output.get("chart_type", "图表")
            return f"数据可视化已生成：{chart_type} 图及统计结果。"

        if skill_name == "email-mgr":
            category = output.get("category_label", output.get("category", ""))
            priority = output.get("priority_label", output.get("priority", ""))
            return f"邮件处理完成：分类为 {category}，优先级 {priority}。"

        if skill_name == "doc-auto":
            document = output.get("document", {})
            if document.get("document_type_label"):
                return f"文档草稿已生成：{document.get('document_type_label', '')}。"
            return "文档自动化处理完成。"

        if skill_name == "intent-recognition":
            return f"客服意图识别完成：{output.get('intent_label', output.get('intent', '未知'))}。"

        if skill_name == "sentiment-analysis":
            label = output.get("sentiment_label", output.get("sentiment", "未知"))
            if output.get("require_human"):
                return f"情感分析完成：当前情绪为 {label}，建议转人工。"
            return f"情感分析完成：当前情绪为 {label}。"

        if skill_name == "skill-orchestrator":
            workflow_name = output.get("workflow_name", output.get("workflow", "业务工作流"))
            completed = output.get("completed_steps", 0)
            total = output.get("total_steps", 0)
            aggregated = output.get("aggregated_result", {})
            summary = aggregated.get("summary", {})
            ready_items = [key for key, value in summary.items() if isinstance(value, bool) and value]
            if ready_items:
                return f"工作流 {workflow_name} 已完成，完成 {completed}/{total} 步，已产出：{', '.join(ready_items[:4])}。"
            return f"工作流 {workflow_name} 已完成，完成 {completed}/{total} 步。"

        return f"技能 {skill_name} 执行完成。"

    def _generate_general_response(self, perception: Dict) -> str:
        intent = perception.get("intent", {})
        intent_label = intent.get("intent_label", "")

        if intent.get("intent") == "general_greeting":
            return "您好！我是AIMS营销助手，可以帮您处理电商运营、社媒营销、订单查询、售后服务等问题。请问有什么可以帮您的？"

        return f"我理解您想了解{intent_label}相关的内容，但目前暂无对应的功能模块。您可以尝试更具体地描述您的需求，或者联系人工客服获取帮助。"

    def get_conversation(self, conversation_id: str) -> Dict:
        history = self.memory.get_conversation_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "history": history,
            "turn_count": len(history),
        }

    def get_pipeline_stats(self, hours: int = 24) -> Dict:
        try:
            conn = get_db_connection()
            c = conn.cursor()
            since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

            c.execute("SELECT COUNT(*) as cnt FROM conversations WHERE updated_at >= ?", (since,))
            total_conversations = c.fetchone()["cnt"]

            c.execute("SELECT COUNT(*) as cnt FROM messages WHERE created_at >= ?", (since,))
            total_messages = c.fetchone()["cnt"]

            c.execute("SELECT intent, COUNT(*) as cnt FROM messages WHERE created_at >= ? AND intent != '' GROUP BY intent ORDER BY cnt DESC LIMIT 10", (since,))
            top_intents = [dict(row) for row in c.fetchall()]

            c.execute("SELECT skill_name, COUNT(*) as cnt, AVG(duration_ms) as avg_ms FROM skill_executions WHERE created_at >= ? GROUP BY skill_name ORDER BY cnt DESC LIMIT 10", (since,))
            skill_stats = [dict(row) for row in c.fetchall()]

            c.execute("SELECT module, AVG(duration_ms) as avg_ms, COUNT(*) as cnt FROM pipeline_logs WHERE created_at >= ? GROUP BY module", (since,))
            module_stats = [dict(row) for row in c.fetchall()]

            conn.close()

            return {
                "period_hours": hours,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "top_intents": top_intents,
                "skill_stats": skill_stats,
                "module_stats": module_stats,
            }
        except Exception as e:
            return {"error": str(e)}


    def get_skill_registry(self) -> Dict:
        return {
            "skills": {name: {"domain": info["domain"], "description": info["description"], "intents": info["intents"]} for name, info in SKILL_REGISTRY.items()},
            "intent_map": INTENT_TO_SKILL_MAP,
            "workflows": WORKFLOW_CATALOG,
        }


def main():
    input_data = json.loads(sys.stdin.read())

    action = input_data.get("action", "process")

    orchestrator = AgentOrchestrator()

    if action == "process":
        message = input_data.get("message", "")
        context = input_data.get("context", {})
        result = orchestrator.process(message, context)
    elif action == "get_conversation":
        conversation_id = input_data.get("conversation_id", "")
        result = orchestrator.get_conversation(conversation_id)
    elif action == "get_stats":
        hours = input_data.get("hours", 24)
        result = orchestrator.get_pipeline_stats(hours)
    elif action == "get_skill_registry":
        result = orchestrator.get_skill_registry()
    else:
        result = {"error": f"未知操作: {action}"}

    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
