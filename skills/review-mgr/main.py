#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 评论情感关键词：强/中/弱三级正向和负向词库
SENTIMENT_KEYWORDS = {
    'positive': {
        'strong': ['非常好', '超级好', '太棒了', '完美', '强烈推荐', '非常满意', '超出预期', '物超所值'],
        'moderate': ['不错', '好用', '满意', '喜欢', '推荐', '值得', '方便', '实用'],
        'weak': ['还行', '可以', '一般般好', '凑合', '过得去'],
    },
    'negative': {
        'strong': ['非常差', '太烂了', '垃圾', '强烈不推荐', '极度失望', '完全不能用', '坑人', '骗人'],
        'moderate': ['不好', '差', '失望', '不满意', '不推荐', '质量差', '难用', '后悔'],
        'weak': ['一般', '不太行', '有点问题', '勉强', '有待改善'],
    },
    'neutral': ['普通', '一般', '中规中矩', '没啥特别', '正常'],
}

REPLY_STRATEGIES = {
    'positive_strong': {
        'name': '好评强回复',
        'template': '感谢您的五星好评！{specific_praise}是我们一直坚持的方向，我们会继续努力，为您提供更好的产品和服务！期待您的再次光临~',
        'priority': 'low',
        'auto_reply': True,
    },
    'positive_moderate': {
        'name': '好评中回复',
        'template': '感谢您的支持和认可！很高兴您对{specific_praise}感到满意，我们会持续优化产品体验。如有任何建议，欢迎随时联系我们~',
        'priority': 'low',
        'auto_reply': True,
    },
    'negative_strong': {
        'name': '差评强回复',
        'template': '非常抱歉给您带来了不好的体验！{specific_issue}的问题我们非常重视，已记录并反馈给相关部门。我们会尽快改进，请您联系我们（{contact}），我们一定给您满意的解决方案！',
        'priority': 'high',
        'auto_reply': False,
    },
    'negative_moderate': {
        'name': '差评中回复',
        'template': '抱歉给您带来不便！关于{specific_issue}的问题，我们已经注意到并正在改进。如果您愿意，请联系我们（{contact}），我们希望能为您解决问题。',
        'priority': 'high',
        'auto_reply': False,
    },
    'negative_weak': {
        'name': '差评弱回复',
        'template': '感谢您的反馈！关于{specific_issue}我们会持续改进，希望能给您带来更好的体验。如有问题随时联系我们~',
        'priority': 'medium',
        'auto_reply': True,
    },
    'neutral': {
        'name': '中性回复',
        'template': '感谢您的评价！我们会继续努力提升产品质量和服务水平，希望能给您带来更好的体验。如有建议欢迎随时告诉我们~',
        'priority': 'medium',
        'auto_reply': True,
    },
    'refund_request': {
        'name': '退款请求回复',
        'template': '非常抱歉给您带来不好的体验！我们理解您的心情，已为您标记优先处理。请联系客服（{contact}），我们将尽快为您处理退款事宜。',
        'priority': 'critical',
        'auto_reply': False,
    },
    'quality_complaint': {
        'name': '质量投诉回复',
        'template': '非常抱歉产品质量没有达到您的期望！这是我们不希望看到的。关于{specific_issue}，我们已经启动质量调查。请联系我们（{contact}），我们一定给您一个满意的答复！',
        'priority': 'critical',
        'auto_reply': False,
    },
}

ALERT_RULES = {
    'negative_rate_spike': {
        'name': '差评率飙升预警',
        'threshold': 0.15,
        'window_days': 7,
        'description': '近7天差评率超过15%',
    },
    'consecutive_negative': {
        'name': '连续差评预警',
        'threshold': 3,
        'description': '连续3条以上差评',
    },
    'rating_drop': {
        'name': '评分骤降预警',
        'threshold': 0.5,
        'window_days': 7,
        'description': '近7天平均评分下降超过0.5分',
    },
    'keyword_alert': {
        'name': '关键词预警',
        'keywords': ['假货', '仿品', '侵权', '投诉', '举报', '315', '工商', '律师'],
        'description': '评论中出现高风险关键词',
    },
    'volume_spike': {
        'name': '评论量异常预警',
        'threshold': 3.0,
        'window_days': 3,
        'description': '近3天评论量为历史均值的3倍以上',
    },
}

COMPETITOR_METRICS = {
    'price_comparison': {'weight': 0.2, 'description': '价格对比'},
    'rating_comparison': {'weight': 0.25, 'description': '评分对比'},
    'review_count': {'weight': 0.15, 'description': '评论数量'},
    'feature_mentions': {'weight': 0.2, 'description': '功能提及度'},
    'sentiment_comparison': {'weight': 0.2, 'description': '情感对比'},
}

REVIEW_KNOWLEDGE_BASE = [
    {
        "id": "reply_best_practices",
        "category": "reply_strategy",
        "title": "评论回复最佳实践",
        "content": "评论回复原则：1) 24小时内回复所有差评；2) 先道歉再解释最后给方案；3) 不与客户争辩；4) 私下解决敏感问题；5) 好评也要回复增强粘性；6) 使用客户名字增加亲切感；7) 避免模板化回复，针对具体问题回应",
    },
    {
        "id": "negative_review_handling",
        "category": "reply_strategy",
        "title": "差评处理SOP",
        "content": "差评处理流程：1) 识别差评类型（质量/物流/服务/误解）；2) 24小时内公开回复；3) 私信联系客户了解详情；4) 提供解决方案（退款/换货/补偿）；5) 跟进处理结果；6) 分析差评根因并改进；7) 鼓励客户修改评价",
    },
    {
        "id": "review_seo",
        "category": "optimization",
        "title": "评论SEO优化",
        "content": "评论对搜索排名的影响：1) 评论数量影响产品排名权重；2) 近30天评论数比历史总量更重要；3) 带图评论权重更高；4) 评论中的关键词影响搜索；5) 回复率影响店铺评分；6) 差评回复可降低负面影响",
    },
]


def analyze_sentiment(text: str) -> Dict:
    if not text:
        return {"score": 0.5, "label": "neutral", "confidence": 0.0}

    positive_score = 0.0
    negative_score = 0.0
    matched_keywords = []

    for strength, keywords in SENTIMENT_KEYWORDS['positive'].items():
        weight = {'strong': 1.0, 'moderate': 0.6, 'weak': 0.3}.get(strength, 0.3)
        for kw in keywords:
            if kw in text:
                positive_score += weight
                matched_keywords.append({"keyword": kw, "type": "positive", "strength": strength})

    for strength, keywords in SENTIMENT_KEYWORDS['negative'].items():
        weight = {'strong': 1.0, 'moderate': 0.6, 'weak': 0.3}.get(strength, 0.3)
        for kw in keywords:
            if kw in text:
                negative_score += weight
                matched_keywords.append({"keyword": kw, "type": "negative", "strength": strength})

    negation_patterns = ['不', '没', '别', '非', '未', '无']
    has_negation = any(neg in text for neg in negation_patterns)
    if has_negation and positive_score > 0:
        for mk in matched_keywords:
            if mk["type"] == "positive":
                idx = text.find(mk["keyword"])
                if idx > 0 and any(text[max(0, idx - 2):idx].find(n) >= 0 for n in negation_patterns):
                    positive_score -= {'strong': 1.0, 'moderate': 0.6, 'weak': 0.3}.get(mk["strength"], 0.3)
                    negative_score += 0.3

    total = positive_score + negative_score
    if total == 0:
        score = 0.5
        label = "neutral"
    else:
        score = 0.5 + (positive_score - negative_score) / (2 * max(total, 1))
        score = max(0.0, min(1.0, score))
        if score >= 0.7:
            label = "positive"
        elif score <= 0.3:
            label = "negative"
        else:
            label = "neutral"

    confidence = min(1.0, total / 5.0)

    return {
        "score": round(score, 3),
        "label": label,
        "confidence": round(confidence, 3),
        "positiveScore": round(positive_score, 2),
        "negativeScore": round(negative_score, 2),
        "matchedKeywords": matched_keywords[:10],
    }


def analyze_sentiment_trend(reviews: List[Dict], window_days: int = 30) -> Dict:
    if not reviews:
        return {"error": "无评论数据"}

    now = datetime.now()
    periods = []
    period_days = 7
    num_periods = max(1, window_days // period_days)

    for i in range(num_periods):
        end_date = now - timedelta(days=i * period_days)
        start_date = end_date - timedelta(days=period_days)
        period_reviews = [
            r for r in reviews
            if start_date <= datetime.strptime(r.get('date', '2024-01-01'), '%Y-%m-%d') < end_date
        ]

        if period_reviews:
            sentiments = [analyze_sentiment(r.get('content', '')) for r in period_reviews]
            avg_score = sum(s['score'] for s in sentiments) / len(sentiments)
            positive_rate = sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments)
            negative_rate = sum(1 for s in sentiments if s['label'] == 'negative') / len(sentiments)
        else:
            avg_score = 0.5
            positive_rate = 0
            negative_rate = 0

        periods.append({
            "period": f"第{num_periods - i}周",
            "startDate": start_date.strftime('%Y-%m-%d'),
            "endDate": end_date.strftime('%Y-%m-%d'),
            "reviewCount": len(period_reviews),
            "avgSentimentScore": round(avg_score, 3),
            "positiveRate": round(positive_rate, 3),
            "negativeRate": round(negative_rate, 3),
        })

    periods.reverse()

    if len(periods) >= 2:
        latest = periods[-1]
        previous = periods[-2]
        trend_direction = "improving" if latest['avgSentimentScore'] > previous['avgSentimentScore'] else (
            "declining" if latest['avgSentimentScore'] < previous['avgSentimentScore'] else "stable"
        )
        score_change = round(latest['avgSentimentScore'] - previous['avgSentimentScore'], 3)
    else:
        trend_direction = "insufficient_data"
        score_change = 0

    return {
        "windowDays": window_days,
        "periods": periods,
        "trendDirection": trend_direction,
        "scoreChange": score_change,
        "summary": {
            "totalReviews": len(reviews),
            "overallSentiment": round(sum(p['avgSentimentScore'] for p in periods) / len(periods), 3),
            "latestNegativeRate": periods[-1]['negativeRate'] if periods else 0,
        },
    }


def detect_alerts(reviews: List[Dict], product_id: str = "") -> Dict:
    alerts = []

    if not reviews:
        return {"alerts": [], "alertCount": 0, "riskLevel": "unknown"}

    now = datetime.now()

    recent_7d = [
        r for r in reviews
        if (now - datetime.strptime(r.get('date', '2024-01-01'), '%Y-%m-%d')).days <= 7
    ]
    if recent_7d:
        negative_count = sum(1 for r in recent_7d if r.get('rating', 5) <= 2)
        negative_rate = negative_count / len(recent_7d)
        if negative_rate > ALERT_RULES['negative_rate_spike']['threshold']:
            alerts.append({
                "rule": ALERT_RULES['negative_rate_spike']['name'],
                "severity": "high",
                "message": f"近7天差评率{round(negative_rate * 100, 1)}%，超过阈值{ALERT_RULES['negative_rate_spike']['threshold'] * 100}%",
                "data": {"negativeRate": round(negative_rate, 3), "threshold": ALERT_RULES['negative_rate_spike']['threshold']},
            })

    sorted_reviews = sorted(reviews, key=lambda x: x.get('date', ''))
    consecutive = 0
    for r in reversed(sorted_reviews):
        if r.get('rating', 5) <= 2:
            consecutive += 1
        else:
            break
    if consecutive >= ALERT_RULES['consecutive_negative']['threshold']:
        alerts.append({
            "rule": ALERT_RULES['consecutive_negative']['name'],
            "severity": "high",
            "message": f"连续{consecutive}条差评，超过阈值{ALERT_RULES['consecutive_negative']['threshold']}",
            "data": {"consecutiveCount": consecutive},
        })

    recent_3d = [
        r for r in reviews
        if (now - datetime.strptime(r.get('date', '2024-01-01'), '%Y-%m-%d')).days <= 3
    ]
    avg_30d = len(reviews) / 30 if len(reviews) > 0 else 0
    if avg_30d > 0 and len(recent_3d) / 3 > avg_30d * ALERT_RULES['volume_spike']['threshold']:
        alerts.append({
            "rule": ALERT_RULES['volume_spike']['name'],
            "severity": "medium",
            "message": f"近3天日均评论{len(recent_3d) / 3:.1f}条，为历史均值{avg_30d:.1f}的{len(recent_3d) / 3 / avg_30d:.1f}倍",
            "data": {"recentDailyAvg": round(len(recent_3d) / 3, 1), "historicalAvg": round(avg_30d, 1)},
        })

    for r in recent_7d:
        content = r.get('content', '')
        for kw in ALERT_RULES['keyword_alert']['keywords']:
            if kw in content:
                alerts.append({
                    "rule": ALERT_RULES['keyword_alert']['name'],
                    "severity": "critical",
                    "message": f"评论中出现高风险关键词: {kw}",
                    "data": {"keyword": kw, "reviewDate": r.get('date', ''), "reviewId": r.get('id', '')},
                })
                break

    risk_level = "low"
    if any(a['severity'] == 'critical' for a in alerts):
        risk_level = "critical"
    elif any(a['severity'] == 'high' for a in alerts):
        risk_level = "high"
    elif any(a['severity'] == 'medium' for a in alerts):
        risk_level = "medium"

    return {
        "alerts": alerts,
        "alertCount": len(alerts),
        "riskLevel": risk_level,
        "productId": product_id,
    }


def generate_reply(review: Dict, product_name: str = "", contact: str = "在线客服") -> Dict:
    content = review.get('content', '')
    rating = review.get('rating', 5)
    sentiment = analyze_sentiment(content)

    strategy_key = 'neutral'
    specific_issue = "您的反馈"
    specific_praise = "您的认可"

    if sentiment['label'] == 'positive':
        if sentiment['score'] >= 0.8:
            strategy_key = 'positive_strong'
        else:
            strategy_key = 'positive_moderate'
        positive_kws = [k['keyword'] for k in sentiment.get('matchedKeywords', []) if k['type'] == 'positive']
        if positive_kws:
            specific_praise = f"您对{positive_kws[0]}的认可"
    elif sentiment['label'] == 'negative':
        if any(kw in content for kw in ['退款', '退钱', '退货']):
            strategy_key = 'refund_request'
        elif any(kw in content for kw in ['质量', '坏了', '破损', '假货']):
            strategy_key = 'quality_complaint'
        elif sentiment['score'] <= 0.2:
            strategy_key = 'negative_strong'
        elif sentiment['score'] <= 0.3:
            strategy_key = 'negative_moderate'
        else:
            strategy_key = 'negative_weak'
        negative_kws = [k['keyword'] for k in sentiment.get('matchedKeywords', []) if k['type'] == 'negative']
        if negative_kws:
            specific_issue = f"关于{negative_kws[0]}的问题"

    strategy = REPLY_STRATEGIES.get(strategy_key, REPLY_STRATEGIES['neutral'])
    reply_text = strategy['template'].replace('{specific_praise}', specific_praise)
    reply_text = reply_text.replace('{specific_issue}', specific_issue)
    reply_text = reply_text.replace('{contact}', contact)

    return {
        "replyText": reply_text,
        "strategy": strategy_key,
        "strategyName": strategy['name'],
        "priority": strategy['priority'],
        "autoReply": strategy['auto_reply'],
        "sentiment": sentiment,
        "requiresApproval": strategy['priority'] in ('high', 'critical'),
    }


def compare_with_competitors(product_reviews: List[Dict], competitor_reviews: Dict[str, List[Dict]],
                              product_name: str = "") -> Dict:
    def calc_metrics(reviews: List[Dict]) -> Dict:
        if not reviews:
            return {"avgRating": 0, "reviewCount": 0, "positiveRate": 0, "negativeRate": 0, "avgSentiment": 0.5}
        ratings = [r.get('rating', 5) for r in reviews]
        sentiments = [analyze_sentiment(r.get('content', '')) for r in reviews]
        return {
            "avgRating": round(sum(ratings) / len(ratings), 2),
            "reviewCount": len(reviews),
            "positiveRate": round(sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments), 3),
            "negativeRate": round(sum(1 for s in sentiments if s['label'] == 'negative') / len(sentiments), 3),
            "avgSentiment": round(sum(s['score'] for s in sentiments) / len(sentiments), 3),
        }

    our_metrics = calc_metrics(product_reviews)

    competitor_metrics = {}
    for comp_name, comp_reviews in competitor_reviews.items():
        competitor_metrics[comp_name] = calc_metrics(comp_reviews)

    advantages = []
    disadvantages = []
    for comp_name, comp_m in competitor_metrics.items():
        if our_metrics['avgRating'] > comp_m['avgRating']:
            advantages.append(f"评分高于{comp_name}({our_metrics['avgRating']} vs {comp_m['avgRating']})")
        elif our_metrics['avgRating'] < comp_m['avgRating']:
            disadvantages.append(f"评分低于{comp_name}({our_metrics['avgRating']} vs {comp_m['avgRating']})")
        if our_metrics['positiveRate'] > comp_m['positiveRate']:
            advantages.append(f"好评率高于{comp_name}({our_metrics['positiveRate']:.1%} vs {comp_m['positiveRate']:.1%})")
        elif our_metrics['positiveRate'] < comp_m['positiveRate']:
            disadvantages.append(f"好评率低于{comp_name}({our_metrics['positiveRate']:.1%} vs {comp_m['positiveRate']:.1%})")

    return {
        "productName": product_name,
        "ourMetrics": our_metrics,
        "competitorMetrics": competitor_metrics,
        "advantages": advantages[:5],
        "disadvantages": disadvantages[:5],
        "overallPosition": "leading" if len(advantages) > len(disadvantages) else (
            "lagging" if len(disadvantages) > len(advantages) else "competitive"),
    }


def extract_review_insights(reviews: List[Dict]) -> Dict:
    if not reviews:
        return {"error": "无评论数据"}

    feature_mentions = {}
    pain_points = []
    praise_points = []

    feature_keywords = {
        'quality': ['质量', '材质', '做工', '质感', '品质'],
        'price': ['价格', '性价比', '便宜', '贵', '划算', '值'],
        'design': ['设计', '外观', '颜值', '好看', '款式'],
        'function': ['功能', '效果', '实用', '好用', '性能'],
        'packaging': ['包装', '盒子', '快递', '发货', '物流'],
        'service': ['服务', '客服', '态度', '售后', '回复'],
        'size': ['大小', '尺寸', '容量', '规格', '重量'],
        'comfort': ['舒适', '手感', '体验', '舒适度', '柔软'],
    }

    for review in reviews:
        content = review.get('content', '')
        rating = review.get('rating', 5)
        sentiment = analyze_sentiment(content)

        for feature, keywords in feature_keywords.items():
            for kw in keywords:
                if kw in content:
                    if feature not in feature_mentions:
                        feature_mentions[feature] = {'positive': 0, 'negative': 0, 'total': 0}
                    feature_mentions[feature]['total'] += 1
                    if sentiment['label'] == 'positive':
                        feature_mentions[feature]['positive'] += 1
                    elif sentiment['label'] == 'negative':
                        feature_mentions[feature]['negative'] += 1

        if rating <= 2 or sentiment['label'] == 'negative':
            negative_kws = [k['keyword'] for k in sentiment.get('matchedKeywords', []) if k['type'] == 'negative']
            if negative_kws:
                pain_points.append({
                    "point": negative_kws[0],
                    "rating": rating,
                    "date": review.get('date', ''),
                })

        if rating >= 4 or sentiment['label'] == 'positive':
            positive_kws = [k['keyword'] for k in sentiment.get('matchedKeywords', []) if k['type'] == 'positive']
            if positive_kws:
                praise_points.append({
                    "point": positive_kws[0],
                    "rating": rating,
                    "date": review.get('date', ''),
                })

    feature_summary = []
    for feature, counts in sorted(feature_mentions.items(), key=lambda x: x[1]['total'], reverse=True):
        positive_rate = counts['positive'] / max(counts['total'], 1)
        feature_summary.append({
            "feature": feature,
            "totalMentions": counts['total'],
            "positiveRate": round(positive_rate, 3),
            "negativeRate": round(counts['negative'] / max(counts['total'], 1), 3),
            "sentiment": "positive" if positive_rate > 0.6 else ("negative" if positive_rate < 0.4 else "mixed"),
        })

    return {
        "totalReviews": len(reviews),
        "featureAnalysis": feature_summary[:8],
        "topPainPoints": sorted(pain_points, key=lambda x: x['rating'])[:5],
        "topPraisePoints": sorted(praise_points, key=lambda x: x['rating'], reverse=True)[:5],
    }


def manage_reviews(input_data: Dict) -> Dict:
    product_name = input_data.get('product_name', '')
    product_id = input_data.get('product_id', '')
    reviews = input_data.get('reviews', [])
    action = input_data.get('action', 'full_analysis')

    result = {"productName": product_name, "productId": product_id, "action": action}

    if action in ('full_analysis', 'sentiment_analysis'):
        if reviews:
            sentiments = []
            for r in reviews:
                s = analyze_sentiment(r.get('content', ''))
                sentiments.append({"reviewId": r.get('id', ''), "sentiment": s, "rating": r.get('rating', 5)})
            result["sentimentAnalysis"] = {
                "totalAnalyzed": len(sentiments),
                "results": sentiments,
                "summary": {
                    "positive": sum(1 for s in sentiments if s['sentiment']['label'] == 'positive'),
                    "negative": sum(1 for s in sentiments if s['sentiment']['label'] == 'negative'),
                    "neutral": sum(1 for s in sentiments if s['sentiment']['label'] == 'neutral'),
                },
            }

    if action in ('full_analysis', 'trend_analysis'):
        if reviews:
            result["trendAnalysis"] = analyze_sentiment_trend(reviews, window_days=input_data.get('window_days', 30))

    if action in ('full_analysis', 'alert_detection'):
        if reviews:
            result["alertDetection"] = detect_alerts(reviews, product_id)

    if action in ('full_analysis', 'reply_generation'):
        if reviews:
            replies = []
            for r in reviews[:20]:
                reply = generate_reply(r, product_name, input_data.get('contact', '在线客服'))
                replies.append({"reviewId": r.get('id', ''), "reply": reply})
            result["replyGeneration"] = {
                "replies": replies,
                "autoApprovable": sum(1 for r in replies if r['reply']['autoReply']),
                "needsApproval": sum(1 for r in replies if r['reply']['requiresApproval']),
            }

    if action in ('full_analysis', 'competitor_comparison'):
        competitor_reviews = input_data.get('competitor_reviews', {})
        if competitor_reviews:
            result["competitorComparison"] = compare_with_competitors(reviews, competitor_reviews, product_name)

    if action in ('full_analysis', 'insights'):
        if reviews:
            result["insights"] = extract_review_insights(reviews)

    alert_data = result.get("alertDetection", {})
    risk_level = alert_data.get("riskLevel", "low")
    needs_human = risk_level in ('critical', 'high')
    reason = ""
    if risk_level == 'critical':
        reason = f"检测到{alert_data.get('alertCount', 0)}个严重预警，需立即人工处理"
    elif risk_level == 'high':
        reason = f"检测到{alert_data.get('alertCount', 0)}个高风险预警，建议人工审核"

    confidence = 100.0
    if risk_level == 'critical':
        confidence -= 40
    elif risk_level == 'high':
        confidence -= 20
    if not reviews:
        confidence -= 30
    confidence = max(0, min(100, confidence))

    result["handoff"] = {
        "needsHumanReview": needs_human,
        "reason": reason,
        "confidence": round(confidence, 1),
        "gate": "auto" if confidence >= 90 else ("notify" if confidence >= 60 else "human"),
    }

    return result


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

    result = manage_reviews(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
