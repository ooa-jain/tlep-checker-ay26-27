import sys
sys.stdout.reconfigure(encoding='utf-8')
import json, openpyxl

wb = openpyxl.load_workbook('OOA_TLEP_Review_Checklist_AY_2026-27.xlsx', data_only=False)
ws = wb['TLEP Review Checklist']

with open('config/checklist.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

assert len(cfg['parameters']) == 49, f"Expected 49 parameters, got {len(cfg['parameters'])}"

for i, p in enumerate(cfg['parameters'], start=1):
    r = p['row_index']
    assert p['parameter_id'] == i, f"Param ID mismatch at {i}"
    cell_id = int(ws.cell(r, 1).value)
    cell_area = str(ws.cell(r, 2).value).strip()
    cell_param = str(ws.cell(r, 3).value).strip()
    cell_crit = str(ws.cell(r, 4).value).strip()
    cell_priority = str(ws.cell(r, 5).value).strip()

    assert p['parameter_id'] == cell_id, f"ID mismatch {p['parameter_id']} vs {cell_id}"
    assert p['review_area'] == cell_area, f"Area mismatch at {i}"
    assert p['parameter'] == cell_param, f"Param mismatch at {i}"
    assert p['criterion'] == cell_crit, f"Criteria mismatch at {i}"
    assert p['priority'] == cell_priority, f"Priority mismatch at {i}"

print("All 49 parameters 100% verified against OOA_TLEP_Review_Checklist_AY_2026-27.xlsx!")
