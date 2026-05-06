#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from typing import Dict, List, Optional

# 平台规则配置
PLATFORM_CONFIG = {
    'amazon': {
        'image_sizes': ['1000x1000', '1500x1500'],
        'title_max_length': 200,
        'description_max_length': 2000,
        'style': 'professional',
        'forbidden_words': ['best', 'top', 'only', 'guarantee', 'perfect']
    },
    'taobao': {
        'image_sizes': ['800x800', '1200x1200'],
        'title_max_length': 60,
        'description_max_length': 5000,
        'style': 'salesy',
        'forbidden_words': ['最', '顶级', '第一', '唯一', '国家级']
    },
    'jd': {
        'image_sizes': ['800x800', '1000x1000'],
        'title_max_length': 100,
        'description_max_length': 10000,
        'style': 'trustworthy',
        'forbidden_words': ['最', '顶级', '第一', '唯一']
    },
    'xiaohongshu': {
        'image_sizes': ['3:4', '1:1'],
        'title_max_length': 20,
        'description_max_length': 1000,
        'style': 'lifestyle',
        'forbidden_words': ['最', '顶级', '第一', '唯一']
    },
    'douyin': {
        'image_sizes': ['9:16'],
        'title_max_length': 30,
        'description_max_length': 500,
        'style': 'vibrant',
        'forbidden_words': ['最', '顶级', '第一', '唯一']
    },
    'video号': {
        'image_sizes': ['9:16', '16:9'],
        'title_max_length': 30,
        'description_max_length': 500,
        'style': 'authentic',
        'forbidden_words': ['最', '顶级', '第一', '唯一']
    }
}

# 文案风格模板
STYLE_TEMPLATES = {
    'professional': {
        'prefix': 'Introducing',
        'suffix': 'Perfect for discerning customers.',
        'tone': 'formal'
    },
    'salesy': {
        'prefix': '限时特惠！',
        'suffix': '错过今天再等一年！',
        'tone': 'excited'
    },
    'trustworthy': {
        'prefix': '品质保证',
        'suffix': '京东自营，正品保障',
        'tone': 'reliable'
    },
    'lifestyle': {
        'prefix': '分享我的宝藏',
        'suffix': '姐妹们冲！',
        'tone': 'friendly'
    },
    'vibrant': {
        'prefix': '家人们谁懂啊',
        'suffix': '点击购物车下单！',
        'tone': 'energetic'
    },
    'authentic': {
        'prefix': '真实体验分享',
        'suffix': '推荐给有需要的朋友',
        'tone': 'sincere'
    }
}

# 素材类型配置
MATERIAL_TYPES = {
    'main_image': {
        'description': '主图',
        'focus': '核心卖点展示'
    },
    'sub_image': {
        'description': '副图',
        'focus': '细节展示、使用场景'
    },
    'detail_page': {
        'description': '详情页',
        'focus': '完整产品信息、使用说明'
    },
    'poster': {
        'description': '海报',
        'focus': '活动主题、促销信息'
    },
    'short_video': {
        'description': '短视频',
        'focus': '产品演示、使用体验'
    },
    'story': {
        'description': '故事/动态',
        'focus': '即时互动、限时活动'
    }
}

def validate_input(input_data: Dict) -> List[str]:
    """校验输入数据"""
    missing_fields = []
    required_fields = ['product_name', 'platform', 'material_type', 'audience']
    
    for field in required_fields:
        if field not in input_data or not input_data.get(field):
            missing_fields.append(field)
    
    return missing_fields

def generate_main_copy(product_name: str, selling_points: List[str], platform: str, style: str) -> str:
    """生成主文案"""
    template = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES['professional'])
    
    # 组合卖点
    points_text = ' '.join(selling_points[:3])
    
    if style == 'salesy':
        return f"{template['prefix']}{product_name} - {points_text} {template['suffix']}"
    elif style == 'lifestyle':
        return f"{template['prefix']}✨ {product_name}\n\n{points_text}\n\n{template['suffix']}"
    elif style == 'vibrant':
        return f"{template['prefix']}！{product_name}真的绝了！\n\n{points_text}\n\n{template['suffix']}"
    else:
        return f"{template['prefix']} {product_name}: {points_text}. {template['suffix']}"

def generate_alternative_titles(product_name: str, selling_points: List[str], platform: str) -> List[str]:
    """生成备选标题"""
    titles = []
    
    # 标题变体
    titles.append(f"{product_name} - {selling_points[0] if selling_points else ''}")
    titles.append(f"{product_name}：{selling_points[1] if len(selling_points) > 1 else selling_points[0] if selling_points else '品质之选'}")
    titles.append(f"为什么选择{product_name}？{selling_points[0] if selling_points else ''}")
    titles.append(f"{product_name}，{selling_points[2] if len(selling_points) > 2 else '值得拥有'}")
    
    # 根据平台规则截断
    config = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG['amazon'])
    return [title[:config['title_max_length']] for title in titles]

def generate_visual_description(product_name: str, selling_points: List[str], material_type: str, platform: str) -> str:
    """生成画面/镜头说明"""
    descriptions = []
    
    if material_type in ['main_image', 'poster']:
        descriptions.append(f"主体：{product_name}居中展示")
        if selling_points:
            descriptions.append(f"突出卖点：{selling_points[0]}")
        descriptions.append("背景简洁，突出产品质感")
        descriptions.append("光线充足，色彩鲜明")
    
    elif material_type == 'sub_image':
        descriptions.append(f"展示{product_name}细节")
        descriptions.append("使用场景展示")
        descriptions.append("尺寸对比（如有）")
        descriptions.append("材质纹理特写")
    
    elif material_type == 'detail_page':
        descriptions.append("产品全景图")
        descriptions.append("细节特写系列")
        descriptions.append("使用步骤演示")
        descriptions.append("用户评价展示")
    
    elif material_type == 'short_video':
        descriptions.append(f"开场：{product_name}展示")
        descriptions.append("产品使用演示")
        descriptions.append("核心卖点特写")
        descriptions.append("结尾CTA引导")
    
    return '\n'.join(descriptions)

def generate_cta(platform: str, goal: str = 'sales') -> str:
    """生成行动号召语"""
    cta_map = {
        'amazon': {
            'sales': '立即购买',
            'awareness': '了解更多'
        },
        'taobao': {
            'sales': '限时抢购',
            'awareness': '进店逛逛'
        },
        'jd': {
            'sales': '立即抢购',
            'awareness': '了解详情'
        },
        'xiaohongshu': {
            'sales': '点击购物车',
            'awareness': '关注获取更多'
        },
        'douyin': {
            'sales': '点击下方购物车',
            'awareness': '关注看更多'
        },
        'video号': {
            'sales': '立即购买',
            'awareness': '关注我们'
        }
    }
    
    return cta_map.get(platform, cta_map['amazon']).get(goal, '立即购买')

def compliance_check(copy: str, platform: str) -> Dict:
    """合规检查"""
    config = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG['amazon'])
    forbidden_words = config['forbidden_words']
    issues = []
    
    for word in forbidden_words:
        if word in copy:
            issues.append(f"文案包含禁用词: {word}")
    
    return {
        'passed': len(issues) == 0,
        'issues': issues
    }

def generate_material(input_data: Dict) -> Dict:
    """生成素材简报"""
    # 1. 校验输入
    missing_fields = validate_input(input_data)
    if missing_fields:
        return {
            'error': '输入不完整',
            'missing_fields': missing_fields
        }
    
    product_name = input_data['product_name']
    platform = input_data['platform']
    material_type = input_data['material_type']
    audience = input_data.get('audience', '')
    selling_points = input_data.get('selling_points', [])
    goal = input_data.get('goal', 'sales')
    
    # 获取平台配置
    config = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG['amazon'])
    style = config['style']
    
    # 2. 生成主文案
    main_copy = generate_main_copy(product_name, selling_points, platform, style)
    
    # 3. 生成备选标题
    alt_titles = generate_alternative_titles(product_name, selling_points, platform)
    
    # 4. 生成画面说明
    visual_desc = generate_visual_description(product_name, selling_points, material_type, platform)
    
    # 5. 生成CTA
    cta = generate_cta(platform, goal)
    
    # 6. 合规检查
    compliance = compliance_check(main_copy, platform)
    
    # 7. 判断是否需要人工确认
    needs_human_review = not compliance['passed'] or any(
        word in product_name for word in ['品牌', '授权', '明星', '医疗', '功效']
    )
    
    return {
        'material_objective': {
            'platform': platform,
            'material_type': MATERIAL_TYPES.get(material_type, {}).get('description', material_type),
            'target_audience': audience,
            'campaign_goal': goal
        },
        'platform_versions': [
            {
                'platform': platform,
                'image_sizes': config['image_sizes'],
                'copy_length': config['title_max_length']
            }
        ],
        'main_copy': main_copy,
        'alternative_titles': alt_titles,
        'visual_description': visual_desc,
        'cta': cta,
        'compliance': compliance,
        'risk_warnings': compliance['issues'],
        'needs_human_review': needs_human_review,
        'review_reason': '合规问题需人工审核' if not compliance['passed'] else '涉及敏感内容需人工确认'
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
    
    # 生成素材
    result = generate_material(input_data)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()