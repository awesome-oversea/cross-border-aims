import pdfplumber
import os
import sys

base = r'd:\Project\aims\refrence\openclaw 权威指南配套素材与资源合集\OpenClaw资源分类合集20 个'

pdfs = [
    ('01-入门与部署', 'openclaw-01-快速上手指南.pdf'),
    ('01-入门与部署', 'openclaw-09-Gateway部署与运维.pdf'),
    ('02-配置与管理', 'openclaw-10-配置详解.pdf'),
    ('02-配置与管理', 'openclaw-11-安全与权限管理.pdf'),
    ('02-配置与管理', 'openclaw-18-环境变量速查表.pdf'),
    ('03-功能与应用', 'openclaw-03-渠道配置全攻略.pdf'),
    ('03-功能与应用', 'openclaw-04-模型提供商指南.pdf'),
    ('03-功能与应用', 'openclaw-05-工具功能大全.pdf'),
    ('03-功能与应用', 'openclaw-06-自动化工作流.pdf'),
    ('03-功能与应用', 'openclaw-07-核心概念与架构.pdf'),
    ('03-功能与应用', 'openclaw-12-插件开发指南.pdf'),
    ('03-功能与应用', 'openclaw-13-高级配置与定制.pdf'),
    ('03-功能与应用', 'openclaw-15-最佳实践与案例.pdf'),
    ('04-运维与故障', 'openclaw-14-故障排除手册.pdf'),
    ('04-运维与故障', 'openclaw-19-故障排除速查表.pdf'),
    ('04-运维与故障', 'openclaw-20-安全配置检查清单.pdf'),
    ('05-速查参考', 'openclaw-16-配置模板速查表.pdf'),
    ('05-速查参考', 'openclaw-17-Slash命令速查表.pdf'),
]

for folder, fname in pdfs:
    pdf_path = os.path.join(base, folder, fname)
    if not os.path.exists(pdf_path):
        print(f'[SKIP] {fname} not found')
        continue
    print(f'\n{"="*80}')
    print(f'FILE: {fname}')
    print(f'{"="*80}')
    try:
        with pdfplumber.open(pdf_path) as pdf:
            max_pages = min(len(pdf.pages), 25)
            for i, page in enumerate(pdf.pages[:max_pages]):
                text = page.extract_text()
                if text:
                    print(f'--- Page {i+1}/{len(pdf.pages)} ---')
                    print(text[:1500])
    except Exception as e:
        print(f'[ERROR] {fname}: {e}')
