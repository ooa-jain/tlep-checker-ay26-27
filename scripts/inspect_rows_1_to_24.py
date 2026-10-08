import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('checklist_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sheet = data['TLEP Review Checklist']
for r in sheet['rows']:
    if r['row'] <= 24:
        print(f"R{r['row']}: {r['values']}")
