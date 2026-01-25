import json

with open('echuu_with_tts_cleaned.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print(f"Cell 数量: {len(nb['cells'])}")
print("=" * 70)

for i, cell in enumerate(nb['cells']):
    source = cell.get('source', [])
    if isinstance(source, list):
        first_line = source[0].strip() if source else ""
    else:
        first_line = source.split('\n')[0].strip() if source else ""
    
    cell_type = "MD" if cell['cell_type'] == 'markdown' else "PY"
    print(f"[{i:2d}] {cell_type} | {first_line[:55]}")

print("=" * 70)
print("完成")
