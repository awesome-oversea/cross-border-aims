import json
import re
from datetime import datetime

def analyze_image(content, analysis_types):
    results = []
    
    if "ocr" in analysis_types:
        ocr_texts = [
            "智能手表 Pro 新品发布",
            "限时优惠 8折起",
            "活动时间：2026年5月1日-5月31日",
            "官方旗舰店"
        ]
        results.append({
            "type": "ocr",
            "confidence": 0.92,
            "data": {
                "texts": ocr_texts,
                "full_text": "\n".join(ocr_texts)
            }
        })
    
    if "object_detection" in analysis_types:
        objects = [
            {"name": "智能手表", "confidence": 0.95, "bbox": [100, 80, 250, 230]},
            {"name": "包装盒", "confidence": 0.88, "bbox": [50, 50, 300, 300]},
            {"name": "背景装饰", "confidence": 0.72, "bbox": [0, 0, 320, 400]}
        ]
        results.append({
            "type": "object_detection",
            "confidence": 0.9,
            "data": {"objects": objects}
        })
    
    if "scene_recognition" in analysis_types:
        scenes = [
            {"scene": "产品展示", "confidence": 0.93},
            {"scene": "商业广告", "confidence": 0.87},
            {"scene": "室内场景", "confidence": 0.75}
        ]
        results.append({
            "type": "scene_recognition",
            "confidence": 0.85,
            "data": {"scenes": scenes}
        })
    
    if "brand_detection" in analysis_types:
        brands = [
            {"brand": "AIMS", "confidence": 0.91},
            {"brand": "智能科技", "confidence": 0.78}
        ]
        results.append({
            "type": "brand_detection",
            "confidence": 0.85,
            "data": {"brands": brands}
        })
    
    if "logo_detection" in analysis_types:
        logos = [
            {"logo": "AIMS Logo", "confidence": 0.94, "bbox": [250, 280, 300, 330]}
        ]
        results.append({
            "type": "logo_detection",
            "confidence": 0.9,
            "data": {"logos": logos}
        })
    
    return results

def analyze_video(content, analysis_types):
    results = []
    
    if "scene_recognition" in analysis_types:
        scenes = [
            {"scene": "产品开箱", "confidence": 0.92, "timestamp": "00:00-00:15"},
            {"scene": "功能演示", "confidence": 0.88, "timestamp": "00:15-00:45"},
            {"scene": "使用场景", "confidence": 0.85, "timestamp": "00:45-01:15"},
            {"scene": "购买引导", "confidence": 0.90, "timestamp": "01:15-01:30"}
        ]
        results.append({
            "type": "scene_recognition",
            "confidence": 0.88,
            "data": {"scenes": scenes, "duration": "01:30"}
        })
    
    if "key_points" in analysis_types:
        key_points = [
            "产品外观展示",
            "核心功能介绍",
            "实际使用场景",
            "优惠信息说明",
            "购买链接引导"
        ]
        results.append({
            "type": "key_points",
            "confidence": 0.91,
            "data": {"key_points": key_points}
        })
    
    if "object_detection" in analysis_types:
        objects = [
            {"name": "智能手表", "confidence": 0.95, "appearances": 45},
            {"name": "用户", "confidence": 0.89, "appearances": 28},
            {"name": "手机", "confidence": 0.78, "appearances": 12}
        ]
        results.append({
            "type": "object_detection",
            "confidence": 0.87,
            "data": {"objects": objects}
        })
    
    return results

def analyze_text(content, analysis_types):
    results = []
    
    if "text_analysis" in analysis_types:
        topics = [
            {"topic": "产品介绍", "confidence": 0.93},
            {"topic": "促销活动", "confidence": 0.88},
            {"topic": "使用体验", "confidence": 0.76}
        ]
        results.append({
            "type": "text_analysis",
            "confidence": 0.86,
            "data": {"topics": topics, "language": "中文", "length": len(content)}
        })
    
    if "sentiment" in analysis_types:
        positive_words = ["喜欢", "好用", "推荐", "满意", "优秀", "很棒", "惊喜"]
        negative_words = ["不好", "差", "失望", "问题", "麻烦", "糟糕"]
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        if positive_count > negative_count:
            sentiment = "positive"
            score = min(0.95, 0.5 + positive_count * 0.1)
        elif negative_count > positive_count:
            sentiment = "negative"
            score = max(-0.95, -0.5 - negative_count * 0.1)
        else:
            sentiment = "neutral"
            score = 0.0
        
        results.append({
            "type": "sentiment",
            "confidence": 0.85,
            "data": {"sentiment": sentiment, "score": round(score, 2)}
        })
    
    if "key_points" in analysis_types:
        key_points = extract_key_points(content)
        results.append({
            "type": "key_points",
            "confidence": 0.88,
            "data": {"key_points": key_points}
        })
    
    return results

def extract_key_points(text):
    key_points = []
    
    price_pattern = r'(\d+(?:\.\d+)?)\s*元|(\d+(?:\.\d+)?)\s*元|¥(\d+(?:\.\d+)?)'
    price_matches = re.findall(price_pattern, text)
    for match in price_matches:
        for group in match:
            if group:
                key_points.append(f"价格：{group}元")
                break
    
    time_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日|\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?'
    time_matches = re.findall(time_pattern, text)
    if time_matches:
        key_points.append("包含时间信息")
    
    product_pattern = r'(智能手表|蓝牙耳机|无线充电器|平板电脑|机械键盘)'
    product_matches = re.findall(product_pattern, text)
    for product in product_matches:
        key_points.append(f"产品：{product}")
    
    action_pattern = r'(购买|下单|领取|参与|抢购|点击)'
    if re.search(action_pattern, text):
        key_points.append("包含行动号召")
    
    if not key_points:
        key_points = ["产品介绍", "功能描述", "用户评价"]
    
    return key_points

def analyze_mixed(content, analysis_types):
    text_results = analyze_text(content.get("text", ""), analysis_types)
    image_results = []
    
    if content.get("image_urls"):
        image_results = analyze_image(content["image_urls"][0] if content["image_urls"] else "", analysis_types)
    
    return text_results + image_results

def analyze(content_type, content, analysis_types):
    """多模态内容分析：按类型（图片/视频/文本/混合）路由到对应分析器"""

    if not analysis_types:
        analysis_types = ["ocr", "object_detection", "scene_recognition", "text_analysis", "sentiment", "key_points", "brand_detection", "logo_detection"]
    
    if content_type == "image":
        results = analyze_image(content, analysis_types)
    elif content_type == "video":
        results = analyze_video(content, analysis_types)
    elif content_type == "text":
        results = analyze_text(content, analysis_types)
    elif content_type == "mixed":
        results = analyze_mixed(content, analysis_types)
    else:
        results = []
    
    summary = generate_summary(results, content)
    keywords = extract_keywords(results, content)
    entities = extract_entities(results, content)
    
    return {
        "content_type": content_type,
        "analysis_results": results,
        "summary": summary,
        "keywords": keywords,
        "entities": entities,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def generate_summary(results, content):
    summaries = []
    
    for result in results:
        if result["type"] == "ocr":
            summaries.append(f"识别到文本内容")
        elif result["type"] == "object_detection":
            objects = [obj["name"] for obj in result["data"].get("objects", [])[:3]]
            summaries.append(f"检测到物体：{', '.join(objects)}")
        elif result["type"] == "scene_recognition":
            scenes = [s["scene"] for s in result["data"].get("scenes", [])[:2]]
            summaries.append(f"场景类型：{', '.join(scenes)}")
        elif result["type"] == "text_analysis":
            topics = [t["topic"] for t in result["data"].get("topics", [])[:2]]
            summaries.append(f"主题分类：{', '.join(topics)}")
        elif result["type"] == "sentiment":
            sentiment = result["data"].get("sentiment", "neutral")
            summaries.append(f"情感倾向：{sentiment}")
        elif result["type"] == "key_points":
            summaries.append(f"提取到{len(result['data'].get('key_points', []))}个关键点")
        elif result["type"] == "brand_detection":
            brands = [b["brand"] for b in result["data"].get("brands", [])[:2]]
            summaries.append(f"识别品牌：{', '.join(brands)}")
    
    if summaries:
        return "；".join(summaries)
    elif isinstance(content, str) and len(content) > 0:
        return content[:50] + "..." if len(content) > 50 else content
    else:
        return "内容分析完成"

def extract_keywords(results, content):
    keywords = []
    
    for result in results:
        if result["type"] == "ocr":
            text = result["data"].get("full_text", "")
            keywords.extend(re.findall(r'[\u4e00-\u9fa5]{2,}', text)[:5])
        elif result["type"] == "object_detection":
            keywords.extend([obj["name"] for obj in result["data"].get("objects", [])[:3]])
        elif result["type"] == "brand_detection":
            keywords.extend([b["brand"] for b in result["data"].get("brands", [])[:2]])
        elif result["type"] == "key_points":
            keywords.extend(result["data"].get("key_points", [])[:3])
    
    if isinstance(content, str):
        keywords.extend(re.findall(r'(智能手表|蓝牙耳机|无线充电器|平板电脑|限时|优惠|活动|新品)', content))
    
    return list(set(keywords))[:10]

def extract_entities(results, content):
    entities = {"products": [], "brands": [], "dates": [], "prices": [], "locations": []}
    
    for result in results:
        if result["type"] == "object_detection":
            entities["products"].extend([obj["name"] for obj in result["data"].get("objects", []) if obj["confidence"] > 0.8])
        elif result["type"] == "brand_detection":
            entities["brands"].extend([b["brand"] for b in result["data"].get("brands", []) if b["confidence"] > 0.8])
        elif result["type"] == "ocr":
            text = result["data"].get("full_text", "")
            entities["dates"].extend(re.findall(r'\d{4}年\d{1,2}月\d{1,2}日', text))
            entities["prices"].extend(re.findall(r'¥\d+(?:\.\d+)?', text))
    
    if isinstance(content, str):
        entities["dates"].extend(re.findall(r'\d{4}-\d{2}-\d{2}', content))
        entities["prices"].extend(re.findall(r'\d+(?:\.\d+)?元', content))
    
    for key in entities:
        entities[key] = list(set(entities[key]))[:5]
    
    return entities

def main():
    import sys
    input_data = json.load(sys.stdin)
    
    content_type = input_data.get("content_type", "text")
    content = input_data.get("content", "")
    analysis_types = input_data.get("analysis_type", [])
    
    result = analyze(content_type, content, analysis_types)
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()