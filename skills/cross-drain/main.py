import json
import sys
from typing import Dict, List, Any

# 跨平台导流规则：各平台允许的导流方式、禁用词和最佳发布时间
PLATFORM_RULES = {
    "xiaohongshu": {
        "name": "小红书",
        "max_text_length": 1000,
        "allowed_links": ["微信", "公众号", "企业微信"],
        "forbidden_words": ["vx", "微信", "微", "私", "加我", "联系方式"],
        "drain_methods": ["评论区引导", "私信回复", "主页简介", "合集链接"],
        "best_time": ["10:00-12:00", "14:00-16:00", "20:00-22:00"]
    },
    "douyin": {
        "name": "抖音",
        "max_text_length": 1000,
        "allowed_links": ["抖音小店", "企业号主页", "团购链接"],
        "forbidden_words": ["vx", "微信", "私", "加我", "联系方式"],
        "drain_methods": ["评论区引导", "私信自动回复", "主页链接", "直播引流"],
        "best_time": ["11:00-13:00", "17:00-19:00", "20:00-23:00"]
    },
    "video-channel": {
        "name": "视频号",
        "max_text_length": 500,
        "allowed_links": ["微信小店", "小程序", "公众号"],
        "forbidden_words": ["vx", "加我", "私"],
        "drain_methods": ["评论区引导", "主页简介", "直播引流", "小程序跳转"],
        "best_time": ["12:00-14:00", "20:00-22:00"]
    },
    "kuaishou": {
        "name": "快手",
        "max_text_length": 1000,
        "allowed_links": ["快手小店", "直播间商品"],
        "forbidden_words": ["vx", "微信", "私", "加我"],
        "drain_methods": ["评论区引导", "私信回复", "主页链接", "直播引流"],
        "best_time": ["10:00-12:00", "18:00-21:00"]
    }
}

RESPONSE_TEMPLATES = {
    "xiaohongshu": {
        "comment": "戳我头像看更多干货~ 想要详细资料可以私信我哦",
        "profile": "✨ 专注分享实用干货\n📚 定期更新优质内容\n💬 欢迎私信交流",
        "auto_reply": "感谢关注！想要获取更多资料，请查看我的主页简介~"
    },
    "douyin": {
        "comment": "想看更多内容？点击我的头像进入主页~",
        "profile": "🎬 每天分享精彩内容\n❤️ 感谢你的关注\n👇 点击下方链接了解更多",
        "auto_reply": "感谢私信！详细资料已整理好，点击主页链接获取~"
    },
    "video-channel": {
        "comment": "点击主页查看更多精彩内容~",
        "profile": "✨ 每日更新\n📖 干货分享\n💡 欢迎交流",
        "auto_reply": "感谢关注！更多内容请点击主页~"
    },
    "kuaishou": {
        "comment": "双击关注，每天更新！",
        "profile": "🔥 精彩内容持续更新\n🎯 关注不迷路\n👇 点击下方了解更多",
        "auto_reply": "感谢私信！详细内容请查看主页~"
    }
}

def validate_input(input_data: Dict) -> List[str]:
    missing = []
    if "action" not in input_data:
        missing.append("action")
    return missing

def analyze_platform(platform: str) -> Dict:
    if platform not in PLATFORM_RULES:
        return {"error": f"未知平台: {platform}"}
    
    return {
        "platform": platform,
        "name": PLATFORM_RULES[platform]["name"],
        "rules": PLATFORM_RULES[platform]
    }

def generate_drain_strategy(platform: str, content_type: str = "product") -> Dict:
    if platform not in PLATFORM_RULES:
        return {"error": f"未知平台: {platform}"}
    
    rules = PLATFORM_RULES[platform]
    templates = RESPONSE_TEMPLATES[platform]
    
    strategy = {
        "platform": platform,
        "platform_name": rules["name"],
        "content_type": content_type,
        "drain_methods": rules["drain_methods"],
        "best_publish_time": rules["best_time"],
        "templates": templates,
        "compliance_notes": {
            "max_text_length": rules["max_text_length"],
            "allowed_links": rules["allowed_links"],
            "avoid_words": rules["forbidden_words"]
        }
    }
    
    return strategy

def generate_drain_content(platform: str, template_type: str, custom_text: str = "") -> Dict:
    if platform not in RESPONSE_TEMPLATES:
        return {"error": f"未知平台: {platform}"}
    
    if template_type not in RESPONSE_TEMPLATES[platform]:
        return {"error": f"未知模板类型: {template_type}"}
    
    base_content = RESPONSE_TEMPLATES[platform][template_type]
    
    if custom_text:
        content = f"{custom_text}\n\n{base_content}"
    else:
        content = base_content
    
    compliance = check_compliance(platform, content)
    
    return {
        "platform": platform,
        "template_type": template_type,
        "content": content,
        "compliance": compliance
    }

def check_compliance(platform: str, content: str) -> Dict:
    if platform not in PLATFORM_RULES:
        return {"status": "unknown", "message": "未知平台"}
    
    rules = PLATFORM_RULES[platform]
    violations = []
    
    if len(content) > rules["max_text_length"]:
        violations.append(f"文本长度超出限制({len(content)}/{rules['max_text_length']})")
    
    for forbidden in rules["forbidden_words"]:
        if forbidden in content:
            violations.append(f"包含敏感词: {forbidden}")
    
    if violations:
        return {
            "status": "warning",
            "violations": violations,
            "suggestion": "请修改内容以符合平台规则"
        }
    else:
        return {
            "status": "pass",
            "violations": [],
            "suggestion": "内容符合平台规则"
        }

def get_cross_platform_strategy(platforms: List[str], content_type: str = "product") -> Dict:
    """跨平台导流策略：为多个平台分别生成导流方案并聚合"""
    strategies = []
    for platform in platforms:
        if platform in PLATFORM_RULES:
            strategy = generate_drain_strategy(platform, content_type)
            strategies.append(strategy)
    
    return {
        "platforms": platforms,
        "content_type": content_type,
        "strategies": strategies,
        "total_platforms": len(strategies)
    }

def main():
    input_data = json.loads(sys.stdin.read())
    missing = validate_input(input_data)
    
    if missing:
        print(json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False))
        return
    
    action = input_data["action"]
    
    if action == "analyze_platform":
        platform = input_data.get("platform", "")
        result = analyze_platform(platform)
    
    elif action == "generate_strategy":
        platform = input_data.get("platform", "")
        content_type = input_data.get("content_type", "product")
        result = generate_drain_strategy(platform, content_type)
    
    elif action == "generate_content":
        platform = input_data.get("platform", "")
        template_type = input_data.get("template_type", "comment")
        custom_text = input_data.get("custom_text", "")
        result = generate_drain_content(platform, template_type, custom_text)
    
    elif action == "check_compliance":
        platform = input_data.get("platform", "")
        content = input_data.get("content", "")
        result = check_compliance(platform, content)
    
    elif action == "cross_platform_strategy":
        platforms = input_data.get("platforms", [])
        content_type = input_data.get("content_type", "product")
        result = get_cross_platform_strategy(platforms, content_type)
    
    else:
        result = {"error": "未知操作", "action": action}
    
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()