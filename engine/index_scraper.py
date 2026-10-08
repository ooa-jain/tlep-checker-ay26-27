"""
Index Scraper and Document Inventory Reconciliation Engine
Extracts course listings, document hyperlinks, and file references from index files (Excel, CSV, DOCX),
verifies document availability, downloads remote files, and coordinates automated OOA compliance audits.
"""

import os
import re
import csv
import tempfile
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

import requests
import openpyxl
from docx import Document

from models.schemas import StatusEnum, TLEPReviewResult
from engine.reviewer import review_tlep_document
from engine.db import save_audit_result
from integrations.google_drive import GoogleDriveConnector, extract_folder_id_from_url


@dataclass
class IndexCourseEntry:
    row_number: int
    course_code: str
    course_title: str
    department: str
    programme: str
    semester: str
    faculty: str
    raw_reference: str
    link_type: str  # "gdrive_url", "direct_url", "local_file", "missing"
    target_url_or_path: Optional[str]
    availability_status: str  # "Available", "Missing / Not Submitted", "Permission Denied", "Download Error"
    local_file_path: Optional[str] = None
    error_detail: Optional[str] = None
    compliance_percentage: Optional[float] = None
    audit_status: Optional[str] = None
    major_blockers_count: int = 0
    minor_fixes_count: int = 0
    audit_result: Optional[TLEPReviewResult] = None


def extract_url_from_cell(cell) -> Optional[str]:
    """Extracts URL from openpyxl cell via hyperlink object, formula, or text."""
    # 1. Native openpyxl hyperlink
    if hasattr(cell, "hyperlink") and cell.hyperlink and cell.hyperlink.target:
        return cell.hyperlink.target.strip()
    
    val = str(cell.value or "").strip()
    if not val:
        return None
        
    # 2. Formula =HYPERLINK("url", "label")
    formula_match = re.search(r'=HYPERLINK\(\s*["\']([^"\']+)["\']', val, re.IGNORECASE)
    if formula_match:
        return formula_match.group(1).strip()
        
    # 3. Direct URL in text
    url_match = re.search(r'https?://[^\s"\'<>]+', val)
    if url_match:
        return url_match.group(0).strip()
        
    # 4. File name with extension
    if re.search(r'\.(xlsx|xls|docx|pdf)$', val, re.IGNORECASE):
        return val
        
    return None


def extract_file_id_from_drive_url(url: str) -> Optional[str]:
    """Extracts individual Google Drive file ID from standard sharing URLs."""
    patterns = [
        r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
        r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
        r"docs\.google\.com/(?:spreadsheets|document)/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]{20,})"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def download_public_drive_file(file_id: str, destination_path: str) -> bool:
    """Attempts direct download of public Google Drive files or exports."""
    session = requests.Session()
    urls = [
        f"https://drive.google.com/uc?export=download&id={file_id}",
        f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx",
        f"https://docs.google.com/document/d/{file_id}/export?format=docx"
    ]
    
    for download_url in urls:
        try:
            response = session.get(download_url, stream=True, timeout=15)
            if response.status_code == 200 and len(response.content) > 200:
                # Ensure not a Google sign-in HTML landing page
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type and b"accounts.google.com" in response.content[:1000]:
                    continue
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                with open(destination_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception:
            continue
            
    return False


def parse_index_excel(file_path: str) -> List[IndexCourseEntry]:
    """Parses Excel index file, extracting courses and document hyperlinks."""
    wb = openpyxl.load_workbook(file_path, data_only=False)
    sheet = wb.active
    
    header_row_idx = None
    col_map = {}
    
    # Locate header row
    for r_idx, row in enumerate(sheet.iter_rows(values_only=False), 1):
        texts = [str(c.value or "").strip().lower() for c in row]
        if any("course" in t or "code" in t or "subject" in t for t in texts):
            header_row_idx = r_idx
            for c_idx, cell in enumerate(row):
                val = str(cell.value or "").strip().lower()
                if "code" in val:
                    col_map["code"] = c_idx
                elif "title" in val or "name" in val or "subject" in val:
                    col_map["title"] = c_idx
                elif "dept" in val or "department" in val:
                    col_map["dept"] = c_idx
                elif "prog" in val:
                    col_map["prog"] = c_idx
                elif "sem" in val:
                    col_map["sem"] = c_idx
                elif "fac" in val or "instructor" in val or "teacher" in val or "facilitator" in val:
                    col_map["faculty"] = c_idx
                elif "link" in val or "url" in val or "tlep" in val or "doc" in val or "file" in val:
                    col_map["link"] = c_idx
            break
            
    if not header_row_idx:
        # Fallback to row 1
        header_row_idx = 1
        col_map = {"code": 0, "title": 1, "link": 2}
        
    # Default column indices if missing
    if "code" not in col_map:
        col_map["code"] = 0
    if "title" not in col_map:
        col_map["title"] = 1 if sheet.max_column > 1 else 0
    if "link" not in col_map:
        col_map["link"] = sheet.max_column - 1
        
    entries: List[IndexCourseEntry] = []
    
    for r_idx, row in enumerate(sheet.iter_rows(min_row=header_row_idx + 1, values_only=False), header_row_idx + 1):
        cells = list(row)
        if not cells or all(c.value is None for c in cells):
            continue
            
        code_val = str(cells[col_map["code"]].value or "").strip() if col_map["code"] < len(cells) else ""
        title_val = str(cells[col_map["title"]].value or "").strip() if col_map["title"] < len(cells) else ""
        
        # If code and title are both empty, skip row
        if not code_val and not title_val:
            continue
            
        dept_val = str(cells[col_map["dept"]].value or "").strip() if col_map.get("dept") is not None and col_map["dept"] < len(cells) else "General"
        prog_val = str(cells[col_map["prog"]].value or "").strip() if col_map.get("prog") is not None and col_map["prog"] < len(cells) else ""
        sem_val = str(cells[col_map["sem"]].value or "").strip() if col_map.get("sem") is not None and col_map["sem"] < len(cells) else ""
        fac_val = str(cells[col_map["faculty"]].value or "").strip() if col_map.get("faculty") is not None and col_map["faculty"] < len(cells) else ""
        
        # Look for link in designated link column or across any cell in row
        link_cell = cells[col_map["link"]] if col_map.get("link") is not None and col_map["link"] < len(cells) else None
        extracted_url = extract_url_from_cell(link_cell) if link_cell else None
        raw_ref = str(link_cell.value or "") if link_cell else ""
        
        if not extracted_url:
            # Check other cells in row for hyperlinks
            for c in cells:
                found_url = extract_url_from_cell(c)
                if found_url and found_url != code_val and found_url != title_val:
                    extracted_url = found_url
                    raw_ref = str(c.value or "")
                    break
                    
        link_type = "missing"
        if extracted_url:
            if "drive.google.com" in extracted_url or "docs.google.com" in extracted_url:
                link_type = "gdrive_url"
            elif extracted_url.startswith("http://") or extracted_url.startswith("https://"):
                link_type = "direct_url"
            else:
                link_type = "local_file"
                
        initial_status = "Available" if link_type != "missing" else "Missing / Not Submitted"
        
        entry = IndexCourseEntry(
            row_number=r_idx,
            course_code=code_val or "UNKNOWN",
            course_title=title_val or "Untitled Course",
            department=dept_val or "General",
            programme=prog_val or "Undergraduate",
            semester=sem_val or "Semester 1",
            faculty=fac_val or "Unassigned",
            raw_reference=raw_ref,
            link_type=link_type,
            target_url_or_path=extracted_url,
            availability_status=initial_status
        )
        entries.append(entry)
        
    return entries


def parse_index_docx(file_path: str) -> List[IndexCourseEntry]:
    """Parses Word DOCX index tables for course lists and hyperlinked files."""
    doc = Document(file_path)
    entries: List[IndexCourseEntry] = []
    row_counter = 1
    
    for table in doc.tables:
        if len(table.rows) < 2:
            continue
        header = [c.text.strip().lower() for c in table.rows[0].cells]
        col_code = next((i for i, h in enumerate(header) if "code" in h), 0)
        col_title = next((i for i, h in enumerate(header) if "title" in h or "name" in h), 1)
        col_link = next((i for i, h in enumerate(header) if "link" in h or "doc" in h or "tlep" in h), len(header) - 1)
        
        for r_idx, row in enumerate(table.rows[1:], 2):
            cells = row.cells
            code_txt = cells[col_code].text.strip() if col_code < len(cells) else ""
            title_txt = cells[col_title].text.strip() if col_title < len(cells) else ""
            link_txt = cells[col_link].text.strip() if col_link < len(cells) else ""
            
            if not code_txt and not title_txt:
                continue
                
            url_match = re.search(r'https?://[^\s]+', link_txt)
            target = url_match.group(0) if url_match else (link_txt if re.search(r'\.(xlsx|docx|pdf)$', link_txt) else None)
            
            link_type = "gdrive_url" if target and "drive.google.com" in target else ("direct_url" if target and target.startswith("http") else ("local_file" if target else "missing"))
            status = "Available" if link_type != "missing" else "Missing / Not Submitted"
            
            entry = IndexCourseEntry(
                row_number=row_counter,
                course_code=code_txt or "UNKNOWN",
                course_title=title_txt or "Untitled Course",
                department="General",
                programme="Undergraduate",
                semester="Semester 1",
                faculty="Unassigned",
                raw_reference=link_txt,
                link_type=link_type,
                target_url_or_path=target,
                availability_status=status
            )
            entries.append(entry)
            row_counter += 1
            
    return entries


def parse_index_document(file_path: str) -> List[IndexCourseEntry]:
    """Dispatcher to parse any supported index file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return parse_index_excel(file_path)
    elif ext == ".docx":
        return parse_index_docx(file_path)
    else:
        raise ValueError(f"Unsupported index file format: {ext}. Please provide .xlsx or .docx.")


def resolve_and_download_index_documents(
    entries: List[IndexCourseEntry],
    base_dir: str,
    gdrive_connector: Optional[GoogleDriveConnector] = None,
    progress_callback = None
) -> List[IndexCourseEntry]:
    """
    Downloads or resolves local/remote documents for all entries.
    Updates each entry's availability_status and local_file_path.
    """
    temp_download_dir = tempfile.mkdtemp(prefix="tlep_index_downloads_")
    total = len(entries)
    
    for idx, entry in enumerate(entries, 1):
        if progress_callback:
            progress_callback(idx, total, f"{entry.course_code}: {entry.course_title}")
            
        if entry.link_type == "missing" or not entry.target_url_or_path:
            entry.availability_status = "Missing / Not Submitted"
            continue
            
        # 1. Local file path check
        if entry.link_type == "local_file":
            candidate_paths = [
                os.path.join(base_dir, entry.target_url_or_path),
                entry.target_url_or_path,
                os.path.join(base_dir, f"{entry.course_code}.xlsx"),
                os.path.join(base_dir, f"{entry.course_code}.docx"),
                os.path.join(base_dir, f"{entry.course_code}.pdf")
            ]
            found = False
            for p in candidate_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    entry.local_file_path = p
                    entry.availability_status = "Available"
                    found = True
                    break
            if not found and os.path.exists(base_dir):
                target_bn = os.path.basename(entry.target_url_or_path or "").lower()
                code_lower = entry.course_code.lower()
                for root, _, files in os.walk(base_dir):
                    for f in files:
                        f_lower = f.lower()
                        if (target_bn and f_lower == target_bn) or (code_lower and (f_lower == f"{code_lower}.xlsx" or f_lower == f"{code_lower}.docx" or f_lower.startswith(f"{code_lower}_"))):
                            cand = os.path.join(root, f)
                            if os.path.isfile(cand):
                                entry.local_file_path = cand
                                entry.availability_status = "Available"
                                found = True
                                break
                    if found:
                        break
            if not found:
                entry.availability_status = "Missing Local File"
                entry.error_detail = f"Referenced file not found in directory: {entry.target_url_or_path}"
            continue
            
        # 2. Google Drive Link
        if entry.link_type == "gdrive_url":
            # Check if file was already downloaded locally in base_dir
            found_local = False
            code_lower = entry.course_code.lower()
            if os.path.exists(base_dir):
                for root, _, files in os.walk(base_dir):
                    for f in files:
                        f_lower = f.lower()
                        if code_lower and (f_lower == f"{code_lower}.xlsx" or f_lower == f"{code_lower}.docx" or f_lower.startswith(f"{code_lower}_")):
                            cand = os.path.join(root, f)
                            if os.path.isfile(cand):
                                entry.local_file_path = cand
                                entry.availability_status = "Available"
                                found_local = True
                                break
                    if found_local:
                        break
            if found_local:
                continue

            file_id = extract_file_id_from_drive_url(entry.target_url_or_path)
            if not file_id:
                # Might be folder link
                folder_id = extract_folder_id_from_url(entry.target_url_or_path)
                if folder_id:
                    entry.availability_status = "Drive Folder (Not Direct File)"
                    entry.error_detail = "Target link points to a folder rather than an individual course document."
                else:
                    entry.availability_status = "Invalid Drive Link"
                    entry.error_detail = "Unable to extract valid Google Drive file ID."
                continue
                
            dest_filename = f"{entry.course_code}_{file_id}.xlsx"
            dest_path = os.path.join(temp_download_dir, dest_filename)
            
            downloaded = False
            # Try API connector if initialized
            if gdrive_connector and gdrive_connector.service:
                try:
                    gdrive_connector.download_file(file_id, dest_path)
                    downloaded = True
                except Exception as ex:
                    entry.error_detail = f"Drive API download failed: {str(ex)}"
                    
            # Try public export fallback
            if not downloaded:
                downloaded = download_public_drive_file(file_id, dest_path)
                
            if downloaded and os.path.exists(dest_path) and os.path.getsize(dest_path) > 100:
                entry.local_file_path = dest_path
                entry.availability_status = "Available"
            else:
                entry.availability_status = "Permission Denied / Inaccessible"
                if not entry.error_detail:
                    entry.error_detail = "Cannot access file. Ensure link sharing is set to 'Anyone with link' or provide credentials."
            continue
            
        # 3. Direct Web URL
        if entry.link_type == "direct_url":
            try:
                dest_path = os.path.join(temp_download_dir, f"{entry.course_code}_downloaded.xlsx")
                resp = requests.get(entry.target_url_or_path, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 100:
                    with open(dest_path, "wb") as f:
                        f.write(resp.content)
                    entry.local_file_path = dest_path
                    entry.availability_status = "Available"
                else:
                    entry.availability_status = "Download Failed"
                    entry.error_detail = f"HTTP status {resp.status_code}"
            except Exception as e:
                entry.availability_status = "Download Failed"
                entry.error_detail = str(e)
                
    return entries


def audit_index_inventory(
    index_file_path: str,
    base_dir: Optional[str] = None,
    gdrive_connector: Optional[GoogleDriveConnector] = None,
    progress_callback = None,
    api_key: Optional[str] = None,
    db_path: str = "data/tlep_audit.db"
) -> Dict[str, Any]:
    """
    Parses index file, downloads referenced course files, audits accessible courses,
    and returns comprehensive inventory metrics and detailed reconciliation rows.
    """
    from datetime import datetime

    if not base_dir:
        base_dir = os.path.dirname(os.path.abspath(index_file_path))
        
    entries = parse_index_document(index_file_path)
    resolved_entries = resolve_and_download_index_documents(
        entries,
        base_dir=base_dir,
        gdrive_connector=gdrive_connector,
        progress_callback=progress_callback
    )
    
    audited_count = 0
    available_count = 0
    missing_count = 0
    inaccessible_count = 0
    
    for entry in resolved_entries:
        if entry.availability_status == "Available" and entry.local_file_path:
            available_count += 1
            try:
                # Execute official 49-parameter audit
                audit_res = review_tlep_document(entry.local_file_path, api_key=api_key)
                entry.audit_result = audit_res
                entry.compliance_percentage = audit_res.compliance_percentage
                entry.audit_status = audit_res.overall_status.value
                entry.major_blockers_count = audit_res.major_revision_count + audit_res.non_compliant_count
                entry.minor_fixes_count = audit_res.needs_revision_count
                
                # Persist in institutional database
                audit_record = {
                    "review_id": audit_res.review_id,
                    "file_name": os.path.basename(entry.local_file_path),
                    "file_path": entry.local_file_path,
                    "school": "Unassigned",
                    "department": entry.department,
                    "programme": entry.programme,
                    "semester": entry.semester,
                    "course_code": entry.course_code,
                    "course_title": entry.course_title,
                    "compliance_pct": audit_res.compliance_percentage,
                    "overall_status": audit_res.overall_status.value,
                    "score_obtained": audit_res.score_obtained,
                    "maximum_score": audit_res.maximum_score,
                    "compliant_count": audit_res.compliant_count,
                    "needs_revision_count": audit_res.needs_revision_count,
                    "major_revision_count": audit_res.major_revision_count,
                    "critical_issues_count": len(audit_res.critical_issues),
                    "critical_issues": audit_res.critical_issues,
                    "department_action_plan": audit_res.department_action_plan,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                save_audit_result(audit_record, db_path=db_path)
                audited_count += 1
            except Exception as audit_err:
                entry.audit_status = "Audit Error"
                entry.error_detail = str(audit_err)
        elif "Missing" in entry.availability_status:
            missing_count += 1
        else:
            inaccessible_count += 1

    summary = {
        "total_listed_in_index": len(resolved_entries),
        "total_documents_available": available_count,
        "total_documents_missing": missing_count,
        "total_inaccessible": inaccessible_count,
        "total_audited": audited_count,
        "submission_rate_pct": round((available_count / len(resolved_entries)) * 100, 1) if resolved_entries else 0.0,
        "entries": resolved_entries
    }
    
    return summary


def generate_index_reconciliation_excel(inventory_summary: Dict[str, Any]) -> bytes:
    """
    Generates a formal multi-sheet Excel reconciliation report:
    1. Executive Inventory Summary
    2. Master Course Reconciliation
    3. Missing Documents Action List
    """
    import io
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    
    # Styles
    navy_fill = PatternFill(start_color="0F294A", end_color="0F294A", fill_type="solid")
    steel_fill = PatternFill(start_color="334E68", end_color="334E68", fill_type="solid")
    light_gray = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    yellow_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    
    font_title = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_sec = Font(name="Calibri", size=12, bold=True, color="0F294A")
    font_th = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Calibri", size=10)
    font_bold = Font(name="Calibri", size=10, bold=True)
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    
    # SHEET 1: Executive Summary
    ws_sum = wb.active
    ws_sum.title = "Executive Summary"
    ws_sum.views.sheetView[0].showGridLines = True
    
    ws_sum.merge_cells("A1:G2")
    c_title = ws_sum["A1"]
    c_title.value = "OFFICE OF ACADEMICS — COURSE TLEP INVENTORY & COMPLIANCE RECONCILIATION"
    c_title.fill = navy_fill
    c_title.font = font_title
    c_title.alignment = Alignment(horizontal="center", vertical="center")
    
    entries: List[IndexCourseEntry] = inventory_summary.get("entries", [])
    total_listed = inventory_summary.get("total_listed_in_index", 0)
    total_avail = inventory_summary.get("total_documents_available", 0)
    total_missing = inventory_summary.get("total_documents_missing", 0)
    total_inaccessible = inventory_summary.get("total_inaccessible", 0)
    total_audited = inventory_summary.get("total_audited", 0)
    sub_rate = inventory_summary.get("submission_rate_pct", 0.0)
    
    ready_count = sum(1 for e in entries if e.audit_status == "Compliant")
    minor_count = sum(1 for e in entries if e.audit_status == "Needs Revision")
    rework_count = sum(1 for e in entries if e.audit_status in ["Major Revision", "Non-Compliant"])
    
    kpis = [
        ("Total Courses Listed in Master Index", total_listed),
        ("Documents Available for Audit", total_avail),
        ("Documents Missing / Not Submitted", total_missing),
        ("Inaccessible / Broken Links", total_inaccessible),
        ("Overall Submission Compliance Rate", f"{sub_rate}%"),
        ("Audited: Approved for Board of Studies", ready_count),
        ("Audited: Minor Adjustments Needed", minor_count),
        ("Audited: Major Rework Required", rework_count),
    ]
    
    ws_sum.cell(row=4, column=1, value="INSTITUTIONAL INVENTORY METRICS").font = font_sec
    ws_sum.cell(row=5, column=1, value="Metric").fill = steel_fill
    ws_sum.cell(row=5, column=1).font = font_th
    ws_sum.cell(row=5, column=2, value="Value").fill = steel_fill
    ws_sum.cell(row=5, column=2).font = font_th
    
    for idx, (lbl, val) in enumerate(kpis, 6):
        ws_sum.cell(row=idx, column=1, value=lbl).font = font_body
        ws_sum.cell(row=idx, column=1).border = thin_border
        c_v = ws_sum.cell(row=idx, column=2, value=val)
        c_v.font = font_bold
        c_v.alignment = Alignment(horizontal="center")
        c_v.border = thin_border
        
    # SHEET 2: Master Course Inventory Table
    ws_master = wb.create_sheet(title="Course Inventory & Audit")
    ws_master.views.sheetView[0].showGridLines = True
    
    headers = [
        "Index Row", "Course Code", "Course Title", "Department", "Programme", 
        "Semester", "Faculty", "Document Status", "Link / Target Reference", 
        "Audit Status", "Compliance %", "Critical Blockers", "Minor Fixes", "Observations / Detail"
    ]
    
    for c_idx, h in enumerate(headers, 1):
        cell = ws_master.cell(row=1, column=c_idx, value=h)
        cell.fill = navy_fill
        cell.font = font_th
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
    for r_idx, e in enumerate(entries, 2):
        row_vals = [
            e.row_number,
            e.course_code,
            e.course_title,
            e.department,
            e.programme,
            e.semester,
            e.faculty,
            e.availability_status,
            e.target_url_or_path or e.raw_reference or "None Provided",
            e.audit_status or "Not Audited",
            f"{e.compliance_percentage}%" if e.compliance_percentage is not None else "-",
            e.major_blockers_count if e.compliance_percentage is not None else "-",
            e.minor_fixes_count if e.compliance_percentage is not None else "-",
            e.error_detail or (f"Compliant ({e.compliance_percentage}%)" if e.audit_status == "Compliant" else "")
        ]
        
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws_master.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_body
            cell.border = thin_border
            
            # Highlight availability
            if c_idx == 8:  # Document Status
                if e.availability_status == "Available":
                    cell.fill = green_fill
                elif "Missing" in e.availability_status:
                    cell.fill = red_fill
                else:
                    cell.fill = yellow_fill
            # Highlight audit status
            elif c_idx == 10:  # Audit Status
                if e.audit_status == "Compliant":
                    cell.fill = green_fill
                elif e.audit_status == "Needs Revision":
                    cell.fill = yellow_fill
                elif e.audit_status in ["Major Revision", "Non-Compliant"]:
                    cell.fill = red_fill

    # SHEET 3: Missing Documents Action List
    ws_missing = wb.create_sheet(title="Action Required - Missing Files")
    ws_missing.views.sheetView[0].showGridLines = True
    
    missing_headers = [
        "Index Row", "Course Code", "Course Title", "Department", "Faculty / Facilitator", 
        "Issue Description", "Link / Raw Reference", "Immediate Follow-Up Action"
    ]
    for c_idx, h in enumerate(missing_headers, 1):
        cell = ws_missing.cell(row=1, column=c_idx, value=h)
        cell.fill = steel_fill
        cell.font = font_th
        cell.alignment = Alignment(horizontal="center", vertical="center")
        
    m_row = 2
    for e in entries:
        if e.availability_status != "Available":
            act = "Collect official TLEP document from course facilitator" if "Missing" in e.availability_status else "Verify Google Drive access permissions with course facilitator"
            m_vals = [
                e.row_number,
                e.course_code,
                e.course_title,
                e.department,
                e.faculty,
                e.availability_status,
                e.raw_reference or "None",
                act
            ]
            for c_idx, val in enumerate(m_vals, 1):
                cell = ws_missing.cell(row=m_row, column=c_idx, value=val)
                cell.font = font_body
                cell.border = thin_border
            m_row += 1

    # Auto-fit columns
    for ws in [ws_sum, ws_master, ws_missing]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len and len(val_str) < 60:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def is_index_file(file_path: str) -> bool:
    """
    Determines if a document is an institutional curriculum/course index or roster,
    rather than an individual course TLEP syllabus/session plan.
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return False
        
    ext = os.path.splitext(file_path)[1].lower()
    fname = os.path.basename(file_path).lower()
    
    # Filename keyword check
    if any(k in fname for k in ["index", "catalog", "inventory", "roster", "course_list", "tlep_links", "master_list"]):
        return True

    if ext in [".xlsx", ".xls"]:
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
            sheet_names_lower = [s.lower() for s in wb.sheetnames]
            
            # If standard single-course TLEP sheets exist, it is a course TLEP, not an index
            if any("session plan" in s for s in sheet_names_lower) or any("course details & syllabus" in s for s in sheet_names_lower):
                return False
                
            for name in wb.sheetnames[:3]:
                ws = wb[name]
                header_detected = False
                row_course_count = 0
                for r_idx, row in enumerate(ws.iter_rows(max_row=25, values_only=True), 1):
                    row_vals = [str(v or "").strip().lower() for v in row if v is not None]
                    
                    if any("code" in v or "course" in v or "subject" in v for v in row_vals) and \
                       any("link" in v or "url" in v or "tlep" in v or "drive" in v or "faculty" in v or "facilitator" in v or "status" in v or "doc" in v for v in row_vals):
                        header_detected = True
                        continue
                        
                    if header_detected:
                        if any(re.match(r"^[A-Z]{2,5}\s*\d{2,4}", str(v).strip()) for v in row if v is not None):
                            row_course_count += 1
                            
                if header_detected and row_course_count >= 1:
                    return True
        except Exception:
            pass

    elif ext == ".docx":
        try:
            doc = Document(file_path)
            for table in doc.tables:
                if len(table.rows) >= 2:
                    header = [c.text.strip().lower() for c in table.rows[0].cells]
                    if any("code" in h or "course" in h for h in header) and any("link" in h or "url" in h or "tlep" in h or "status" in h for h in header):
                        return True
        except Exception:
            pass

    return False


def audit_directory_or_batch(
    files_or_dir: Any,
    base_dir: Optional[str] = None,
    gdrive_connector: Optional[GoogleDriveConnector] = None,
    mode: str = "auto",  # "auto", "index", "courses"
    progress_callback = None,
    api_key: Optional[str] = None,
    db_path: str = "data/tlep_audit.db"
) -> Dict[str, Any]:
    """
    Unified Ingestion & Inventory Reconciliation Engine.
    Handles any combination of:
    - Master Index spreadsheets / catalogs (.xlsx, .docx)
    - Standalone Course TLEP files (.xlsx, .docx, .pdf)
    - Directories or ZIPs containing mixed indexes and course files.
    """
    from engine.batch_processor import process_batch_files
    
    # 1. Resolve list of files and base directory
    if isinstance(files_or_dir, str):
        if os.path.isdir(files_or_dir):
            base_dir = files_or_dir
            all_files = []
            for root, _, fnames in os.walk(files_or_dir):
                for fn in fnames:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in [".xlsx", ".xls", ".docx", ".pdf"] and not fn.startswith("~$"):
                        all_files.append(os.path.join(root, fn))
        else:
            all_files = [files_or_dir]
            if not base_dir:
                base_dir = os.path.dirname(os.path.abspath(files_or_dir))
    else:
        all_files = list(files_or_dir)
        if not base_dir and all_files:
            base_dir = os.path.dirname(os.path.abspath(all_files[0]))

    if not all_files:
        return {
            "type": "empty",
            "message": "No supported files (.xlsx, .docx, .pdf) detected.",
            "audited_count": 0
        }

    # 2. Identify index files vs course files
    index_files = []
    course_files = []
    
    if mode == "index":
        index_files = [f for f in all_files if os.path.splitext(f)[1].lower() in [".xlsx", ".xls", ".docx"]]
        course_files = [f for f in all_files if f not in index_files]
    elif mode == "courses":
        course_files = all_files
    else:  # "auto"
        for f in all_files:
            if is_index_file(f):
                index_files.append(f)
            else:
                course_files.append(f)

    # 3. If index files found: Reconcile Index Inventory
    if index_files:
        primary_index = index_files[0]
        summary = audit_index_inventory(
            index_file_path=primary_index,
            base_dir=base_dir,
            gdrive_connector=gdrive_connector,
            progress_callback=progress_callback,
            api_key=api_key,
            db_path=db_path
        )
        return {
            "type": "index_inventory",
            "primary_index_path": primary_index,
            "all_index_paths": index_files,
            "inventory_summary": summary,
            "audited_count": summary.get("total_audited", 0),
            "total_listed": summary.get("total_listed_in_index", 0),
            "available_count": summary.get("total_documents_available", 0),
            "missing_count": summary.get("total_documents_missing", 0),
            "inaccessible_count": summary.get("total_inaccessible", 0)
        }

    # 4. If no index files: Audit all courses directly
    else:
        results = process_batch_files(
            course_files,
            progress_callback=progress_callback,
            api_key=api_key,
            db_path=db_path
        )
        return {
            "type": "direct_batch",
            "results": results,
            "audited_count": len(results),
            "course_files": course_files
        }

