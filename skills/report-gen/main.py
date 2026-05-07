#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
from datetime import datetime, timedelta

def validate_input(input_data):
    missing = []
    if not input_data.get("report_type"):
        missing.append("report_type")
    return missing

def generate_daily_report(input_data):
    """生成日报：订单/营收/畅销商品/流量/客服多维度经营数据"""

    date = input_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    platform = input_data.get("platform", "all")
    
    simulated_data = {
        "orders": {
            "total": 1256,
            "completed": 1189,
            "pending": 67,
            "cancelled": 0,
            "growth": 12.5
        },
        "revenue": {
            "total": 895620,
            "avg_order_value": 713,
            "growth": 8.3
        },
        "products": {
            "top_sellers": [
                {"name": "智能手表", "sales": 156, "revenue": 124800},
                {"name": "蓝牙耳机", "sales": 234, "revenue": 70200},
                {"name": "无线充电器", "sales": 312, "revenue": 46800}
            ],
            "new_arrivals": 5
        },
        "traffic": {
            "visitors": 15680,
            "conversion_rate": 8.0,
            "avg_duration": "3分25秒"
        },
        "customer_service": {
            "total_queries": 342,
            "resolved": 328,
            "response_time": "2分15秒",
            "satisfaction_rate": 96.5
        }
    }
    
    report = {
        "title": f"{date} 每日经营报表",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "date": date,
            "platform": platform,
            "period": "日报"
        },
        "sections": [
            {
                "title": "订单概览",
                "data": [
                    {"label": "订单总数", "value": simulated_data["orders"]["total"], "unit": "单", "growth": simulated_data["orders"]["growth"]},
                    {"label": "已完成", "value": simulated_data["orders"]["completed"], "unit": "单"},
                    {"label": "待处理", "value": simulated_data["orders"]["pending"], "unit": "单"},
                    {"label": "取消率", "value": "0%", "unit": ""}
                ]
            },
            {
                "title": "营收数据",
                "data": [
                    {"label": "总营收", "value": f"¥{simulated_data['revenue']['total']:,}", "unit": "", "growth": simulated_data["revenue"]["growth"]},
                    {"label": "客单价", "value": f"¥{simulated_data['revenue']['avg_order_value']}", "unit": ""}
                ]
            },
            {
                "title": "畅销商品TOP3",
                "data": simulated_data["products"]["top_sellers"]
            },
            {
                "title": "流量数据",
                "data": [
                    {"label": "访客数", "value": simulated_data["traffic"]["visitors"], "unit": "人"},
                    {"label": "转化率", "value": simulated_data["traffic"]["conversion_rate"], "unit": "%"},
                    {"label": "平均停留", "value": simulated_data["traffic"]["avg_duration"], "unit": ""}
                ]
            },
            {
                "title": "客服数据",
                "data": [
                    {"label": "咨询量", "value": simulated_data["customer_service"]["total_queries"], "unit": "条"},
                    {"label": "解决率", "value": f"{(simulated_data['customer_service']['resolved']/simulated_data['customer_service']['total_queries'])*100:.1f}%", "unit": ""},
                    {"label": "响应时间", "value": simulated_data["customer_service"]["response_time"], "unit": ""},
                    {"label": "满意度", "value": simulated_data["customer_service"]["satisfaction_rate"], "unit": "%"}
                ]
            }
        ],
        "insights": [
            "今日订单量同比增长12.5%，表现良好",
            "智能手表成为今日销量冠军",
            "客服满意度高达96.5%，值得表扬",
            "转化率略有下降，建议优化商品详情页"
        ],
        "recommendations": [
            "关注待处理订单，尽快完成发货",
            "考虑增加畅销商品库存",
            "继续保持优质的客户服务"
        ]
    }
    
    return report

def generate_weekly_report(input_data):
    """生成周报：周概览/每日趋势/品类排行/洞察/建议"""

    end_date = input_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")
    
    report = {
        "title": f"{start_date} - {end_date} 周经营报表",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "period": "周报",
            "start_date": start_date,
            "end_date": end_date
        },
        "sections": [
            {
                "title": "本周概览",
                "data": [
                    {"label": "订单总数", "value": 8956, "unit": "单", "growth": 8.2},
                    {"label": "总营收", "value": "¥6,258,900", "unit": "", "growth": 6.5},
                    {"label": "访客数", "value": 112580, "unit": "人", "growth": 10.3},
                    {"label": "转化率", "value": 7.9, "unit": "%"}
                ]
            },
            {
                "title": "每日趋势",
                "data": [
                    {"day": "周一", "orders": 1120, "revenue": 786500},
                    {"day": "周二", "orders": 1256, "revenue": 895600},
                    {"day": "周三", "orders": 1342, "revenue": 968500},
                    {"day": "周四", "orders": 1428, "revenue": 1025800},
                    {"day": "周五", "orders": 1568, "revenue": 1156200},
                    {"day": "周六", "orders": 1156, "revenue": 856800},
                    {"day": "周日", "orders": 1086, "revenue": 579500}
                ]
            },
            {
                "title": "品类销售排行",
                "data": [
                    {"category": "3C数码", "sales": 3420, "revenue": "¥2,856,800"},
                    {"category": "家居用品", "sales": 2156, "revenue": "¥1,245,600"},
                    {"category": "美妆护肤", "sales": 1896, "revenue": "¥1,156,800"},
                    {"category": "服饰鞋包", "sales": 1484, "revenue": "¥999,700"}
                ]
            }
        ],
        "insights": [
            "本周整体业绩表现平稳，订单量同比增长8.2%",
            "周五达到本周销售高峰，建议关注周末促销",
            "3C数码品类贡献最大，占比45%",
            "访客增长良好，但转化率略有下降"
        ],
        "recommendations": [
            "加大周末促销力度，提升周末销量",
            "优化商品推荐算法，提升转化率",
            "关注美妆护肤品类，增长潜力大"
        ],
        "next_week_plan": [
            "新品上架：智能手环",
            "促销活动：周末限时折扣",
            "客服培训：提升响应速度"
        ]
    }
    
    return report

def generate_monthly_report(input_data):
    date = input_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    year, month = date[:4], date[5:7]
    
    report = {
        "title": f"{year}年{month}月月度经营报表",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "period": "月报",
            "month": f"{year}-{month}"
        },
        "sections": [
            {
                "title": "月度概览",
                "data": [
                    {"label": "订单总数", "value": 38560, "unit": "单", "growth": 15.3},
                    {"label": "总营收", "value": "¥28,568,900", "unit": "", "growth": 12.8},
                    {"label": "访客数", "value": 486520, "unit": "人", "growth": 18.5},
                    {"label": "转化率", "value": 7.9, "unit": "%"}
                ]
            },
            {
                "title": "销售趋势",
                "data": [
                    {"week": "第1周", "orders": 8956, "revenue": "¥6,528,600"},
                    {"week": "第2周", "orders": 9658, "revenue": "¥7,156,800"},
                    {"week": "第3周", "orders": 10256, "revenue": "¥7,685,200"},
                    {"week": "第4周", "orders": 9690, "revenue": "¥7,198,300"}
                ]
            },
            {
                "title": "平台分布",
                "data": [
                    {"platform": "淘宝", "share": 45, "revenue": "¥12,855,005"},
                    {"platform": "京东", "share": 32, "revenue": "¥9,142,048"},
                    {"platform": "拼多多", "share": 15, "revenue": "¥4,285,335"},
                    {"platform": "抖音", "share": 8, "revenue": "¥2,285,512"}
                ]
            },
            {
                "title": "关键指标",
                "data": [
                    {"label": "客单价", "value": "¥741", "unit": ""},
                    {"label": "复购率", "value": 23.5, "unit": "%"},
                    {"label": "退货率", "value": 4.2, "unit": "%"},
                    {"label": "平均发货时长", "value": "12.5小时", "unit": ""}
                ]
            }
        ],
        "insights": [
            "本月业绩创历史新高，同比增长15.3%",
            "淘宝平台贡献最大，占比45%",
            "复购率保持在23.5%，用户粘性良好",
            "退货率控制在4.2%，低于行业平均水平"
        ],
        "recommendations": [
            "加大抖音渠道投入，增长潜力大",
            "优化供应链，进一步缩短发货时间",
            "推出会员体系，提升复购率"
        ],
        "goals": [
            {"goal": "订单目标", "current": 38560, "target": 40000, "progress": 96.4},
            {"goal": "营收目标", "current": "¥28,568,900", "target": "¥30,000,000", "progress": 95.2},
            {"goal": "转化率目标", "current": 7.9, "target": 8.5, "progress": 92.9}
        ]
    }
    
    return report

def main():
    try:
        input_data = json.loads(sys.stdin.read())
        
        missing = validate_input(input_data)
        if missing:
            sys.stdout.buffer.write((json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False) + "\n").encode('utf-8'))
            return
        
        report_type = input_data.get("report_type", "daily")
        
        if report_type == "daily":
            report = generate_daily_report(input_data)
        elif report_type == "weekly":
            report = generate_weekly_report(input_data)
        elif report_type == "monthly":
            report = generate_monthly_report(input_data)
        else:
            report = generate_daily_report(input_data)
        
        sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False) + "\n").encode('utf-8'))
        
    except Exception as e:
        sys.stdout.buffer.write((json.dumps({"error": str(e)}, ensure_ascii=False) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()