"""
Test Batch Processing & Institutional Rollup for 2000+ Courses
Uses an isolated test DB and cleans up completely after execution.
"""

import sys
import os
import shutil
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_pipeline import create_sample_test_tlep
from engine.batch_processor import process_batch_files
from engine.db import get_all_audits, get_audit_summary_by_department
from reports.excel_report import generate_consolidated_report


def main():
    test_batch_dir = "tests/test_batch_data"
    test_db_path = "tests/test_audit.db"
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.makedirs(test_batch_dir, exist_ok=True)
    
    f1_dir = os.path.join(test_batch_dir, "Computer_Science", "BTech_CSE", "Sem_6")
    f2_dir = os.path.join(test_batch_dir, "Management_Studies", "MBA", "Sem_2")
    os.makedirs(f1_dir, exist_ok=True)
    os.makedirs(f2_dir, exist_ok=True)
    
    p1 = os.path.join(f1_dir, "CS601_Machine_Learning.xlsx")
    p2 = os.path.join(f1_dir, "CS602_Cloud_Computing.xlsx")
    p3 = os.path.join(f2_dir, "MBA201_Financial_Management.xlsx")
    
    create_sample_test_tlep(p1)
    create_sample_test_tlep(p2)
    create_sample_test_tlep(p3)
    
    print("\nRunning batch audit on 3 courses using isolated test DB...")
    results = process_batch_files([p1, p2, p3], db_path=test_db_path)
    
    assert len(results) == 3, f"Expected 3 records, got {len(results)}"
    
    # Verify DB
    all_audits = get_all_audits(db_path=test_db_path)
    print(f"Total audits in isolated test DB: {len(all_audits)}")
    assert len(all_audits) == 3
    
    # Verify Dept Summary
    dept_summary = get_audit_summary_by_department(db_path=test_db_path)
    print("Department Summary:", dept_summary)
    assert len(dept_summary) >= 1
    
    # Generate Consolidated Master Excel
    out_xlsx = os.path.join(test_batch_dir, "Master_Consolidated_Rollup.xlsx")
    generate_consolidated_report(all_audits, output_path=out_xlsx)
    assert os.path.exists(out_xlsx), "Master Excel was not generated"
    print(f"Master Consolidated Excel successfully created at: {out_xlsx}")
    
    # Clean up test files and test DB
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_batch_dir):
        shutil.rmtree(test_batch_dir)
        
    print("Batch test passed 100% and cleaned up test data completely!")


if __name__ == "__main__":
    main()
