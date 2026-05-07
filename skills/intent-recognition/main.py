import json
import re
from datetime import datetime

def recognize_intent(user_message, history=None):
    """客服意图识别：关键词匹配 + 历史上下文增强，输出意图标签和置信度"""

    if history is None:
        history = []

    text = user_message.lower()

    intent_patterns = {
        "presales": {
            "keywords": ["价格", "多少钱", "规格", "参数", "功能", "怎么用", "如何使用", "发货时间", "有货吗", "库存", "优惠", "打折", "团购", "批发", "能不能", "可以买吗", "在哪里买", "官网", "正品", "真假", "辨别"],
            "weight": 1.0
        },
        "order_query": {
            "keywords": ["订单", "下单", "付款", "待发货", "待收货", "已完成", "订单号", "ord", "订单号是", "查订单", "看看订单", "我的订单", "什么时候到", "发货了吗", "发货没"],
            "weight": 1.0
        },
        "logistics": {
            "keywords": ["物流", "快递", "运单", "单号", "到哪了", "派送", "签收", "未收到", "在路上", "快递员", "派送中", "已揽收", "运输中", "到达", "迟迟没到"],
            "weight": 1.0
        },
        "aftersale": {
            "keywords": ["售后", "退货", "换货", "维修", "退换", "退换货", "质保", "保修", "坏了", "质量问题", "不喜欢", "效果不好", "退货退款"],
            "weight": 1.0
        },
        "complaint": {
            "keywords": ["投诉", "差评", "举报", "反馈", "不满", "失望", "太差", "骗子", "虚假宣传", "欺诈", "坑人", "无良", "严重问题", "必须投诉", "我要投诉", "非常不满"],
            "weight": 1.0
        },
        "refund": {
            "keywords": ["退款", "退钱", "钱什么时候到", "退款进度", "退款到账", "还没收到钱", "退款申请", "取消订单退款", "付多了", "多扣"],
            "weight": 1.0
        },
        "exchange": {
            "keywords": ["换货", "换颜色", "换型号", "换大小", "换款式", "换商品", "换一下", "想换", "更换"],
            "weight": 1.0
        },
        "tracking": {
            "keywords": ["查物流", "看快递", "运单号", "追踪", "跟踪", "物流查询", "快递查询", "到哪儿了", " sf ", "顺丰", "圆通", "中通", "韵达", "申通", "ems"],
            "weight": 1.0
        }
    }

    history_text = " ".join([h.get("content", "") for h in history]).lower()

    scores = {}
    matched_keywords = {}

    for intent, config in intent_patterns.items():
        score = 0
        keywords_found = []

        for keyword in config["keywords"]:
            if keyword.lower() in text or keyword.lower() in history_text:
                score += 1
                keywords_found.append(keyword)

        if score > 0:
            scores[intent] = score
            matched_keywords[intent] = keywords_found

    if not scores:
        if any(word in text for word in ["你好", "在吗", "请问", "咨询", "问一下", "问一下", "帮忙", "帮助"]):
            return {
                "intent": "general",
                "intent_label": "一般咨询",
                "confidence": 0.6,
                "keywords": [],
                "entities": extract_entities(user_message),
                "suggestions": ["询问用户具体需求", "引导用户描述问题"],
                "response_template": "您好！请问有什么可以帮您的？"
            }
        else:
            return {
                "intent": "unclear",
                "intent_label": "无法识别",
                "confidence": 0.3,
                "keywords": [],
                "entities": extract_entities(user_message),
                "suggestions": ["请人工客服介入", "引导用户重新描述问题"],
                "response_template": "抱歉，我没能理解您的问题，请您重新描述一下您遇到的状况，我会尽力帮助您。"
            }

    best_intent = max(scores, key=scores.get)
    max_score = scores[best_intent]

    confidence = min(0.95, 0.5 + (max_score * 0.15))

    if best_intent in ["tracking", "logistics"] and "物流" in history_text:
        best_intent = "logistics"
        confidence = max(confidence, 0.75)

    if best_intent == "order_query" and "退款" in text:
        best_intent = "refund"
        confidence = 0.8

    entities = extract_entities(user_message)
    if entities.get("order_id") and best_intent not in ["order_query", "refund"]:
        scores["order_query"] = scores.get("order_query", 0) + 0.5
        if scores["order_query"] > max_score:
            best_intent = "order_query"
            max_score = scores["order_query"]
            confidence = 0.85

    intent_labels = {
        "presales": "售前咨询",
        "order_query": "订单查询",
        "logistics": "物流咨询",
        "aftersale": "售后处理",
        "complaint": "投诉建议",
        "refund": "退款咨询",
        "exchange": "换货咨询",
        "tracking": "物流跟踪",
        "general": "一般咨询",
        "unclear": "无法识别"
    }

    suggestions_map = {
        "presales": ["查询商品信息", "提供价格和规格", "解答使用问题"],
        "order_query": ["查询订单状态", "提供订单详情", "解答配送时间"],
        "logistics": ["查询物流进度", "提供快递信息", "解答配送问题"],
        "aftersale": ["了解售后政策", "协助办理退货", "提供维修服务"],
        "complaint": ["认真倾听诉求", "记录问题详情", "及时反馈处理"],
        "refund": ["查询退款进度", "解释退款流程", "协助解决问题"],
        "exchange": ["了解换货政策", "协助办理换货", "提供换货方案"],
        "tracking": ["查询物流信息", "提供快递追踪", "解答配送疑问"],
        "general": ["了解具体需求", "提供相应帮助"],
        "unclear": ["请人工客服介入", "引导用户重新描述"]
    }

    response_templates = {
        "presales": "您好！感谢您的咨询。关于{topic}，我来为您详细介绍。请问您想了解哪方面的信息呢？",
        "order_query": "您好！我来帮您查询订单信息。请提供一下您的订单号或者收货人信息。",
        "logistics": "您好！我来帮您查询物流进度。请提供一下运单号。",
        "aftersale": "您好！关于售后问题，我会尽力为您解决。请问您遇到的是什么情况呢？",
        "complaint": "您好！非常抱歉给您带来不好的体验，请您详细描述一下问题，我们会认真处理。",
        "refund": "您好！我来帮您查询退款进度。请提供一下您的订单号。",
        "exchange": "您好！关于换货问题，我来帮您处理。请问您想换什么商品呢？",
        "tracking": "您好！我来帮您追踪物流。请提供一下运单号。",
        "general": "您好！请问有什么可以帮您的？",
        "unclear": "抱歉，我没能理解您的问题，请您重新描述一下您遇到的状况。"
    }

    result = {
        "intent": best_intent,
        "intent_label": intent_labels.get(best_intent, "未知"),
        "confidence": round(confidence, 2),
        "keywords": matched_keywords.get(best_intent, []),
        "entities": entities,
        "suggestions": suggestions_map.get(best_intent, []),
        "response_template": response_templates.get(best_intent, "")
    }

    return result

def extract_entities(text):
    entities = {}

    order_patterns = [
        r'订单号[：:]\s*([A-Za-z0-9]{10,20})',
        r'订单[：:]\s*([A-Za-z0-9]{10,20})',
        r'ord\d+',
        r'([A-Za-z]{2,}\d{8,15})',
        r'(\d{10,20})'
    ]

    for pattern in order_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            potential_order = match.group(1) if match.lastindex else match.group()
            if len(potential_order) >= 10:
                entities["order_id"] = potential_order.upper()
                break

    tracking_patterns = [
        r'(SF\d{10,15})',
        r'(YT\d{10,15})',
        r'(ZT\d{10,15})',
        r'(STO\d{10,15})',
        r'(YD\d{10,15})',
        r'(EMS\d{10,15})',
        r'(JK\d{10,15})',
        r'(\d{12,18})'
    ]

    for pattern in tracking_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities["tracking_number"] = match.group(1)
            break

    phone_patterns = [
        r'1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}',
        r'\d{3}[\s\-]?\d{4}[\s\-]?\d{4}'
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[\s\-]', '', match.group())
            if len(phone) == 11:
                entities["phone"] = phone[:3] + "****" + phone[-4:]
                entities["phone_raw"] = phone
                break

    product_keywords = ["智能手表", "蓝牙耳机", "无线充电器", "手机壳", "数据线", "移动电源", "音箱", "平板", "笔记本", "键盘", "鼠标", "显示器"]
    for product in product_keywords:
        if product in text:
            entities["product_name"] = product
            break

    return entities

def main():
    import sys
    input_data = json.load(sys.stdin)

    user_message = input_data.get("user_message", "")
    history = input_data.get("history", [])

    result = recognize_intent(user_message, history)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()