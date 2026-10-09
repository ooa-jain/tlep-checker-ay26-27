# OOA TLEP Compliance Review System — AY 2026–27

Production-grade, evidence-based academic quality assurance compliance checker for Teaching-Learning and Evaluation Plans (TLEP), built for the **Office of Academics (OOA)** review process for **Academic Year 2026–27**.

---

## Source of Truth
- **Official Workbook**: [`OOA_TLEP_Review_Checklist_AY_2026-27.xlsx`](file:///C:/coding/tlep%20checker/OOA_TLEP_Review_Checklist_AY_2026-27.xlsx)
- **Official Review Areas**: 9 Areas (A to I)
- **Official Parameters**: Exactly 49 Parameters
- **Scoring Methodology**:
  - `Compliant` = 2 points
  - `Needs Revision` = 1 point
  - `Major Revision` = 0 points
  - `Non-Compliant` = 0 points
  - `NA / Not Reviewed` = Excluded from both numerator and denominator
  - $\text{Applicable Parameters} = \text{Total Parameters} - \text{NA Parameters} - \text{Not Reviewed}$
  - $\text{Maximum Score} = \text{Applicable Parameters} \times 2$
  - $\text{Compliance \%} = \frac{\text{Obtained Score}}{\text{Maximum Score}} \times 100$
- **Zero Fake Data Policy**:
  - The system contains strictly **0 synthetic, dummy, or pre-populated records**.
  - All audit evaluations, evidence quotes, and metrics are derived strictly from genuine department-uploaded TLEPs.

---

## Project Architecture

```text
tlep-checker/
├── app.py                      # Interactive Streamlit Web Dashboard
├── config/
│   └── checklist.json          # Canonical 49-parameter checklist configuration
├── models/
│   └── schemas.py              # Pydantic schemas for TLEP, findings & audit
├── extractors/
│   ├── base.py                 # Multi-format extractor dispatcher
│   ├── excel.py                # Excel (.xlsx, .xls) table & cell extractor
│   ├── docx.py                 # Word (.docx) paragraphs & tables extractor
│   └── pdf.py                  # PDF PyMuPDF text & page extractor
├── engine/
│   ├── checklist_engine.py     # Parameter loader and registry
│   ├── rule_engine.py          # Deterministic mathematical & structural validation
│   ├── ai_engine.py            # Academic qualitative analysis with heuristic fallback
│   ├── simplifier.py           # Plain-English jargon-free translator & quick-fix generator
│   ├── batch_processor.py      # Institutional batch processor (2000+ courses)
│   ├── db.py                   # SQLite persistence layer for cross-department audits
│   ├── cross_validation.py     # Relational graph consistency engine
│   ├── hours_validation.py     # 12-parameter learning hours & credit validator
│   ├── scoring.py              # Official scoring & area-wise aggregator
│   ├── index_scraper.py        # Master index scraper & document inventory engine
│   └── reviewer.py             # End-to-end master review pipeline
├── integrations/
│   └── google_drive.py         # Google Drive folder syncer and batch reader
├── reports/
│   └── excel_report.py         # Multi-sheet audit report generator
├── tests/
│   └── test_pipeline.py        # End-to-end test suite
└── requirements.txt
```

---

## Project Roadmap & Execution Progress

- [x] **Step 1: Inspect & Parse Official Excel Checklist**
  - Inspected all 5 sheets: `Instructions`, `TLEP Review Checklist`, `Dashboard`, `CO-PO Review`, `Hours Validation`.
  - Extracted scoring rules, formula structures, and priorities.
- [x] **Step 2: Structured 49-Parameter Configuration**
  - Created [`config/checklist.json`](file:///C:/coding/tlep%20checker/config/checklist.json) containing all 49 parameters with 100% fidelity.
  - Verified 1:1 match with official workbook via [`scripts/verify_checklist_data.py`](file:///C:/coding/tlep%20checker/scripts/verify_checklist_data.py).
- [x] **Step 3: Document Extractors (Excel, DOCX, PDF)**
  - Built [`extractors/excel.py`](file:///C:/coding/tlep%20checker/extractors/excel.py), [`extractors/docx.py`](file:///C:/coding/tlep%20checker/extractors/docx.py), and [`extractors/pdf.py`](file:///C:/coding/tlep%20checker/extractors/pdf.py).
  - Built unified dispatcher [`extractors/base.py`](file:///C:/coding/tlep%20checker/extractors/base.py).
- [x] **Step 4: Normalized Internal TLEP Representation**
  - Implemented canonical data model using Pydantic schemas in [`models/schemas.py`](file:///C:/coding/tlep%20checker/models/schemas.py).
- [x] **Step 5: Deterministic Validation Engine**
  - Code-based mathematical & structural verification (credits, L-T-P-E, hours, totals, session gaps, missing fields) in [`engine/rule_engine.py`](file:///C:/coding/tlep%20checker/engine/rule_engine.py).
- [x] **Step 6: AI Academic Review Engine**
  - Qualitative checks (CO action verbs, Bloom's Taxonomy alignment, syllabus depth, pedagogy suitability, rubrics) in [`engine/ai_engine.py`](file:///C:/coding/tlep%20checker/engine/ai_engine.py) with offline heuristic fallback.
- [x] **Step 7: Cross-Validation & Relationship Graph Engine**
  - Relational consistency: Course  Module  Topic  Session  CO  BTL  PO/PSO  Assessment  Rubric in [`engine/cross_validation.py`](file:///C:/coding/tlep%20checker/engine/cross_validation.py).
- [x] **Step 8: Learning Hours & Credit Validation Module**
  - Full comparison: Approved vs TLEP vs Module vs Session vs Synchronous/Asynchronous/Notional hours in [`engine/hours_validation.py`](file:///C:/coding/tlep%20checker/engine/hours_validation.py).
- [x] **Step 9: Scoring & Aggregation Engine**
  - Calculate exact scores, compliance %, area-wise breakdown, and audit metadata in [`engine/scoring.py`](file:///C:/coding/tlep%20checker/engine/scoring.py).
- [x] **Step 10: Multi-Sheet Excel Audit Report**
  - Generates official multi-sheet downloadable audit reports in [`reports/excel_report.py`](file:///C:/coding/tlep%20checker/reports/excel_report.py).
  - Consolidated Institutional Export includes:
    1. **`Executive Summary`** with institutional KPIs and department performance leaderboard.
    2. **`All Courses Master`** sorted by School, Department, Programme, and Semester.
    3. **Dedicated Department Tabs** (e.g. `CSE`, `Management`, `Commerce`) for each department with course-specific findings and required actions.
    4. **Department-Filtered Download Button** in the UI to export single department packages directly for HoDs.
- [x] **Step 11: Single-TLEP Review Dashboard UI (Streamlit)**
  - Implemented interactive web UI in [`app.py`](file:///C:/coding/tlep%20checker/app.py) with drag-and-drop upload, filtering, KPI cards, hours table, CO-PO review, critical issues, and downloadable audit reports.
  - Added **Plain-English Jargon-Free Simplifier** ([`engine/simplifier.py`](file:///C:/coding/tlep%20checker/engine/simplifier.py)) and **3-Second Traffic Light Verdict** for fast faculty reviews.
- [x] **Step 12: End-to-End Test Suite**
  - Verified end-to-end execution on sample data via [`tests/test_pipeline.py`](file:///C:/coding/tlep%20checker/tests/test_pipeline.py) (100% test pass).
- [x] **Step 13: Bulk TLEP Processing Engine & Institutional Portfolio (2000+ Courses)**
  - Implemented [`engine/batch_processor.py`](file:///C:/coding/tlep%20checker/engine/batch_processor.py) & [`engine/db.py`](file:///C:/coding/tlep%20checker/engine/db.py).
  - Handles **5-tier institutional academic hierarchy**:
    $$\text{School / Faculty} \longrightarrow \text{Department} \longrightarrow \text{Programme} \longrightarrow \text{Semester} \longrightarrow \text{Course (TLEP)}$$
  - Added institutional dashboard with School/Department drill-down, leaderboard, and master consolidated Excel export.
  - Verified via [`tests/test_batch.py`](file:///C:/coding/tlep%20checker/tests/test_batch.py).
- [x] **Step 14: Google Drive Folder Integration**
  - Implemented [`integrations/google_drive.py`](file:///C:/coding/tlep%20checker/integrations/google_drive.py).
  - Connects to shared Google Drive folder URLs, scans subfolders for Department/Programme structures, and downloads supported files.
  - Feeds directly into the exact same 49-parameter review pipeline and consolidated rollup generator.
  - Verified via [`tests/test_gdrive.py`](file:///C:/coding/tlep%20checker/tests/test_gdrive.py).
- [x] **Step 15: Index Scraper & Document Inventory Reconciliation Engine**
  - Implemented [`engine/index_scraper.py`](file:///C:/coding/tlep%20checker/engine/index_scraper.py).
  - Automatically parses curriculum index / catalog documents (`.xlsx`, `.docx`), scrapes embedded hyperlinks, Google Drive links, and local file paths.
  - Performs real-time document inventory reconciliation (Documents Available vs Missing / Not Submitted vs Inaccessible Links).
  - Automatically downloads remote files, audits every accessible document against all 49 parameters, and exports a dedicated 3-sheet **Inventory & Compliance Reconciliation Workbook**.
  - Verified via [`tests/test_index_scraper.py`](file:///C:/coding/tlep%20checker/tests/test_index_scraper.py).

---


- [x] **Step 16: AI Semantic Enrichment (Secondary Layer)**
  - Upgraded AI integration to correctly parse structural context and pass to gemini-1.5-pro.
  - Ensures Hardcoded Rule Engine is always the primary source of truth for audit status and scores.
  - AI acts only as a qualitative enrichment layer, appending academic feedback to deterministic findings.
- [x] **Step 17: Concurrent Multiple Report Export**
  - Added capability to generate a ZIP archive containing all individual 6-sheet Course Audit Reports.
  - Available after batch ingestion or index reconciliation, directly in the UI alongside the master rollup.
- [x] **Step 18: Bugfixes & Optimization (Pointers & Cache)**
  - Enforced bullet-point (pointers) outputs in the AI engine and explicitly restricted generic summaries.
  - Resolved `GoogleDriveConnector` attribute error by implementing the missing `sync_and_download_folder` method.
  - Fixed Streamlit `st.session_state` caching issues where older single/batch TLEP results lingered inappropriately on new file uploads.
  - Ensure API Key propagates reliably into the Batch and Index scraping pipelines to activate full AI processing across large portfolios.


## Cloud Deployment & Institutional Access

The repository is published on GitHub:
* **GitHub Repository**: [https://github.com/ooa-jain/tlep-checker-ay26-27](https://github.com/ooa-jain/tlep-checker-ay26-27)

### Deploying to Streamlit Community Cloud (Free & Instant)
To host this so everyone across departments and leadership can access it with a permanent web link:
1. Navigate to [share.streamlit.io](https://share.streamlit.io) and log in with the `ooa-jain` GitHub account.
2. Click **New app**.
3. Fill in:
   - **Repository**: `ooa-jain/tlep-checker-ay26-27`
   - **Branch**: `master`
   - **Main file path**: `app.py`
4. Click **Deploy!**
5. You will receive an instant public institutional URL (e.g., `https://tlep-checker-ay26-27.streamlit.app`).

---

## Running Locally

The application is actively running live on your workstation at:
* **Local URL**: [http://localhost:8501](http://localhost:8501)

Or start manually in your terminal:
```powershell
streamlit run app.py
```


### Recent Updates
1. **Executive Summary Feature:** Added automated Executive Narrative generation matching the TLEP REVIEW REMARKS format using the Gemini Pro API.
2. **UI Integration:** Integrated the generated executive narrative into a prominent tab in the Streamlit UI.
3. **Caching & Concurrency fixes:** Fixed Streamlit caching causing duplicate outputs, corrected batch processor AI context propagation, and patched the Google Drive connector missing attribute issue.
