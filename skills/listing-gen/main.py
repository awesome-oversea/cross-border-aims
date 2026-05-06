#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))

LIMIT_WORDS_CN = [
    '最', '顶级', '第一', '唯一', '首选', '极致', '完美',
    '国家级', '世界级', '全国第一', '全网第一', '销量第一', '冠军',
    '特效', '神奇', '神效', '根治', '治愈', '防癌', '抗癌', '无毒',
    '无副作用', '无添加', '纯天然', '100%', '绝对', '永久', '永不褪色',
    '史上最强', '绝无仅有', '史无前例', '万能', '零风险', '包治',
    '秒杀', '抢爆', '卖疯了', '抢购', '甩卖', '清仓', '特价',
]

LIMIT_WORDS_EN = [
    'best', 'top', 'only', 'guarantee', 'perfect', 'miracle', 'cure',
    '100%', 'forever', 'ultimate', 'number one', '#1', 'unbeatable',
    'revolutionary', 'breakthrough', 'risk-free', 'proven', 'instant',
]

PLATFORM_RULES = {
    'amazon': {
        'title_max_length': 200,
        'bullet_points': 5,
        'bullet_max_length': 500,
        'description_max_length': 2000,
        'forbidden_words': LIMIT_WORDS_EN,
        'title_pattern': 'Brand + Model + Key Feature + Material/Size + Color',
        'bullet_prefix': ['PREMIUM QUALITY:', 'VERSATILE USE:', 'EASY TO USE:', 'DURABLE DESIGN:', 'PERFECT GIFT:'],
        'keyword_max': 250,
        'backend_attr': ['target_audience', 'subject_keywords', 'other_attributes', 'intended_use'],
    },
    'amazon_uk': {
        'title_max_length': 200,
        'bullet_points': 5,
        'bullet_max_length': 500,
        'description_max_length': 2000,
        'forbidden_words': LIMIT_WORDS_EN,
        'title_pattern': 'Brand + Model + Key Feature + Material/Size + Colour',
        'bullet_prefix': ['PREMIUM QUALITY:', 'VERSATILE USE:', 'EASY TO USE:', 'DURABLE DESIGN:', 'PERFECT GIFT:'],
        'keyword_max': 250,
        'backend_attr': ['target_audience', 'subject_keywords', 'other_attributes', 'intended_use'],
    },
    'amazon_de': {
        'title_max_length': 200,
        'bullet_points': 5,
        'bullet_max_length': 500,
        'description_max_length': 2000,
        'forbidden_words': LIMIT_WORDS_EN + ['bestseller', 'testsieger'],
        'title_pattern': 'Marke + Modell + Hauptmerkmal + Material/Größe + Farbe',
        'bullet_prefix': ['PREMIUM QUALITÄT:', 'VIELSEITIG EINSETZBAR:', 'EINFACH ZU BEDIENEN:', 'LANGLEBIGES DESIGN:', 'PERFEKTES GESCHENK:'],
        'keyword_max': 250,
        'backend_attr': ['target_audience', 'subject_keywords', 'other_attributes', 'intended_use'],
    },
    'amazon_jp': {
        'title_max_length': 200,
        'bullet_points': 5,
        'bullet_max_length': 500,
        'description_max_length': 2000,
        'forbidden_words': ['最高', '一番', '唯一', '完璧', '絶対', '永久'],
        'title_pattern': 'ブランド + モデル + 主要特徴 + 材質/サイズ + 色',
        'bullet_prefix': ['高品質:', '多用途:', '使いやすい:', '耐久性:', 'ギフトに最適:'],
        'keyword_max': 250,
        'backend_attr': ['target_audience', 'subject_keywords', 'other_attributes', 'intended_use'],
    },
    'taobao': {
        'title_max_length': 60,
        'bullet_points': 10,
        'bullet_max_length': 100,
        'description_max_length': 5000,
        'forbidden_words': LIMIT_WORDS_CN,
        'title_pattern': '品牌 + 核心卖点 + 属性词 + 促销词',
        'bullet_prefix': [],
        'keyword_max': 60,
        'backend_attr': [],
    },
    'jd': {
        'title_max_length': 100,
        'bullet_points': 5,
        'bullet_max_length': 200,
        'description_max_length': 10000,
        'forbidden_words': LIMIT_WORDS_CN,
        'title_pattern': '品牌 + 型号 + 核心卖点 + 规格参数',
        'bullet_prefix': [],
        'keyword_max': 100,
        'backend_attr': [],
    },
    'pinduoduo': {
        'title_max_length': 50,
        'bullet_points': 5,
        'bullet_max_length': 80,
        'description_max_length': 2000,
        'forbidden_words': LIMIT_WORDS_CN,
        'title_pattern': '品牌 + 卖点 + 属性 + 促销',
        'bullet_prefix': [],
        'keyword_max': 50,
        'backend_attr': [],
    },
    'shopee': {
        'title_max_length': 120,
        'bullet_points': 5,
        'bullet_max_length': 300,
        'description_max_length': 3000,
        'forbidden_words': LIMIT_WORDS_EN,
        'title_pattern': 'Brand + Key Feature + Spec + Model',
        'bullet_prefix': [],
        'keyword_max': 120,
        'backend_attr': [],
    },
    'lazada': {
        'title_max_length': 255,
        'bullet_points': 5,
        'bullet_max_length': 500,
        'description_max_length': 4000,
        'forbidden_words': LIMIT_WORDS_EN,
        'title_pattern': 'Brand + Model + Key Feature + Specification',
        'bullet_prefix': [],
        'keyword_max': 255,
        'backend_attr': [],
    },
}

CATEGORY_COMPLIANCE_RULES = {
    'electronics': {
        'required_certifications': ['CE', 'FCC', 'RoHS'],
        'forbidden_claims': ['waterproof IP68 without proof', 'medical device'],
        'required_disclosures': ['battery capacity', 'charging time', 'warranty period'],
    },
    'clothing': {
        'required_certifications': [],
        'forbidden_claims': ['anti-bacterial without proof', 'UV protection without rating'],
        'required_disclosures': ['material composition', 'size chart', 'care instructions'],
    },
    'food': {
        'required_certifications': ['FDA', 'HACCP'],
        'forbidden_claims': ['cure disease', 'weight loss guarantee', 'organic without certification'],
        'required_disclosures': ['ingredients', 'allergens', 'nutrition facts', 'shelf life'],
    },
    'beauty': {
        'required_certifications': ['FDA', 'GMP'],
        'forbidden_claims': ['whitening guarantee', 'anti-aging proof', 'medical effect'],
        'required_disclosures': ['ingredients', 'usage instructions', 'warnings'],
    },
    'toys': {
        'required_certifications': ['CE', 'ASTM', 'CPSIA'],
        'forbidden_claims': ['educational guarantee', 'suitable for all ages'],
        'required_disclosures': ['age recommendation', 'choking hazard', 'material safety'],
    },
    'home': {
        'required_certifications': [],
        'forbidden_claims': ['energy saving guarantee', 'health benefit'],
        'required_disclosures': ['dimensions', 'material', 'assembly required'],
    },
}

SEO_KEYWORD_STRATEGIES = {
    'amazon': {
        'title_weight': 0.35,
        'bullet_weight': 0.25,
        'description_weight': 0.15,
        'backend_weight': 0.25,
        'keyword_placement': ['title beginning', 'title middle', 'bullet first line', 'description first 100 chars'],
    },
    'taobao': {
        'title_weight': 0.50,
        'bullet_weight': 0.15,
        'description_weight': 0.20,
        'backend_weight': 0.15,
        'keyword_placement': ['title core position', 'subtitle', 'attribute tags'],
    },
}

RAG_KNOWLEDGE_BASE = [
    {
        "id": "amazon_title_guide",
        "category": "listing_rules",
        "title": "Amazon标题优化指南",
        "content": "Amazon标题应遵循：1) 品牌+型号+核心卖点+材质/尺寸+颜色；2) 首字母大写（介词除外）；3) 避免堆砌关键词；4) 使用数字而非文字；5) 不使用促销信息；6) 标题前60字符决定移动端展示效果",
        "platform": "amazon",
    },
    {
        "id": "amazon_bullet_guide",
        "category": "listing_rules",
        "title": "Amazon五点描述优化指南",
        "content": "五点描述最佳实践：1) 每点以大写关键词开头；2) 突出用户利益而非仅功能；3) 包含具体数据支撑；4) 前2点放最重要卖点；5) 每点控制在200-300字符；6) 使用情感触发词增强购买欲",
        "platform": "amazon",
    },
    {
        "id": "amazon_keyword_guide",
        "category": "listing_rules",
        "title": "Amazon搜索关键词优化指南",
        "content": "Backend关键词策略：1) 不重复标题已有词；2) 使用长尾关键词；3) 包含同义词和变体；4) 不使用竞品品牌名；5) 不使用主观评价词；6) 单词间用空格分隔；7) 总字符控制在250字节内",
        "platform": "amazon",
    },
    {
        "id": "taobao_title_guide",
        "category": "listing_rules",
        "title": "淘宝标题优化指南",
        "content": "淘宝标题策略：1) 核心词放最前或最后；2) 属性词+核心词+促销词组合；3) 利用满30字增加曝光；4) 避免重复词浪费位置；5) 结合生意参谋选词；6) 季节性关键词及时更新",
        "platform": "taobao",
    },
    {
        "id": "compliance_general",
        "category": "compliance",
        "title": "跨境电商通用合规要求",
        "content": "通用合规红线：1) 不得使用极限词和绝对化用语；2) 不得虚假宣传功效；3) 不得侵权使用他人品牌/专利；4) 食品/化妆品需认证标识；5) 电子类需安全认证；6) 玩具类需年龄标注和安全警告",
        "platform": "all",
    },
    {
        "id": "ab_test_title",
        "category": "optimization",
        "title": "Listing标题A/B测试策略",
        "content": "标题A/B测试方法：1) 变量控制：仅改变一个元素（关键词位置/同义词/数字表达）；2) 测试周期：至少7天覆盖完整购买周期；3) 指标监控：CTR、转化率、搜索排名；4) 样本量：至少1000次曝光；5) 方案设计：信息型vs情感型、功能型vs场景型",
        "platform": "all",
    },
    {
        "id": "seo_long_tail",
        "category": "optimization",
        "title": "长尾关键词SEO策略",
        "content": "长尾关键词策略：1) 使用3-5词组合覆盖精准搜索意图；2) 包含使用场景（for home office/kitchen/gift）；3) 包含目标人群（for women/men/kids/seniors）；4) 包含规格属性（stainless steel/18oz/compact）；5) 利用问答平台挖掘真实搜索词",
        "platform": "all",
    },
]


class RAGRetriever:
    def __init__(self):
        self.use_simulated = True
        self.client = None
        self._try_connect()

    def _try_connect(self):
        try:
            from pymilvus import MilvusClient
            self.client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}")
            self.use_simulated = False
        except Exception:
            self.use_simulated = True

    def search(self, query: str, top_k: int = 5, category: str = None, platform: str = None) -> List[Dict]:
        if self.use_simulated:
            return self._simulated_search(query, top_k, category, platform)
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            query_vector = model.encode(query).tolist()
            expr_parts = []
            if category:
                expr_parts.append(f"category == '{category}'")
            if platform and platform != "all":
                expr_parts.append(f"platform == '{platform}' or platform == 'all'")
            expr = " and ".join(expr_parts) if expr_parts else None
            results = self.client.search(
                collection_name="ecommerce_knowledge",
                data=[query_vector],
                limit=top_k,
                expr=expr,
                output_fields=["content", "title", "category", "source"],
            )
            return [{"score": h["distance"], "content": h["entity"]["content"], "title": h["entity"]["title"]} for h in results[0]]
        except Exception:
            return self._simulated_search(query, top_k, category, platform)

    def _simulated_search(self, query: str, top_k: int = 5, category: str = None, platform: str = None) -> List[Dict]:
        results = []
        query_lower = query.lower()
        for doc in RAG_KNOWLEDGE_BASE:
            if category and doc.get("category") != category:
                continue
            if platform and doc.get("platform") not in [platform, "all"]:
                continue
            score = self._text_similarity(query_lower, doc["content"].lower())
            if score > 0:
                results.append({"score": round(score, 4), "content": doc["content"], "title": doc["title"], "category": doc.get("category", "")})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _text_similarity(query: str, text: str) -> float:
        query_words = set(query.split())
        text_words = set(text.split())
        if not query_words:
            return 0.0
        return len(query_words & text_words) / len(query_words)


def validate_input(input_data: Dict) -> Dict:
    errors = []
    warnings = []
    required = ['platform', 'product_name', 'category']
    for field in required:
        if field not in input_data or not input_data.get(field):
            errors.append(field)
    if 'selling_points' not in input_data or not input_data.get('selling_points'):
        warnings.append('selling_points')
    if 'features' not in input_data or not input_data.get('features'):
        warnings.append('features')
    return {"errors": errors, "warnings": warnings}


def get_platform_key(platform: str, site: str = "") -> str:
    if platform == "amazon" and site:
        site_map = {"US": "amazon", "UK": "amazon_uk", "DE": "amazon_de", "JP": "amazon_jp"}
        return site_map.get(site.upper(), "amazon")
    return platform


def generate_title(product_name: str, selling_points: List[str], platform: str, site: str,
                   brand: str = "", model: str = "", color: str = "", material: str = "",
                   size: str = "") -> Dict:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['amazon'])
    max_len = rules['title_max_length']

    if platform.startswith('amazon'):
        parts = []
        if brand:
            parts.append(brand)
        if model:
            parts.append(model)
        core_feature = selling_points[0] if selling_points else product_name
        parts.append(core_feature)
        if material:
            parts.append(material)
        if size:
            parts.append(size)
        if color:
            parts.append(color)
        title = ' '.join(parts)
    elif platform in ('taobao', 'pinduoduo'):
        parts = []
        if brand:
            parts.append(brand)
        core = selling_points[0] if selling_points else product_name
        parts.append(core)
        for sp in selling_points[1:3]:
            parts.append(sp)
        title = ' '.join(parts)
    elif platform == 'jd':
        parts = []
        if brand:
            parts.append(brand)
        if model:
            parts.append(model)
        core = selling_points[0] if selling_points else product_name
        parts.append(core)
        if material:
            parts.append(material)
        title = ' '.join(parts)
    else:
        parts = []
        if brand:
            parts.append(brand)
        core = selling_points[0] if selling_points else product_name
        parts.append(core)
        for sp in selling_points[1:2]:
            parts.append(sp)
        title = ' '.join(parts)

    title = title[:max_len]
    ab_title = _generate_ab_title(product_name, selling_points, platform, brand, max_len)

    return {
        "title": title,
        "title_length": len(title),
        "max_length": max_len,
        "ab_variant": ab_title,
        "pattern_used": rules.get('title_pattern', ''),
    }


def _generate_ab_title(product_name: str, selling_points: List[str], platform: str,
                       brand: str, max_len: int) -> Dict:
    variants = {}

    if platform.startswith('amazon'):
        feature_first = ' '.join([selling_points[0], brand, product_name] + selling_points[1:3]) if selling_points else product_name
        benefit_first = f"{brand} {product_name} - Perfect for {selling_points[0]}" if selling_points else product_name
        variants["feature_first"] = feature_first[:max_len]
        variants["benefit_first"] = benefit_first[:max_len]
    elif platform in ('taobao', 'pinduoduo'):
        core_first = ' '.join([selling_points[0] if selling_points else product_name, brand, product_name])
        scene_first = f"{' '.join(selling_points[:2])} {product_name}" if len(selling_points) >= 2 else product_name
        variants["core_first"] = core_first[:max_len]
        variants["scene_first"] = scene_first[:max_len]
    else:
        variants["variant_a"] = f"{brand} {product_name} {' '.join(selling_points[:2])}"[:max_len] if selling_points else product_name
        variants["variant_b"] = f"{product_name} - {' '.join(selling_points[:2])}"[:max_len] if selling_points else product_name

    return variants


def generate_bullet_points(selling_points: List[str], features: List[str], specs: Dict,
                           platform: str, material: str = "", audience: str = "") -> Dict:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['amazon'])
    max_bullets = rules['bullet_points']
    max_len = rules['bullet_max_length']
    prefixes = rules.get('bullet_prefix', [])

    bullets = []
    for i, sp in enumerate(selling_points[:max_bullets]):
        prefix = prefixes[i] if i < len(prefixes) else f"{i + 1}."
        benefit = _feature_to_benefit(sp, audience)
        bullet_text = f"{prefix} {benefit}"
        bullets.append(bullet_text[:max_len])

    remaining = max_bullets - len(bullets)
    if remaining > 0 and features:
        for feat in features[:remaining]:
            idx = len(bullets)
            prefix = prefixes[idx] if idx < len(prefixes) else f"{idx + 1}."
            bullet_text = f"{prefix} {feat}"
            bullets.append(bullet_text[:max_len])

    remaining = max_bullets - len(bullets)
    if remaining > 0 and specs:
        for key, value in list(specs.items())[:remaining]:
            idx = len(bullets)
            prefix = prefixes[idx] if idx < len(prefixes) else f"{idx + 1}."
            bullet_text = f"{prefix} {key}: {value}"
            bullets.append(bullet_text[:max_len])

    if material and len(bullets) < max_bullets:
        idx = len(bullets)
        prefix = prefixes[idx] if idx < len(prefixes) else f"{idx + 1}."
        bullet_text = f"{prefix} Made from premium {material} for lasting quality"
        bullets.append(bullet_text[:max_len])

    return {
        "bulletPoints": bullets,
        "count": len(bullets),
        "max_count": max_bullets,
    }


def _feature_to_benefit(feature: str, audience: str = "") -> str:
    benefit_map = {
        'waterproof': 'Stay dry and confident in any weather with our waterproof design',
        'lightweight': 'Enjoy all-day comfort with our ultra-lightweight construction',
        'durable': 'Built to last through daily use with premium durable materials',
        'portable': 'Take it anywhere effortlessly with the compact portable design',
        'rechargeable': 'Never worry about batteries with convenient USB recharging',
        'adjustable': 'Customize your perfect fit with easy-to-use adjustable settings',
        'wireless': 'Cut the cords and enjoy true freedom with wireless technology',
        'stainless steel': 'Resist rust and corrosion with premium stainless steel construction',
        'ergonomic': 'Experience maximum comfort with our ergonomic design',
        'easy clean': 'Save time with our easy-clean surface that wipes down in seconds',
    }
    feature_lower = feature.lower()
    for key, benefit in benefit_map.items():
        if key in feature_lower:
            prefix = f"Perfect for {audience} - " if audience else ""
            return f"{prefix}{benefit}"
    return feature


def generate_search_keywords(product_name: str, selling_points: List[str], category: str,
                             platform: str, audience: str = "", use_cases: List[str] = None) -> Dict:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['amazon'])
    max_keywords = rules.get('keyword_max', 250)

    core_keywords = [product_name.lower()]
    for sp in selling_points:
        words = sp.lower().split()
        core_keywords.extend([w for w in words if len(w) > 2])

    category_keywords = [category.lower()]
    if audience:
        category_keywords.append(f"for {audience.lower()}")
    if use_cases:
        for uc in use_cases:
            category_keywords.append(f"for {uc.lower()}")

    long_tail = []
    for sp in selling_points[:3]:
        long_tail.append(f"{product_name} {sp}".lower())
    if audience:
        long_tail.append(f"{product_name} for {audience}".lower())
    if use_cases:
        for uc in use_cases[:2]:
            long_tail.append(f"{product_name} for {uc}".lower())

    all_keywords = core_keywords + category_keywords + long_tail
    seen = set()
    unique_keywords = []
    for kw in all_keywords:
        kw_clean = kw.strip()
        if kw_clean and kw_clean not in seen:
            seen.add(kw_clean)
            unique_keywords.append(kw_clean)

    total_len = sum(len(kw) + 1 for kw in unique_keywords)
    while total_len > max_keywords and len(unique_keywords) > 5:
        removed = unique_keywords.pop()
        total_len -= len(removed) + 1

    strategy = SEO_KEYWORD_STRATEGIES.get(platform, SEO_KEYWORD_STRATEGIES['amazon'])

    return {
        "searchKeywords": unique_keywords,
        "total_count": len(unique_keywords),
        "total_length": total_len,
        "max_length": max_keywords,
        "strategy": {
            "title_weight": strategy['title_weight'],
            "bullet_weight": strategy['bullet_weight'],
            "description_weight": strategy['description_weight'],
            "backend_weight": strategy['backend_weight'],
            "placement_tips": strategy['keyword_placement'],
        },
    }


def generate_description(product_name: str, selling_points: List[str], features: List[str],
                         material: str, specs: Dict, platform: str, brand: str = "",
                         audience: str = "") -> Dict:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['amazon'])
    max_len = rules['description_max_length']

    if platform.startswith('amazon'):
        parts = [
            f"Discover the {product_name}" + (f" by {brand}" if brand else ""),
            "",
        ]
        if audience:
            parts.append(f"Designed specifically for {audience}, this product delivers exceptional performance and value.")
        parts.append("KEY FEATURES:")
        for i, sp in enumerate(selling_points, 1):
            parts.append(f"  {i}. {sp}")
        if features:
            parts.append("")
            parts.append("ADDITIONAL FEATURES:")
            for feat in features[:5]:
                parts.append(f"  - {feat}")
        if specs:
            parts.append("")
            parts.append("SPECIFICATIONS:")
            for key, value in list(specs.items())[:8]:
                parts.append(f"  {key}: {value}")
        if material:
            parts.append("")
            parts.append(f"CRAFTED WITH CARE: Made from premium {material} for lasting quality and performance.")
        parts.append("")
        parts.append("ORDER NOW and experience the difference!")
    elif platform in ('taobao', 'jd', 'pinduoduo'):
        parts = [f"【{product_name}】"]
        if brand:
            parts[0] = f"【{brand} {product_name}】"
        parts.append("")
        if selling_points:
            parts.append("核心卖点：")
            for sp in selling_points:
                parts.append(f"  ✅ {sp}")
        if features:
            parts.append("")
            parts.append("产品特色：")
            for feat in features[:5]:
                parts.append(f"  · {feat}")
        if specs:
            parts.append("")
            parts.append("规格参数：")
            for key, value in list(specs.items())[:8]:
                parts.append(f"  {key}：{value}")
        if material:
            parts.append(f"\n材质：{material}")
    else:
        parts = [f"Introducing {product_name}" + (f" by {brand}" if brand else "")]
        for sp in selling_points[:5]:
            parts.append(f"  - {sp}")
        if features:
            parts.append("")
            for feat in features[:3]:
                parts.append(f"  * {feat}")

    description = '\n'.join(parts)
    description = description[:max_len]

    return {
        "description": description,
        "length": len(description),
        "max_length": max_len,
    }


def compliance_check(title: str, bullet_points: List[str], description: str,
                     platform: str, category: str = "") -> Dict:
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES['amazon'])
    forbidden_words = rules['forbidden_words']
    issues = []
    severity_map = {"high": [], "medium": [], "low": []}

    for word in forbidden_words:
        if word.lower() in title.lower():
            issue = f"标题包含禁用词: {word}"
            issues.append(issue)
            severity_map["high"].append(issue)
    for i, bullet in enumerate(bullet_points):
        for word in forbidden_words:
            if word.lower() in bullet.lower():
                issue = f"第{i + 1}点描述包含禁用词: {word}"
                issues.append(issue)
                severity_map["high"].append(issue)
    for word in forbidden_words:
        if word.lower() in description.lower():
            issue = f"长描述包含禁用词: {word}"
            issues.append(issue)
            severity_map["medium"].append(issue)

    if len(title) > rules['title_max_length']:
        issue = f"标题长度超出限制: {len(title)}/{rules['title_max_length']}"
        issues.append(issue)
        severity_map["medium"].append(issue)

    category_rules = CATEGORY_COMPLIANCE_RULES.get(category, {})
    if category_rules:
        for claim in category_rules.get('forbidden_claims', []):
            if claim.lower() in description.lower():
                issue = f"类目禁止声明: {claim}"
                issues.append(issue)
                severity_map["high"].append(issue)

    medical_patterns = [
        r'治疗|治愈|防癌|抗癌|降血压|降血糖|减肥|瘦身效果',
        r'cure|treat|prevent|heal|medical|therapeutic',
    ]
    for pattern in medical_patterns:
        if re.search(pattern, title + ' ' + description, re.IGNORECASE):
            issue = "包含医疗功效声明，需提供证明文件"
            issues.append(issue)
            severity_map["high"].append(issue)
            break

    infringement_patterns = [
        r'比.+更好|优于.+|吊打.+|秒杀.+',
        r'better than|superior to|kills the competition',
    ]
    for pattern in infringement_patterns:
        if re.search(pattern, title + ' ' + description, re.IGNORECASE):
            issue = "包含侵权对比声明"
            issues.append(issue)
            severity_map["medium"].append(issue)
            break

    return {
        "passed": len(severity_map["high"]) == 0,
        "issues": issues,
        "severity": severity_map,
        "high_count": len(severity_map["high"]),
        "medium_count": len(severity_map["medium"]),
        "low_count": len(severity_map["low"]),
    }


def calculate_confidence(compliance: Dict, input_data: Dict, rag_results: List[Dict]) -> float:
    score = 100.0
    if compliance["high_count"] > 0:
        score -= compliance["high_count"] * 20
    if compliance["medium_count"] > 0:
        score -= compliance["medium_count"] * 10
    if not input_data.get('selling_points'):
        score -= 15
    if not input_data.get('features'):
        score -= 10
    if not rag_results:
        score -= 10
    elif len(rag_results) < 2:
        score -= 5
    if not input_data.get('material'):
        score -= 5
    return max(0.0, min(100.0, score))


def generate_optimization_suggestions(title_result: Dict, bullet_result: Dict,
                                      keyword_result: Dict, desc_result: Dict,
                                      compliance: Dict, platform: str) -> List[Dict]:
    suggestions = []

    if compliance["high_count"] > 0:
        suggestions.append({
            "type": "compliance",
            "priority": "critical",
            "suggestion": "修复合规问题后再提交，高风险禁用词和医疗声明必须移除",
            "action": "remove_forbidden_words",
        })

    title_len_ratio = title_result.get("title_length", 0) / max(title_result.get("max_length", 1), 1)
    if title_len_ratio < 0.5:
        suggestions.append({
            "type": "seo",
            "priority": "high",
            "suggestion": f"标题仅使用了{title_len_ratio:.0%}的可用空间，建议补充更多关键词提升搜索曝光",
            "action": "expand_title",
        })
    elif title_len_ratio > 0.95:
        suggestions.append({
            "type": "seo",
            "priority": "medium",
            "suggestion": "标题接近长度上限，确保关键信息未被截断",
            "action": "check_title_truncation",
        })

    if bullet_result.get("count", 0) < bullet_result.get("max_count", 5):
        suggestions.append({
            "type": "content",
            "priority": "medium",
            "suggestion": f"五点描述仅{bullet_result['count']}条，建议补充到{bullet_result['max_count']}条以提升转化率",
            "action": "add_bullet_points",
        })

    ab_variant = title_result.get("ab_variant", {})
    if ab_variant:
        suggestions.append({
            "type": "ab_test",
            "priority": "low",
            "suggestion": "建议进行标题A/B测试，对比信息型vs情感型标题的点击率差异",
            "action": "run_ab_test",
            "variants": ab_variant,
        })

    kw_len = keyword_result.get("total_length", 0)
    kw_max = keyword_result.get("max_length", 250)
    if kw_len < kw_max * 0.6:
        suggestions.append({
            "type": "seo",
            "priority": "medium",
            "suggestion": f"搜索关键词仅使用了{kw_len}/{kw_max}字节，建议补充长尾词",
            "action": "expand_keywords",
        })

    return suggestions


def generate_listing(input_data: Dict) -> Dict:
    validation = validate_input(input_data)
    if validation["errors"]:
        return {"error": "输入不完整，缺少必填字段", "missing_fields": validation["errors"], "warnings": validation["warnings"]}

    platform_key = get_platform_key(input_data.get('platform', 'amazon'), input_data.get('site', ''))
    platform = input_data.get('platform', 'amazon')
    site = input_data.get('site', '')
    language = input_data.get('language', 'en-US')
    product_name = input_data['product_name']
    category = input_data.get('category', '')
    selling_points = input_data.get('selling_points', [])
    features = input_data.get('features', [])
    specs = input_data.get('specs', {})
    material = input_data.get('material', '')
    brand = input_data.get('brand', '')
    model = input_data.get('model', '')
    color = input_data.get('color', '')
    size = input_data.get('size', '')
    audience = input_data.get('target_audience', '')
    use_cases = input_data.get('use_cases', [])

    rag = RAGRetriever()
    rag_query = f"{product_name} {category} listing optimization rules"
    rag_results = rag.search(rag_query, top_k=5, category="listing_rules", platform=platform)
    compliance_results = rag.search(f"{category} compliance requirements", top_k=3, category="compliance")
    optimization_results = rag.search(f"{platform} listing optimization", top_k=3, category="optimization")

    title_result = generate_title(product_name, selling_points, platform_key, site,
                                  brand, model, color, material, size)
    bullet_result = generate_bullet_points(selling_points, features, specs, platform_key, material, audience)
    keyword_result = generate_search_keywords(product_name, selling_points, category, platform, audience, use_cases)
    desc_result = generate_description(product_name, selling_points, features, material, specs, platform, brand, audience)

    compliance = compliance_check(title_result["title"], bullet_result["bulletPoints"],
                                  desc_result["description"], platform_key, category)

    confidence = calculate_confidence(compliance, input_data, rag_results)

    suggestions = generate_optimization_suggestions(title_result, bullet_result, keyword_result,
                                                    desc_result, compliance, platform)

    needs_human = confidence < 60 or compliance["high_count"] > 0
    reason = ""
    if compliance["high_count"] > 0:
        reason = f"存在{compliance['high_count']}个高风险合规问题"
    elif confidence < 60:
        reason = f"置信度仅{confidence:.0f}%，建议人工复核"

    handoff = {
        "needsHumanReview": needs_human,
        "reason": reason,
        "confidence": round(confidence, 1),
        "gate": "auto" if confidence >= 90 else ("notify" if confidence >= 60 else "human"),
    }

    return {
        "platform": platform,
        "site": site,
        "language": language,
        "title": title_result["title"],
        "titleMeta": {
            "length": title_result["title_length"],
            "maxLength": title_result["max_length"],
            "patternUsed": title_result["pattern_used"],
            "abVariants": title_result["ab_variant"],
        },
        "bulletPoints": bullet_result["bulletPoints"],
        "bulletMeta": {
            "count": bullet_result["count"],
            "maxCount": bullet_result["max_count"],
        },
        "searchKeywords": keyword_result["searchKeywords"],
        "keywordMeta": {
            "totalCount": keyword_result["total_count"],
            "totalLength": keyword_result["total_length"],
            "maxLength": keyword_result["max_length"],
            "strategy": keyword_result["strategy"],
        },
        "description": desc_result["description"],
        "descriptionMeta": {
            "length": desc_result["length"],
            "maxLength": desc_result["max_length"],
        },
        "compliance": compliance,
        "ragReferences": {
            "listingRules": [{"title": r["title"], "score": r["score"]} for r in rag_results],
            "complianceRules": [{"title": r["title"], "score": r["score"]} for r in compliance_results],
            "optimizationTips": [{"title": r["title"], "score": r["score"]} for r in optimization_results],
        },
        "optimizationSuggestions": suggestions,
        "handoff": handoff,
    }


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

    result = generate_listing(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
