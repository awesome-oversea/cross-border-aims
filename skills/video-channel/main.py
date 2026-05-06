#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json

def validate_input(input_data):
    missing = []
    if not input_data.get("product") and not input_data.get("topic"):
        missing.append("product 或 topic")
    if not input_data.get("audience"):
        missing.append("audience")
    return missing

def generate_video_script(product, audience, duration=60):
    opening_hooks = [
        "家人们！今天发现一个宝藏好物！",
        "姐妹们快看！这个真的绝了！",
        "谁还没有这个？我真的会谢！",
        "挖到宝了！这个必须分享给你们！",
        "亲测有效！这个太好用了！"
    ]
    
    endings = [
        "喜欢的宝子们赶紧冲！",
        "点击下方链接立即购买！",
        "记得点赞关注哦！",
        "评论区告诉我你们的看法！",
        "下期想看什么评论告诉我！"
    ]
    
    hooks = {
        "young_female": opening_hooks[1],
        "young_male": opening_hooks[0],
        "middle_aged": "今天给大家推荐一个实用好物！",
        "general": opening_hooks[3]
    }
    
    structures = {
        "short": {
            "segments": [
                {"name": "开场", "duration": 3, "content": hooks.get(audience, opening_hooks[-1])},
                {"name": "产品展示", "duration": 15, "content": f"这就是我们今天的主角——{product}"},
                {"name": "核心卖点", "duration": 10, "content": "它最大的特点就是好用又实惠"},
                {"name": "使用演示", "duration": 10, "content": "让我给大家演示一下"},
                {"name": "收尾", "duration": 2, "content": endings[0]}
            ],
            "total_duration": 40
        },
        "medium": {
            "segments": [
                {"name": "开场", "duration": 5, "content": hooks.get(audience, opening_hooks[-1])},
                {"name": "痛点引入", "duration": 8, "content": "你是不是也有这样的困扰？"},
                {"name": "产品展示", "duration": 12, "content": f"别担心，{product}来帮你"},
                {"name": "核心卖点", "duration": 15, "content": "三大核心优势：好用、实惠、耐用"},
                {"name": "使用演示", "duration": 15, "content": "让我演示给大家看"},
                {"name": "用户评价", "duration": 10, "content": "看看其他用户怎么说"},
                {"name": "引导行动", "duration": 5, "content": endings[1]}
            ],
            "total_duration": 70
        },
        "long": {
            "segments": [
                {"name": "开场", "duration": 5, "content": hooks.get(audience, opening_hooks[-1])},
                {"name": "痛点引入", "duration": 10, "content": "分享一个困扰我很久的问题"},
                {"name": "产品展示", "duration": 15, "content": f"直到我遇到了{product}"},
                {"name": "核心卖点1", "duration": 12, "content": "首先它非常好用"},
                {"name": "核心卖点2", "duration": 12, "content": "其次价格非常实惠"},
                {"name": "核心卖点3", "duration": 12, "content": "最重要的是品质保证"},
                {"name": "深度演示", "duration": 20, "content": "详细使用教程"},
                {"name": "用户评价", "duration": 10, "content": "真实用户反馈"},
                {"name": "优惠信息", "duration": 8, "content": "现在购买有优惠"},
                {"name": "引导行动", "duration": 6, "content": endings[1]}
            ],
            "total_duration": 110
        }
    }
    
    if duration <= 45:
        return structures["short"]
    elif duration <= 90:
        return structures["medium"]
    else:
        return structures["long"]

def generate_title(product, audience):
    titles = {
        "young_female": [
            f"{product}真的绝了！姐妹们冲！",
            f"挖到宝藏{product}！爱了爱了",
            f"这个{product}也太好用了吧！"
        ],
        "young_male": [
            f"{product}实测！真的香！",
            f"发现一个好东西-{product}",
            f"{product}体验分享！"
        ],
        "middle_aged": [
            f"{product}推荐！实用好物",
            f"分享一个好东西-{product}",
            f"{product}使用体验"
        ],
        "general": [
            f"{product}开箱体验！",
            f"推荐一个好物-{product}",
            f"{product}值得入手吗？"
        ]
    }
    return titles.get(audience, titles["general"])

def check_compliance(content):
    violations = []
    sensitive_words = ["微信", "vx", "加我", "私我", "联系方式", "二维码", "微信号", "群"]
    
    for word in sensitive_words:
        if word in content:
            violations.append(f"包含导流敏感词: {word}")
    
    if len(content) > 5000:
        violations.append("内容过长，建议精简")
    
    return violations

def generate_distribution_suggestions(audience):
    suggestions = {
        "young_female": {
            "platforms": ["小红书", "抖音", "视频号"],
            "best_time": ["12:00-13:00", "18:00-22:00"],
            "tags": ["#好物推荐", "#女生必备", "#种草"]
        },
        "young_male": {
            "platforms": ["抖音", "B站", "视频号"],
            "best_time": ["12:00-13:00", "19:00-23:00"],
            "tags": ["#数码科技", "#好物分享", "#开箱"]
        },
        "middle_aged": {
            "platforms": ["视频号", "抖音"],
            "best_time": ["09:00-11:00", "15:00-17:00"],
            "tags": ["#实用好物", "#生活技巧", "#分享"]
        },
        "general": {
            "platforms": ["抖音", "视频号", "小红书"],
            "best_time": ["12:00-13:00", "18:00-21:00"],
            "tags": ["#好物推荐", "#分享", "#日常"]
        }
    }
    return suggestions.get(audience, suggestions["general"])

def main():
    try:
        input_data = json.loads(sys.stdin.read())
        
        missing = validate_input(input_data)
        if missing:
            sys.stdout.buffer.write((json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False) + "\n").encode('utf-8'))
            return
        
        product = input_data.get("product", "")
        topic = input_data.get("topic", "")
        audience = input_data.get("audience", "general")
        duration = int(input_data.get("duration", 60))
        style = input_data.get("style", "friendly")
        
        content_topic = product if product else topic
        
        script = generate_video_script(content_topic, audience, duration)
        titles = generate_title(content_topic, audience)
        violations = check_compliance(content_topic)
        distribution = generate_distribution_suggestions(audience)
        
        result = {
            "title_options": titles,
            "script": {
                "total_duration": script["total_duration"],
                "segments": script["segments"]
            },
            "style": style,
            "distribution_suggestions": {
                "platforms": distribution["platforms"],
                "best_publish_time": distribution["best_time"],
                "suggested_tags": distribution["tags"]
            },
            "social_interaction_points": [
                "引导点赞关注",
                "评论区互动提问",
                "转发给朋友",
                "点击购物车"
            ],
            "risk_warnings": violations if violations else ["无风险"],
            "compliance_check": "合规" if not violations else "需审核",
            "production_notes": [
                f"建议拍摄时长: {duration}秒",
                "准备产品实物展示",
                "添加字幕和背景音乐",
                "注意光线和画质"
            ]
        }
        
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True) + "\n").encode('utf-8'))
        
    except Exception as e:
        sys.stdout.buffer.write((json.dumps({"error": str(e)}, ensure_ascii=True) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()