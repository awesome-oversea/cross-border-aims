#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json

def validate_input(input_data):
    missing = []
    if not input_data.get("subject"):
        missing.append("subject")
    if not input_data.get("body"):
        missing.append("body")
    return missing

def classify_email(subject, body):
    categories = {
        "customer_service": ["订单", "退款", "售后", "客服", "投诉", "问题", "咨询", "帮助"],
        "business": ["报价", "合同", "合作", "询价", "采购", "招标"],
        "meeting": ["会议", "日程", "时间", "邀约", "面谈"],
        "progress": ["进度", "进展", "汇报", "更新"],
        "general": []
    }
    
    text = (subject + " " + body).lower()
    
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    
    return "general"

def extract_todo_items(body):
    todo_items = []
    lines = body.split('\n')
    for line in lines:
        if any(prefix in line.lower() for prefix in ["需要", "请", "务必", "尽快", "必须", "待办"]):
            todo_items.append(line.strip())
    return todo_items[:5]

def analyze_priority(subject, body):
    priority_keywords = {
        "high": ["紧急", "立刻", "马上", "尽快", "严重", "问题", "故障"],
        "medium": ["请", "需要", "希望", "建议", "计划"],
        "low": ["信息", "通知", "告知", "分享", "说明"]
    }
    
    text = (subject + " " + body).lower()
    
    for priority, keywords in priority_keywords.items():
        if any(keyword in text for keyword in keywords):
            return priority
    
    return "medium"

def check_sensitive(content):
    sensitive_keywords = ["报价", "价格", "合同", "金额", "付款", "转账", "发票", "法律", "合规"]
    return any(keyword in content for keyword in sensitive_keywords)

def generate_reply_draft(category, subject, body, sender):
    drafts = {
        "customer_service": f"""您好！

感谢您的来信，关于"{subject}"的问题，我们已经收到。

我们会尽快为您处理，请耐心等待。如有紧急情况，请直接拨打客服热线。

此致
AIMS客服团队
""",
        "business": f"""您好！

感谢您的业务咨询，关于"{subject}"事宜，我们非常重视。

请提供更多详细信息，我们将尽快安排专人与您对接。

此致
AIMS商务团队
""",
        "meeting": f"""您好！

感谢您的会议邀约，关于"{subject}"的会议安排。

请提供具体时间和地点，我们会尽快确认参会人员并回复。

此致
AIMS团队
""",
        "progress": f"""您好！

感谢您的进度汇报，关于"{subject}"的进展我们已知悉。

请继续保持沟通，如有需要协调的地方请随时告知。

此致
AIMS项目团队
""",
        "general": f"""您好！

感谢您的来信，关于"{subject}"我们已收到。

我们会根据具体内容进行处理，并尽快给您回复。

此致
AIMS团队
"""
    }
    return drafts.get(category, drafts["general"])

def main():
    try:
        input_data = json.loads(sys.stdin.read())
        
        missing = validate_input(input_data)
        if missing:
            sys.stdout.buffer.write((json.dumps({"error": "输入不完整", "missing_fields": missing}, ensure_ascii=False) + "\n").encode('utf-8'))
            return
        
        subject = input_data.get("subject", "")
        body = input_data.get("body", "")
        sender = input_data.get("sender", "")
        attachments = input_data.get("attachments", [])
        
        category = classify_email(subject, body)
        priority = analyze_priority(subject, body)
        todo_items = extract_todo_items(body)
        is_sensitive = check_sensitive(subject + body)
        reply_draft = generate_reply_draft(category, subject, body, sender)
        
        result = {
            "category": category,
            "category_label": {
                "customer_service": "客户服务",
                "business": "商务合作",
                "meeting": "会议邀约",
                "progress": "进度汇报",
                "general": "一般邮件"
            }.get(category, "一般邮件"),
            "priority": priority,
            "priority_label": {
                "high": "高",
                "medium": "中",
                "low": "低"
            }.get(priority, "中"),
            "todo_items": todo_items,
            "is_sensitive": is_sensitive,
            "allow_direct_send": not is_sensitive,
            "approval_required": is_sensitive,
            "reply_draft": reply_draft,
            "suggestion": "涉及敏感内容，需要人工审核后发送" if is_sensitive else "可以直接回复",
            "sender": sender,
            "attachment_count": len(attachments)
        }
        
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=True) + "\n").encode('utf-8'))
        
    except Exception as e:
        sys.stdout.buffer.write((json.dumps({"error": str(e)}, ensure_ascii=True) + "\n").encode('utf-8'))

if __name__ == "__main__":
    main()