import docx
import os

base = r'd:\Project\aims\refrence\openclaw 权威指南配套素材与资源合集\书本配套可复制素材合集14个'
output = r'd:\Project\aims\docx_extract_output.txt'

docx_files = [f for f in os.listdir(base) if f.endswith('.docx')]

with open(output, 'w', encoding='utf-8') as f:
    for fname in sorted(docx_files):
        fpath = os.path.join(base, fname)
        f.write(f'\n{"="*80}\n')
        f.write(f'FILE: {fname}\n')
        f.write(f'{"="*80}\n')
        try:
            doc = docx.Document(fpath)
            for para in doc.paragraphs:
                if para.text.strip():
                    f.write(para.text + '\n')
        except Exception as e:
            f.write(f'[ERROR] {fname}: {e}\n')

print(f'Done! Output saved to {output}')
