import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('checklist_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for sname, sdata in data.items():
    print('==============================')
    print('SHEET:', sname, f'(max_row={sdata["max_row"]}, max_col={sdata["max_col"]})')
    print('==============================')
    for r in sdata['rows']:
        vals = [v for v in r['values'] if v is not None and v != '']
        if vals:
            print(f'Row {r["row"]}: {vals[:6]}')
