import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('checklist_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for sheet_name in ['Instructions', 'Dashboard', 'CO-PO Review', 'Hours Validation']:
    sheet = data[sheet_name]
    print(f"\n==================== SHEET: {sheet_name} ====================")
    for r in sheet['rows']:
        print(f"R{r['row']}: {r['values']}")
