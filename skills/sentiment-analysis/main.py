import json
import re
from datetime import datetime

def analyze_sentiment(user_message, history=None, context=None):
    """客服情感分析：正则模式匹配 + 情绪强度分级 + 历史连续负面检测 + 转人工策略"""

    if history is None:
        history = []
    if context is None:
        context = {}

    text = user_message.lower()

    negative_patterns = [
        (r'非常不满|极其失望|彻底失望|完全失望', -0.9, "极度失望"),
        (r'极度愤怒|暴怒|气死了|太气人了|太过分了', -0.9, "极度愤怒"),
        (r'强烈投诉|必须投诉|我要投诉|投诉到底|投诉到底', -0.85, "投诉威胁"),
        (r'骗子|虚假宣传|欺诈|坑人|无良商家', -0.85, "欺诈指控"),
        (r'垃圾|废物|没用|烂透了|一无是处', -0.8, "极端贬低"),
        (r'再也不买了|绝对不会再来|永远拉黑', -0.8, "永久流失风险"),
        (r'着急|急死了|非常急|太慢了|慢死了', -0.65, "焦急催促"),
        (r'失望|很失望|太失望|失望透顶', -0.6, "深度失望"),
        (r'不满|不满意|不太满意|有问题', -0.5, "轻度不满"),
        (r'差|太差|不好|不太好|不怎么样', -0.45, "评价不佳"),
        (r'慢|比较慢|有点慢|效率低', -0.35, "效率抱怨"),
        (r'麻烦|真麻烦|太麻烦了', -0.3, "麻烦感知")
    ]

    positive_patterns = [
        (r'非常满意|特别满意|超级满意|太棒了', 0.9, "极度满意"),
        (r'感谢|谢谢|多谢|感激不尽', 0.8, "真诚感谢"),
        (r'很好|非常好|挺好的|不错', 0.6, "正面评价"),
        (r'喜欢|挺喜欢|比较喜欢', 0.5, "喜好表达"),
        (r'好的|知道了|了解|明白', 0.1, "中性确认"),
        (r'好的|可以|行|没问题', 0.0, "平淡回应")
    ]

    angry_indicators = [
        '生气', '恼火', '发火', '愤怒', '暴怒',
        '太过分了', '太过分', '无法接受', '容忍',
        '什么破', '垃圾', '废物', '骗子'
    ]

    anxious_indicators = [
        '着急', '急死了', '急', '担心', '担忧',
        '害怕', '不安', '焦虑', '什么时候',
        '怎么还没', '怎么还不到'
    ]

    disappointed_indicators = [
        '失望', '绝望', '不抱希望', '算了',
        '放弃', '无奈', '无可奈何', '认栽'
    ]

    score = 0.0
    detected_emotions = []
    matched_keywords = []

    for pattern, weight, label in negative_patterns:
        if re.search(pattern, text):
            score += weight
            detected_emotions.append(label)
            matched_keywords.append(label)

    for pattern, weight, label in positive_patterns:
        if re.search(pattern, text):
            score += weight
            if label not in detected_emotions:
                detected_emotions.append(label)
            matched_keywords.append(label)

    is_angry = any(indicator in text for indicator in angry_indicators)
    is_anxious = any(indicator in text for indicator in anxious_indicators)
    is_disappointed = any(indicator in text for indicator in disappointed_indicators)

    if is_angry and score < 0:
        detected_emotions.append("愤怒激动")
        matched_keywords.append("愤怒")
        score = min(score, -0.7)

    if is_anxious and score < 0:
        detected_emotions.append("焦虑担忧")
        matched_keywords.append("焦虑")
        score = min(score, -0.5)

    if is_disappointed and score < 0:
        detected_emotions.append("失望沮丧")
        matched_keywords.append("失望")
        score = min(score, -0.6)

    score = max(-1.0, min(1.0, score))

    if score >= 0.5:
        sentiment = "positive"
        sentiment_label = "正面积极"
    elif score >= 0.1:
        sentiment = "neutral"
        sentiment_label = "中性平淡"
    elif score >= -0.3:
        sentiment = "negative"
        sentiment_label = "负面不满"
    elif score >= -0.6:
        sentiment = "angry"
        sentiment_label = "愤怒激动"
    elif score >= -0.8:
        sentiment = "anxious"
        sentiment_label = "焦虑担忧"
    else:
        sentiment = "disappointed"
        sentiment_label = "失望沮丧"

    if abs(score) <= 0.1:
        intensity = "low"
    elif abs(score) <= 0.4:
        intensity = "medium"
    elif abs(score) <= 0.7:
        intensity = "high"
    else:
        intensity = "critical"

    history_negative_count = 0
    for h in history[-3:]:
        h_content = h.get("content", "").lower()
        h_sentiment = h.get("sentiment", "neutral")
        if h_sentiment in ["negative", "angry", "anxious", "disappointed"]:
            history_negative_count += 1
        for _, weight, _ in negative_patterns:
            if re.search(r'\w+', h_content):
                history_negative_count += 0.1

    continuous_negative = history_negative_count >= 2

    require_human = False
    transfer_reason = ""

    if intensity == "critical":
        require_human = True
        transfer_reason = "检测到极度负面情绪（critical），立即转人工处理"
    elif continuous_negative and score < -0.5:
        require_human = True
        transfer_reason = "连续对话呈现负面情绪，需人工介入安抚"
    elif "投诉" in text or "举报" in text or "曝光" in text:
        require_human = True
        transfer_reason = "检测到投诉/举报意图，需人工处理"
    elif context.get("customer_tier") == "VIP" and score < -0.3:
        require_human = True
        transfer_reason = "VIP客户情绪负面，需高级客服处理"
    elif context.get("order_value", 0) > 5000 and score < -0.4:
        require_human = True
        transfer_reason = "高价值订单客户情绪异常，需重点关注"

    priority_map = {
        "critical": "critical",
        "angry_high": "urgent",
        "disappointed_high": "high",
        "anxious_high": "high",
        "negative_medium": "normal",
        "neutral": "low",
        "positive": "low"
    }

    if intensity == "critical":
        priority_level = "critical"
    elif sentiment == "angry" and intensity == "high":
        priority_level = "urgent"
    elif sentiment in ["disappointed", "anxious"] and intensity == "high":
        priority_level = "high"
    elif sentiment == "negative" and intensity == "medium":
        priority_level = "normal"
    elif sentiment in ["neutral", "positive"]:
        priority_level = "low"
    else:
        priority_level = "normal"

    if require_human:
        priority_level = "critical" if intensity == "critical" else ("urgent" if sentiment == "angry" else priority_level)

    response_strategies = {
        "positive": "使用友好语气，感谢客户支持，适时推荐关联产品",
        "neutral": "保持专业语气，准确解答问题，适时引导客户需求",
        "negative": "使用同理心语言，表达理解和歉意，积极解决问题",
        "angry": "使用最温和的语言，避免争辩，表达高度重视和立即处理意愿",
        "anxious": "提供明确时间节点和进度更新，消除客户焦虑",
        "disappointed": "真诚道歉并提供补偿方案，尽力挽回客户信任"
    }

    result = {
        "sentiment": sentiment,
        "sentiment_score": round(score, 2),
        "sentiment_label": sentiment_label,
        "emotion_keywords": matched_keywords[:5],
        "intensity": intensity,
        "require_human": require_human,
        "transfer_reason": transfer_reason,
        "priority_level": priority_level,
        "suggested_response": response_strategies.get(sentiment, "保持专业，积极解决问题")
    }

    return result

def main():
    import sys
    input_data = json.load(sys.stdin)

    user_message = input_data.get("user_message", "")
    history = input_data.get("history", [])
    context = input_data.get("context", {})

    result = analyze_sentiment(user_message, history, context)

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()