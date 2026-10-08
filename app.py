"""
OOA TLEP Compliance Review System
AY 2026–27
Institutional Scale Edition — Single Course Review & 2000+ Course Portfolio Manager
"""

import streamlit as st
import os
import tempfile
import pandas as pd
from engine.reviewer import review_tlep_document
from reports.excel_report import generate_excel_report, generate_consolidated_report
from engine.scoring import aggregate_area_breakdown
from engine.simplifier import simplify_finding
from engine.batch_processor import process_batch_files, extract_and_process_zip
from engine.db import get_all_audits, get_audit_summary_by_department
from models.schemas import StatusEnum

st.set_page_config(
    page_title="OOA TLEP Checker — AY 2026–27",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styles
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1F497D;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #555;
        margin-bottom: 1.2rem;
    }
    .verdict-box-green {
        background-color: #E8F5E9;
        border-left: 6px solid #2E7D32;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .verdict-box-yellow {
        background-color: #FFFDE7;
        border-left: 6px solid #FBC02D;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .verdict-box-red {
        background-color: #FFEBEE;
        border-left: 6px solid #C62828;
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar: Operation Mode Switcher
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/diploma.png", width=64)
    st.title("OOA TLEP Review")
    st.markdown("**Academic Year 2026–27**")
    
    mode = st.radio(
        "Select Operation Mode:",
        ["📄 Single Course Review", "🏢 Department & Institutional Portfolio (2000+)"],
        index=0
    )
    
    st.divider()
    st.subheader("⚙️ Settings")
    api_key_input = st.text_input(
        "AI Key (Optional)",
        type="password",
        help="Optional: If left blank, runs using high-speed deterministic rules and academic heuristic algorithms."
    )
    
    st.divider()
    st.caption("Office of Academics (OOA) • Official Quality Assurance Standard")

# =========================================================================
# MODE 1: SINGLE COURSE TLEP REVIEW
# =========================================================================
if mode == "📄 Single Course Review":
    st.markdown('<div class="main-title">🎓 Single Course TLEP Review</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Audit an individual course syllabus and session plan against all 49 OOA criteria.</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Course TLEP Document (XLSX, DOCX, or PDF)",
        type=["xlsx", "xls", "docx", "pdf"],
        help="Drag and drop an individual course TLEP file here."
    )

    if uploaded_file is not None:
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            check_clicked = st.button("🚀 REVIEW COURSE TLEP", use_container_width=True, type="primary")
            
        if check_clicked or "last_result" in st.session_state:
            if check_clicked:
                with st.spinner("Analyzing course against 49 official criteria, validating contact hours, and checking outcomes..."):
                    suffix = os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getbuffer())
                        tmp_path = tmp.name

                    try:
                        result = review_tlep_document(tmp_path, api_key=api_key_input)
                        st.session_state["last_result"] = result
                        st.session_state["uploaded_file_name"] = uploaded_file.name
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

            result = st.session_state["last_result"]

            # Executive Verdict
            st.divider()
            major_issues_count = result.major_revision_count + result.non_compliant_count
            needs_revision_count = result.needs_revision_count
            
            if major_issues_count == 0 and needs_revision_count == 0:
                st.markdown(f"""
                <div class="verdict-box-green">
                    <h3 style="color: #2E7D32; margin: 0 0 6px 0;">🟢 READY FOR SIGN-OFF (Score: {result.compliance_percentage}%)</h3>
                    <p style="margin: 0; color: #1B5E20; font-size: 1.05rem;">
                        <strong>Verdict:</strong> All 49 academic quality parameters are compliant. This course TLEP is ready for Board of Studies (BoS) submission.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            elif major_issues_count == 0:
                st.markdown(f"""
                <div class="verdict-box-yellow">
                    <h3 style="color: #F57F17; margin: 0 0 6px 0;">🟡 MINOR ADJUSTMENTS NEEDED (Score: {result.compliance_percentage}%)</h3>
                    <p style="margin: 0; color: #E65100; font-size: 1.05rem;">
                        <strong>Verdict:</strong> Course is sound, but has <strong>{needs_revision_count} minor items</strong> to fix before final sign-off.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="verdict-box-red">
                    <h3 style="color: #C62828; margin: 0 0 6px 0;">🔴 REWORK REQUIRED BEFORE SUBMISSION (Score: {result.compliance_percentage}%)</h3>
                    <p style="margin: 0; color: #B71C1C; font-size: 1.05rem;">
                        <strong>Verdict:</strong> Found <strong>{major_issues_count} major issue(s)</strong> that must be resolved prior to submission.
                    </p>
                </div>
                """, unsafe_allow_html=True)

            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Compliance Score", f"{result.compliance_percentage}%", delta=f"{result.score_obtained} / {result.maximum_score} pts")
            with col2:
                st.metric("Fully Approved", f"{result.compliant_count} / {result.applicable_parameters}")
            with col3:
                st.metric("Quick Fixes", result.needs_revision_count)
            with col4:
                st.metric("Major Blockers", major_issues_count)
            with col5:
                st.metric("Not Applicable (NA)", result.na_count)

            report_bytes = generate_excel_report(result)
            st.download_button(
                label="📥 Download Official OOA Excel Audit Report (.xlsx)",
                data=report_bytes,
                file_name=f"OOA_Course_Audit_{result.file_name}_{result.review_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            st.divider()

            # Progressive Tabs
            tab_plain, tab_hours, tab_outcomes, tab_full_audit, tab_areas = st.tabs([
                "⚡ 1. What To Fix (Plain English)",
                "⏱️ 2. Class Hours & Workload",
                "🎯 3. What's Taught vs What's Tested",
                "📋 4. Complete 49-Parameter Audit",
                "📊 5. Section-by-Section Scores"
            ])

            actionable_findings = [f for f in result.parameter_findings if f.status in [StatusEnum.NEEDS_REVISION, StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT]]

            with tab_plain:
                st.subheader("⚡ Plain-English Fix Checklist")
                simplified_items = [simplify_finding(f) for f in actionable_findings]
                if not simplified_items:
                    st.success("🎉 Amazing! There are zero action items. The entire plan is compliant.")
                else:
                    high_fixes = [item for item in simplified_items if item["priority"] == "High" or item["status"] in ["Major Revision", "Non-Compliant"]]
                    other_fixes = [item for item in simplified_items if item not in high_fixes]
                    if high_fixes:
                        st.markdown("#### 🚨 Must-Fix Blockers (High Priority)")
                        for fix in high_fixes:
                            st.error(f"**Fix {fix['friendly_name']}** (Checklist #{fix['parameter_id']})\n\n"
                                     f"• **What's wrong:** {fix['what_is_wrong']}\n\n"
                                     f"• **What to do:** 👉 **{fix['what_to_do']}**\n\n"
                                     f"• **Location:** `{fix['where']}`")
                    if other_fixes:
                        st.markdown("#### ✏️ Minor Enhancements & Clarifications")
                        for fix in other_fixes:
                            st.warning(f"**Adjust {fix['friendly_name']}** (Checklist #{fix['parameter_id']})\n\n"
                                       f"• **What's wrong:** {fix['what_is_wrong']}\n\n"
                                       f"• **What to do:** 👉 **{fix['what_to_do']}**\n\n"
                                       f"• **Location:** `{fix['where']}`")

            with tab_hours:
                st.subheader("⏱️ Hours & Credit Workload Verification")
                hours_display = []
                for hr in result.hours_validation_rows:
                    status_icon = "✅" if hr.status == StatusEnum.COMPLIANT else ("⚠️" if hr.status == StatusEnum.NEEDS_REVISION else "❌")
                    hours_display.append({
                        "Item": hr.parameter,
                        "In Curriculum": hr.approved if hr.approved is not None else "-",
                        "In Submitted TLEP": hr.tlep if hr.tlep is not None else "-",
                        "Variance": hr.variance,
                        "Status": f"{status_icon} {hr.status.value}",
                        "Explanation": hr.remarks,
                        "Action Needed": hr.action_required or "None"
                    })
                st.dataframe(pd.DataFrame(hours_display), use_container_width=True)

            with tab_outcomes:
                st.subheader("🎯 Learning Outcomes Alignment (End-to-End)")
                c_info = result.normalized_tlep
                if c_info and c_info.course_outcomes:
                    co_matrix = []
                    for co in c_info.course_outcomes:
                        taught_in = [s.session_number for s in c_info.sessions if co.id.upper() in [x.upper() for x in s.co_mapped]]
                        tested_in = [a.component_name for a in c_info.assessments if co.id.upper() in [x.upper() for x in a.co_mapped]]
                        co_matrix.append({
                            "Outcome ID": co.id,
                            "What Students Will Learn": co.statement,
                            "Cognitive Level (Bloom)": co.btl or "Not specified",
                            "Taught in Classes?": f"✅ Yes ({len(taught_in)} classes)" if taught_in else "❌ No classes mapped",
                            "Tested in Exams?": f"✅ Yes ({len(tested_in)} assessments)" if tested_in else "❌ Not evaluated"
                        })
                    st.dataframe(pd.DataFrame(co_matrix), use_container_width=True)
                else:
                    st.info("No Course Outcomes detected in the document to analyze.")

            with tab_full_audit:
                st.subheader("📋 Official 49-Parameter Academic Review")
                display_findings = result.parameter_findings
                for f in display_findings:
                    status_color = "green" if f.status == StatusEnum.COMPLIANT else ("orange" if f.status == StatusEnum.NEEDS_REVISION else "red")
                    with st.expander(f"**#{f.parameter_id} [{f.review_area}] {f.parameter}** — :{status_color}[{f.status.value}] ({f.score if f.score is not None else 'NA'} pts)"):
                        st.markdown(f"**Official Criterion:** {f.criterion}")
                        st.markdown(f"**Audit Finding:** {f.reason}")
                        if f.action_required:
                            st.error(f"**Action Required:** {f.action_required}")
                        st.caption(f"Priority: {f.priority.value} | Validation: {f.validation_type.value}")
                        if f.evidence:
                            st.markdown("**Evidence in Document:**")
                            for ev in f.evidence:
                                st.code(f"Location: {ev.location}\nText: {ev.text}", language="text")

            with tab_areas:
                st.subheader("📊 Performance by OOA Review Area")
                area_summary = aggregate_area_breakdown(result.parameter_findings)
                st.dataframe(pd.DataFrame(area_summary), use_container_width=True)
    else:
        st.info("👆 Upload an individual course TLEP file above to begin.")

# =========================================================================
# MODE 2: INSTITUTIONAL PORTFOLIO (2000+ COURSES)
# =========================================================================
else:
    st.markdown('<div class="main-title">🏢 Institutional TLEP Portfolio (2000+ Courses)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Hierarchical compliance monitoring across Schools, Departments, Programmes, and Semesters.</div>', unsafe_allow_html=True)

    # Tabs: Upload Batch vs Portfolio Dashboard
    p_tab1, p_tab2 = st.tabs(["📊 Portfolio Analytics & Drill-Down", "📥 Batch Upload / Process Folder"])

    with p_tab2:
        st.subheader("Bulk Ingest Course TLEPs")
        
        ingest_method = st.radio(
            "Select Batch Ingestion Source:",
            ["☁️ Google Drive Folder Link", "📁 Upload Multiple Files / ZIP"],
            horizontal=True
        )

        if ingest_method == "☁️ Google Drive Folder Link":
            st.markdown("#### Google Drive TLEP Review")
            st.caption("Provide a shared Google Drive folder link containing course TLEP files or department subfolders.")
            
            gdrive_url = st.text_input(
                "Google Drive Folder Link:",
                placeholder="https://drive.google.com/drive/folders/1A2B3C4D5E6F..."
            )
            
            col_gd1, col_gd2, col_gd3 = st.columns(3)
            with col_gd1:
                inc_subfolders = st.checkbox("Include subfolders (Dept/Prog)", value=True)
            with col_gd2:
                review_all = st.checkbox("Review all supported files", value=True)
            with col_gd3:
                gen_consolidated = st.checkbox("Generate consolidated report", value=True)
                
            with st.expander("🔐 Google Drive Authentication (Optional for Public Folders)"):
                gdrive_api_key = st.text_input("Google Drive API Key", type="password")
                sa_file = st.file_uploader("Or Upload Service Account JSON", type=["json"])
                
            if st.button("🚀 START GOOGLE DRIVE REVIEW", type="primary"):
                if not gdrive_url:
                    st.error("Please enter a valid Google Drive folder link.")
                else:
                    from integrations.google_drive import extract_folder_id_from_url, GoogleDriveConnector
                    folder_id = extract_folder_id_from_url(gdrive_url)
                    
                    if not folder_id:
                        st.error("Invalid Google Drive folder link format. Please provide a standard folder URL.")
                    else:
                        sa_path = None
                        if sa_file:
                            sa_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
                            sa_tmp.write(sa_file.getbuffer())
                            sa_path = sa_tmp.name
                            
                        try:
                            connector = GoogleDriveConnector(
                                service_account_json_path=sa_path,
                                api_key=gdrive_api_key or os.environ.get("GOOGLE_DRIVE_API_KEY")
                            )
                            
                            status_box = st.empty()
                            p_bar = st.progress(0.0)
                            
                            status_box.info(f"Connecting to Google Drive folder `{folder_id}`...")
                            temp_sync_dir = tempfile.mkdtemp()
                            
                            def on_gd_progress(cur, tot, fname):
                                p_bar.progress(cur / tot)
                                status_box.text(f"Syncing from Drive ({cur}/{tot}): {fname}")
                                
                            downloaded_files = connector.sync_and_download_folder(
                                folder_id=folder_id,
                                target_dir=temp_sync_dir,
                                include_subfolders=inc_subfolders,
                                progress_callback=on_gd_progress
                            )
                            
                            if not downloaded_files:
                                st.warning("No supported TLEP documents (.xlsx, .docx, .pdf) found in this Drive folder.")
                            else:
                                status_box.info(f"Auditing {len(downloaded_files)} courses from Google Drive...")
                                def on_audit_progress(cur, tot, fname):
                                    p_bar.progress(cur / tot)
                                    status_box.text(f"Auditing course ({cur}/{tot}): {fname}")
                                    
                                results = process_batch_files(downloaded_files, progress_callback=on_audit_progress, api_key=api_key_input)
                                p_bar.progress(1.0)
                                status_box.success(f"🎉 Successfully audited all {len(results)} courses from Google Drive! View them in the Analytics tab.")
                                
                        except PermissionError as pe:
                            st.error(f"Access Denied: {str(pe)}")
                        except Exception as ex:
                            st.error(f"Error accessing Google Drive: {str(ex)}")
                        finally:
                            if sa_path and os.path.exists(sa_path):
                                os.remove(sa_path)

        else:
            st.markdown("#### Upload Multiple Files or ZIP Archive")
            st.caption("Upload files directly or provide a zip file structured by `Department / Programme / Semester / Course.xlsx`.")
            batch_upload = st.file_uploader(
                "Upload Batch (Multiple Files or ZIP)",
                type=["zip", "xlsx", "docx", "pdf"],
                accept_multiple_files=True
            )
            
            if batch_upload:
                if st.button("🚀 PROCESS BATCH NOW", type="primary"):
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    temp_dir = tempfile.mkdtemp()
                    all_paths = []
                    
                    for f in batch_upload:
                        dest = os.path.join(temp_dir, f.name)
                        with open(dest, "wb") as buffer:
                            buffer.write(f.getbuffer())
                        all_paths.append(dest)
                        
                    def on_progress(cur, tot, fname):
                        progress_bar.progress(cur / tot)
                        status_text.text(f"Processing ({cur}/{tot}): {fname}")
                        
                    if len(all_paths) == 1 and all_paths[0].endswith(".zip"):
                        results = extract_and_process_zip(all_paths[0], progress_callback=on_progress, api_key=api_key_input)
                    else:
                        results = process_batch_files(all_paths, progress_callback=on_progress, api_key=api_key_input)
                        
                    status_text.success(f"✅ Processed {len(results)} courses successfully! Check the Analytics tab.")

    with p_tab1:
        audits = get_all_audits()
        if not audits:
            st.info("No courses have been processed yet. Upload a batch or single TLEP to view institutional metrics.")
        else:
            df_audits = pd.DataFrame(audits)
            
            # Institutional High-Level KPIs
            tot_courses = len(df_audits)
            avg_comp = round(df_audits["compliance_pct"].mean(), 1)
            ready_count = (df_audits["overall_status"] == "Compliant").sum()
            minor_count = (df_audits["overall_status"] == "Needs Revision").sum()
            rework_count = (df_audits["overall_status"].isin(["Major Revision", "Non-Compliant"])).sum()
            
            kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
            with kpi_c1:
                st.metric("Total Courses", tot_courses)
            with kpi_c2:
                st.metric("Avg Compliance", f"{avg_comp}%")
            with kpi_c3:
                st.metric("Ready for BoS", ready_count)
            with kpi_c4:
                st.metric("Minor Edits Needed", minor_count)
            with kpi_c5:
                st.metric("Action Required", rework_count)
                
            # Download Master Consolidated Excel Report
            consolidated_bytes = generate_consolidated_report(audits)
            st.download_button(
                label="📥 Download Master Institutional Audit Rollup (.xlsx)",
                data=consolidated_bytes,
                file_name="OOA_Institutional_TLEP_Rollup_AY_2026_27.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.divider()

            # Filters: Department -> Programme -> Semester
            st.markdown("### 🔍 Institutional Filter & Drill-Down")
            f_col1, f_col2, f_col3 = st.columns(3)
            
            dept_list = ["All Departments"] + sorted(list(df_audits["department"].dropna().unique()))
            with f_col1:
                sel_dept = st.selectbox("Filter by Department:", dept_list)
                
            filtered_df = df_audits if sel_dept == "All Departments" else df_audits[df_audits["department"] == sel_dept]
            
            prog_list = ["All Programmes"] + sorted(list(filtered_df["programme"].dropna().unique()))
            with f_col2:
                sel_prog = st.selectbox("Filter by Programme:", prog_list)
                
            if sel_prog != "All Programmes":
                filtered_df = filtered_df[filtered_df["programme"] == sel_prog]
                
            sem_list = ["All Semesters"] + sorted(list(filtered_df["semester"].dropna().unique()))
            with f_col3:
                sel_sem = st.selectbox("Filter by Semester:", sem_list)
                
            if sel_sem != "All Semesters":
                filtered_df = filtered_df[filtered_df["semester"] == sel_sem]

            # Department Summary Leaderboard
            st.markdown("#### 🏆 Department Performance Leaderboard")
            dept_summary = get_audit_summary_by_department()
            if dept_summary:
                st.dataframe(pd.DataFrame(dept_summary), use_container_width=True)

            # Course-by-Course Table
            st.markdown(f"#### 📚 Course Compliance Records ({len(filtered_df)} Courses)")
            view_cols = ["course_code", "course_title", "department", "programme", "semester", "compliance_pct", "overall_status", "major_revision_count", "needs_revision_count"]
            st.dataframe(
                filtered_df[view_cols].rename(columns={
                    "course_code": "Code",
                    "course_title": "Course Title",
                    "department": "Department",
                    "programme": "Programme",
                    "semester": "Semester",
                    "compliance_pct": "Compliance %",
                    "overall_status": "Status",
                    "major_revision_count": "Blockers",
                    "needs_revision_count": "Minor Fixes"
                }),
                use_container_width=True
            )
