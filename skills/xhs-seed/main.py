#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

PLATFORM_RULES = {
    'title_max_length': 20,
    'content_max_length': 1000,
    'image_count_range': (4, 9),
    'hashtag_max': 10,
    'forbidden_words': [
        '最', '顶级', '第一', '唯一', '国家级', '世界级',
        '治疗', '治愈', '防癌', '抗癌', '特效', '神奇',
        '微信', 'vx', 'wechat', '二维码', '加我', '私聊',
        '代购', '假货', '高仿', 'A货', '1:1',
    ],
    'sensitive_patterns': [
        r'微信号|加微信|加我微信',
        r'vx|v\.x|v-x',
        r'wechat|weixin',
        r'二维码|扫码|长按识别',
        r'私聊|私信我|加我',
        r'\d{3,}[\s\-]*\d{4,}[\s\-]*\d{3,}',
        r'转账|支付宝|收款|付款',
    ],
}

NOTE_TEMPLATES = {
    'product': {
        'description': '产品种草笔记',
        'structure': ['痛点引入', '产品展示', '使用体验', '效果对比', '购买建议'],
        'engagement_score': 0.65,
        'best_post_time': ['12:00', '18:00', '21:00'],
    },
    'scene': {
        'description': '场景种草笔记',
        'structure': ['场景描述', '问题提出', '解决方案', '效果展示', '总结推荐'],
        'engagement_score': 0.72,
        'best_post_time': ['08:00', '12:00', '20:00'],
    },
    'review': {
        'description': '测评笔记',
        'structure': ['产品介绍', '测试过程', '结果分析', '优缺点总结', '购买建议'],
        'engagement_score': 0.78,
        'best_post_time': ['10:00', '14:00', '21:00'],
    },
    'haul': {
        'description': '开箱/购物分享',
        'structure': ['开箱展示', '好物推荐', '避坑提醒', '购买渠道', '互动提问'],
        'engagement_score': 0.70,
        'best_post_time': ['12:00', '19:00', '22:00'],
    },
    'tutorial': {
        'description': '教程/攻略笔记',
        'structure': ['问题引入', '步骤详解', '效果展示', '小贴士', '互动引导'],
        'engagement_score': 0.82,
        'best_post_time': ['09:00', '13:00', '20:00'],
    },
    'comparison': {
        'description': '对比评测笔记',
        'structure': ['选品背景', '对比维度', '详细对比', '结论推荐', '互动讨论'],
        'engagement_score': 0.85,
        'best_post_time': ['10:00', '15:00', '21:00'],
    },
}

TONE_STYLES = {
    'casual': {
        'prefix': '姐妹们',
        'suffix': '冲就完事了！',
        'words': ['绝绝子', 'yyds', '爱了爱了', '谁懂啊', '真的绝', '好家伙', '救命'],
        'emoji_density': 'high',
    },
    'professional': {
        'prefix': '分享一个',
        'suffix': '值得入手~',
        'words': ['亲测有效', '强烈推荐', '性价比高', '品质保证', '实测数据'],
        'emoji_density': 'low',
    },
    'humorous': {
        'prefix': '家人们谁懂啊',
        'suffix': '笑不活了哈哈哈',
        'words': ['救命', '笑死', '离谱', '绝了', '蚌埠住了', '破防了'],
        'emoji_density': 'medium',
    },
    'gentle': {
        'prefix': '嗨~',
        'suffix': '希望对你们有帮助呀💕',
        'words': ['好温柔', '太治愈了', '幸福感满满', '心动', '安利'],
        'emoji_density': 'medium',
    },
}

VIRAL_TEMPLATES = [
    {
        "id": "pain_point_hook",
        "name": "痛点钩子型",
        "pattern": "痛点→共鸣→解决方案→效果→号召",
        "example_hook": "有没有{audience}和我一样{pain_point}？",
        "engagement_rate": 0.75,
    },
    {
        "id": "before_after",
        "name": "前后对比型",
        "pattern": "Before→After→方法→细节→互动",
        "example_hook": "用了{product}一个月，变化也太大了吧！",
        "engagement_rate": 0.82,
    },
    {
        "id": "secret_share",
        "name": "秘密分享型",
        "pattern": "悬念→揭秘→详细→效果→号召",
        "example_hook": "终于知道为什么{audience}都{result}了！",
        "engagement_rate": 0.70,
    },
    {
        "id": "list_countdown",
        "name": "清单倒计时型",
        "pattern": "清单→逐个展开→总结→互动",
        "example_hook": "{n}个让{audience}生活品质飙升的好物！",
        "engagement_rate": 0.68,
    },
    {
        "id": "story_telling",
        "name": "故事叙述型",
        "pattern": "起因→经过→转折→结果→感悟",
        "example_hook": "上个月{event}，没想到{result}...",
        "engagement_rate": 0.73,
    },
]

TREND_KEYWORDS = {
    'beauty': ['早C晚A', '刷酸', '抗老', '敏感肌', '成分党', '平价替代', '国货之光'],
    'fashion': ['穿搭公式', '显瘦', '小个子', '通勤', '氛围感', '老钱风', '多巴胺'],
    'food': ['减脂餐', '空气炸锅', '一人食', '懒人料理', '低卡', '代餐', '养生'],
    'home': ['极简', '收纳', '租房改造', '桌面布置', '小户型', 'ins风', '治愈系'],
    'fitness': ['居家运动', '帕梅拉', '拉伸', '体态矫正', '马甲线', '减脂', '增肌'],
    'digital': ['桌面搭子', '效率工具', '学生党', '平价好物', '办公神器', '降噪'],
}

ENGAGEMENT_PREDICTION_FACTORS = {
    'title_score': 0.25,
    'content_score': 0.20,
    'image_score': 0.20,
    'timing_score': 0.15,
    'hashtag_score': 0.10,
    'interaction_score': 0.10,
}

XHS_KNOWLEDGE_BASE = [
    {
        "id": "xhs_algorithm",
        "category": "platform_rules",
        "title": "小红书推荐算法机制",
        "content": "小红书推荐算法：1) CES评分=点赞×1+收藏×1+评论×4+转发×4+关注×8；2) 初始流量池约200-500曝光；3) 互动率>10%进入下一级流量池；4) 收藏率>5%持续推荐；5) 发布后2小时是黄金期；6) 笔记权重：原创>搬运，图文>纯文",
    },
    {
        "id": "xhs_title_formula",
        "category": "content_strategy",
        "title": "小红书爆款标题公式",
        "content": "爆款标题公式：1) 数字+好处：'7天见效的XX方法'；2) 痛点+解决：'终于解决了XX问题'；3) 身份+场景：'学生党必看的XX'；4) 对比+反差：'从XX到XX只用了一步'；5) 好奇+悬念：'原来XX才是关键'；6) 清单+数字：'XX必入的5件好物'",
    },
    {
        "id": "xhs_content_calendar",
        "category": "content_strategy",
        "title": "小红书内容日历规划",
        "content": "内容日历规划：1) 周一：干货教程类（搜索流量高）；2) 周三：好物种草类（消费决策期）；3) 周五：生活方式类（周末消费）；4) 周日：互动话题类（用户活跃高峰）；5) 节假日提前7天布局相关内容；6) 每月1-2个系列话题提升账号权重",
    },
    {
        "id": "xhs_compliance",
        "category": "compliance",
        "title": "小红书内容合规红线",
        "content": "合规红线：1) 禁止导流：微信号/二维码/外链；2) 禁止医疗宣称：治疗效果/处方建议；3) 禁止极限词：最好/第一/唯一；4) 禁止虚假种草：未使用推荐/夸大效果；5) 禁止价格误导：虚假原价/虚假折扣；6) 美妆需标注是否广告合作",
    },
]


def validate_input(input_data: Dict) -> Dict:
    errors = []
    warnings = []
    if not input_data.get('product_name'):
        errors.append('product_name')
    if not input_data.get('selling_points') and not input_data.get('features'):
        warnings.append('selling_points or features')
    return {"errors": errors, "warnings": warnings}


def predict_engagement(title: str, content: str, note_type: str, post_time: str = "",
                       hashtags: List[str] = None, image_count: int = 4) -> Dict:
    factors = ENGAGEMENT_PREDICTION_FACTORS

    title_score = 0.5
    if any(kw in title for kw in ['必入', '绝了', 'yyds', '谁懂', '救命', '挖到宝']):
        title_score = 0.85
    elif any(kw in title for kw in ['推荐', '分享', '测评']):
        title_score = 0.65
    if len(title) > 5 and len(title) <= PLATFORM_RULES['title_max_length']:
        title_score += 0.1
    title_score = min(1.0, title_score)

    content_score = 0.5
    content_len = len(content)
    if 300 <= content_len <= 800:
        content_score = 0.8
    elif 200 <= content_len <= 1000:
        content_score = 0.6
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF✨💡🔥💕🌟]', content))
    if 3 <= emoji_count <= 10:
        content_score += 0.1
    content_score = min(1.0, content_score)

    image_score = 0.5
    min_img, max_img = PLATFORM_RULES['image_count_range']
    if min_img <= image_count <= max_img:
        image_score = 0.85
    elif image_count >= 3:
        image_score = 0.6

    timing_score = 0.5
    template = NOTE_TEMPLATES.get(note_type, NOTE_TEMPLATES['product'])
    best_times = template.get('best_post_time', ['12:00', '18:00', '21:00'])
    if post_time:
        for bt in best_times:
            if abs(int(post_time[:2]) - int(bt[:2])) <= 1:
                timing_score = 0.9
                break
    else:
        timing_score = 0.7

    hashtag_score = 0.5
    if hashtags and 3 <= len(hashtags) <= 8:
        hashtag_score = 0.8
    elif hashtags and len(hashtags) > 0:
        hashtag_score = 0.6

    interaction_score = 0.5
    if any(kw in content for kw in ['评论区', '留言', '你们觉得', '你们呢', '一起']):
        interaction_score = 0.85

    total_score = (
        title_score * factors['title_score'] +
        content_score * factors['content_score'] +
        image_score * factors['image_score'] +
        timing_score * factors['timing_score'] +
        hashtag_score * factors['hashtag_score'] +
        interaction_score * factors['interaction_score']
    )

    if total_score >= 0.75:
        level = "high"
        expected_likes = "500+"
        expected_collects = "200+"
    elif total_score >= 0.55:
        level = "medium"
        expected_likes = "100-500"
        expected_collects = "50-200"
    else:
        level = "low"
        expected_likes = "<100"
        expected_collects = "<50"

    return {
        "totalScore": round(total_score, 3),
        "level": level,
        "expectedLikes": expected_likes,
        "expectedCollects": expected_collects,
        "factors": {
            "title": round(title_score, 2),
            "content": round(content_score, 2),
            "image": round(image_score, 2),
            "timing": round(timing_score, 2),
            "hashtag": round(hashtag_score, 2),
            "interaction": round(interaction_score, 2),
        },
        "improvementTips": _generate_engagement_tips(title_score, content_score, image_score, timing_score, interaction_score),
    }


def _generate_engagement_tips(title: float, content: float, image: float, timing: float, interaction: float) -> List[str]:
    tips = []
    if title < 0.7:
        tips.append("标题缺乏吸引力，建议使用数字+好处或痛点+解决公式")
    if content < 0.7:
        tips.append("正文长度建议控制在300-800字，适当添加emoji增加可读性")
    if image < 0.7:
        tips.append("建议配4-9张高质量图片，首图决定点击率")
    if timing < 0.7:
        tips.append("建议在12:00/18:00/21:00前后发布，覆盖用户活跃高峰")
    if interaction < 0.7:
        tips.append("结尾增加互动引导，如'你们还有什么好方法？评论区告诉我！'")
    return tips


def generate_content_calendar(product_name: str, category: str, selling_points: List[str],
                               weeks: int = 4) -> Dict:
    calendar = []
    content_types = list(NOTE_TEMPLATES.keys())
    base_date = datetime.now()

    weekly_plan = [
        {"day": "周一", "type": "tutorial", "focus": "干货教程"},
        {"day": "周二", "type": "product", "focus": "好物种草"},
        {"day": "周三", "type": "comparison", "focus": "对比评测"},
        {"day": "周四", "type": "scene", "focus": "场景种草"},
        {"day": "周五", "type": "haul", "focus": "购物分享"},
        {"day": "周六", "type": "review", "focus": "深度测评"},
        {"day": "周日", "type": "product", "focus": "互动话题"},
    ]

    for week in range(weeks):
        week_start = base_date + timedelta(weeks=week)
        for day_plan in weekly_plan:
            day_offset = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"].index(day_plan["day"])
            post_date = week_start + timedelta(days=(week_start.weekday() - day_offset) % 7 + week * 7)
            template = NOTE_TEMPLATES[day_plan["type"]]
            best_time = template["best_post_time"][0]

            sp_idx = (week * 7 + day_offset) % max(len(selling_points), 1)
            sp = selling_points[sp_idx] if selling_points else product_name

            calendar.append({
                "date": post_date.strftime("%Y-%m-%d"),
                "day": day_plan["day"],
                "type": day_plan["type"],
                "typeName": template["description"],
                "focus": day_plan["focus"],
                "suggestedTopic": f"{sp}·{day_plan['focus']}",
                "bestPostTime": best_time,
                "structure": template["structure"],
                "week": week + 1,
            })

    return {
        "productName": product_name,
        "category": category,
        "totalDays": len(calendar),
        "weeks": weeks,
        "calendar": calendar,
    }


def generate_trend_analysis(category: str, product_name: str) -> Dict:
    category_trends = TREND_KEYWORDS.get(category, [])
    hot_keywords = category_trends[:5] if category_trends else []

    seasonal_keywords = []
    current_month = datetime.now().month
    if current_month in [3, 4, 5]:
        seasonal_keywords = ['春季', '换季', '春夏', '轻薄', '透气']
    elif current_month in [6, 7, 8]:
        seasonal_keywords = ['夏季', '防晒', '清凉', '冰丝', '透气']
    elif current_month in [9, 10, 11]:
        seasonal_keywords = ['秋季', '换季', '秋冬', '保暖', '叠穿']
    else:
        seasonal_keywords = ['冬季', '保暖', '过年', '年货', '送礼']

    content_angles = []
    for kw in hot_keywords[:3]:
        content_angles.append({
            "keyword": kw,
            "angle": f"{product_name}+{kw}组合种草",
            "estimatedCompetition": "medium",
            "suggestedFormat": "comparison" if '对比' in kw or '替代' in kw else "product",
        })

    return {
        "category": category,
        "hotKeywords": hot_keywords,
        "seasonalKeywords": seasonal_keywords,
        "contentAngles": content_angles,
        "trendScore": round(len(hot_keywords) / 7 * 100, 1),
        "recommendation": f"当前{category}赛道热度{'较高' if len(hot_keywords) >= 4 else '一般'}，建议结合{hot_keywords[0] if hot_keywords else '日常'}话题创作",
    }


def generate_titles(product_name: str, selling_points: List[str], audience: str,
                    note_type: str = "product", tone: str = "casual") -> Dict:
    titles = []
    style = TONE_STYLES.get(tone, TONE_STYLES['casual'])

    viral_hooks = []
    for vt in VIRAL_TEMPLATES:
        hook = vt["example_hook"].replace("{audience}", audience).replace("{product}", product_name)
        if selling_points:
            hook = hook.replace("{pain_point}", selling_points[0]).replace("{result}", selling_points[0])
        viral_hooks.append({"template": vt["name"], "hook": hook, "engagementRate": vt["engagement_rate"]})

    title_formulas = [
        (f"{selling_points[0]}！{product_name}真的绝了" if selling_points else f"{product_name}真的绝了！", "痛点型"),
        (f"{audience}必入！{product_name}使用心得", "身份型"),
        (f"用了{product_name}一个月，变化太大了", "前后对比型"),
        (f"终于找到适合{audience}的{product_name}了", "解决型"),
        (f"{selling_points[0]}！{product_name}yyds" if selling_points else f"{product_name}yyds", "情感型"),
        (f"挖到宝了！{product_name}{selling_points[0]}" if selling_points else f"挖到宝了！{product_name}", "发现型"),
        (f"{product_name}测评｜{audience}真实分享", "测评型"),
        (f"后悔没早买！{product_name}{selling_points[0] if selling_points else ''}", "后悔型"),
    ]

    for title_text, formula_type in title_formulas:
        truncated = title_text[:PLATFORM_RULES['title_max_length']]
        titles.append({"title": truncated, "formula": formula_type, "length": len(truncated)})

    return {
        "titles": titles[:6],
        "viralHooks": viral_hooks,
        "recommendedFormula": max(viral_hooks, key=lambda x: x["engagementRate"])["template"],
    }


def generate_hashtags(product_name: str, category: str, selling_points: List[str]) -> Dict:
    tags = []
    tags.append(f"#{product_name.replace(' ', '')}")
    if category:
        tags.append(f"#{category}")
    for sp in selling_points[:3]:
        tag = sp.replace(' ', '')[:8]
        if tag and f"#{tag}" not in tags:
            tags.append(f"#{tag}")
    category_trends = TREND_KEYWORDS.get(category, [])
    for trend in category_trends[:3]:
        if f"#{trend}" not in tags:
            tags.append(f"#{trend}")
    tags.append("#好物分享")
    tags.append("#种草")

    unique_tags = list(dict.fromkeys(tags))[:PLATFORM_RULES['hashtag_max']]

    return {
        "hashtags": unique_tags,
        "count": len(unique_tags),
        "maxCount": PLATFORM_RULES['hashtag_max'],
        "strategy": "核心词+类目词+趋势词+通用词组合",
    }


def generate_content(product_name: str, selling_points: List[str], features: List[str],
                     note_type: str, tone: str, audience: str = "") -> Dict:
    style = TONE_STYLES.get(tone, TONE_STYLES['casual'])
    template = NOTE_TEMPLATES.get(note_type, NOTE_TEMPLATES['product'])

    sections = {}
    if note_type == 'product':
        sections["hook"] = f"{style['prefix']}！我不允许还有人不知道这个{selling_points[0] if selling_points else product_name}的好物！"
        sections["pain_point"] = f"之前一直被{selling_points[0] if selling_points else '这个问题'}困扰，直到发现了{product_name}！"
        sections["experience"] = f"用了{style['words'][0]}！{features[0] if features else '整体体验'}都很不错"
        sections["detail"] = '\n'.join([f"  ✅ {sp}" for sp in selling_points[:5]])
        sections["recommend"] = f"推荐给所有{audience or style['prefix']}，真的值得入手！{style['suffix']}"
    elif note_type == 'tutorial':
        sections["hook"] = f"今天教大家如何用{product_name}解决{selling_points[0] if selling_points else '日常问题'}！"
        sections["steps"] = '\n'.join([f"Step {i + 1}: {sp}" for i, sp in enumerate(selling_points[:5])])
        sections["tips"] = f"小贴士：{features[0] if features else '坚持使用效果更好'}"
        sections["result"] = f"按照这个方法，{style['words'][0]}！效果立竿见影"
        sections["interaction"] = "你们还有什么好方法？评论区告诉我！"
    elif note_type == 'comparison':
        sections["hook"] = f"{product_name}到底值不值得买？{audience or '大家'}看完就知道了！"
        sections["pros"] = '\n'.join([f"  ✅ {sp}" for sp in selling_points[:3]])
        sections["cons"] = "  ⚠️ 价格略高（但物有所值）"
        sections["verdict"] = f"综合来看，{style['words'][0]}！推荐指数⭐⭐⭐⭐⭐"
        sections["interaction"] = "你们觉得呢？评论区聊聊～"
    elif note_type == 'scene':
        sections["hook"] = f"{'居家办公' if not audience else audience}必备好物！{product_name}太香了"
        sections["scene"] = f"最近发现{product_name}真的{style['words'][0]}，特别适合{selling_points[0] if selling_points else '日常使用'}"
        sections["highlight"] = '\n'.join([f"  🌟 {sp}" for sp in selling_points[:3]])
        sections["recommend"] = f"喜欢的{audience or '姐妹'}可以冲！{style['suffix']}"
    else:
        sections["hook"] = f"最近入手了{product_name}，来跟大家分享！"
        sections["content"] = '\n'.join([f"  · {sp}" for sp in selling_points[:5]])
        sections["recommend"] = f"总体推荐！{style['suffix']}"

    full_content = '\n\n'.join(sections.values())

    return {
        "sections": sections,
        "fullContent": full_content,
        "totalLength": len(full_content),
        "maxLength": PLATFORM_RULES['content_max_length'],
        "structure": template["structure"],
    }


def compliance_check(content: str, titles: List[Dict]) -> Dict:
    issues = []
    severity_map = {"high": [], "medium": [], "low": []}

    for word in PLATFORM_RULES['forbidden_words']:
        if word in content:
            issue = f"正文包含禁用词: {word}"
            issues.append(issue)
            severity_map["high"].append(issue)
        for t in titles:
            if word in t.get("title", ""):
                issue = f"标题包含禁用词: {word}"
                issues.append(issue)
                severity_map["high"].append(issue)

    for pattern in PLATFORM_RULES['sensitive_patterns']:
        if re.search(pattern, content, re.IGNORECASE):
            issue = "正文包含敏感引流内容"
            issues.append(issue)
            severity_map["high"].append(issue)
            break

    if len(content) > PLATFORM_RULES['content_max_length']:
        issue = f"正文长度超出限制: {len(content)}/{PLATFORM_RULES['content_max_length']}"
        issues.append(issue)
        severity_map["medium"].append(issue)

    return {
        "passed": len(severity_map["high"]) == 0,
        "issues": issues,
        "severity": severity_map,
        "highCount": len(severity_map["high"]),
        "mediumCount": len(severity_map["medium"]),
    }


def generate_xhs_note(input_data: Dict) -> Dict:
    validation = validate_input(input_data)
    if validation["errors"]:
        return {"error": "输入不完整", "missing_fields": validation["errors"], "warnings": validation["warnings"]}

    product_name = input_data['product_name']
    selling_points = input_data.get('selling_points', [])
    features = input_data.get('features', [])
    category = input_data.get('category', 'home')
    audience = input_data.get('target_audience', '姐妹们')
    note_type = input_data.get('note_type', 'product')
    tone = input_data.get('tone', 'casual')
    post_time = input_data.get('post_time', '')
    image_count = input_data.get('image_count', 6)

    title_result = generate_titles(product_name, selling_points, audience, note_type, tone)
    content_result = generate_content(product_name, selling_points, features, note_type, tone, audience)
    hashtag_result = generate_hashtags(product_name, category, selling_points)
    trend_result = generate_trend_analysis(category, product_name)

    compliance = compliance_check(content_result["fullContent"], title_result["titles"])

    engagement = predict_engagement(
        title_result["titles"][0]["title"] if title_result["titles"] else "",
        content_result["fullContent"],
        note_type,
        post_time,
        hashtag_result["hashtags"],
        image_count,
    )

    calendar = None
    if input_data.get('generate_calendar'):
        calendar = generate_content_calendar(product_name, category, selling_points, weeks=4)

    needs_human = compliance["highCount"] > 0 or engagement["totalScore"] < 0.4
    reason = ""
    if compliance["highCount"] > 0:
        reason = f"存在{compliance['highCount']}个高风险合规问题"
    elif engagement["totalScore"] < 0.4:
        reason = f"互动预测分数仅{engagement['totalScore']:.0%}，建议优化内容"

    confidence = 100.0
    if compliance["highCount"] > 0:
        confidence -= compliance["highCount"] * 25
    if compliance["mediumCount"] > 0:
        confidence -= compliance["mediumCount"] * 10
    if engagement["totalScore"] < 0.5:
        confidence -= 20
    if not selling_points:
        confidence -= 15
    confidence = max(0, min(100, confidence))

    return {
        "platform": "xiaohongshu",
        "noteType": NOTE_TEMPLATES.get(note_type, {}).get('description', note_type),
        "targetAudience": audience,
        "titles": title_result["titles"],
        "viralHooks": title_result["viralHooks"],
        "recommendedFormula": title_result["recommendedFormula"],
        "content": content_result["sections"],
        "fullContent": content_result["fullContent"],
        "contentMeta": {
            "length": content_result["totalLength"],
            "maxLength": content_result["maxLength"],
            "structure": content_result["structure"],
        },
        "hashtags": hashtag_result["hashtags"],
        "hashtagMeta": {
            "count": hashtag_result["count"],
            "maxCount": hashtag_result["maxCount"],
            "strategy": hashtag_result["strategy"],
        },
        "imageSuggestions": [
            f"{product_name}产品首图（场景化展示）",
            f"{selling_points[0]}细节特写" if selling_points else "产品细节特写",
            f"{product_name}使用场景图",
            "Before/After对比图" if note_type in ('comparison', 'review') else "效果展示图",
            f"{product_name}与同类产品对比" if note_type == 'comparison' else "生活方式图",
        ][:image_count],
        "engagementPrediction": engagement,
        "trendAnalysis": trend_result,
        "compliance": compliance,
        "calendar": calendar,
        "handoff": {
            "needsHumanReview": needs_human,
            "reason": reason,
            "confidence": round(confidence, 1),
            "gate": "auto" if confidence >= 90 else ("notify" if confidence >= 60 else "human"),
        },
    }


def main():
    if len(sys.argv) > 1:
        input_json = sys.argv[1]
    else:
        input_json = sys.stdin.read()

    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        sys.stdout.buffer.write((json.dumps({'error': '无效的JSON输入'}, ensure_ascii=True) + "\n").encode("utf-8"))
        return

    result = generate_xhs_note(input_data)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))


if __name__ == '__main__':
    main()
