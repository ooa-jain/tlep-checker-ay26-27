import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('checklist_dump.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sheet = data['TLEP Review Checklist']
print(f"Max row: {sheet['max_row']}, Max col: {sheet['max_col']}")
# print header row(s)
for r in sheet['rows']:
    if r['row'] <= 4:
        print(f"HEADER R{r['row']}: {r['values']}")
    else:
        # data rows
        print(f"PARAM R{r['row']}: ID={r['values'][0]} | Area={r['values'][1]} | Param={r['values'][2]} | Crit={r['values'][3]} | Weight={r['values'][4]} | Status={r['values'][5]} | Score={r['values'][6]} | Remarks={r['values'][7] if len(r['values']) > 7 else ''}")
