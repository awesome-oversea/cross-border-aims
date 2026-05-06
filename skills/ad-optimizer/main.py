#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

BID_STRATEGIES = {
    'conservative': {
        'name': '保守策略',
        'description': '优先控制ACOS，适合新品期或利润敏感产品',
        'max_bid_change': 10,
        'target_acos_range': (15, 25),
        'pause_threshold': {'acos': 50, 'spend_no_conversion': 80},
        'budget_utilization_target': 0.8,
    },
    'moderate': {
        'name': '稳健策略',
        'description': '平衡ACOS与流量，适合成长期产品',
        'max_bid_change': 20,
        'target_acos_range': (20, 35),
        'pause_threshold': {'acos': 60, 'spend_no_conversion': 120},
        'budget_utilization_target': 0.9,
    },
    'aggressive': {
        'name': '激进策略',
        'description': '最大化流量和转化，适合爆款期或高利润产品',
        'max_bid_change': 30,
        'target_acos_range': (25, 45),
        'pause_threshold': {'acos': 80, 'spend_no_conversion': 200},
        'budget_utilization_target': 0.95,
    },
}

BUDGET_ALLOCATION_MODELS = {
    'performance_based': {
        'name': '绩效驱动分配',
        'description': '根据历史表现分配预算，高ROAS活动获得更多预算',
        'formula': 'budget_share = (ROAS_i / sum(ROAS)) * total_budget',
    },
    'pareto_based': {
        'name': '帕累托分配',
        'description': '80%预算给TOP 20%活动，20%预算给潜力活动',
        'formula': 'top_20%_budget = 0.8 * total, rest_budget = 0.2 * total',
    },
    'equal_weighted': {
        'name': '均等分配',
        'description': '所有活动平均分配预算，适合测试期',
        'formula': 'budget_share = total_budget / num_campaigns',
    },
    'lifecycle_based': {
        'name': '生命周期分配',
        'description': '根据产品生命周期阶段分配预算',
        'formula': 'new=30%, growth=40%, mature=20%, decline=10%',
    },
}

CAMPAIGN_TYPE_RULES = {
    'sp': {
        'name': 'Sponsored Products',
        'optimization_focus': ['keyword_bid', 'negative_keywords', 'placement'],
        'bid_strategy': 'dynamic_up_down',
        'typical_acos_range': (15, 35),
    },
    'sb': {
        'name': 'Sponsored Brands',
        'optimization_focus': ['creative', 'keyword_selection', 'landing_page'],
        'bid_strategy': 'dynamic_down',
        'typical_acos_range': (20, 40),
    },
    'sd': {
        'name': 'Sponsored Display',
        'optimization_focus': ['audience_targeting', 'creative', 'bid'],
        'bid_strategy': 'fixed',
        'typical_acos_range': (25, 50),
    },
}

INDUSTRY_BENCHMARKS = {
    'electronics': {'ctr': (0.3, 0.8), 'cvr': (5, 12), 'acos': (18, 30), 'cpc_range': (0.5, 2.0)},
    'clothing': {'ctr': (0.4, 1.0), 'cvr': (3, 8), 'acos': (20, 35), 'cpc_range': (0.3, 1.5)},
    'home': {'ctr': (0.3, 0.7), 'cvr': (4, 10), 'acos': (15, 28), 'cpc_range': (0.4, 1.8)},
    'beauty': {'ctr': (0.5, 1.2), 'cvr': (5, 15), 'acos': (20, 40), 'cpc_range': (0.6, 2.5)},
    'toys': {'ctr': (0.3, 0.9), 'cvr': (4, 10), 'acos': (18, 32), 'cpc_range': (0.4, 1.6)},
    'food': {'ctr': (0.4, 1.0), 'cvr': (8, 18), 'acos': (12, 25), 'cpc_range': (0.3, 1.2)},
}

AD_KNOWLEDGE_BASE = [
    {
        "id": "acos_optimization",
        "category": "ad_strategy",
        "title": "ACOS优化核心策略",
        "content": "ACOS优化三步法：1) 降低无效花费：添加否定关键词、降低高ACOS关键词出价、暂停无转化广告组；2) 提高转化率：优化Listing、A/B测试主图、调整落地页；3) 提高客单价：捆绑销售、关联推荐、提升品牌溢价",
    },
    {
        "id": "bid_strategy_guide",
        "category": "ad_strategy",
        "title": "竞价策略选择指南",
        "content": "竞价策略选择：1) 固定竞价：适合新品测试期，控制成本；2) 动态竞价仅降低：适合稳定期，防止超支；3) 动态竞价提高和降低：适合成长期，抓住转化机会；4) 基于位置的竞价调整：TOP of Search加价0-50%",
    },
    {
        "id": "budget_allocation_guide",
        "category": "ad_strategy",
        "title": "预算分配最佳实践",
        "content": "预算分配原则：1) 70%预算给已验证的高ROAS关键词；2) 20%预算给有潜力的长尾词测试；3) 10%预算给新品曝光；4) 每周review预算利用率，低于80%需调整；5) 旺季前2周提前增加预算50-100%",
    },
    {
        "id": "keyword_optimization",
        "category": "ad_strategy",
        "title": "关键词优化方法论",
        "content": "关键词四象限管理：1) 高转化低ACOS：增加预算和出价，扩大流量；2) 高转化高ACOS：优化出价，精准匹配；3) 低转化低ACOS：优化Listing，提高转化；4) 低转化高ACOS：添加否定词或暂停",
    },
    {
        "id": "seasonal_strategy",
        "category": "ad_strategy",
        "title": "季节性广告策略",
        "content": "季节性广告规划：1) 旺季前4周：增加预算30%，拓展关键词；2) 旺季前2周：预算翻倍，确保广告位；3) 旺季期间：监控ACOS，动态调整出价；4) 旺季后期：逐步降低预算，清理库存；5) 淡季：维持基础曝光，测试新品",
    },
]


def validate_input(input_data: Dict) -> Dict:
    errors = []
    warnings = []
    if not input_data.get('platform'):
        errors.append('platform')
    if not input_data.get('campaign_type'):
        warnings.append('campaign_type')
    metrics = input_data.get('metrics', {})
    if not metrics:
        if 'acos' not in input_data and 'ctr' not in input_data:
            errors.append('metrics (acos, ctr, cvr, roas required)')
    return {"errors": errors, "warnings": warnings}


def extract_metrics(input_data: Dict) -> Dict:
    metrics = input_data.get('metrics', {})
    if not metrics:
        metrics = {}
        for key in ['impressions', 'clicks', 'spend', 'conversions', 'revenue',
                     'acos', 'ctr', 'cvr', 'roas', 'cpc', 'cpa']:
            if key in input_data:
                metrics[key] = input_data[key]
    clicks = metrics.get('clicks', 0)
    spend = metrics.get('spend', 0)
    conversions = metrics.get('conversions', 0)
    revenue = metrics.get('revenue', 0)
    impressions = metrics.get('impressions', 0)

    if clicks > 0 and 'cpc' not in metrics:
        metrics['cpc'] = round(spend / clicks, 2)
    if conversions > 0 and 'cpa' not in metrics:
        metrics['cpa'] = round(spend / conversions, 2)
    if spend > 0 and revenue > 0 and 'roas' not in metrics:
        metrics['roas'] = round(revenue / spend, 2)
    if clicks > 0 and 'ctr' not in metrics:
        metrics['ctr'] = round(clicks / max(impressions, 1) * 100, 2)
    if clicks > 0 and 'cvr' not in metrics:
        metrics['cvr'] = round(conversions / clicks * 100, 2)
    if spend > 0 and revenue > 0 and 'acos' not in metrics:
        metrics['acos'] = round(spend / revenue * 100, 2)

    return metrics


def analyze_campaign_health(metrics: Dict, campaign_type: str, category: str = "",
                            strategy: str = "moderate") -> Dict:
    strategy_config = BID_STRATEGIES.get(strategy, BID_STRATEGIES['moderate'])
    campaign_rules = CAMPAIGN_TYPE_RULES.get(campaign_type, CAMPAIGN_TYPE_RULES['sp'])
    benchmarks = INDUSTRY_BENCHMARKS.get(category, {})

    health_score = 100.0
    issues = []
    strengths = []

    acos = metrics.get('acos', 0)
    ctr = metrics.get('ctr', 0)
    cvr = metrics.get('cvr', 0)
    roas = metrics.get('roas', 0)
    spend = metrics.get('spend', 0)
    conversions = metrics.get('conversions', 0)
    cpc = metrics.get('cpc', 0)

    target_acos_low, target_acos_high = strategy_config['target_acos_range']

    if acos > 0:
        if acos > target_acos_high * 1.5:
            health_score -= 30
            issues.append({"type": "critical_acos", "message": f"ACOS {acos}%远超目标{target_acos_high}%", "severity": "critical"})
        elif acos > target_acos_high:
            health_score -= 15
            issues.append({"type": "high_acos", "message": f"ACOS {acos}%高于目标{target_acos_high}%", "severity": "high"})
        elif acos <= target_acos_low:
            strengths.append({"type": "excellent_acos", "message": f"ACOS {acos}%表现优秀，低于目标{target_acos_low}%"})

    if benchmarks:
        ctr_low, ctr_high = benchmarks.get('ctr', (0.3, 1.0))
        if ctr > 0 and ctr < ctr_low:
            health_score -= 15
            issues.append({"type": "low_ctr", "message": f"CTR {ctr}%低于行业均值{ctr_low}%", "severity": "medium"})
        elif ctr > 0 and ctr >= ctr_high:
            strengths.append({"type": "high_ctr", "message": f"CTR {ctr}%高于行业均值"})

        cvr_low, cvr_high = benchmarks.get('cvr', (3, 10))
        if cvr > 0 and cvr < cvr_low:
            health_score -= 15
            issues.append({"type": "low_cvr", "message": f"CVR {cvr}%低于行业均值{cvr_low}%", "severity": "medium"})
        elif cvr > 0 and cvr >= cvr_high:
            strengths.append({"type": "high_cvr", "message": f"CVR {cvr}%高于行业均值"})

    pause_acos = strategy_config['pause_threshold']['acos']
    pause_spend = strategy_config['pause_threshold']['spend_no_conversion']
    if acos > pause_acos:
        health_score -= 20
        issues.append({"type": "should_pause", "message": f"ACOS {acos}%超过暂停阈值{pause_acos}%，建议暂停", "severity": "critical"})
    if spend > pause_spend and conversions == 0:
        health_score -= 25
        issues.append({"type": "no_conversion", "message": f"花费{spend}无转化，超过阈值{pause_spend}", "severity": "critical"})

    health_score = max(0, min(100, health_score))

    if health_score >= 80:
        status = "healthy"
    elif health_score >= 50:
        status = "warning"
    else:
        status = "critical"

    return {
        "healthScore": round(health_score, 1),
        "status": status,
        "issues": issues,
        "strengths": strengths,
        "strategyUsed": strategy,
        "campaignType": campaign_type,
    }


def generate_bid_recommendations(metrics: Dict, campaign_type: str, strategy: str = "moderate",
                                  keywords: List[Dict] = None) -> Dict:
    strategy_config = BID_STRATEGIES.get(strategy, BID_STRATEGIES['moderate'])
    max_change = strategy_config['max_bid_change']
    target_acos_low, target_acos_high = strategy_config['target_acos_range']

    campaign_bid = None
    acos = metrics.get('acos', 0)
    cpc = metrics.get('cpc', 0)
    roas = metrics.get('roas', 0)

    if cpc > 0:
        if acos > target_acos_high:
            over_ratio = (acos - target_acos_high) / target_acos_high
            decrease_pct = min(over_ratio * 30, max_change)
            campaign_bid = {
                "action": "decrease",
                "percentage": round(decrease_pct, 1),
                "current_cpc": cpc,
                "suggested_cpc": round(cpc * (1 - decrease_pct / 100), 2),
                "reason": f"ACOS {acos}%高于目标{target_acos_high}%，建议降低出价{round(decrease_pct, 1)}%",
                "requires_approval": decrease_pct > 15,
            }
        elif acos < target_acos_low and roas > 3:
            increase_pct = min(15, max_change)
            campaign_bid = {
                "action": "increase",
                "percentage": round(increase_pct, 1),
                "current_cpc": cpc,
                "suggested_cpc": round(cpc * (1 + increase_pct / 100), 2),
                "reason": f"ACOS {acos}%低于目标{target_acos_low}%且ROAS优秀，建议提高出价获取更多流量",
                "requires_approval": False,
            }
        else:
            campaign_bid = {
                "action": "maintain",
                "percentage": 0,
                "current_cpc": cpc,
                "suggested_cpc": cpc,
                "reason": f"ACOS {acos}%在目标范围内，维持当前出价",
                "requires_approval": False,
            }

    keyword_bids = []
    if keywords:
        for kw in keywords:
            kw_acos = kw.get('acos', 0)
            kw_cpc = kw.get('cpc', 0)
            kw_conversions = kw.get('conversions', 0)
            kw_spend = kw.get('spend', 0)
            kw_name = kw.get('name', 'unknown')

            if kw_acos > target_acos_high * 1.5 and kw_conversions == 0:
                keyword_bids.append({
                    "keyword": kw_name,
                    "action": "pause",
                    "reason": f"ACOS {kw_acos}%过高且无转化",
                    "suggested_cpc": 0,
                    "requires_approval": True,
                })
            elif kw_acos > target_acos_high:
                decrease = min((kw_acos - target_acos_high) / target_acos_high * 25, max_change)
                keyword_bids.append({
                    "keyword": kw_name,
                    "action": "decrease",
                    "percentage": round(decrease, 1),
                    "current_cpc": kw_cpc,
                    "suggested_cpc": round(kw_cpc * (1 - decrease / 100), 2),
                    "reason": f"ACOS {kw_acos}%高于目标",
                    "requires_approval": decrease > 15,
                })
            elif kw_acos < target_acos_low and kw_conversions > 3:
                increase = min(10, max_change * 0.5)
                keyword_bids.append({
                    "keyword": kw_name,
                    "action": "increase",
                    "percentage": round(increase, 1),
                    "current_cpc": kw_cpc,
                    "suggested_cpc": round(kw_cpc * (1 + increase / 100), 2),
                    "reason": f"ACOS优秀{kw_acos}%，增加流量",
                    "requires_approval": False,
                })

    return {
        "campaignBid": campaign_bid,
        "keywordBids": keyword_bids,
        "strategy": strategy,
        "strategyName": strategy_config['name'],
    }


def allocate_budget(campaigns: List[Dict], total_budget: float,
                     model: str = "performance_based") -> Dict:
    if not campaigns:
        return {"error": "无广告活动数据", "allocations": []}

    allocations = []

    if model == "performance_based":
        total_roas = sum(max(c.get('roas', 0), 0.1) for c in campaigns)
        for c in campaigns:
            roas = max(c.get('roas', 0), 0.1)
            share = roas / total_roas
            allocated = round(total_budget * share, 2)
            allocations.append({
                "campaign": c.get('name', c.get('campaign_id', 'unknown')),
                "current_budget": c.get('budget', 0),
                "allocated_budget": allocated,
                "share_percentage": round(share * 100, 1),
                "roas": roas,
                "change": round(allocated - c.get('budget', 0), 2),
            })
    elif model == "pareto_based":
        sorted_campaigns = sorted(campaigns, key=lambda x: x.get('roas', 0), reverse=True)
        top_count = max(1, len(sorted_campaigns) // 5)
        top_budget = total_budget * 0.8
        rest_budget = total_budget * 0.2
        for i, c in enumerate(sorted_campaigns):
            if i < top_count:
                allocated = round(top_budget / top_count, 2)
                tier = "top"
            else:
                allocated = round(rest_budget / max(1, len(sorted_campaigns) - top_count), 2)
                tier = "growth"
            allocations.append({
                "campaign": c.get('name', c.get('campaign_id', 'unknown')),
                "current_budget": c.get('budget', 0),
                "allocated_budget": allocated,
                "tier": tier,
                "roas": c.get('roas', 0),
                "change": round(allocated - c.get('budget', 0), 2),
            })
    elif model == "lifecycle_based":
        lifecycle_shares = {'new': 0.30, 'growth': 0.40, 'mature': 0.20, 'decline': 0.10}
        lifecycle_campaigns = {'new': [], 'growth': [], 'mature': [], 'decline': []}
        for c in campaigns:
            stage = c.get('lifecycle', 'growth')
            lifecycle_campaigns[stage].append(c)
        for stage, share in lifecycle_shares.items():
            stage_budget = total_budget * share
            stage_camps = lifecycle_campaigns[stage]
            if stage_camps:
                per_campaign = round(stage_budget / len(stage_camps), 2)
                for c in stage_camps:
                    allocations.append({
                        "campaign": c.get('name', c.get('campaign_id', 'unknown')),
                        "current_budget": c.get('budget', 0),
                        "allocated_budget": per_campaign,
                        "lifecycle": stage,
                        "share_percentage": round(share * 100, 1),
                        "change": round(per_campaign - c.get('budget', 0), 2),
                    })
    else:
        per_campaign = round(total_budget / len(campaigns), 2)
        for c in campaigns:
            allocations.append({
                "campaign": c.get('name', c.get('campaign_id', 'unknown')),
                "current_budget": c.get('budget', 0),
                "allocated_budget": per_campaign,
                "share_percentage": round(100 / len(campaigns), 1),
                "change": round(per_campaign - c.get('budget', 0), 2),
            })

    return {
        "model": model,
        "modelName": BUDGET_ALLOCATION_MODELS.get(model, BUDGET_ALLOCATION_MODELS['equal_weighted'])['name'],
        "totalBudget": total_budget,
        "allocations": allocations,
    }


def forecast_roi(metrics: Dict, proposed_changes: Dict = None, days: int = 30) -> Dict:
    current_daily_spend = metrics.get('spend', 0)
    current_daily_revenue = metrics.get('revenue', 0)
    current_daily_conversions = metrics.get('conversions', 0)
    current_roas = metrics.get('roas', 0)
    current_acos = metrics.get('acos', 0)

    if proposed_changes:
        spend_change = proposed_changes.get('spend_change_pct', 0)
        bid_change = proposed_changes.get('bid_change_pct', 0)
        projected_daily_spend = current_daily_spend * (1 + spend_change / 100)
        if bid_change < 0:
            cvr_improvement = abs(bid_change) * 0.3
            projected_daily_revenue = current_daily_revenue * (1 + cvr_improvement / 100)
        elif bid_change > 0:
            traffic_increase = bid_change * 0.5
            projected_daily_revenue = current_daily_revenue * (1 + traffic_increase / 100)
        else:
            projected_daily_revenue = current_daily_revenue
    else:
        projected_daily_spend = current_daily_spend
        projected_daily_revenue = current_daily_revenue

    if projected_daily_spend > 0:
        projected_roas = round(projected_daily_revenue / projected_daily_spend, 2)
        projected_acos = round(projected_daily_spend / max(projected_daily_revenue, 1) * 100, 2)
    else:
        projected_roas = 0
        projected_acos = 0

    projected_monthly_spend = round(projected_daily_spend * days, 2)
    projected_monthly_revenue = round(projected_daily_revenue * days, 2)
    projected_monthly_profit = round(projected_monthly_revenue - projected_monthly_spend, 2)

    confidence = 70
    if current_daily_conversions < 5:
        confidence -= 20
    if current_daily_spend < 10:
        confidence -= 15
    confidence = max(30, min(90, confidence))

    return {
        "currentMetrics": {
            "dailySpend": current_daily_spend,
            "dailyRevenue": current_daily_revenue,
            "roas": current_roas,
            "acos": current_acos,
        },
        "projectedMetrics": {
            "dailySpend": round(projected_daily_spend, 2),
            "dailyRevenue": round(projected_daily_revenue, 2),
            "roas": projected_roas,
            "acos": projected_acos,
        },
        "monthlyForecast": {
            "totalSpend": projected_monthly_spend,
            "totalRevenue": projected_monthly_revenue,
            "totalProfit": projected_monthly_profit,
            "days": days,
        },
        "confidence": confidence,
        "disclaimer": "预测基于历史数据趋势，实际结果可能因市场变化而不同",
    }


def analyze_ad_portfolio(campaigns: List[Dict], category: str = "") -> Dict:
    if not campaigns:
        return {"error": "无广告活动组合数据"}

    total_spend = sum(c.get('spend', 0) for c in campaigns)
    total_revenue = sum(c.get('revenue', 0) for c in campaigns)
    total_conversions = sum(c.get('conversions', 0) for c in campaigns)

    portfolio_roas = round(total_revenue / max(total_spend, 1), 2)
    portfolio_acos = round(total_spend / max(total_revenue, 1) * 100, 2)

    type_distribution = {}
    for c in campaigns:
        ctype = c.get('campaign_type', 'sp')
        if ctype not in type_distribution:
            type_distribution[ctype] = {'count': 0, 'spend': 0, 'revenue': 0, 'conversions': 0}
        type_distribution[ctype]['count'] += 1
        type_distribution[ctype]['spend'] += c.get('spend', 0)
        type_distribution[ctype]['revenue'] += c.get('revenue', 0)
        type_distribution[ctype]['conversions'] += c.get('conversions', 0)

    type_analysis = {}
    for ctype, data in type_distribution.items():
        type_roas = round(data['revenue'] / max(data['spend'], 1), 2)
        spend_share = round(data['spend'] / max(total_spend, 1) * 100, 1)
        type_analysis[ctype] = {
            "name": CAMPAIGN_TYPE_RULES.get(ctype, {}).get('name', ctype),
            "count": data['count'],
            "spend": round(data['spend'], 2),
            "revenue": round(data['revenue'], 2),
            "roas": type_roas,
            "spendShare": spend_share,
            "conversions": data['conversions'],
        }

    recommendations = []
    for ctype, analysis in type_analysis.items():
        if analysis['roas'] < 1.5 and analysis['spendShare'] > 20:
            recommendations.append({
                "type": "rebalance",
                "target": ctype,
                "suggestion": f"{analysis['name']}ROAS仅{analysis['roas']}但占预算{analysis['spendShare']}%，建议减少预算分配",
                "priority": "high",
            })
        if ctype == 'sp' and analysis['spendShare'] < 50:
            recommendations.append({
                "type": "increase",
                "target": ctype,
                "suggestion": f"SP广告仅占{analysis['spendShare']}%，建议提升到50%以上作为核心流量来源",
                "priority": "medium",
            })

    return {
        "portfolioMetrics": {
            "totalCampaigns": len(campaigns),
            "totalSpend": round(total_spend, 2),
            "totalRevenue": round(total_revenue, 2),
            "totalConversions": total_conversions,
            "portfolioROAS": portfolio_roas,
            "portfolioACOS": portfolio_acos,
        },
        "typeAnalysis": type_analysis,
        "recommendations": recommendations,
    }


def optimize_advertising(input_data: Dict) -> Dict:
    validation = validate_input(input_data)
    if validation["errors"]:
        return {"error": "输入不完整", "missing_fields": validation["errors"], "warnings": validation["warnings"]}

    platform = input_data.get('platform', 'amazon')
    campaign_type = input_data.get('campaign_type', 'sp')
    category = input_data.get('category', '')
    strategy = input_data.get('strategy', 'moderate')
    action = input_data.get('action', 'full_analysis')

    metrics = extract_metrics(input_data)

    result = {"platform": platform, "campaignType": campaign_type, "action": action}

    if action in ('full_analysis', 'health_check'):
        result["healthAnalysis"] = analyze_campaign_health(metrics, campaign_type, category, strategy)

    if action in ('full_analysis', 'bid_optimization'):
        keywords = input_data.get('keywords', [])
        result["bidRecommendations"] = generate_bid_recommendations(metrics, campaign_type, strategy, keywords)

    if action in ('full_analysis', 'budget_allocation'):
        campaigns = input_data.get('campaigns', [])
        total_budget = input_data.get('total_budget', 0)
        model = input_data.get('budget_model', 'performance_based')
        if campaigns and total_budget > 0:
            result["budgetAllocation"] = allocate_budget(campaigns, total_budget, model)

    if action in ('full_analysis', 'roi_forecast'):
        proposed_changes = input_data.get('proposed_changes', None)
        forecast_days = input_data.get('forecast_days', 30)
        result["roiForecast"] = forecast_roi(metrics, proposed_changes, forecast_days)

    if action in ('full_analysis', 'portfolio_analysis'):
        campaigns = input_data.get('campaigns', [])
        if campaigns:
            result["portfolioAnalysis"] = analyze_ad_portfolio(campaigns, category)

    result["metrics"] = metrics
    result["strategy"] = {
        "name": BID_STRATEGIES.get(strategy, BID_STRATEGIES['moderate'])['name'],
        "description": BID_STRATEGIES.get(strategy, BID_STRATEGIES['moderate'])['description'],
        "id": strategy,
    }

    health = result.get("healthAnalysis", {})
    needs_human = health.get("status") == "critical" or any(
        i.get("severity") == "critical" for i in health.get("issues", [])
    )
    result["handoff"] = {
        "needsHumanReview": needs_human,
        "reason": "存在严重广告问题需要人工决策" if needs_human else "",
        "confidence": health.get("healthScore", 50),
        "gate": "auto" if health.get("healthScore", 50) >= 90 else ("notify" if health.get("healthScore", 50) >= 60 else "human"),
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

    result = optimize_advertising(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
