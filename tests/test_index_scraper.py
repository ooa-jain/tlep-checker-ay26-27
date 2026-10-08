import os
import sys
import shutil
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import openpyxl
from engine.index_scraper import parse_index_excel, audit_index_inventory, generate_index_reconciliation_excel
from tests.test_pipeline import create_sample_test_tlep

def test_index_scraper_pipeline():
    temp_dir = tempfile.mkdtemp(prefix="test_index_suite_")
    try:
        # Create a valid sample course file in the directory
        valid_course_path = os.path.join(temp_dir, "CS701_Deep_Learning.xlsx")
        create_sample_test_tlep(valid_course_path)

        # Create an index file referencing the course file, a missing course, and a remote link
        index_path = os.path.join(temp_dir, "Department_TLEP_Master_Index.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Course Index"
        
        ws.append(["Sl No", "Course Code", "Course Title", "Department", "Programme", "Semester", "Course Facilitator", "TLEP Document Link"])
        
        # 1. Available local file
        ws.append([1, "CS701", "Deep Learning", "Computer Science", "B.Tech CSE", "Sem 7", "Dr. A. Sharma", "CS701_Deep_Learning.xlsx"])
        
        # 2. Course with missing document
        ws.append([2, "CS702", "Distributed Systems", "Computer Science", "B.Tech CSE", "Sem 7", "Dr. B. Verma", ""])
        
        # 3. Course with dummy external link
        ws.append([3, "CS703", "Natural Language Processing", "Computer Science", "B.Tech CSE", "Sem 7", "Dr. C. Rao", "https://drive.google.com/file/d/dummy_file_id_12345/view"])

        wb.save(index_path)

        # Parse index
        entries = parse_index_excel(index_path)
        assert len(entries) == 3, f"Expected 3 entries, found {len(entries)}"
        assert entries[0].course_code == "CS701"
        assert entries[1].course_code == "CS702"
        assert entries[2].course_code == "CS703"

        # Audit index inventory
        test_db_path = os.path.join(temp_dir, "test_audit.db")
        result = audit_index_inventory(index_path, base_dir=temp_dir, db_path=test_db_path)
        assert result["total_listed_in_index"] == 3
        assert result["total_documents_available"] == 1
        assert result["total_documents_missing"] == 1
        assert result["total_audited"] == 1
        assert result["submission_rate_pct"] == 33.3

        # Generate reconciliation report
        report_bytes = generate_index_reconciliation_excel(result)
        assert len(report_bytes) > 2000, "Reconciliation report should contain valid Excel bytes"

        print("test_index_scraper_pipeline passed successfully!")

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_index_scraper_pipeline()
