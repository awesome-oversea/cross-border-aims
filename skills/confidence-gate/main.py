import json
from datetime import datetime

def evaluate_confidence(intent_result, sentiment_result, rag_result=None, context=None):
    if rag_result is None:
        rag_result = {"hit": False, "confidence": 0.0, "content": ""}
    if context is None:
        context = {}

    intent_confidence = intent_result.get("confidence", 0.5)
    sentiment_score = sentiment_result.get("sentiment_score", 0.0)
    sentiment_intensity = sentiment_result.get("intensity", "medium")
    sentiment_require_human = sentiment_result.get("require_human", False)
    rag_confidence = rag_result.get("confidence", 0.5) if rag_result.get("hit") else 0.3

    intent_weight = 0.40
    sentiment_weight = 0.25
    rag_weight = 0.25
    context_weight = 0.10

    sentiment_confidence = 1.0 - abs(sentiment_score)
    if sentiment_intensity == "critical":
        sentiment_confidence *= 0.3
    elif sentiment_intensity == "high":
        sentiment_confidence *= 0.6
    elif sentiment_intensity == "medium":
        sentiment_confidence *= 0.8
    elif sentiment_intensity == "low":
        sentiment_confidence *= 0.95

    context_score = 0.5
    if context.get("customer_tier") == "VIP":
        context_score += 0.2
    if context.get("order_value", 0) > 5000:
        context_score += 0.15
    if context.get("previous_complaints", 0) > 3:
        context_score -= 0.2
    if context.get("customer_duration", 0) > 365:
        context_score += 0.1
    context_confidence = max(0.0, min(1.0, context_score))

    overall_confidence = (
        intent_confidence * intent_weight +
        sentiment_confidence * sentiment_weight +
        rag_confidence * rag_weight +
        context_confidence * context_weight
    )

    overall_confidence = max(0.0, min(1.0, overall_confidence))

    if overall_confidence >= 0.85:
        risk_level = "low"
    elif overall_confidence >= 0.6:
        risk_level = "medium"
    elif overall_confidence >= 0.4:
        risk_level = "high"
    else:
        risk_level = "critical"

    negative_sentiments = ["angry", "anxious", "disappointed"]
    is_negative_emotion = sentiment_result.get("sentiment", "neutral") in negative_sentiments

    auto_conditions = [
        intent_confidence >= 0.7,
        (not is_negative_emotion or sentiment_intensity in ["low", "medium"]),
        rag_confidence >= 0.6,
        risk_level != "critical"
    ]

    human_conditions = [
        overall_confidence < 0.4,
        sentiment_intensity == "critical",
        sentiment_require_human,
        risk_level == "critical"
    ]

    vip_high_value = (
        context.get("customer_tier") == "VIP" and
        overall_confidence < 0.7
    )
    if vip_high_value:
        human_conditions.append(True)

    high_value_negative = (
        context.get("order_value", 0) > 5000 and
        is_negative_emotion
    )
    if high_value_negative:
        human_conditions.append(True)

    if any(human_conditions):
        decision = "human"
        if sentiment_intensity == "critical":
            processing_mode = "立即转人工，优先处理"
            action = "立即转接人工客服，使用安抚话术，同步客户历史信息"
        elif overall_confidence < 0.4:
            processing_mode = "强制转人工"
            action = "转接人工客服，因置信度不足无法自动处理"
        else:
            processing_mode = "转人工处理"
            action = "根据情感分析结果转人工处理"
    elif all(auto_conditions):
        decision = "auto"
        processing_mode = "自动处理"
        action = f"直接执行{intent_result.get('intent_label', '')}流程"
    else:
        decision = "confirm"
        processing_mode = "确认后处理"
        action = "询问用户确认意图后执行"

    confidence_breakdown = {
        "intent_confidence": round(intent_confidence, 2),
        "sentiment_confidence": round(sentiment_confidence, 2),
        "rag_confidence": round(rag_confidence, 2),
        "context_confidence": round(context_confidence, 2),
        "weights": {
            "intent": intent_weight,
            "sentiment": sentiment_weight,
            "rag": rag_weight,
            "context": context_weight
        }
    }

    message_map = {
        "auto": f"高置信度（{overall_confidence:.0%}），自动执行{intent_result.get('intent_label', '')}",
        "confirm": f"中置信度（{overall_confidence:.0%}），建议确认用户意图后执行",
        "human": f"低置信度（{overall_confidence:.0%}）或高风险，转人工处理"
    }

    result = {
        "decision": decision,
        "confidence": round(overall_confidence, 2),
        "confidence_breakdown": confidence_breakdown,
        "risk_level": risk_level,
        "processing_mode": processing_mode,
        "action": action,
        "message": message_map.get(decision, "未知决策"),
        "intent": intent_result.get("intent", "unknown"),
        "intent_label": intent_result.get("intent_label", "未知"),
        "sentiment": sentiment_result.get("sentiment", "neutral"),
        "sentiment_label": sentiment_result.get("sentiment_label", "中性"),
        "requires_immediate_attention": risk_level in ["high", "critical"] or sentiment_intensity in ["high", "critical"]
    }

    return result

def main():
    import sys
    input_data = json.load(sys.stdin)

    intent_result = input_data.get("intent_result", {})
    sentiment_result = input_data.get("sentiment_result", {})
    rag_result = input_data.get("rag_result", {})
    context = input_data.get("context", {})

    result = evaluate_confidence(intent_result, sentiment_result, rag_result, context)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()