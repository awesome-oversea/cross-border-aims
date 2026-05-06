import json
import random
from datetime import datetime

_product_catalog = [
    {"product_id": "P001", "name": "智能手表 Pro", "category": "智能穿戴", "price": 899, "rating": 4.8, "sales": 12580, "tags": ["智能", "运动", "健康"]},
    {"product_id": "P002", "name": "无线蓝牙耳机", "category": "音频设备", "price": 199, "rating": 4.6, "sales": 23450, "tags": ["无线", "音乐", "便携"]},
    {"product_id": "P003", "name": "无线充电器", "category": "配件", "price": 89, "rating": 4.5, "sales": 18920, "tags": ["无线", "充电", "便携"]},
    {"product_id": "P004", "name": "平板电脑", "category": "电脑数码", "price": 2999, "rating": 4.7, "sales": 8760, "tags": ["平板", "办公", "娱乐"]},
    {"product_id": "P005", "name": "机械键盘", "category": "电脑配件", "price": 399, "rating": 4.6, "sales": 15680, "tags": ["键盘", "办公", "游戏"]},
    {"product_id": "P006", "name": "无线鼠标", "category": "电脑配件", "price": 129, "rating": 4.4, "sales": 12340, "tags": ["鼠标", "办公", "无线"]},
    {"product_id": "P007", "name": "便携音箱", "category": "音频设备", "price": 299, "rating": 4.5, "sales": 9870, "tags": ["音箱", "便携", "户外"]},
    {"product_id": "P008", "name": "智能手环", "category": "智能穿戴", "price": 299, "rating": 4.3, "sales": 16540, "tags": ["智能", "运动", "健康"]},
    {"product_id": "P009", "name": "移动电源", "category": "配件", "price": 159, "rating": 4.4, "sales": 21340, "tags": ["充电", "便携", "大容量"]},
    {"product_id": "P010", "name": "电竞耳机", "category": "音频设备", "price": 499, "rating": 4.7, "sales": 7890, "tags": ["游戏", "耳机", "降噪"]},
    {"product_id": "P011", "name": "智能台灯", "category": "智能家居", "price": 199, "rating": 4.5, "sales": 11230, "tags": ["智能", "照明", "护眼"]},
    {"product_id": "P012", "name": "便携投影仪", "category": "影音设备", "price": 1599, "rating": 4.6, "sales": 5670, "tags": ["投影", "便携", "家庭影院"]},
    {"product_id": "P013", "name": "智能门锁", "category": "智能家居", "price": 899, "rating": 4.7, "sales": 6540, "tags": ["智能", "安全", "家居"]},
    {"product_id": "P014", "name": "蓝牙键盘", "category": "电脑配件", "price": 199, "rating": 4.3, "sales": 9870, "tags": ["键盘", "蓝牙", "便携"]},
    {"product_id": "P015", "name": "游戏手柄", "category": "游戏设备", "price": 299, "rating": 4.5, "sales": 8760, "tags": ["游戏", "手柄", "电竞"]},
    {"product_id": "P016", "name": "智能摄像头", "category": "智能家居", "price": 399, "rating": 4.4, "sales": 10230, "tags": ["安防", "智能", "监控"]},
    {"product_id": "P017", "name": "电子书阅读器", "category": "阅读设备", "price": 999, "rating": 4.8, "sales": 4560, "tags": ["阅读", "墨水屏", "护眼"]},
    {"product_id": "P018", "name": "车载充电器", "category": "配件", "price": 69, "rating": 4.2, "sales": 14560, "tags": ["车载", "充电", "便携"]},
    {"product_id": "P019", "name": "降噪耳机", "category": "音频设备", "price": 799, "rating": 4.7, "sales": 6780, "tags": ["降噪", "耳机", "高端"]},
    {"product_id": "P020", "name": "智能音箱", "category": "智能家居", "price": 599, "rating": 4.6, "sales": 9870, "tags": ["智能", "音箱", "语音助手"]}
]

def get_popular_products(limit=6):
    popular = sorted(_product_catalog, key=lambda p: p["sales"], reverse=True)[:limit]
    return [add_recommendation_info(p, "热销商品") for p in popular]

def get_new_arrivals(limit=6):
    new_arrivals = sorted(_product_catalog, key=lambda p: p["rating"], reverse=True)[:limit]
    return [add_recommendation_info(p, "新品推荐") for p in new_arrivals]

def get_personalized_recommendations(user_profile, limit=6):
    tags = user_profile.get("tags", [])
    preferences = user_profile.get("preferences", {})
    
    scored_products = []
    for product in _product_catalog:
        score = 0
        
        for tag in tags:
            if tag in ["高价值", "VIP"]:
                if product["price"] > 500:
                    score += 2
            elif tag in ["数码爱好者"]:
                if product["category"] in ["智能穿戴", "音频设备", "电脑数码"]:
                    score += 2
            elif tag.lower() in [t.lower() for t in product["tags"]]:
                score += 1
        
        if preferences.get("categories"):
            for cat in preferences["categories"]:
                if cat in product["category"]:
                    score += 2
        
        if preferences.get("price_range"):
            price_range = preferences["price_range"]
            if price_range == "1000-3000" and 1000 <= product["price"] <= 3000:
                score += 1
            elif price_range == "0-1000" and product["price"] < 1000:
                score += 1
            elif price_range == "3000+" and product["price"] > 3000:
                score += 1
        
        if score > 0:
            scored_products.append((product, score))
    
    scored_products.sort(key=lambda x: x[1], reverse=True)
    recommendations = [add_recommendation_info(p[0], "个性化推荐", p[1]/10) for p in scored_products[:limit]]
    
    if len(recommendations) < limit:
        recommendations.extend(get_popular_products(limit - len(recommendations)))
    
    return recommendations

def get_related_products(product_id, limit=6):
    target_product = next((p for p in _product_catalog if p["product_id"] == product_id), None)
    if not target_product:
        return get_popular_products(limit)
    
    scored_products = []
    for product in _product_catalog:
        if product["product_id"] == product_id:
            continue
        
        score = 0
        if product["category"] == target_product["category"]:
            score += 3
        
        common_tags = set(product["tags"]) & set(target_product["tags"])
        score += len(common_tags) * 2
        
        price_diff = abs(product["price"] - target_product["price"]) / target_product["price"]
        if price_diff < 0.5:
            score += 1
        
        if score > 0:
            scored_products.append((product, score))
    
    scored_products.sort(key=lambda x: x[1], reverse=True)
    recommendations = [add_recommendation_info(p[0], "关联推荐", p[1]/10) for p in scored_products[:limit]]
    
    return recommendations

def get_complementary_products(product_id, limit=6):
    complementary_map = {
        "P001": ["P003", "P009"],
        "P002": ["P007"],
        "P004": ["P005", "P006", "P014"],
        "P005": ["P006"],
        "P010": ["P015"],
        "P012": ["P015"],
        "P017": ["P011"]
    }
    
    complementary_ids = complementary_map.get(product_id, [])
    recommendations = []
    
    for pid in complementary_ids:
        product = next((p for p in _product_catalog if p["product_id"] == pid), None)
        if product:
            recommendations.append(add_recommendation_info(product, "搭配购买"))
    
    if len(recommendations) < limit:
        recommendations.extend(get_popular_products(limit - len(recommendations)))
    
    return recommendations

def get_cross_sell_recommendations(order_items, limit=6):
    purchased_categories = set()
    for item in order_items:
        product = next((p for p in _product_catalog if p["product_id"] == item.get("product_id")), None)
        if product:
            purchased_categories.add(product["category"])
    
    scored_products = []
    for product in _product_catalog:
        if product["category"] not in purchased_categories:
            score = product["sales"] * 0.1 + product["rating"]
            scored_products.append((product, score))
    
    scored_products.sort(key=lambda x: x[1], reverse=True)
    recommendations = [add_recommendation_info(p[0], "交叉销售推荐") for p in scored_products[:limit]]
    
    return recommendations

def add_recommendation_info(product, reason, confidence=None):
    result = {
        "product_id": product["product_id"],
        "name": product["name"],
        "category": product["category"],
        "price": product["price"],
        "image": f"https://example.com/images/{product['product_id']}.jpg",
        "rating": product["rating"],
        "sales": product["sales"],
        "reason": reason,
        "confidence": confidence if confidence else round(random.uniform(0.7, 0.95), 2)
    }
    return result

def recommend(user_id=None, user_profile=None, context=None, recommendation_type="personalized", limit=6):
    if user_profile is None:
        user_profile = {}
    if context is None:
        context = {}
    
    recommendations = []
    strategy = ""
    
    if recommendation_type == "personalized":
        recommendations = get_personalized_recommendations(user_profile, limit)
        strategy = "基于用户画像的个性化推荐"
    elif recommendation_type == "related":
        product_id = context.get("product_id", "")
        recommendations = get_related_products(product_id, limit)
        strategy = "基于商品关联的推荐"
    elif recommendation_type == "popular":
        recommendations = get_popular_products(limit)
        strategy = "基于销量的热门推荐"
    elif recommendation_type == "new_arrivals":
        recommendations = get_new_arrivals(limit)
        strategy = "基于评分的新品推荐"
    elif recommendation_type == "complementary":
        product_id = context.get("product_id", "")
        recommendations = get_complementary_products(product_id, limit)
        strategy = "基于搭配的互补推荐"
    elif recommendation_type == "cross_sell":
        order_items = context.get("order_items", [])
        recommendations = get_cross_sell_recommendations(order_items, limit)
        strategy = "基于订单的交叉销售推荐"
    else:
        recommendations = get_popular_products(limit)
        strategy = "默认热门推荐"
    
    explanation = f"为您推荐{len(recommendations)}件商品，基于{strategy}策略"
    
    result = {
        "recommendations": recommendations,
        "strategy": strategy,
        "explanation": explanation,
        "total_count": len(recommendations),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return result

def main():
    import sys
    input_data = json.load(sys.stdin)
    
    user_id = input_data.get("user_id", "")
    user_profile = input_data.get("user_profile", {})
    context = input_data.get("context", {})
    recommendation_type = input_data.get("recommendation_type", "personalized")
    limit = input_data.get("limit", 6)
    
    result = recommend(user_id, user_profile, context, recommendation_type, limit)
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()