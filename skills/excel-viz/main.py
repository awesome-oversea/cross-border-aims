#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
from datetime import datetime

def validate_input(input_data):
    missing = []
    if not input_data.get("data"):
        missing.append("data")
    if not input_data.get("chart_type"):
        missing.append("chart_type")
    return missing

def generate_chart_spec(data, chart_type, title=""):
    spec_templates = {
        "bar": {
            "type": "bar",
            "title": title,
            "xField": "name",
            "yField": "value",
            "seriesField": None,
            "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
        },
        "line": {
            "type": "line",
            "title": title,
            "xField": "name",
            "yField": "value",
            "seriesField": None,
            "smooth": True,
            "color": ["#5470c6"]
        },
        "pie": {
            "type": "pie",
            "title": title,
            "angleField": "value",
            "colorField": "name",
            "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]
        },
        "area": {
            "type": "area",
            "title": title,
            "xField": "name",
            "yField": "value",
            "seriesField": None,
            "smooth": True,
            "color": ["rgba(84, 112, 198, 0.3)"]
        },
        "scatter": {
            "type": "scatter",
            "title": title,
            "xField": "x",
            "yField": "y",
            "colorField": "category",
            "color": ["#5470c6", "#91cc75", "#fac858"]
        },
        "funnel": {
            "type": "funnel",
            "title": title,
            "xField": "value",
            "yField": "name",
            "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
        },
        "radar": {
            "type": "radar",
            "title": title,
            "indicator": [],
            "data": []
        },
        "gauge": {
            "type": "gauge",
            "title": title,
            "valueField": "value",
            "min": 0,
            "max": 100,
            "color": ["#30bf78", "#fac858", "#ee6666"]
        }
    }
    
    spec = spec_templates.get(chart_type, spec_templates["bar"])
    
    if chart_type == "radar":
        indicators = [{"name": item["name"], "max": max([d["value"] for d in data])} for item in data]
        spec["indicator"] = indicators
        spec["data"] = [{"name": "数据", "value": [item["value"] for item in data]}]
    elif chart_type == "gauge":
        spec["valueField"] = data[0]["value"] if data else 0
        spec["min"] = 0
        spec["max"] = 100
    else:
        spec["data"] = data
    
    return spec

def generate_excel_formula(data, operation):
    formulas = {
        "sum": f"=SUM({','.join([f'A{i+1}' for i in range(len(data))])})",
        "avg": f"=AVERAGE({','.join([f'A{i+1}' for i in range(len(data))])})",
        "max": f"=MAX({','.join([f'A{i+1}' for i in range(len(data))])})",
        "min": f"=MIN({','.join([f'A{i+1}' for i in range(len(data))])})",
        "count": f"=COUNT({','.join([f'A{i+1}' for i in range(len(data))])})",
        "median": f"=MEDIAN({','.join([f'A{i+1}' for i in range(len(data))])})",
        "stdev": f"=STDEV.S({','.join([f'A{i+1}' for i in range(len(data))])})"
    }
    return formulas.get(operation, "")

def analyze_data(data):
    if not data:
        return {}
    
    values = [item["value"] for item in data if isinstance(item.get("value"), (int, float))]
    
    if not values:
        return {}
    
    return {
        "count": len(values),
        "sum": sum(values),
        "avg": sum(values) / len(values),
        "max": max(values),
        "min": min(values),
        "range": max(values) - min(values),
        "variance": sum((v - sum(values)/len(values))**2 for v in values) / len(values) if len(values) > 1 else 0
    }

def generate_table_html(data, headers=None):
    if not data:
        return "<p>暂无数据</p>"
    
    if headers is None:
        headers = list(data[0].keys()) if data else []
    
    html = "<table style='border-collapse: collapse; width: 100%; border: 1px solid #ddd;'>"
    html += "<thead><tr>"
    for header in headers:
        html += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2;'>{header}</th>"
    html += "</tr></thead><tbody>"
    
    for row in data:
        html += "<tr>"
        for header in headers:
            value = row.get(header, "")
            html += f"<td style='border: 1px solid #ddd; padding: 8px;'>{value}</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html

def main():
    try:
        input_data = json.loads(sys.stdin.read())
        
        missing = validate_input(input_data)
        if missing:
            sys.stdout.buffer.write((json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False) + "\n").encode('utf-8'))
            return
        
        data = input_data.get("data", [])
        chart_type = input_data.get("chart_type", "bar")
        title = input_data.get("title", "")
        operation = input_data.get("operation", "")
        
        chart_spec = generate_chart_spec(data, chart_type, title)
        stats = analyze_data(data)
        formula = generate_excel_formula(data, operation) if operation else ""
        table_html = generate_table_html(data)
        
        result = {
            "chart_spec": chart_spec,
            "chart_type": chart_type,
            "title": title,
            "statistics": stats,
            "excel_formula": formula,
            "table_html": table_html,
            "data_summary": {
                "rows": len(data),
                "columns": len(data[0].keys()) if data else 0,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "suggestions": [
                f"数据共{len(data)}条记录",
                f"建议选择{chart_type}图表进行可视化展示",
                "如需更复杂的分析，可以使用数据透视表功能"
            ]
        }
        
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True) + "\n").encode('utf-8'))
        
    except Exception as e:
        sys.stdout.buffer.write((json.dumps({"error": str(e)}, ensure_ascii=True) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()