from docx import Document
import os

base_dir = r'D:\Project\aims\refrence'
subdir = None
for d in os.listdir(base_dir):
    full = os.path.join(base_dir, d)
    if os.path.isdir(full) and 'OpenClaw' in d and '龙虾' in d:
        subdir = full
        print(f'Found dir: {d}')
        for fn in os.listdir(full):
            print(f'  File: {fn}')
            if '全书代码' in fn:
                filepath = os.path.join(full, fn)
                print(f'  Converting: {filepath}')
                doc = Document(filepath)
                outpath = os.path.join(base_dir, 'openclaw_full_code.md')
                with open(outpath, 'w', encoding='utf-8') as out:
                    for para in doc.paragraphs:
                        out.write(para.text + '\n')
                print(f'  Converted to openclaw_full_code.md')
        break

if not subdir:
    print('No matching directory found')
