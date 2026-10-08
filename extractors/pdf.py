"""
PDF TLEP Extractor
Extracts structured text, tables, and page metadata from PDF files using PyMuPDF (fitz).
Preserves exact page numbers for evidence traceability.
"""

import fitz  # PyMuPDF
import re
from typing import Dict, Any, List, Optional
from models.schemas import (
    NormalizedTLEP, CourseInfo, CourseObjective, CourseOutcome,
    CopoMappingItem, ModuleItem, SessionItem, AssessmentComponent,
    LearningResource, LearningHoursSummary
)


def extract_pdf_tlep(file_path: str) -> NormalizedTLEP:
    doc = fitz.open(file_path)
    
    raw_tables = []
    full_text_lines = []
    page_texts = {}
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        p_num = page_idx + 1
        p_text = page.get_text()
        page_texts[p_num] = p_text
        full_text_lines.append(f"--- Page {p_num} ---")
        full_text_lines.append(p_text)
        
        # Extract tables if PyMuPDF table finder is available
        try:
            tabs = page.find_tables()
            for t_idx, tab in enumerate(tabs):
                df_rows = tab.extract()
                table_rows = []
                for r_idx, r in enumerate(df_rows):
                    cells = [str(c).strip() if c is not None else "" for c in r]
                    table_rows.append({"row": r_idx + 1, "cells": cells})
                raw_tables.append({
                    "page": p_num,
                    "table_index": t_idx + 1,
                    "rows": table_rows
                })
        except Exception:
            pass
            
    raw_text = "\n".join(full_text_lines)
    
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
    
    # 1. Parse Course Info across pages
    for p_num, p_text in page_texts.items():
        lines = [line.strip() for line in p_text.splitlines() if line.strip()]
        for line in lines:
            line_l = line.lower()
            if "course code" in line_l and not course_info.course_code:
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) > 1:
                    course_info.course_code = parts[1].strip()
            if ("course title" in line_l or "course name" in line_l) and not course_info.course_title:
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) > 1:
                    course_info.course_title = parts[1].strip()
            if "semester" in line_l and not course_info.semester:
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) > 1:
                    course_info.semester = parts[1].strip()
            if ("academic year" in line_l or "ay " in line_l) and not course_info.academic_year:
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) > 1:
                    course_info.academic_year = parts[1].strip()
            if "credits" in line_l and not course_info.credits:
                m = re.search(r"credits\s*[:\-]?\s*(\d+(\.\d+)?)", line, re.IGNORECASE)
                if m:
                    course_info.credits = float(m.group(1))
            if ("l-t-p-e" in line_l or "ltpe" in line_l) and not course_info.ltpe:
                parts = re.split(r"[:\-]", line, maxsplit=1)
                if len(parts) > 1:
                    course_info.ltpe = parts[1].strip()

    # 2. Parse COs from tables or text
    for p_num, p_text in page_texts.items():
        for line in p_text.splitlines():
            line_s = line.strip()
            co_m = re.match(r"^(CO\s*\d+)[\s:\.\-]+(.*)$", line_s, re.IGNORECASE)
            if co_m:
                co_id = co_m.group(1).upper().replace(" ", "")
                stmt = co_m.group(2).strip()
                btl = ""
                btl_m = re.search(r"\[(K\d|L\d|Level\s*\d|Apply|Understand|Analyze|Evaluate|Create)\]", stmt, re.IGNORECASE)
                if btl_m:
                    btl = btl_m.group(1)
                if not any(e.id == co_id for e in outcomes):
                    outcomes.append(CourseOutcome(
                        id=co_id,
                        statement=stmt,
                        btl=btl if btl else None,
                        raw_location=f"Page {p_num}"
                    ))

    # 3. Parse Sessions from tables
    for t_item in raw_tables:
        p_num = t_item.get("page", 1)
        t_id = t_item.get("table_index", 1)
        header_idx = -1
        col_map = {}
        for r_idx, r_item in enumerate(t_item["rows"]):
            cells = [c.lower() for c in r_item["cells"]]
            if any("session" in c for c in cells) and (any("topic" in c for c in cells) or any("pedagogy" in c for c in cells)):
                header_idx = r_idx
                for c_i, c_val in enumerate(cells):
                    if "session" in c_val or "sl" in c_val:
                        col_map["session_no"] = c_i
                    elif "module" in c_val or "unit" in c_val:
                        col_map["module"] = c_i
                    elif "topic" in c_val:
                        col_map["topic"] = c_i
                    elif "co" in c_val:
                        col_map["co"] = c_i
                    elif "pedagogy" in c_val:
                        col_map["pedagogy"] = c_i
                    elif "mode" in c_val:
                        col_map["mode"] = c_i
                    elif "reading" in c_val:
                        col_map["readings"] = c_i
                break
                
        if header_idx != -1:
            for s_row in t_item["rows"][header_idx + 1:]:
                c_vals = s_row["cells"]
                if not any(c_vals):
                    continue
                s_no_str = c_vals[col_map.get("session_no", 0)] if col_map.get("session_no") is not None and col_map.get("session_no") < len(c_vals) else ""
                s_match = re.search(r"^\d+", s_no_str.strip())
                if s_match:
                    s_num = int(s_match.group(0))
                    topic_str = c_vals[col_map["topic"]] if "topic" in col_map and col_map["topic"] < len(c_vals) else ""
                    mod_str = c_vals[col_map["module"]] if "module" in col_map and col_map["module"] < len(c_vals) else ""
                    ped_str = c_vals[col_map["pedagogy"]] if "pedagogy" in col_map and col_map["pedagogy"] < len(c_vals) else ""
                    mode_str = c_vals[col_map["mode"]] if "mode" in col_map and col_map["mode"] < len(c_vals) else ""
                    read_str = c_vals[col_map["readings"]] if "readings" in col_map and col_map["readings"] < len(c_vals) else ""
                    
                    co_str = c_vals[col_map["co"]] if "co" in col_map and col_map["co"] < len(c_vals) else ""
                    mapped_cos = [c.upper().replace(" ", "") for c in re.findall(r"CO\s*\d+", co_str, re.IGNORECASE)]
                    
                    sessions.append(SessionItem(
                        session_number=s_num,
                        module=mod_str,
                        topic=topic_str,
                        hours=1.0,
                        co_mapped=mapped_cos,
                        pedagogy=ped_str,
                        mode_of_delivery=mode_str,
                        readings=read_str,
                        source_location=f"Page {p_num}, Table {t_id}, Row {s_row['row']}"
                    ))

    if sessions:
        hours_summary.total_session_hours = float(sum(s.hours or 1.0 for s in sessions))
        
    return NormalizedTLEP(
        source_file=file_path,
        file_type="pdf",
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
