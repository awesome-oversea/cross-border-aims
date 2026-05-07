#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import math
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 快递公司信息库：运单号正则模式、平均时效、覆盖范围
CARRIER_INFO = {
    'sf': {'name': '顺丰速运', 'code': 'SF', 'tracking_pattern': r'SF\d{12}', 'avg_days': 2, 'coverage': '国内'},
    'yt': {'name': '圆通速递', 'code': 'YT', 'tracking_pattern': r'YT\d{13}', 'avg_days': 3, 'coverage': '国内'},
    'zt': {'name': '中通快递', 'code': 'ZT', 'tracking_pattern': r'7\d{13}', 'avg_days': 3, 'coverage': '国内'},
    'sto': {'name': '申通快递', 'code': 'STO', 'tracking_pattern': r'77\d{12}', 'avg_days': 3, 'coverage': '国内'},
    'yd': {'name': '韵达快递', 'code': 'YD', 'tracking_pattern': r'\d{13}', 'avg_days': 3, 'coverage': '国内'},
    'ems': {'name': 'EMS', 'code': 'EMS', 'tracking_pattern': r'[A-Z]{2}\d{9}[A-Z]{2}', 'avg_days': 4, 'coverage': '国际'},
    'dhl': {'name': 'DHL', 'code': 'DHL', 'tracking_pattern': r'\d{10}', 'avg_days': 5, 'coverage': '国际'},
    'fedex': {'name': 'FedEx', 'code': 'FDX', 'tracking_pattern': r'\d{12}', 'avg_days': 5, 'coverage': '国际'},
    'ups': {'name': 'UPS', 'code': 'UPS', 'tracking_pattern': r'1Z[A-Z0-9]{16}', 'avg_days': 5, 'coverage': '国际'},
    'fba': {'name': 'Amazon FBA', 'code': 'FBA', 'tracking_pattern': r'FBA\d{12}', 'avg_days': 7, 'coverage': '跨境'},
}

TRACKING_STATUS_MAP = {
    'info_received': {'label': '信息已收到', 'description': '物流公司已收到订单信息', 'progress': 10},
    'picked_up': {'label': '已揽收', 'description': '快递员已取件', 'progress': 20},
    'in_transit': {'label': '运输中', 'description': '包裹正在运输途中', 'progress': 40},
    'arrived_hub': {'label': '到达中转站', 'description': '包裹已到达中转站', 'progress': 50},
    'departed_hub': {'label': '离开中转站', 'description': '包裹已离开中转站', 'progress': 60},
    'out_for_delivery': {'label': '派送中', 'description': '快递员正在派送', 'progress': 80},
    'delivered': {'label': '已签收', 'description': '包裹已签收', 'progress': 100},
    'exception': {'label': '异常', 'description': '物流出现异常', 'progress': 0},
    'returned': {'label': '退回', 'description': '包裹已退回', 'progress': 0},
}

EXCEPTION_TYPES = {
    'address_issue': {'label': '地址问题', 'suggestion': '请联系快递员确认收货地址', 'severity': 'medium'},
    'contact_issue': {'label': '联系不上收件人', 'suggestion': '请保持电话畅通，等待快递员联系', 'severity': 'medium'},
    'weather_delay': {'label': '天气延误', 'suggestion': '因天气原因延误，请耐心等待', 'severity': 'low'},
    'customs_hold': {'label': '海关扣留', 'suggestion': '包裹正在清关，可能需要提供相关证明', 'severity': 'high'},
    'damaged': {'label': '包裹损坏', 'suggestion': '请联系卖家处理，拍照留证', 'severity': 'high'},
    'lost': {'label': '包裹丢失', 'suggestion': '请联系卖家和快递公司索赔', 'severity': 'critical'},
}

# 跨境物流阶段定义：国内揽收→运输→出口报关→国际运输→进口清关→目的国派送
CROSS_BORDER_STAGES = [
    {'stage': 'domestic_pickup', 'label': '国内揽收', 'avg_hours': 24},
    {'stage': 'domestic_transit', 'label': '国内运输', 'avg_hours': 48},
    {'stage': 'export_customs', 'label': '出口报关', 'avg_hours': 24},
    {'stage': 'international_transit', 'label': '国际运输', 'avg_hours': 72},
    {'stage': 'import_customs', 'label': '进口清关', 'avg_hours': 48},
    {'stage': 'destination_delivery', 'label': '目的国派送', 'avg_hours': 48},
]


def identify_carrier(tracking_number: str) -> Dict:
    import re
    for code, info in CARRIER_INFO.items():
        if re.match(info['tracking_pattern'], tracking_number):
            return {"code": code, **info}
    if tracking_number.startswith('SF'):
        return {"code": 'sf', **CARRIER_INFO['sf']}
    return {"code": "unknown", "name": "未知快递", "avg_days": 5, "coverage": "未知"}


def generate_tracking_timeline(tracking_number: str, carrier_code: str = "") -> Dict:
    carrier = identify_carrier(tracking_number) if not carrier_code else CARRIER_INFO.get(carrier_code, {"name": "未知快递", "avg_days": 5})
    carrier_name = carrier.get('name', '未知快递')

    try:
        seed = int(''.join(filter(str.isdigit, tracking_number))[-4:])
    except (ValueError, IndexError):
        seed = hash(tracking_number) % 10000

    status_keys = list(TRACKING_STATUS_MAP.keys())
    normal_statuses = [k for k in status_keys if k not in ('exception', 'returned')]
    current_idx = seed % len(normal_statuses)
    current_status = normal_statuses[current_idx]

    now = datetime.now()
    timeline = []
    locations = [
        "深圳市南山区科技园营业点",
        "广州市白云区中转站",
        "长沙市岳麓区分拨中心",
        "武汉市江汉区网点",
        "北京市朝阳区派送点",
        "北京市海淀区签收点",
    ]

    for i in range(current_idx + 1):
        status = normal_statuses[i]
        time_offset = timedelta(hours=(current_idx - i) * 8 + seed % 6)
        timeline.append({
            "time": (now - time_offset).strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "label": TRACKING_STATUS_MAP[status]['label'],
            "description": TRACKING_STATUS_MAP[status]['description'],
            "location": locations[i] if i < len(locations) else "",
            "progress": TRACKING_STATUS_MAP[status]['progress'],
        })

    estimated_delivery = now + timedelta(days=carrier.get('avg_days', 3) - current_idx * 0.5)
    if current_status == 'delivered':
        estimated_delivery = now

    return {
        "trackingNumber": tracking_number,
        "carrier": carrier_name,
        "carrierCode": carrier.get('code', 'unknown'),
        "currentStatus": current_status,
        "currentLabel": TRACKING_STATUS_MAP[current_status]['label'],
        "progress": TRACKING_STATUS_MAP[current_status]['progress'],
        "timeline": timeline,
        "estimatedDelivery": estimated_delivery.strftime("%Y-%m-%d"),
        "isDelivered": current_status == 'delivered',
    }


def generate_cross_border_tracking(tracking_number: str, origin: str = "CN", destination: str = "US") -> Dict:
    domestic = generate_tracking_timeline(tracking_number)
    now = datetime.now()
    try:
        seed = int(''.join(filter(str.isdigit, tracking_number))[-3:])
    except (ValueError, IndexError):
        seed = hash(tracking_number) % 1000

    current_stage_idx = seed % len(CROSS_BORDER_STAGES)
    cross_border_timeline = []

    elapsed_hours = 0
    for i in range(current_stage_idx + 1):
        stage = CROSS_BORDER_STAGES[i]
        stage_time = now - timedelta(hours=sum(CROSS_BORDER_STAGES[j]['avg_hours'] for j in range(current_stage_idx, len(CROSS_BORDER_STAGES))) + elapsed_hours)
        elapsed_hours += stage['avg_hours']
        cross_border_timeline.append({
            "stage": stage['stage'],
            "label": stage['label'],
            "status": "completed" if i < current_stage_idx else "in_progress",
            "time": stage_time.strftime("%Y-%m-%d %H:%M:%S"),
            "avgHours": stage['avg_hours'],
        })

    total_hours = sum(s['avg_hours'] for s in CROSS_BORDER_STAGES)
    completed_hours = sum(CROSS_BORDER_STAGES[i]['avg_hours'] for i in range(current_stage_idx))
    progress = round(completed_hours / total_hours * 100, 1)

    return {
        "trackingNumber": tracking_number,
        "type": "cross_border",
        "origin": origin,
        "destination": destination,
        "currentStage": CROSS_BORDER_STAGES[current_stage_idx]['label'],
        "progress": progress,
        "timeline": cross_border_timeline,
        "domesticTracking": domestic,
        "estimatedDelivery": (now + timedelta(hours=total_hours - completed_hours)).strftime("%Y-%m-%d"),
        "totalTransitHours": total_hours,
    }


def detect_exception(tracking_number: str, timeline: List[Dict] = None) -> Dict:
    try:
        seed = int(''.join(filter(str.isdigit, tracking_number))[-2:])
    except (ValueError, IndexError):
        seed = 0

    has_exception = seed % 10 == 0
    if not has_exception:
        return {"hasException": False, "exceptionType": None, "suggestion": ""}

    exception_keys = list(EXCEPTION_TYPES.keys())
    exc_type = exception_keys[seed % len(exception_keys)]
    exc_info = EXCEPTION_TYPES[exc_type]

    return {
        "hasException": True,
        "exceptionType": exc_type,
        "exceptionLabel": exc_info['label'],
        "suggestion": exc_info['suggestion'],
        "severity": exc_info['severity'],
        "needsAction": exc_info['severity'] in ('high', 'critical'),
    }


def estimate_delivery_time(tracking_number: str, destination: str = "") -> Dict:
    carrier = identify_carrier(tracking_number)
    avg_days = carrier.get('avg_days', 3)

    try:
        seed = int(''.join(filter(str.isdigit, tracking_number))[-3:])
    except (ValueError, IndexError):
        seed = 0

    variance = seed % 3 - 1
    estimated_days = max(1, avg_days + variance)

    now = datetime.now()
    estimated_date = now + timedelta(days=estimated_days)

    if estimated_date.weekday() >= 5:
        estimated_date += timedelta(days=2 - estimated_date.weekday() % 5)

    return {
        "trackingNumber": tracking_number,
        "carrier": carrier.get('name', '未知快递'),
        "estimatedDays": estimated_days,
        "estimatedDate": estimated_date.strftime("%Y-%m-%d"),
        "confidence": 0.7 if avg_days <= 3 else 0.5,
        "factors": [
            f"快递公司平均时效: {avg_days}天",
            f"目的地: {destination or '国内'}",
            "周末可能延迟1-2天",
        ],
    }


def track_logistics(input_data: Dict) -> Dict:
    tracking_number = input_data.get('tracking_number', '')
    if not tracking_number:
        return {"error": "需要提供tracking_number"}

    action = input_data.get('action', 'track')
    origin = input_data.get('origin', 'CN')
    destination = input_data.get('destination', '')

    if action == 'track':
        is_cross_border = input_data.get('cross_border', False) or destination not in ('', 'CN', '国内')
        if is_cross_border:
            result = generate_cross_border_tracking(tracking_number, origin, destination)
        else:
            result = generate_tracking_timeline(tracking_number)

        exception = detect_exception(tracking_number, result.get('timeline', []))
        result["exception"] = exception

        needs_human = exception.get('needsAction', False) or exception.get('severity') == 'critical'
        result["handoff"] = {
            "needsHumanReview": needs_human,
            "reason": f"物流异常: {exception.get('exceptionLabel', '')}" if needs_human else "",
            "confidence": 80.0,
            "gate": "human" if needs_human else "auto",
        }
        return result

    elif action == 'estimate':
        return estimate_delivery_time(tracking_number, destination)

    elif action == 'carrier':
        return identify_carrier(tracking_number)

    else:
        return {"error": f"不支持的操作: {action}"}


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

    result = track_logistics(input_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
