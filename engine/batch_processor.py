"""
Batch Processing Engine for Institutional Scale (2000+ TLEPs)
Handles department, programme, and semester folder hierarchies.
"""

import os
import zipfile
import shutil
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from engine.reviewer import review_tlep_document
from engine.db import save_audit_result
from models.schemas import TLEPReviewResult, StatusEnum


def extract_hierarchy_from_path(file_path: str) -> Dict[str, str]:
    """
    Infers Department, Programme, and Semester from standard directory hierarchy:
    e.g. /Root/Department_of_Computer_Science/BTech_CSE/Semester_6/CS601.xlsx
    """
    parts = os.path.normpath(file_path).split(os.sep)
    dept = "Unassigned"
    prog = "Unassigned"
    sem = "Unassigned"
    
    if len(parts) >= 4:
        dept = parts[-4].replace("_", " ")
        prog = parts[-3].replace("_", " ")
        sem = parts[-2].replace("_", " ")
    elif len(parts) == 3:
        dept = parts[-3].replace("_", " ")
        prog = parts[-2].replace("_", " ")
    elif len(parts) == 2:
        dept = parts[-2].replace("_", " ")
        
    return {"department": dept, "programme": prog, "semester": sem}


def process_single_file_batch(
    file_path: str,
    api_key: Optional[str] = None,
    db_path: str = "data/tlep_audit.db"
) -> Dict[str, Any]:
    """Processes one course TLEP and saves to DB."""
    path_meta = extract_hierarchy_from_path(file_path)
    
    # Execute full 49-parameter review
    result: TLEPReviewResult = review_tlep_document(file_path, api_key=api_key)
    
    # Priority: Document header metadata > Folder path metadata
    dept = result.normalized_tlep.course_info.department or path_meta["department"]
    prog = result.normalized_tlep.course_info.programme or path_meta["programme"]
    sem = result.normalized_tlep.course_info.semester or path_meta["semester"]
    course_code = result.normalized_tlep.course_info.course_code or os.path.splitext(os.path.basename(file_path))[0]
    course_title = result.normalized_tlep.course_info.course_title or os.path.splitext(os.path.basename(file_path))[0]
    
    audit_record = {
        "review_id": result.review_id,
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "department": dept,
        "programme": prog,
        "semester": sem,
        "course_code": course_code,
        "course_title": course_title,
        "compliance_pct": result.compliance_percentage,
        "overall_status": result.overall_status.value,
        "score_obtained": result.score_obtained,
        "maximum_score": result.maximum_score,
        "compliant_count": result.compliant_count,
        "needs_revision_count": result.needs_revision_count,
        "major_revision_count": result.major_revision_count,
        "critical_issues_count": len(result.critical_issues),
        "critical_issues": result.critical_issues,
        "department_action_plan": result.department_action_plan,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    save_audit_result(audit_record, db_path=db_path)
    return audit_record


def process_batch_files(
    file_paths: List[str],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    api_key: Optional[str] = None,
    db_path: str = "data/tlep_audit.db"
) -> List[Dict[str, Any]]:
    """Runs batch audit sequentially across multiple files."""
    results = []
    total = len(file_paths)
    
    for idx, fpath in enumerate(file_paths, 1):
        if progress_callback:
            progress_callback(idx, total, os.path.basename(fpath))
            
        try:
            record = process_single_file_batch(fpath, api_key=api_key, db_path=db_path)
            record["status_flag"] = "SUCCESS"
            results.append(record)
        except Exception as e:
            results.append({
                "review_id": f"ERR-{idx}",
                "file_name": os.path.basename(fpath),
                "file_path": fpath,
                "department": "Unknown",
                "programme": "Unknown",
                "semester": "Unknown",
                "course_code": "PARSE_ERROR",
                "course_title": os.path.basename(fpath),
                "compliance_pct": 0.0,
                "overall_status": "Failed",
                "score_obtained": 0,
                "maximum_score": 98,
                "compliant_count": 0,
                "needs_revision_count": 0,
                "major_revision_count": 0,
                "critical_issues_count": 1,
                "critical_issues": [{"issue": f"Parsing failed: {str(e)}"}],
                "department_action_plan": [],
                "status_flag": "FAILED",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            
    return results


def extract_and_process_zip(
    zip_path: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Unpacks a zip containing department folder trees and reviews all courses."""
    temp_extract_dir = os.path.join("temp_batches", datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(temp_extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(temp_extract_dir)
        
    supported_files = []
    for root, _, files in os.walk(temp_extract_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".xlsx", ".xls", ".docx", ".pdf"] and not f.startswith("~$"):
                supported_files.append(os.path.join(root, f))
                
    results = process_batch_files(supported_files, progress_callback, api_key=api_key)
    return results
