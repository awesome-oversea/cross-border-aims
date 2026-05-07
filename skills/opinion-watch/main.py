#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from typing import Dict, List, Optional

# 情绪词库
# 情感词库：正向/负向/危机三类情绪词
SENTIMENT_WORDS = {
    'positive': ['好', '棒', '赞', '满意', '喜欢', '推荐', '不错', '爱了', '绝绝子'],
    'negative': ['差', '烂', '坏', '坑', '骗', '垃圾', '无语', '失望', '后悔'],
    'crisis': ['投诉', '举报', '曝光', '维权', '法律', '欺诈', '假货', '劣质', '倒闭']
}

# 风险等级定义
RISK_LEVELS = {
    'low': {
        'score': 0,
        'description': '低风险',
        'action': '常规处理',
        'escalation': '无需升级'
    },
    'medium': {
        'score': 1,
        'description': '中风险',
        'action': '关注处理',
        'escalation': '客服跟进'
    },
    'high': {
        'score': 2,
        'description': '高风险',
        'action': '紧急处理',
        'escalation': '运营介入'
    },
    'critical': {
        'score': 3,
        'description': '严重风险',
        'action': '危机响应',
        'escalation': '公关团队'
    }
}

# 危机关键词
# 危机关键词：触发危机响应的高风险词
CRISIS_KEYWORDS = [
    '投诉', '举报', '曝光', '维权', '法律', '起诉', '欺诈', '假货', '劣质',
    '退款', '退货', '差评', '拉黑', '抵制', '倒闭', '跑路', '骗子', '诈骗',
    '垃圾', '废物', '无语', '恶心', '后悔', '上当', '被骗', '虚假宣传'
]

# 扩散风险关键词
SPREAD_KEYWORDS = [
    '大家注意', '千万别买', '避坑', '提醒', '转发', '扩散', '避雷', '拉黑',
    '抵制', '再也不来', '一生黑', '曝光这家', '挂出来', '让大家看看'
]

def analyze_sentiment(content: str) -> Dict:
    """分析情绪倾向"""
    sentiment_counts = {
        'positive': 0,
        'negative': 0,
        'crisis': 0
    }
    
    # 统计各类情绪词
    for sentiment, words in SENTIMENT_WORDS.items():
        for word in words:
            sentiment_counts[sentiment] += content.count(word)
    
    # 判断主情绪
    if sentiment_counts['crisis'] > 0:
        main_sentiment = 'crisis'
    elif sentiment_counts['negative'] > sentiment_counts['positive']:
        main_sentiment = 'negative'
    elif sentiment_counts['positive'] > sentiment_counts['negative']:
        main_sentiment = 'positive'
    else:
        main_sentiment = 'neutral'
    
    return {
        'sentiment': main_sentiment,
        'sentiment_label': {
            'positive': '正向',
            'negative': '负向',
            'crisis': '危机',
            'neutral': '中性'
        }[main_sentiment],
        'scores': sentiment_counts
    }

def assess_risk(content: str, sentiment: Dict, engagement: Dict = None) -> Dict:
    """评估风险等级"""
    risk_score = 0
    
    # 根据情绪评分
    if sentiment['sentiment'] == 'negative':
        risk_score += 1
    elif sentiment['sentiment'] == 'crisis':
        risk_score += 2
    
    # 检查危机关键词
    crisis_count = sum(1 for word in CRISIS_KEYWORDS if word in content)
    risk_score += crisis_count
    
    # 检查扩散风险
    spread_count = sum(1 for word in SPREAD_KEYWORDS if word in content)
    risk_score += spread_count * 2
    
    # 考虑互动数据
    if engagement:
        comments = engagement.get('comments', 0)
        shares = engagement.get('shares', 0)
        likes = engagement.get('likes', 0)
        
        if comments > 100 or shares > 50 or likes > 500:
            risk_score += 1
        
        if comments > 500 or shares > 200 or likes > 2000:
            risk_score += 1
    
    # 确定风险等级
    if risk_score >= 5:
        level = 'critical'
    elif risk_score >= 3:
        level = 'high'
    elif risk_score >= 2:
        level = 'medium'
    else:
        level = 'low'
    
    return RISK_LEVELS[level]

def extract_themes(content: str, brand_words: List[str] = None) -> List[str]:
    """提取舆情主题"""
    themes = []
    
    # 预设主题关键词
    theme_keywords = {
        'quality': ['质量', '材质', '做工', '品质', '坏', '烂'],
        'service': ['服务', '客服', '态度', '售后', '客服态度'],
        'logistics': ['物流', '快递', '发货', '运输', '到货'],
        'price': ['价格', '贵', '便宜', '性价比', '优惠'],
        'product_mismatch': ['不符', '错发', '型号', '规格', '不是'],
        'false_advertising': ['虚假', '夸大', '骗人', '误导']
    }
    
    for theme, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in content:
                themes.append(theme)
                break
    
    # 添加品牌相关主题
    if brand_words:
        for word in brand_words:
            if word in content:
                themes.append(f'brand_{word}')
    
    return list(set(themes)) if themes else ['other']

def generate_alert_summary(content: str, sentiment: Dict, risk: Dict, themes: List[str]) -> str:
    """生成告警摘要"""
    summary_parts = [
        f"【舆情告警】",
        f"情绪类型: {sentiment['sentiment_label']}",
        f"风险等级: {risk['description']}",
        f"涉及主题: {', '.join(themes)}",
        f"原文摘要: {content[:50]}..."
    ]
    
    return ' '.join(summary_parts)

def generate_response(recommendations: str, risk_level: str) -> str:
    """生成回复建议"""
    responses = {
        'low': '感谢您的反馈，我们会持续改进。如有问题请联系客服。',
        'medium': '非常抱歉给您带来不好的体验，我们已记录您的反馈，会尽快处理。',
        'high': '非常重视您的反馈，我们的客服团队会在24小时内联系您处理。',
        'critical': '我们已收到您的反馈，相关负责人正在紧急处理，请保持电话畅通。'
    }
    
    return responses.get(risk_level, responses['medium'])

def suggest_escalation(risk_level: str, themes: List[str]) -> Dict:
    """建议升级路径"""
    escalation_map = {
        'low': {
            'owner': '客服',
            'action': '常规回复',
            'timeline': '24小时'
        },
        'medium': {
            'owner': '运营',
            'action': '重点关注',
            'timeline': '12小时'
        },
        'high': {
            'owner': '高级运营',
            'action': '紧急处理',
            'timeline': '4小时'
        },
        'critical': {
            'owner': '公关团队',
            'action': '危机响应',
            'timeline': '1小时'
        }
    }
    
    return escalation_map.get(risk_level, escalation_map['medium'])

def monitor_opinion(input_data: Dict) -> Dict:
    """舆情监控主流程：情感分析→主题提取→风险评估→告警→升级路径→回复建议"""

    """监控舆情"""
    # 校验必要字段
    if 'content' not in input_data or not input_data.get('content'):
        return {
            'error': '缺少评论内容',
            'missing_fields': ['content']
        }
    
    content = input_data['content']
    platform = input_data.get('platform', 'unknown')
    brand_words = input_data.get('brand_words', [])
    engagement = input_data.get('engagement', {})
    
    # 1. 分析情绪
    sentiment = analyze_sentiment(content)
    
    # 2. 提取主题
    themes = extract_themes(content, brand_words)
    
    # 3. 评估风险
    risk = assess_risk(content, sentiment, engagement)
    
    # 4. 生成告警摘要
    alert_summary = generate_alert_summary(content, sentiment, risk, themes)
    
    # 5. 建议升级路径
    escalation = suggest_escalation(list(RISK_LEVELS.keys())[list(RISK_LEVELS.values()).index(risk)], themes)
    
    # 6. 生成回复建议
    response = generate_response('', list(RISK_LEVELS.keys())[list(RISK_LEVELS.values()).index(risk)])
    
    # 7. 判断是否需要人工介入
    needs_human_review = risk['score'] >= 2  # 高风险和严重风险需要人工
    
    return {
        'platform': platform,
        'content_summary': content[:100] + '...' if len(content) > 100 else content,
        'sentiment': sentiment,
        'themes': themes,
        'theme_labels': [
            {'quality': '质量问题', 'service': '服务问题', 'logistics': '物流问题',
             'price': '价格问题', 'product_mismatch': '商品不符',
             'false_advertising': '虚假宣传', 'other': '其他'}[theme.split('_')[0] if '_' in theme else theme]
            for theme in themes
        ],
        'risk_assessment': {
            'level': list(RISK_LEVELS.keys())[list(RISK_LEVELS.values()).index(risk)],
            'description': risk['description'],
            'action': risk['action'],
            'score': risk['score']
        },
        'alert_summary': alert_summary,
        'escalation': escalation,
        'suggested_response': response,
        'needs_human_review': needs_human_review,
        'review_reason': f"{risk['description']}需要人工处理" if needs_human_review else ''
    }

def main():
    """主入口函数"""
    # 读取输入
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()
    
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        print(json.dumps({'error': '无效的JSON输入'}))
        return
    
    # 监控舆情
    result = monitor_opinion(input_data)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()