from docx import Document
import os

f = r'D:\Project\aims\refrence\OpenClaw零门槛上手：养只"龙虾"替你干活\OpenClaw零门槛上手：养只"龙虾"替你干活-全书代码(1).docx'
if os.path.exists(f):
    doc = Document(f)
    outpath = r'D:\Project\aims\refrence\openclaw_full_code.md'
    with open(outpath, 'w', encoding='utf-8') as out:
        for para in doc.paragraphs:
            out.write(para.text + '\n')
    print(f'Converted: openclaw_full_code.md')
else:
    print(f'Not found: {f}')
