"""
Excel TLEP Extractor
Extracts structured course data, tables, and text from .xlsx / .xls workbooks.
Preserves sheet names, row/col locations, and table structures.
"""

import openpyxl
import re
from typing import Dict, Any, List, Optional
from models.schemas import (
    NormalizedTLEP, CourseInfo, CourseObjective, CourseOutcome,
    CopoMappingItem, ModuleItem, SessionItem, AssessmentComponent,
    LearningResource, LearningHoursSummary
)


def extract_excel_tlep(file_path: str) -> NormalizedTLEP:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    
    raw_tables = []
    full_text_lines = []
    
    # Extract all sheet data
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        full_text_lines.append(f"--- Sheet: {sheet_name} ---")
        sheet_rows = []
        for r in range(1, ws.max_row + 1):
            row_vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
            # stringify
            str_vals = [str(v).strip() if v is not None else "" for v in row_vals]
            if any(str_vals):
                sheet_rows.append({"row": r, "cells": str_vals})
                full_text_lines.append(" | ".join([v for v in str_vals if v]))
        
        raw_tables.append({
            "sheet_name": sheet_name,
            "max_row": ws.max_row,
            "max_col": ws.max_column,
            "rows": sheet_rows
        })
        
    raw_text = "\n".join(full_text_lines)
    
    # Initialize normalized models
    course_info = CourseInfo()
    objectives = []
    outcomes = []
    copo_mappings = []
    modules = []
    sessions = []
    assessments = []
    resources = []
    hours_summary = LearningHoursSummary()
    notes = []
    
    # 1. Parse Course Information
    # Look across all cells for key patterns like "Course Code", "Course Title", "Credits", "L-T-P-E", "Semester", "AY"
    for table in raw_tables:
        sname = table["sheet_name"]
        for r_item in table["rows"]:
            r = r_item["row"]
            cells = r_item["cells"]
            for c_idx, cell_str in enumerate(cells):
                c_lower = cell_str.lower()
                next_val = cells[c_idx + 1] if c_idx + 1 < len(cells) and cells[c_idx + 1] else ""
                
                # Course Code
                if ("course code" in c_lower or "subject code" in c_lower) and not course_info.course_code:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.course_code = val
                        
                # Course Title
                if ("course title" in c_lower or "course name" in c_lower or "subject name" in c_lower) and not course_info.course_title:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.course_title = val
                        
                # Semester
                if "semester" in c_lower and not course_info.semester:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.semester = val
                        
                # Academic Year
                if ("academic year" in c_lower or "ay " in c_lower or "a.y" in c_lower) and not course_info.academic_year:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.academic_year = val
                        
                # Credits
                if c_lower in ["credits", "credit", "total credits", "credits:"] and not course_info.credits:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    try:
                        m = re.search(r"\d+(\.\d+)?", val)
                        if m:
                            course_info.credits = float(m.group(0))
                    except Exception:
                        pass
                        
                # L-T-P-E
                if "l-t-p-e" in c_lower or "ltpe" in c_lower or "l:t:p:e" in c_lower:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.ltpe = val
                        
                # CA:ESE
                if "ca:ese" in c_lower or "ca : ese" in c_lower or "cie:see" in c_lower:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.ca_ese = val
                        
                # School / Department / Programme
                if ("school of" in c_lower or ("school" in c_lower and "high school" not in c_lower)) and not course_info.school:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.school = val
                if "department" in c_lower and not course_info.department:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.department = val
                if "programme" in c_lower and not course_info.programme:
                    val = next_val if next_val else cell_str.split(":")[-1].strip()
                    if val and val != cell_str:
                        course_info.programme = val

    # 2. Extract Course Outcomes (COs) & Bloom's Taxonomy Levels (BTL)
    # Search for rows where first or second column has CO1, CO2, etc.
    for table in raw_tables:
        sname = table["sheet_name"]
        for r_item in table["rows"]:
            cells = [c for c in r_item["cells"] if c]
            if not cells:
                continue
            for idx, c in enumerate(cells):
                co_match = re.match(r"^(CO\s*\d+)[\s:\.\-]*", c, re.IGNORECASE)
                if co_match:
                    co_id = co_match.group(1).upper().replace(" ", "")
                    # statement
                    statement = ""
                    btl = ""
                    if len(cells) > idx + 1:
                        statement = cells[idx + 1]
                    if len(cells) > idx + 2:
                        # might be BTL or another column
                        possible_btl = cells[idx + 2]
                        if re.search(r"(K\d|L\d|Level\s*\d|Apply|Remember|Understand|Analyze|Evaluate|Create)", possible_btl, re.IGNORECASE):
                            btl = possible_btl
                    # if statement contains BTL at the end
                    btl_match = re.search(r"\[(K\d|L\d|Level\s*\d|Apply|Understand|Analyze|Evaluate|Create)\]", statement, re.IGNORECASE)
                    if btl_match and not btl:
                        btl = btl_match.group(1)
                    
                    # avoid duplicate CO additions
                    if not any(existing.id == co_id for existing in outcomes):
                        outcomes.append(CourseOutcome(
                            id=co_id,
                            statement=statement if statement else c,
                            btl=btl if btl else None,
                            raw_location=f"Sheet '{sname}', Row {r_item['row']}"
                        ))
                    break

    # 3. Extract CO-PO / PSO Mappings
    # Check for matrix headers PO1..PO12, PSO1..PSO4
    for table in raw_tables:
        sname = table["sheet_name"]
        # Look for header row with PO1
        for r_idx, r_item in enumerate(table["rows"]):
            cells = r_item["cells"]
            po_cols = {}
            for col_i, cell in enumerate(cells):
                cell_clean = cell.strip().upper()
                if re.match(r"^PO\s*\d+$", cell_clean) or re.match(r"^PSO\s*\d+$", cell_clean):
                    po_cols[col_i] = cell_clean.replace(" ", "")
            
            if len(po_cols) >= 3:
                # Next rows are likely CO rows
                for subsequent in table["rows"][r_idx + 1: r_idx + 15]:
                    sub_cells = subsequent["cells"]
                    if not sub_cells:
                        continue
                    first_non_empty = next((c for c in sub_cells if c), "")
                    co_match = re.match(r"^(CO\s*\d+)", first_non_empty, re.IGNORECASE)
                    if co_match:
                        co_id = co_match.group(1).upper().replace(" ", "")
                        for col_i, po_name in po_cols.items():
                            if col_i < len(sub_cells):
                                val = sub_cells[col_i].strip()
                                if val in ["1", "2", "3", "-", ""]:
                                    copo_mappings.append(CopoMappingItem(
                                        co_id=co_id,
                                        target_id=po_name,
                                        level=int(val) if val.isdigit() else val,
                                        justification=""
                                    ))

    # 4. Extract Sessions
    # Look for session table headers like "Session", "Session No", "Topic", "Pedagogy", "CO"
    for table in raw_tables:
        sname = table["sheet_name"]
        header_row_idx = -1
        col_map = {}
        for r_idx, r_item in enumerate(table["rows"]):
            cells = [c.lower() for c in r_item["cells"]]
            if any("session" in c for c in cells) and (any("topic" in c for c in cells) or any("pedagogy" in c for c in cells)):
                header_row_idx = r_idx
                for c_i, c_val in enumerate(cells):
                    if "session" in c_val or "sl" in c_val:
                        col_map["session_no"] = c_i
                    elif "module" in c_val or "unit" in c_val:
                        col_map["module"] = c_i
                    elif "topic" in c_val or "portion" in c_val or "content" in c_val:
                        col_map["topic"] = c_i
                    elif "co" in c_val:
                        col_map["co"] = c_i
                    elif "pedagogy" in c_val or "activity" in c_val or "method" in c_val:
                        col_map["pedagogy"] = c_i
                    elif "mode" in c_val or "delivery" in c_val:
                        col_map["mode"] = c_i
                    elif "reading" in c_val or "reference" in c_val:
                        col_map["readings"] = c_i
                    elif "hour" in c_val or "duration" in c_val:
                        col_map["hours"] = c_i
                break
                
        if header_row_idx != -1:
            for s_item in table["rows"][header_row_idx + 1:]:
                c_vals = s_item["cells"]
                if not any(c_vals):
                    continue
                sess_no_val = c_vals[col_map.get("session_no", 0)] if col_map.get("session_no") is not None and col_map.get("session_no") < len(c_vals) else ""
                
                # Check if it's a numeric session
                s_num_match = re.search(r"^\d+", sess_no_val.strip())
                if s_num_match:
                    s_num = int(s_num_match.group(0))
                    topic_val = c_vals[col_map["topic"]] if "topic" in col_map and col_map["topic"] < len(c_vals) else ""
                    mod_val = c_vals[col_map["module"]] if "module" in col_map and col_map["module"] < len(c_vals) else ""
                    ped_val = c_vals[col_map["pedagogy"]] if "pedagogy" in col_map and col_map["pedagogy"] < len(c_vals) else ""
                    mode_val = c_vals[col_map["mode"]] if "mode" in col_map and col_map["mode"] < len(c_vals) else ""
                    read_val = c_vals[col_map["readings"]] if "readings" in col_map and col_map["readings"] < len(c_vals) else ""
                    
                    # CO mapped
                    co_val = c_vals[col_map["co"]] if "co" in col_map and col_map["co"] < len(c_vals) else ""
                    mapped_cos = re.findall(r"CO\s*\d+", co_val, re.IGNORECASE)
                    mapped_cos = [c.upper().replace(" ", "") for c in mapped_cos]
                    
                    sessions.append(SessionItem(
                        session_number=s_num,
                        module=mod_val,
                        topic=topic_val,
                        hours=1.0,
                        co_mapped=mapped_cos,
                        pedagogy=ped_val,
                        mode_of_delivery=mode_val,
                        readings=read_val,
                        source_location=f"Sheet '{sname}', Row {s_item['row']}"
                    ))

    # 5. Extract Assessments
    for table in raw_tables:
        sname = table["sheet_name"]
        for r_item in table["rows"]:
            cells = [c for c in r_item["cells"] if c]
            row_str = " ".join(cells).lower()
            if any(k in row_str for k in ["assignment", "quiz", "mid term", "end term", "cie", "see", "ese", "presentation", "lab test"]):
                # try to extract weightage
                weight = None
                for c in cells:
                    w_match = re.search(r"(\d+)\s*%", c)
                    if w_match:
                        weight = float(w_match.group(1))
                        break
                    elif c.isdigit() and int(c) in [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 100]:
                        weight = float(c)
                
                comp_name = cells[0] if cells else "Assessment"
                assessments.append(AssessmentComponent(
                    component_name=comp_name,
                    weightage=weight,
                    co_mapped=[c.upper().replace(" ", "") for c in re.findall(r"CO\s*\d+", row_str, re.IGNORECASE)]
                ))

    # Summary hours
    if sessions:
        hours_summary.total_session_hours = float(sum(s.hours or 1.0 for s in sessions))
    
    return NormalizedTLEP(
        source_file=file_path,
        file_type="xlsx",
        raw_text=raw_text,
        raw_tables=raw_tables,
        course_info=course_info,
        course_objectives=objectives,
        course_outcomes=outcomes,
        copo_mappings=copo_mappings,
        modules=modules,
        sessions=sessions,
        assessments=assessments,
        resources=resources,
        hours_summary=hours_summary,
        parsing_notes=notes
    )
