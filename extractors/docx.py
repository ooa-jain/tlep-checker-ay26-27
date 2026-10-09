"""
DOCX TLEP Extractor
Extracts structured course data, tables, headings, and paragraphs from .docx files.
Preserves table cells, row numbers, and document sections.
"""

import docx
import re
from typing import Dict, Any, List, Optional
from models.schemas import (
    NormalizedTLEP, CourseInfo, CourseObjective, CourseOutcome,
    CopoMappingItem, ModuleItem, SessionItem, AssessmentComponent,
    LearningResource, LearningHoursSummary
)


def extract_docx_tlep(file_path: str) -> NormalizedTLEP:
    doc = docx.Document(file_path)
    
    raw_tables = []
    full_text_lines = []
    
    # Extract text from paragraphs
    for p_idx, p in enumerate(doc.paragraphs):
        p_text = p.text.strip()
        if p_text:
            full_text_lines.append(p_text)
            
    # Extract text and structure from tables
    for t_idx, table in enumerate(doc.tables):
        full_text_lines.append(f"--- Table {t_idx + 1} ---")
        table_rows = []
        for r_idx, row in enumerate(table.rows):
            # deduplicate merged cells in row if needed
            cells = [cell.text.strip() for cell in row.cells]
            table_rows.append({"row": r_idx + 1, "cells": cells})
            clean_cells = [c for c in cells if c]
            if clean_cells:
                full_text_lines.append(" | ".join(clean_cells))
                
        raw_tables.append({
            "table_index": t_idx + 1,
            "rows": table_rows
        })
        
    raw_text = "\n".join(full_text_lines)
    
    # Initialize models
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
    
    # 1. Parse Course Information from paragraphs and tables
    # Check paragraphs first
    for p in doc.paragraphs:
        txt = p.text.strip()
        txt_l = txt.lower()
        if any(x in txt_l for x in ["course code", "subject code", "course id", "module code"]) and not course_info.course_code:
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1:
                course_info.course_code = parts[1].strip()
        if any(x in txt_l for x in ["course title", "course name", "subject name", "module title", "module name"]):
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1 and not course_info.course_title:
                course_info.course_title = parts[1].strip()
        if any(x in txt_l for x in ["semester", "term", "sem"]) and not course_info.semester:
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1:
                course_info.semester = parts[1].strip()
        if any(x in txt_l for x in ["academic year", "ay ", "a.y", "session year"]) and not course_info.academic_year:
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1:
                course_info.academic_year = parts[1].strip()
        if any(x in txt_l for x in ["credits", "credit", "total credits", "course credits"]) and not course_info.credits:
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1:
                m = re.search(r"\d+(\.\d+)?", parts[1])
                if m:
                    course_info.credits = float(m.group(0))
        if any(x in txt_l for x in ["l-t-p-e", "ltpe", "l:t:p:e", "l t p e", "l/t/p/e"]) and not course_info.ltpe:
            parts = re.split(r"[:\-]", txt, maxsplit=1)
            if len(parts) > 1:
                course_info.ltpe = parts[1].strip()

    # Also check tables for course info
    for t_item in raw_tables:
        t_id = t_item["table_index"]
        for r_item in t_item["rows"]:
            cells = r_item["cells"]
            for idx, c in enumerate(cells):
                cl = c.lower()
                next_c = cells[idx + 1] if idx + 1 < len(cells) else ""
                if any(x in cl for x in ["course code", "subject code", "course id", "module code"]) and not course_info.course_code:
                    course_info.course_code = next_c or c.split(":")[-1].strip()
                if any(x in cl for x in ["course title", "course name", "subject name", "module title", "module name"]) and not course_info.course_title:
                    course_info.course_title = next_c or c.split(":")[-1].strip()
                if any(x in cl for x in ["semester", "term", "sem"]) and not course_info.semester:
                    course_info.semester = next_c or c.split(":")[-1].strip()
                if any(x in cl for x in ["academic year", "ay ", "a.y", "session year"]) and not course_info.academic_year:
                    course_info.academic_year = next_c or c.split(":")[-1].strip()
                if any(x in cl for x in ["credits", "credit", "total credits", "course credits"]) and not course_info.credits:
                    val = next_c or c.split(":")[-1].strip()
                    m = re.search(r"\d+(\.\d+)?", val)
                    if m:
                        course_info.credits = float(m.group(0))
                if any(x in cl for x in ["l-t-p-e", "ltpe", "l:t:p:e", "l t p e", "l/t/p/e"]) and not course_info.ltpe:
                    course_info.ltpe = next_c or c.split(":")[-1].strip()

    # 2. Extract Course Outcomes
    for t_item in raw_tables:
        t_id = t_item["table_index"]
        for r_item in t_item["rows"]:
            cells = [c for c in r_item["cells"] if c]
            if not cells:
                continue
            for idx, c in enumerate(cells):
                co_m = re.match(r"^(CO\s*\d+)[\s:\.\-]*", c, re.IGNORECASE)
                if co_m:
                    co_id = co_m.group(1).upper().replace(" ", "")
                    stmt = cells[idx + 1] if len(cells) > idx + 1 else c
                    btl = ""
                    if len(cells) > idx + 2:
                        btl = cells[idx + 2]
                    btl_m = re.search(r"\[(K\d|L\d|Level\s*\d|Apply|Understand|Analyze|Evaluate|Create)\]", stmt, re.IGNORECASE)
                    if btl_m and not btl:
                        btl = btl_m.group(1)
                    
                    if not any(e.id == co_id for e in outcomes):
                        outcomes.append(CourseOutcome(
                            id=co_id,
                            statement=stmt,
                            btl=btl if btl else None,
                            raw_location=f"Table {t_id}, Row {r_item['row']}"
                        ))
                    break

    # 3. Extract Sessions from tables
    for t_item in raw_tables:
        t_id = t_item["table_index"]
        header_idx = -1
        col_map = {}
        for r_idx, r_item in enumerate(t_item["rows"]):
            cells = [c.lower() for c in r_item["cells"]]
            if any("session" in c for c in cells) and (any("topic" in c for c in cells) or any("pedagogy" in c for c in cells)):
                header_idx = r_idx
                for c_i, c_val in enumerate(cells):
                    if any(x in c_val for x in ["session", "sl", "s.no", "serial", "lec"]):
                        col_map["session_no"] = c_i
                    elif any(x in c_val for x in ["module", "unit", "chapter"]):
                        col_map["module"] = c_i
                    elif any(x in c_val for x in ["topic", "portion", "content", "syllabus", "coverage"]):
                        col_map["topic"] = c_i
                    elif any(x in c_val for x in ["co", "course outcome", "mapped co"]):
                        col_map["co"] = c_i
                    elif any(x in c_val for x in ["pedagogy", "activity", "method", "teaching", "strategy"]):
                        col_map["pedagogy"] = c_i
                    elif any(x in c_val for x in ["mode", "delivery", "platform"]):
                        col_map["mode"] = c_i
                    elif any(x in c_val for x in ["reading", "reference", "material", "book"]):
                        col_map["readings"] = c_i
                    elif any(x in c_val for x in ["hour", "duration", "time", "period"]):
                        col_map["hours"] = c_i
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
                        source_location=f"Table {t_id}, Row {s_row['row']}"
                    ))

    if sessions:
        hours_summary.total_session_hours = float(sum(s.hours or 1.0 for s in sessions))
        
    return NormalizedTLEP(
        source_file=file_path,
        file_type="docx",
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
