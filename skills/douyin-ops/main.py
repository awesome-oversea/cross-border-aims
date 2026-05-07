#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from typing import Dict, List, Optional

import importlib.util
try:
    _sp = importlib.util.spec_from_file_location("douyin-ops_dl", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..\data-layer\main.py"))
    if _sp and _sp.loader:
        _md = importlib.util.module_from_spec(_sp)
        sys.modules["douyin-ops_dl"] = _md
        _sp.loader.exec_module(_md)
        dou_dl_avail = True
    else:
        dou_dl_avail = False
except Exception:
    dou_dl_avail = False

def _store_do(title, txt, plat):
    if not dou_dl_avail:
        return
    try:
        from datetime import datetime as _dt
        _md.DataManager().insert_record("contents", {
            "content_id": f"gen-{_dt.now().strftime('%Y%m%d%H%M%S%f')}",
            "type": "post", "platform": plat,
            "title": (title or "")[:200], "content": (txt or "")[:2000],
            "tags": "[]", "status": "generated",
            "created_at": _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception:
        pass


# 抖音平台规则
# 抖音平台规则：时长选项/文本长度/禁用词/敏感引流模式
PLATFORM_RULES = {
    'duration_options': [15, 30, 60, 90],
    'max_text_length': 1000,
    'forbidden_words': ['最', '顶级', '第一', '唯一', '国家级', '世界级',
                       '治疗', '治愈', '防癌', '抗癌', '特效', '神奇',
                       '微信', 'vx', 'wechat', '二维码', '加我', '私聊',
                       '秒杀', '限量', '抢疯了', '售罄', '爆款'],
    'sensitive_patterns': [
        r'微信号|加微信|微信联系',
        r'vx|v\.x|v-x',
        r'wechat|weixin',
        r'二维码|扫码|长按识别',
        r'私聊|私信我|加我',
        r'\d{3,}[\s\-]*\d{4,}[\s\-]*\d{3,}',  # 电话号码
        r'\d+元|¥\d+'  # 价格（可能违规）
    ]
}

# 视频类型模板
# 视频类型模板：产品展示/直播切片/开箱/剧情/测评，含时长建议和分镜结构
VIDEO_TEMPLATES = {
    'product': {
        'description': '产品展示视频',
        'duration': 30,
        'structure': ['钩子(0-3s)', '产品展示(3-10s)', '卖点介绍(10-20s)', '使用演示(20-25s)', 'CTA(25-30s)']
    },
    'live_clip': {
        'description': '直播切片',
        'duration': 60,
        'structure': ['精彩片段开头', '产品讲解', '互动环节', '下单引导']
    },
    'unboxing': {
        'description': '开箱视频',
        'duration': 30,
        'structure': ['开箱惊喜', '产品展示', '细节特写', '使用感受', '推荐']
    },
    'skit': {
        'description': '剧情/场景视频',
        'duration': 15,
        'structure': ['冲突/问题', '解决方案', '产品植入', '结尾']
    },
    'review': {
        'description': '测评视频',
        'duration': 60,
        'structure': ['产品介绍', '测试过程', '结果展示', '优缺点分析', '购买建议']
    }
}

# 发布时间建议
# 最佳发布时间建议：早通勤/午休/下班/睡前
BEST_TIMES = {
    'morning': ['07:30-09:00', '通勤时间'],
    'noon': ['12:00-13:30', '午休时间'],
    'afternoon': ['17:00-19:00', '下班时间'],
    'evening': ['20:00-22:30', '睡前时间']
}

def validate_input(input_data: Dict) -> List[str]:
    """校验输入数据"""
    missing_fields = []
    required_fields = ['product_name', 'selling_points', 'duration', 'video_type']
    
    for field in required_fields:
        if field not in input_data or not input_data.get(field):
            missing_fields.append(field)
    
    return missing_fields

def generate_hook(product_name: str, selling_points: List[str]) -> str:
    """生成3秒钩子：通过抛出疑问/惊叹/警告快速抓住注意力"""

    """生成3秒钩子"""
    hooks = [
        f"家人们！这个{product_name}绝了！",
        f"没想到{product_name}这么好用！",
        f"谁还没买{product_name}？",
        f"{selling_points[0]}！{product_name}太香了！",
        f"警告！看完这个视频你会想买{product_name}！"
    ]
    
    return hooks[0]

def generate_script(product_name: str, selling_points: List[str], features: List[str],
                    video_type: str, duration: int) -> List[Dict]:
    """生成分镜脚本：按视频类型和时长选择模板，逐镜定义时间/景别/画面/台词"""

    """生成分镜脚本"""
    template = VIDEO_TEMPLATES.get(video_type, VIDEO_TEMPLATES['product'])
    script = []
    
    if video_type == 'product':
        # 15秒版本
        if duration <= 15:
            script = [
                {'time': '0-3s', 'shot': '特写', 'scene': f'{product_name}产品展示', 'line': f"家人们！这个{product_name}绝了！"},
                {'time': '3-8s', 'shot': '中景', 'scene': '产品细节', 'line': f"{selling_points[0]}，{selling_points[1] if len(selling_points) > 1 else '品质超好'}"},
                {'time': '8-12s', 'shot': '近景', 'scene': '使用演示', 'line': '用起来特别方便'},
                {'time': '12-15s', 'shot': '特写', 'scene': '产品+字幕', 'line': '点击购物车下单！'}
            ]
        # 30秒版本
        else:
            script = [
                {'time': '0-3s', 'shot': '特写', 'scene': f'{product_name}产品展示', 'line': f"家人们谁懂啊！这个{product_name}真的绝了！"},
                {'time': '3-10s', 'shot': '中景', 'scene': '产品细节展示', 'line': f"首先看这个外观，{selling_points[0]}，颜值超高！"},
                {'time': '10-18s', 'shot': '近景', 'scene': '核心功能演示', 'line': f"再看功能，{selling_points[1] if len(selling_points) > 1 else '性能超强'}，用起来特别顺手！"},
                {'time': '18-25s', 'shot': '全景', 'scene': '使用场景展示', 'line': f"不管是{features[0] if features else '日常使用'}还是{features[1] if len(features) > 1 else '工作学习'}都很合适！"},
                {'time': '25-30s', 'shot': '特写', 'scene': '产品+购物车图标', 'line': '喜欢的家人们点击下方购物车直接冲！'}
            ]
    
    elif video_type == 'live_clip':
        script = [
            {'time': '0-5s', 'shot': '特写', 'scene': '主播激动表情', 'line': '家人们！今天这个福利太炸了！'},
            {'time': '5-20s', 'shot': '中景', 'scene': '产品展示', 'line': f"就是这个{product_name}，{selling_points[0]}，{selling_points[1]}！"},
            {'time': '20-40s', 'shot': '近景', 'scene': '功能演示', 'line': '我给大家演示一下，真的特别好用！'},
            {'time': '40-55s', 'shot': '全景', 'scene': '主播与产品', 'line': '今天直播间特价，错过今天再等一年！'},
            {'time': '55-60s', 'shot': '特写', 'scene': '购物车+价格', 'line': '赶紧点击购物车下单！'}
        ]
    
    elif video_type == 'unboxing':
        script = [
            {'time': '0-3s', 'shot': '特写', 'scene': '快递盒', 'line': '今天来拆一个期待已久的包裹！'},
            {'time': '3-10s', 'shot': '中景', 'scene': '开箱过程', 'line': '哇！包装好精美！'},
            {'time': '10-18s', 'shot': '特写', 'scene': '产品展示', 'line': f"就是这个{product_name}，颜值太高了！"},
            {'time': '18-25s', 'shot': '近景', 'scene': '细节特写', 'line': f"{selling_points[0]}，做工特别精细！"},
            {'time': '25-30s', 'shot': '全景', 'scene': '产品使用', 'line': '喜欢的宝子们可以冲！'}
        ]
    
    elif video_type == 'skit':
        script = [
            {'time': '0-3s', 'shot': '中景', 'scene': '人物烦恼表情', 'line': '唉，这个问题真的烦死了！'},
            {'time': '3-8s', 'shot': '特写', 'scene': '拿出产品', 'line': '直到我遇到了它！'},
            {'time': '8-12s', 'shot': '近景', 'scene': '使用产品', 'line': f"{product_name}，{selling_points[0]}，太好用了！"},
            {'time': '12-15s', 'shot': '特写', 'scene': '满意表情', 'line': '早知道早买了！'}
        ]
    
    return script

def generate_captions(script: List[Dict]) -> str:
    """生成字幕"""
    captions = []
    for shot in script:
        captions.append(shot['line'])
    return '\n'.join(captions)

def generate_hashtags(product_name: str, selling_points: List[str]) -> List[str]:
    """生成话题标签"""
    hashtags = [
        f"#{product_name}",
        "#好物推荐",
        "#开箱",
        "#测评",
        "#抖音好物"
    ]
    
    # 添加卖点相关标签
    for point in selling_points[:3]:
        hashtags.append(f"#{point}")
    
    return hashtags[:10]

def suggest_publish_time(audience: str) -> Dict:
    """建议发布时间"""
    if audience == '学生' or audience == '年轻人':
        return {
            'best_time': BEST_TIMES['evening'],
            'alternative': [BEST_TIMES['noon'], BEST_TIMES['afternoon']]
        }
    elif audience == '上班族':
        return {
            'best_time': BEST_TIMES['morning'],
            'alternative': [BEST_TIMES['evening'], BEST_TIMES['afternoon']]
        }
    else:
        return {
            'best_time': BEST_TIMES['evening'],
            'alternative': [BEST_TIMES['afternoon'], BEST_TIMES['noon']]
        }

def compliance_check(script: List[Dict], captions: str) -> Dict:
    """合规检查：禁用词 + 敏感模式（微信号/二维码/电话/价格），用于判断是否需要人工审核"""

    """合规检查"""
    issues = []
    all_text = captions + ' '.join([shot['line'] for shot in script])
    
    # 检查禁用词
    for word in PLATFORM_RULES['forbidden_words']:
        if word in all_text:
            issues.append(f"内容包含禁用词: {word}")
    
    # 检查敏感模式
    for pattern in PLATFORM_RULES['sensitive_patterns']:
        if re.search(pattern, all_text, re.IGNORECASE):
            issues.append(f"内容包含敏感内容")
    
    return {
        'passed': len(issues) == 0,
        'issues': issues
    }

def generate_douyin_video(input_data: Dict) -> Dict:
    """生成抖音视频脚本主流程：校验→钩子→分镜→字幕→标签→发布时间→合规→门控判断"""

    """生成抖音视频脚本"""
    # 1. 校验输入
    missing_fields = validate_input(input_data)
    if missing_fields:
        return {
            'error': '输入不完整',
            'missing_fields': missing_fields
        }
    
    product_name = input_data['product_name']
    selling_points = input_data.get('selling_points', [])
    features = input_data.get('features', [])
    video_type = input_data.get('video_type', 'product')
    duration = input_data.get('duration', 30)
    target_audience = input_data.get('target_audience', '年轻人')
    
    # 2. 生成钩子
    hook = generate_hook(product_name, selling_points)
    
    # 3. 生成分镜脚本
    script = generate_script(product_name, selling_points, features, video_type, duration)
    
    # 4. 生成字幕
    captions = generate_captions(script)
    
    # 5. 生成话题标签
    hashtags = generate_hashtags(product_name, selling_points)
    
    # 6. 建议发布时间
    publish_time = suggest_publish_time(target_audience)
    
    # 7. 合规检查
    compliance = compliance_check(script, captions)
    
    # 8. 判断是否需要人工复核
    needs_human_review = not compliance['passed']
    
    return {
        'platform': 'douyin',
        'video_type': VIDEO_TEMPLATES.get(video_type, {}).get('description', video_type),
        'duration': duration,
        'target_audience': target_audience,
        'hook': hook,
        'script': script,
        'captions': captions,
        'hashtags': hashtags,
        'publish_time': publish_time,
        'production_notes': [
            f"建议拍摄设备：手机/相机",
            f"建议画面比例：9:16",
            f"建议背景音乐：流行/轻快",
            f"字幕样式：大字体、清晰"
        ],
        'compliance': compliance,
        'needs_human_review': needs_human_review,
        'review_reason': compliance['issues'][0] if compliance['issues'] else ''
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
    
    # 生成抖音视频脚本
    result = generate_douyin_video(input_data)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()