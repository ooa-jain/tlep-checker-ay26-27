"""
SQLite Database Layer for OOA TLEP Compliance Review System
Stores audit records for thousands of courses across Departments and Programmes.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = "data/tlep_audit.db"


def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS course_audits (
        review_id TEXT PRIMARY KEY,
        file_name TEXT,
        file_path TEXT,
        department TEXT,
        programme TEXT,
        semester TEXT,
        course_code TEXT,
        course_title TEXT,
        compliance_pct REAL,
        overall_status TEXT,
        score_obtained INTEGER,
        maximum_score INTEGER,
        compliant_count INTEGER,
        needs_revision_count INTEGER,
        major_revision_count INTEGER,
        critical_issues_count INTEGER,
        critical_issues_json TEXT,
        action_plan_json TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_audit_result(result_dict: Dict[str, Any], db_path: str = DB_PATH):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO course_audits (
        review_id, file_name, file_path, department, programme, semester,
        course_code, course_title, compliance_pct, overall_status,
        score_obtained, maximum_score, compliant_count, needs_revision_count,
        major_revision_count, critical_issues_count, critical_issues_json,
        action_plan_json, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result_dict["review_id"],
        result_dict["file_name"],
        result_dict.get("file_path", ""),
        result_dict.get("department", "Unassigned"),
        result_dict.get("programme", "Unassigned"),
        result_dict.get("semester", "Unassigned"),
        result_dict.get("course_code", "Unknown"),
        result_dict.get("course_title", "Unknown"),
        result_dict["compliance_pct"],
        result_dict["overall_status"],
        result_dict["score_obtained"],
        result_dict["maximum_score"],
        result_dict["compliant_count"],
        result_dict["needs_revision_count"],
        result_dict["major_revision_count"],
        result_dict["critical_issues_count"],
        json.dumps(result_dict.get("critical_issues", [])),
        json.dumps(result_dict.get("department_action_plan", [])),
        result_dict["timestamp"]
    ))
    conn.commit()
    conn.close()


def get_all_audits(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM course_audits ORDER BY timestamp DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_audit_summary_by_department(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        department,
        COUNT(*) as total_courses,
        ROUND(AVG(compliance_pct), 1) as avg_compliance,
        SUM(CASE WHEN overall_status = 'Compliant' THEN 1 ELSE 0 END) as approved_courses,
        SUM(CASE WHEN overall_status = 'Needs Revision' THEN 1 ELSE 0 END) as minor_fix_courses,
        SUM(CASE WHEN overall_status IN ('Major Revision', 'Non-Compliant') THEN 1 ELSE 0 END) as rework_courses
    FROM course_audits
    GROUP BY department
    ORDER BY avg_compliance ASC
    """)
    rows = []
    for r in cur.fetchall():
        rows.append({
            "department": r[0],
            "total_courses": r[1],
            "avg_compliance": r[2],
            "approved_courses": r[3],
            "minor_fix_courses": r[4],
            "rework_courses": r[5]
        })
    conn.close()
    return rows
