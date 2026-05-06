#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from typing import Dict, List, Optional

# 文档类型模板
DOCUMENT_TEMPLATES = {
    'weekly_report': {
        'description': '周报',
        'structure': ['本周工作总结', '工作成果', '遇到的问题', '下周工作计划'],
        'required_fields': ['week', 'department', 'author']
    },
    'meeting_minutes': {
        'description': '会议纪要',
        'structure': ['会议主题', '参会人员', '会议时间', '会议内容', '决议事项', '待办事项'],
        'required_fields': ['title', 'date', 'participants']
    },
    'project_plan': {
        'description': '项目计划',
        'structure': ['项目背景', '目标', '阶段计划', '资源需求', '风险评估'],
        'required_fields': ['project_name', 'objective']
    },
    'summary': {
        'description': '摘要',
        'structure': ['核心内容', '关键要点', '结论建议'],
        'required_fields': []
    },
    'business_case': {
        'description': '业务方案',
        'structure': ['需求分析', '方案设计', '实施步骤', '预期效果', '成本预算'],
        'required_fields': ['title', 'objective']
    }
}

# 风险关键词
RISK_KEYWORDS = [
    '合同', '协议', '法律', '法规', '合规', '条款',
    '保密', '机密', '隐私', '敏感',
    '对外公告', '声明', '通知', '公告'
]

def validate_input(input_data: Dict) -> List[str]:
    """校验输入数据"""
    missing_fields = []
    
    if 'content' not in input_data or not input_data.get('content'):
        missing_fields.append('content')
    
    if 'document_type' not in input_data or not input_data.get('document_type'):
        missing_fields.append('document_type')
    
    # 检查特定文档类型的必填字段
    doc_type = input_data.get('document_type')
    if doc_type in DOCUMENT_TEMPLATES:
        for field in DOCUMENT_TEMPLATES[doc_type]['required_fields']:
            if field not in input_data:
                missing_fields.append(field)
    
    return missing_fields

def extract_key_points(content: str) -> List[str]:
    """提取关键要点"""
    points = []
    
    # 按段落分割
    paragraphs = re.split(r'[\n\r]+', content)
    
    for para in paragraphs:
        para = para.strip()
        if len(para) < 10:
            continue
        
        # 提取以数字或符号开头的列表项
        list_match = re.match(r'^[\d\-\*·]+[\s\.]+(.+)', para)
        if list_match:
            points.append(list_match.group(1).strip())
        else:
            # 提取句子主干
            sentences = re.split(r'[。！？]', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 10:
                    # 提取主谓宾结构（简化处理）
                    points.append(sentence[:50] + '...' if len(sentence) > 50 else sentence)
    
    return list(set(points))[:10]

def generate_summary(content: str) -> str:
    """生成摘要"""
    # 简单摘要：取前300字
    clean_content = re.sub(r'\s+', ' ', content)
    if len(clean_content) <= 300:
        return clean_content
    else:
        return clean_content[:300] + '...（全文共{}字）'.format(len(clean_content))

def generate_document(content: str, doc_type: str, metadata: Dict) -> Dict:
    """生成结构化文档"""
    template = DOCUMENT_TEMPLATES.get(doc_type, DOCUMENT_TEMPLATES['summary'])
    
    document = {
        'document_type': doc_type,
        'document_type_label': template['description'],
        'metadata': metadata,
        'summary': generate_summary(content),
        'key_points': extract_key_points(content),
        'sections': []
    }
    
    # 根据模板生成章节
    for section in template['structure']:
        document['sections'].append({
            'title': section,
            'content': '',
            'status': 'draft'
        })
    
    # 填充部分内容
    if doc_type == 'weekly_report':
        document['sections'][0]['content'] = f"【{metadata.get('week', '')}周报】\n\n{generate_summary(content)}"
        document['sections'][1]['content'] = "\n".join([f"- {point}" for point in document['key_points'][:5]])
        document['sections'][3]['content'] = "待补充：下周具体工作计划"
    
    elif doc_type == 'meeting_minutes':
        document['sections'][0]['content'] = metadata.get('title', '')
        document['sections'][1]['content'] = metadata.get('participants', '')
        document['sections'][2]['content'] = metadata.get('date', '')
        document['sections'][3]['content'] = generate_summary(content)
        document['sections'][4]['content'] = "待讨论确定"
        document['sections'][5]['content'] = "\n".join([f"- [ ] 待办事项" for _ in range(3)])
    
    elif doc_type == 'project_plan':
        document['sections'][0]['content'] = generate_summary(content)
        document['sections'][1]['content'] = metadata.get('objective', '')
        document['sections'][2]['content'] = "阶段1：准备阶段\n阶段2：实施阶段\n阶段3：验收阶段"
        document['sections'][3]['content'] = "待评估"
        document['sections'][4]['content'] = "待识别"
    
    elif doc_type == 'business_case':
        document['sections'][0]['content'] = generate_summary(content)
        document['sections'][1]['content'] = metadata.get('objective', '')
        document['sections'][2]['content'] = "步骤1：需求确认\n步骤2：方案设计\n步骤3：开发实施\n步骤4：上线验收"
        document['sections'][3]['content'] = "待评估"
        document['sections'][4]['content'] = "待估算"
    
    return document

def check_risk(content: str, doc_type: str) -> List[str]:
    """检查风险内容"""
    risks = []
    
    # 检查风险关键词
    for keyword in RISK_KEYWORDS:
        if keyword in content:
            risks.append(f"文档内容包含风险关键词: {keyword}")
    
    # 特定文档类型风险
    high_risk_types = ['contract', 'agreement', 'legal', 'announcement']
    if any(t in doc_type.lower() for t in high_risk_types):
        risks.append(f"文档类型为{doc_type}，涉及正式文件，建议人工复核")
    
    return risks

def check_missing_info(document: Dict) -> List[str]:
    """检查缺失信息"""
    missing = []
    
    # 检查必填字段
    doc_type = document['document_type']
    template = DOCUMENT_TEMPLATES.get(doc_type, {})
    
    for field in template.get('required_fields', []):
        if not document['metadata'].get(field):
            missing.append(f"缺少必要信息: {field}")
    
    # 检查章节内容
    for section in document['sections']:
        if not section['content'] or section['content'] == '待补充：':
            missing.append(f"章节「{section['title']}」内容为空")
    
    return missing

def automate_document(input_data: Dict) -> Dict:
    """自动化文档处理"""
    # 1. 校验输入
    missing_fields = validate_input(input_data)
    if missing_fields:
        return {
            'error': '输入不完整',
            'missing_fields': missing_fields
        }
    
    content = input_data['content']
    doc_type = input_data['document_type']
    metadata = input_data.get('metadata', {})
    
    # 2. 生成结构化文档
    document = generate_document(content, doc_type, metadata)
    
    # 3. 检查风险
    risks = check_risk(content, doc_type)
    
    # 4. 检查缺失信息
    missing_info = check_missing_info(document)
    
    # 5. 判断是否需要人工复核
    needs_human_review = len(risks) > 0 or len(missing_info) > 0
    
    return {
        'success': True,
        'document': document,
        'risks': risks,
        'missing_info': missing_info,
        'needs_human_review': needs_human_review,
        'review_reason': risks[0] if risks else (missing_info[0] if missing_info else '')
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
    
    # 处理文档
    result = automate_document(input_data)
    
    # 输出结果
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()