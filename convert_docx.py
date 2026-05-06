from docx import Document
import os

files = [
    r'D:\Project\aims\refrence\OpenClaw零门槛上手：养只"龙虾"替你干活\OpenClaw零门槛上手：养只"龙虾"替你干活-全书代码.docx',
    r'D:\Project\aims\refrence\OpenClaw超级个体实操手册\附录B 常用Skills清单.docx',
    r'D:\Project\aims\refrence\OpenClaw超级个体实操手册\附录C 开箱即用的配置脚本模板.docx',
    r'D:\Project\aims\refrence\OpenClaw超级个体实操手册\附录G 国产Claw全景指南.docx',
    r'D:\Project\aims\refrence\OpenClaw超级个体实操手册\附录A 命令速查表.docx',
    r'D:\Project\aims\refrence\OpenClaw超级个体实操手册\附录F 安全防护指南.docx',
]

for f in files:
    if os.path.exists(f):
        doc = Document(f)
        basename = os.path.splitext(os.path.basename(f))[0]
        outpath = os.path.join(r'D:\Project\aims\refrence', basename + '.md')
        with open(outpath, 'w', encoding='utf-8') as out:
            for para in doc.paragraphs:
                out.write(para.text + '\n')
        print(f'Converted: {basename}')
    else:
        print(f'Not found: {f}')
