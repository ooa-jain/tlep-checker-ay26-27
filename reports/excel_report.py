"""
Excel Audit Report Generator
Generates individual course audit reports and institutional consolidated batch reports with Department-wise tabs.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from models.schemas import TLEPReviewResult, StatusEnum
from engine.scoring import aggregate_area_breakdown
import io
import re
from typing import List, Dict, Any

__all__ = ["generate_excel_report", "generate_consolidated_report"]


def generate_excel_report(result: TLEPReviewResult, output_path: str = None) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    title_font = Font(name="Calibri", size=16, bold=True, color="1F497D")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    accent_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    
    status_fills = {
        StatusEnum.COMPLIANT.value: PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
        StatusEnum.NEEDS_REVISION.value: PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
        StatusEnum.MAJOR_REVISION.value: PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
        StatusEnum.NON_COMPLIANT.value: PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
        StatusEnum.NA.value: PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
    }
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # 1. Executive Summary
    ws_summary = wb.create_sheet(title="Executive Summary")
    ws_summary.views.sheetView[0].showGridLines = True
    
    ws_summary.cell(1, 1, "OOA TLEP COMPLIANCE AUDIT REPORT — AY 2026–27").font = title_font
    ws_summary.cell(2, 1, f"Audit Date: {result.review_date} | Review ID: {result.review_id} | File: {result.file_name}").font = bold_font
    
    ws_summary.cell(4, 1, "Overall Compliance Score:").font = bold_font
    ws_summary.cell(4, 2, f"{result.compliance_percentage}%").font = Font(size=14, bold=True, color="006100" if result.compliance_percentage >= 80 else "9C0006")
    
    ws_summary.cell(5, 1, "Overall Status:").font = bold_font
    ws_summary.cell(5, 2, result.overall_status.value).font = bold_font
    ws_summary.cell(5, 2).fill = status_fills.get(result.overall_status.value, accent_fill)
    
    ws_summary.cell(6, 1, "Score Obtained:").font = bold_font
    ws_summary.cell(6, 2, f"{result.score_obtained} / {result.maximum_score}").font = regular_font
    
    ws_summary.cell(7, 1, "Applicable Parameters:").font = bold_font
    ws_summary.cell(7, 2, f"{result.applicable_parameters} (of {result.total_parameters})").font = regular_font

    headers_counts = ["Status Category", "Count", "Scoring Weight", "Total Points"]
    for c_idx, h in enumerate(headers_counts, 1):
        cell = ws_summary.cell(9, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    counts_data = [
        ("Compliant", result.compliant_count, 2, result.compliant_count * 2),
        ("Needs Revision", result.needs_revision_count, 1, result.needs_revision_count * 1),
        ("Major Revision", result.major_revision_count, 0, 0),
        ("Non-Compliant", result.non_compliant_count, 0, 0),
        ("Not Applicable (NA)", result.na_count, "Excluded", 0),
    ]
    for r_idx, (cat, cnt, wt, pts) in enumerate(counts_data, 10):
        ws_summary.cell(r_idx, 1, cat).font = bold_font
        ws_summary.cell(r_idx, 2, cnt).font = regular_font
        ws_summary.cell(r_idx, 3, str(wt)).font = regular_font
        ws_summary.cell(r_idx, 4, pts).font = regular_font
        for c in range(1, 5):
            ws_summary.cell(r_idx, c).border = thin_border
            ws_summary.cell(r_idx, c).alignment = Alignment(horizontal="center" if c > 1 else "left")

    area_summary = aggregate_area_breakdown(result.parameter_findings)
    ws_summary.cell(17, 1, "AREA-WISE COMPLIANCE BREAKDOWN").font = bold_font
    area_headers = ["Review Area", "Total Params", "Compliant", "Needs Rev", "Major Rev", "Score", "Max", "Compliance %"]
    for c_idx, h in enumerate(area_headers, 1):
        cell = ws_summary.cell(18, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for r_idx, a_item in enumerate(area_summary, 19):
        ws_summary.cell(r_idx, 1, a_item["review_area"]).font = regular_font
        ws_summary.cell(r_idx, 2, a_item["total"]).font = regular_font
        ws_summary.cell(r_idx, 3, a_item["compliant"]).font = regular_font
        ws_summary.cell(r_idx, 4, a_item["needs_revision"]).font = regular_font
        ws_summary.cell(r_idx, 5, a_item["major_revision"]).font = regular_font
        ws_summary.cell(r_idx, 6, a_item["score"]).font = regular_font
        ws_summary.cell(r_idx, 7, a_item["max_score"]).font = regular_font
        ws_summary.cell(r_idx, 8, f"{a_item['compliance_pct']}%").font = bold_font
        for c in range(1, 9):
            ws_summary.cell(r_idx, c).border = thin_border
            ws_summary.cell(r_idx, c).alignment = Alignment(horizontal="center" if c > 1 else "left")

    # 2. 49-Parameter Review
    ws_review = wb.create_sheet(title="49-Parameter Review")
    ws_review.views.sheetView[0].showGridLines = True
    
    rev_headers = ["Sl. No.", "Review Area", "Parameter", "OOA Review Criteria", "Priority", "Status", "Score", "OOA Remarks / Reason", "Department Action Required", "Evidence Text", "Evidence Location"]
    for c_idx, h in enumerate(rev_headers, 1):
        cell = ws_review.cell(1, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    for r_idx, f in enumerate(result.parameter_findings, 2):
        ws_review.cell(r_idx, 1, f.parameter_id).font = regular_font
        ws_review.cell(r_idx, 2, f.review_area).font = regular_font
        ws_review.cell(r_idx, 3, f.parameter).font = bold_font
        ws_review.cell(r_idx, 4, f.criterion).font = regular_font
        ws_review.cell(r_idx, 5, f.priority.value).font = regular_font
        
        status_cell = ws_review.cell(r_idx, 6, f.status.value)
        status_cell.font = bold_font
        status_cell.fill = status_fills.get(f.status.value, accent_fill)
        status_cell.alignment = Alignment(horizontal="center")
        
        ws_review.cell(r_idx, 7, f.score if f.score is not None else "-").font = bold_font
        ws_review.cell(r_idx, 7).alignment = Alignment(horizontal="center")
        
        ws_review.cell(r_idx, 8, f.reason).font = regular_font
        ws_review.cell(r_idx, 9, f.action_required).font = regular_font
        
        ev_text = "; ".join([e.text for e in f.evidence]) if f.evidence else "-"
        ev_loc = "; ".join([e.location for e in f.evidence]) if f.evidence else "-"
        ws_review.cell(r_idx, 10, ev_text).font = regular_font
        ws_review.cell(r_idx, 11, ev_loc).font = regular_font
        
        for c in range(1, 12):
            ws_review.cell(r_idx, c).border = thin_border
            ws_review.cell(r_idx, c).alignment = Alignment(vertical="top", wrap_text=True)

    # 3. Hours Validation
    ws_hours = wb.create_sheet(title="Hours Validation")
    ws_hours.views.sheetView[0].showGridLines = True
    
    h_headers = ["Parameter", "Approved Curriculum", "As per TLEP", "Variance", "OOA Status", "Remarks", "Evidence", "Action Required"]
    for c_idx, h in enumerate(h_headers, 1):
        cell = ws_hours.cell(1, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for r_idx, hr in enumerate(result.hours_validation_rows, 2):
        ws_hours.cell(r_idx, 1, hr.parameter).font = bold_font
        ws_hours.cell(r_idx, 2, str(hr.approved) if hr.approved is not None else "-").font = regular_font
        ws_hours.cell(r_idx, 3, str(hr.tlep) if hr.tlep is not None else "-").font = regular_font
        ws_hours.cell(r_idx, 4, str(hr.variance)).font = regular_font
        
        st_cell = ws_hours.cell(r_idx, 5, hr.status.value)
        st_cell.font = bold_font
        st_cell.fill = status_fills.get(hr.status.value, accent_fill)
        st_cell.alignment = Alignment(horizontal="center")
        
        ws_hours.cell(r_idx, 6, hr.remarks).font = regular_font
        ws_hours.cell(r_idx, 7, hr.evidence).font = regular_font
        ws_hours.cell(r_idx, 8, hr.action_required).font = regular_font
        for c in range(1, 9):
            ws_hours.cell(r_idx, c).border = thin_border

    # 4. Critical Issues
    ws_crit = wb.create_sheet(title="Critical Issues")
    ws_crit.views.sheetView[0].showGridLines = True
    
    cr_headers = ["Param ID", "Review Area", "Parameter", "Critical Issue Detected", "Evidence", "Action Required"]
    for c_idx, h in enumerate(cr_headers, 1):
        cell = ws_crit.cell(1, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for r_idx, ci in enumerate(result.critical_issues, 2):
        ws_crit.cell(r_idx, 1, ci.get("parameter_id", "-")).font = bold_font
        ws_crit.cell(r_idx, 2, ci.get("review_area", "")).font = regular_font
        ws_crit.cell(r_idx, 3, ci.get("parameter", "")).font = bold_font
        ws_crit.cell(r_idx, 4, ci.get("issue", "")).font = regular_font
        ws_crit.cell(r_idx, 5, ci.get("evidence", "")).font = regular_font
        ws_crit.cell(r_idx, 6, ci.get("action", "")).font = regular_font
        for c in range(1, 7):
            ws_crit.cell(r_idx, c).border = thin_border

    # 5. Department Action Plan
    ws_act = wb.create_sheet(title="Department Action Plan")
    ws_act.views.sheetView[0].showGridLines = True
    
    ap_headers = ["Priority", "Section", "Parameter", "Deficiency / Issue", "Evidence", "Corrective Action Required", "Compliance Status"]
    for c_idx, h in enumerate(ap_headers, 1):
        cell = ws_act.cell(1, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for r_idx, ap in enumerate(result.department_action_plan, 2):
        pr_cell = ws_act.cell(r_idx, 1, ap.get("priority", ""))
        pr_cell.font = bold_font
        pr_cell.alignment = Alignment(horizontal="center")
        if ap.get("priority") == "HIGH":
            pr_cell.fill = status_fills[StatusEnum.MAJOR_REVISION.value]
        elif ap.get("priority") == "MEDIUM":
            pr_cell.fill = status_fills[StatusEnum.NEEDS_REVISION.value]
            
        ws_act.cell(r_idx, 2, ap.get("section", "")).font = regular_font
        ws_act.cell(r_idx, 3, ap.get("parameter", "")).font = bold_font
        ws_act.cell(r_idx, 4, ap.get("issue", "")).font = regular_font
        ws_act.cell(r_idx, 5, ap.get("evidence", "")).font = regular_font
        ws_act.cell(r_idx, 6, ap.get("action", "")).font = regular_font
        
        st_cell = ws_act.cell(r_idx, 7, ap.get("status", ""))
        st_cell.font = bold_font
        st_cell.alignment = Alignment(horizontal="center")
        st_cell.fill = status_fills.get(ap.get("status"), accent_fill)
        
        for c in range(1, 8):
            ws_act.cell(r_idx, c).border = thin_border

    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    buffer = io.BytesIO()
    wb.save(buffer)
    report_bytes = buffer.getvalue()
    
    if output_path:
        with open(output_path, "wb") as f:
            f.write(report_bytes)
            
    return report_bytes


def generate_consolidated_report(records: List[Dict[str, Any]], output_path: str = None) -> bytes:
    """
    Generates institutional roll-up report for hundreds/thousands of course TLEPs.
    Includes:
    1. Executive Summary & Department Leaderboard
    2. Master Course Audit Rollup
    3. Dedicated Department-wise Tabs for each department!
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    title_font = Font(name="Calibri", size=16, bold=True, color="1F497D")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    accent_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # ----------------------------------------------------
    # Sheet 1: Executive Summary & Department Breakdown
    # ----------------------------------------------------
    ws_exec = wb.create_sheet(title="Executive Summary")
    ws_exec.views.sheetView[0].showGridLines = True
    
    ws_exec.cell(1, 1, "OOA TLEP INSTITUTIONAL COMPLIANCE AUDIT — AY 2026–27").font = title_font
    
    total_courses = len(records)
    avg_compliance = round(sum(r.get("compliance_pct", 0) for r in records) / total_courses, 1) if total_courses > 0 else 0.0
    ready_count = sum(1 for r in records if r.get("overall_status") == "Compliant")
    minor_count = sum(1 for r in records if r.get("overall_status") == "Needs Revision")
    rework_count = sum(1 for r in records if r.get("overall_status") in ["Major Revision", "Non-Compliant"])
    
    ws_exec.cell(3, 1, "Total Courses Audited:").font = bold_font
    ws_exec.cell(3, 2, total_courses).font = bold_font
    ws_exec.cell(4, 1, "Institutional Avg Compliance:").font = bold_font
    ws_exec.cell(4, 2, f"{avg_compliance}%").font = Font(size=13, bold=True, color="006100" if avg_compliance >= 80 else "9C0006")
    ws_exec.cell(5, 1, "Ready for BoS (Compliant):").font = bold_font
    ws_exec.cell(5, 2, ready_count).font = regular_font
    ws_exec.cell(6, 1, "Minor Edits Needed:").font = bold_font
    ws_exec.cell(6, 2, minor_count).font = regular_font
    ws_exec.cell(7, 1, "Rework Required (Blockers):").font = bold_font
    ws_exec.cell(7, 2, rework_count).font = regular_font

    # Aggregate by Department
    dept_map = {}
    for r in records:
        dept = r.get("department", "Unassigned")
        if dept not in dept_map:
            dept_map[dept] = []
        dept_map[dept].append(r)
        
    ws_exec.cell(10, 1, "DEPARTMENT-WISE PERFORMANCE BREAKDOWN").font = bold_font
    dept_headers = ["Department", "School / Faculty", "Total Courses", "Avg Compliance %", "Ready for BoS", "Minor Fixes", "Rework Required"]
    for c_idx, h in enumerate(dept_headers, 1):
        cell = ws_exec.cell(11, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for r_idx, (d_name, d_records) in enumerate(sorted(dept_map.items()), 12):
        d_tot = len(d_records)
        d_avg = round(sum(x.get("compliance_pct", 0) for x in d_records) / d_tot, 1) if d_tot > 0 else 0.0
        d_ready = sum(1 for x in d_records if x.get("overall_status") == "Compliant")
        d_minor = sum(1 for x in d_records if x.get("overall_status") == "Needs Revision")
        d_rework = sum(1 for x in d_records if x.get("overall_status") in ["Major Revision", "Non-Compliant"])
        d_school = d_records[0].get("school", "Unassigned")
        
        ws_exec.cell(r_idx, 1, d_name).font = bold_font
        ws_exec.cell(r_idx, 2, d_school).font = regular_font
        ws_exec.cell(r_idx, 3, d_tot).font = regular_font
        ws_exec.cell(r_idx, 4, f"{d_avg}%").font = bold_font
        ws_exec.cell(r_idx, 5, d_ready).font = regular_font
        ws_exec.cell(r_idx, 6, d_minor).font = regular_font
        ws_exec.cell(r_idx, 7, d_rework).font = regular_font
        for c in range(1, 8):
            ws_exec.cell(r_idx, c).border = thin_border
            ws_exec.cell(r_idx, c).alignment = Alignment(horizontal="center" if c > 2 else "left")

    # ----------------------------------------------------
    # Sheet 2: Master Course Roll-up (All Courses)
    # ----------------------------------------------------
    ws_master = wb.create_sheet(title="All Courses Master")
    ws_master.views.sheetView[0].showGridLines = True
    
    ws_master.cell(1, 1, "MASTER COURSE AUDIT LIST (ALL DEPARTMENTS)").font = title_font
    
    cols = ["School / Faculty", "Department", "Programme", "Semester", "Course Code", "Course Title", "Compliance %", "Status", "Score", "Max", "Blockers", "Quick Fixes", "File Name"]
    for c_idx, h in enumerate(cols, 1):
        cell = ws_master.cell(3, c_idx, h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    # Sort records by Department -> Programme -> Semester -> Code
    sorted_records = sorted(records, key=lambda x: (
        x.get("department", ""),
        x.get("programme", ""),
        x.get("semester", ""),
        x.get("course_code", "")
    ))
    
    for r_idx, r in enumerate(sorted_records, 4):
        ws_master.cell(r_idx, 1, r.get("school", "Unassigned")).font = regular_font
        ws_master.cell(r_idx, 2, r.get("department", "Unassigned")).font = regular_font
        ws_master.cell(r_idx, 3, r.get("programme", "Unassigned")).font = regular_font
        ws_master.cell(r_idx, 4, r.get("semester", "-")).font = regular_font
        ws_master.cell(r_idx, 5, r.get("course_code", "-")).font = bold_font
        ws_master.cell(r_idx, 6, r.get("course_title", "-")).font = regular_font
        ws_master.cell(r_idx, 7, f"{r.get('compliance_pct', 0.0)}%").font = bold_font
        ws_master.cell(r_idx, 8, r.get("overall_status", "-")).font = bold_font
        ws_master.cell(r_idx, 9, r.get("score_obtained", 0)).font = regular_font
        ws_master.cell(r_idx, 10, r.get("maximum_score", 98)).font = regular_font
        ws_master.cell(r_idx, 11, r.get("major_revision_count", 0)).font = regular_font
        ws_master.cell(r_idx, 12, r.get("needs_revision_count", 0)).font = regular_font
        ws_master.cell(r_idx, 13, r.get("file_name", "-")).font = regular_font
        for c in range(1, 14):
            ws_master.cell(r_idx, c).border = thin_border

    # ----------------------------------------------------
    # Sheets 3+: Dedicated Tabs for Each Department
    # ----------------------------------------------------
    for d_name, d_records in sorted(dept_map.items()):
        # Clean title for excel tab (max 31 characters, remove special characters)
        clean_tab_title = re.sub(r"[\\/*?:\[\]]", "", d_name)[:30].strip()
        if not clean_tab_title:
            clean_tab_title = "Dept"
            
        ws_dept = wb.create_sheet(title=clean_tab_title)
        ws_dept.views.sheetView[0].showGridLines = True
        
        ws_dept.cell(1, 1, f"DEPARTMENT AUDIT: {d_name}").font = title_font
        
        d_tot = len(d_records)
        d_avg = round(sum(x.get("compliance_pct", 0) for x in d_records) / d_tot, 1) if d_tot > 0 else 0.0
        ws_dept.cell(2, 1, f"Total Courses: {d_tot} | Average Compliance: {d_avg}%").font = bold_font
        
        d_cols = ["Programme", "Semester", "Course Code", "Course Title", "Compliance %", "Status", "Score", "Max", "Blockers", "Quick Fixes", "Action Summary"]
        for c_idx, h in enumerate(d_cols, 1):
            cell = ws_dept.cell(4, c_idx, h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            
        for r_idx, r in enumerate(d_records, 5):
            ws_dept.cell(r_idx, 1, r.get("programme", "Unassigned")).font = regular_font
            ws_dept.cell(r_idx, 2, r.get("semester", "-")).font = regular_font
            ws_dept.cell(r_idx, 3, r.get("course_code", "-")).font = bold_font
            ws_dept.cell(r_idx, 4, r.get("course_title", "-")).font = regular_font
            ws_dept.cell(r_idx, 5, f"{r.get('compliance_pct', 0.0)}%").font = bold_font
            ws_dept.cell(r_idx, 6, r.get("overall_status", "-")).font = bold_font
            ws_dept.cell(r_idx, 7, r.get("score_obtained", 0)).font = regular_font
            ws_dept.cell(r_idx, 8, r.get("maximum_score", 98)).font = regular_font
            ws_dept.cell(r_idx, 9, r.get("major_revision_count", 0)).font = regular_font
            ws_dept.cell(r_idx, 10, r.get("needs_revision_count", 0)).font = regular_font
            
            # Action summary text
            crit_issues = r.get("critical_issues", [])
            action_text = "; ".join(c.get("issue", "") for c in crit_issues[:2]) if crit_issues else "Ready for BoS"
            ws_dept.cell(r_idx, 11, action_text).font = regular_font
            
            for c in range(1, 12):
                ws_dept.cell(r_idx, c).border = thin_border

    # Auto-adjust column widths for all sheets
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    report_bytes = buffer.getvalue()
    
    if output_path:
        with open(output_path, "wb") as f:
            f.write(report_bytes)
            
    return report_bytes
