"""
OOA TLEP Compliance Review System — AY 2026–27
Institutional Scale Edition — Single Course Review & 2000+ Course Portfolio Manager
Enterprise Executive UI
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

# Page Configuration
st.set_page_config(
    page_title="OOA TLEP Compliance Portal — AY 2026–27",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise Academic Design System
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

<style>
    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #F8FAFC;
    }
    
    /* Top Navigation Banner */
    .top-nav {
        background: linear-gradient(135deg, #0F294A 0%, #1A365D 50%, #2A4365 100%);
        border-radius: 12px;
        padding: 22px 28px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 4px 20px rgba(15, 41, 74, 0.12);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .top-nav-title {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .top-nav-subtitle {
        font-size: 0.95rem;
        color: #CBD5E1;
        margin-top: 4px;
        font-weight: 500;
    }
    .top-nav-badge {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(8px);
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #F8FAFC;
    }

    /* Executive Verdict Banners */
    .verdict-card {
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 22px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
        border: 1px solid transparent;
        display: flex;
        align-items: flex-start;
        gap: 16px;
    }
    .verdict-green {
        background: #F0FDF4;
        border-color: #BBF7D0;
        border-left: 6px solid #16A34A;
    }
    .verdict-yellow {
        background: #FEFCE8;
        border-color: #FEF08A;
        border-left: 6px solid #CA8A04;
    }
    .verdict-red {
        background: #FEF2F2;
        border-color: #FECACA;
        border-left: 6px solid #DC2626;
    }
    
    .verdict-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0 0 4px 0;
    }
    .verdict-green .verdict-title { color: #15803D; }
    .verdict-yellow .verdict-title { color: #A16207; }
    .verdict-red .verdict-title { color: #B91C1C; }
    
    .verdict-desc {
        margin: 0;
        font-size: 0.98rem;
        color: #334155;
        line-height: 1.5;
    }

    /* Stat KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
        margin-bottom: 22px;
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.05);
    }
    .kpi-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* Action Item Cards (Tab 1) */
    .action-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        border-left: 5px solid #0284C7;
    }
    .action-card-high {
        border-left-color: #DC2626;
        background: #FFFBFB;
    }
    .action-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .action-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
    }
    .badge-urgent {
        background: #FEE2E2;
        color: #991B1B;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .badge-minor {
        background: #FEF3C7;
        color: #92400E;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    
    /* Clean Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Tabs Navigation Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 0.92rem;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EFF6FF !important;
        color: #1D4ED8 !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 12px 0 16px 0;">
        <div style="font-size: 2.2rem; margin-bottom: 4px;">🏛️</div>
        <div style="font-weight: 800; font-size: 1.15rem; color: #0F294A; letter-spacing: -0.01em;">OFFICE OF ACADEMICS</div>
        <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; letter-spacing: 0.05em; text-transform: uppercase;">Quality Assurance Division</div>
    </div>
    """, unsafe_allow_html=True)
    
    mode = st.radio(
        "Navigation Mode:",
        ["📄 Single Course Review", "🏢 Institutional Portfolio (2000+)"],
        index=0
    )
    
    st.divider()
    st.markdown("**Academic Year:** `AY 2026–27`")
    st.markdown("**Standards:** `49 Official Criteria`")
    st.markdown("**Audit Engine:** `Deterministic + AI Hybrid`")
    
    with st.expander("⚙️ Advanced AI Settings"):
        api_key_input = st.text_input(
            "API Key (Optional)",
            type="password",
            help="Optional: If blank, system executes using high-speed deterministic rules and academic heuristic algorithms."
        )
    
    st.divider()
    st.caption("🔒 Verified OOA Template Baseline • Zero Fabricated Data")

# Top Navigation Header Banner
st.markdown("""
<div class="top-nav">
    <div>
        <div class="top-nav-title">
            <span>🏛️</span> OOA Academic Compliance Portal
        </div>
        <div class="top-nav-subtitle">
            Teaching-Learning and Evaluation Plan (TLEP) Quality Assurance Engine • AY 2026–27
        </div>
    </div>
    <div class="top-nav-badge">
        Official OOA Standard
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================================
# MODE 1: SINGLE COURSE TLEP REVIEW
# =========================================================================
if mode == "📄 Single Course Review":
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="font-size: 1.35rem; font-weight: 700; color: #0F172A; margin: 0;">Single Course Compliance Audit</h3>
        <p style="color: #64748B; margin: 2px 0 0 0; font-size: 0.95rem;">Upload a department-submitted course TLEP file to conduct an evidence-based audit against all 49 parameters.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Course TLEP Document (XLSX, DOCX, or PDF)",
        type=["xlsx", "xls", "docx", "pdf"],
        help="Upload the official department Course TLEP."
    )

    if uploaded_file is not None:
        col_btn, _ = st.columns([1.5, 4])
        with col_btn:
            check_clicked = st.button("🚀 EXECUTE COMPLIANCE AUDIT", use_container_width=True, type="primary")
            
        if check_clicked or "last_result" in st.session_state:
            if check_clicked:
                with st.spinner("Analyzing document structure, executing 49-parameter checks, and verifying hours..."):
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

            # Executive Decision Banner
            major_issues_count = result.major_revision_count + result.non_compliant_count
            needs_revision_count = result.needs_revision_count
            
            if major_issues_count == 0 and needs_revision_count == 0:
                st.markdown(f"""
                <div class="verdict-card verdict-green">
                    <div style="font-size: 1.8rem;">🟢</div>
                    <div>
                        <div class="verdict-title">APPROVED FOR BOARD OF STUDIES (Score: {result.compliance_percentage}%)</div>
                        <div class="verdict-desc">
                            All 49 academic quality parameters meet prescribed compliance standards. Course syllabus, hours, outcomes, and assessment schemes are mathematically and pedagogically aligned.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif major_issues_count == 0:
                st.markdown(f"""
                <div class="verdict-card verdict-yellow">
                    <div style="font-size: 1.8rem;">🟡</div>
                    <div>
                        <div class="verdict-title">CONDITIONAL APPROVAL — MINOR EDITS REQUIRED (Score: {result.compliance_percentage}%)</div>
                        <div class="verdict-desc">
                            The academic framework is sound, but requires <strong>{needs_revision_count} minor correction(s)</strong> (e.g., academic year tagging, reading citations, or BTL clarifications) prior to final sign-off.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="verdict-card verdict-red">
                    <div style="font-size: 1.8rem;">🔴</div>
                    <div>
                        <div class="verdict-title">REWORK REQUIRED — MAJOR DEFICIENCIES DETECTED (Score: {result.compliance_percentage}%)</div>
                        <div class="verdict-desc">
                            Audit identified <strong>{major_issues_count} structural blocker(s)</strong> (such as unassessed outcomes, module hour mismatches, or missing session alignment) that must be resolved by the department before submission.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Executive KPI Cards
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-label">Compliance Score</div>
                    <div class="kpi-value" style="color: {'#15803D' if result.compliance_percentage >= 85 else ('#B45309' if result.compliance_percentage >= 70 else '#B91C1C')};">
                        {result.compliance_percentage}%
                    </div>
                    <div class="kpi-sub">{result.score_obtained} / {result.maximum_score} Points</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Compliant Parameters</div>
                    <div class="kpi-value" style="color: #15803D;">{result.compliant_count}</div>
                    <div class="kpi-sub">Of {result.applicable_parameters} Applicable</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Minor Fixes</div>
                    <div class="kpi-value" style="color: #B45309;">{result.needs_revision_count}</div>
                    <div class="kpi-sub">1 Point Each</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Major Blockers</div>
                    <div class="kpi-value" style="color: #B91C1C;">{major_issues_count}</div>
                    <div class="kpi-sub">0 Points Each</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">NA Parameters</div>
                    <div class="kpi-value" style="color: #64748B;">{result.na_count}</div>
                    <div class="kpi-sub">Excluded from Score</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Export Button
            report_bytes = generate_excel_report(result)
            st.download_button(
                label="📥 Download Official 6-Sheet Audit Report (.xlsx)",
                data=report_bytes,
                file_name=f"OOA_TLEP_Audit_{result.file_name}_{result.review_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

            st.write("")

            # Progressive Tabs
            tab_plain, tab_hours, tab_outcomes, tab_full_audit, tab_areas = st.tabs([
                "⚡ Faculty Action Checklist",
                "⏱️ Learning Hours & Credits",
                "🎯 Outcome & Assessment Alignment",
                "📋 Official 49-Parameter Audit",
                "📊 Area Breakdown"
            ])

            actionable_findings = [f for f in result.parameter_findings if f.status in [StatusEnum.NEEDS_REVISION, StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT]]

            # TAB 1: Faculty Action Checklist
            with tab_plain:
                st.markdown("#### ⚡ Priority Department Action Items")
                st.caption("Consolidated actionable list for the course facilitator and department head.")
                
                simplified_items = [simplify_finding(f) for f in actionable_findings]
                if not simplified_items:
                    st.success("🎉 Complete Compliance: No corrective actions are required for this course.")
                else:
                    high_fixes = [item for item in simplified_items if item["priority"] == "High" or item["status"] in ["Major Revision", "Non-Compliant"]]
                    other_fixes = [item for item in simplified_items if item not in high_fixes]
                    
                    if high_fixes:
                        st.markdown("##### 🚨 Critical Blockers (Must Fix for BoS Sign-Off)")
                        for fix in high_fixes:
                            st.markdown(f"""
                            <div class="action-card action-card-high">
                                <div class="action-card-header">
                                    <span class="action-card-title">{fix['friendly_name']} (Parameter #{fix['parameter_id']})</span>
                                    <span class="badge-urgent">Critical Blocker</span>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 8px;">
                                    <div>
                                        <div style="font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Observation / Deficiency</div>
                                        <div style="font-size: 0.95rem; color: #334155; margin-top: 2px;">{fix['what_is_wrong']}</div>
                                        <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">📍 Location: <code>{fix['where']}</code></div>
                                    </div>
                                    <div style="background: #F8FAFC; border-radius: 8px; padding: 10px 14px; border: 1px dashed #CBD5E1;">
                                        <div style="font-size: 0.8rem; font-weight: 700; color: #0284C7; text-transform: uppercase;">Required Action</div>
                                        <div style="font-size: 0.95rem; font-weight: 600; color: #0F172A; margin-top: 2px;">👉 {fix['what_to_do']}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                    if other_fixes:
                        st.markdown("##### ✏️ Recommended Adjustments (Quality Refinements)")
                        for fix in other_fixes:
                            st.markdown(f"""
                            <div class="action-card">
                                <div class="action-card-header">
                                    <span class="action-card-title">{fix['friendly_name']} (Parameter #{fix['parameter_id']})</span>
                                    <span class="badge-minor">Minor Adjustment</span>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 8px;">
                                    <div>
                                        <div style="font-size: 0.8rem; font-weight: 700; color: #64748B; text-transform: uppercase;">Observation / Deficiency</div>
                                        <div style="font-size: 0.95rem; color: #334155; margin-top: 2px;">{fix['what_is_wrong']}</div>
                                        <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">📍 Location: <code>{fix['where']}</code></div>
                                    </div>
                                    <div style="background: #F8FAFC; border-radius: 8px; padding: 10px 14px; border: 1px dashed #CBD5E1;">
                                        <div style="font-size: 0.8rem; font-weight: 700; color: #0284C7; text-transform: uppercase;">Required Action</div>
                                        <div style="font-size: 0.95rem; font-weight: 600; color: #0F172A; margin-top: 2px;">👉 {fix['what_to_do']}</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

            # TAB 2: Hours & Credits
            with tab_hours:
                st.markdown("#### ⏱️ Credit & Contact Hours Validation (Sheet 5)")
                st.caption("Reconciles approved curriculum credits, L-T-P-E distribution, session contact hours, and notional learning hours.")
                hours_display = []
                for hr in result.hours_validation_rows:
                    status_icon = "✅" if hr.status == StatusEnum.COMPLIANT else ("⚠️" if hr.status == StatusEnum.NEEDS_REVISION else "❌")
                    hours_display.append({
                        "Parameter": hr.parameter,
                        "Approved Curriculum": hr.approved if hr.approved is not None else "-",
                        "As per TLEP": hr.tlep if hr.tlep is not None else "-",
                        "Variance": hr.variance,
                        "Status": f"{status_icon} {hr.status.value}",
                        "Remarks": hr.remarks,
                        "Required Action": hr.action_required or "-"
                    })
                st.dataframe(pd.DataFrame(hours_display), use_container_width=True)

            # TAB 3: Outcomes vs Assessments
            with tab_outcomes:
                st.markdown("#### 🎯 Course Outcome Alignment Matrix")
                st.caption("Verifies that every Course Outcome (CO) is explicitly taught in class sessions and evaluated in assessments.")
                c_info = result.normalized_tlep
                if c_info and c_info.course_outcomes:
                    co_matrix = []
                    for co in c_info.course_outcomes:
                        taught_in = [s.session_number for s in c_info.sessions if co.id.upper() in [x.upper() for x in s.co_mapped]]
                        tested_in = [a.component_name for a in c_info.assessments if co.id.upper() in [x.upper() for x in a.co_mapped]]
                        co_matrix.append({
                            "CO ID": co.id,
                            "Course Outcome Statement": co.statement,
                            "Cognitive Level (BTL)": co.btl or "Not specified",
                            "Taught in Sessions": f"✅ {len(taught_in)} Sessions" if taught_in else "❌ 0 Sessions Mapped",
                            "Evaluated in Assessments": f"✅ {len(tested_in)} Assessments" if tested_in else "❌ Unassessed Outcome"
                        })
                    st.dataframe(pd.DataFrame(co_matrix), use_container_width=True)
                else:
                    st.info("No Course Outcomes detected in the document to analyze.")

            # TAB 4: Official 49-Parameter Audit
            with tab_full_audit:
                st.markdown("#### 📋 Complete 49-Parameter Quality Assurance Audit")
                st.caption("Official review criteria, traceable evidence locations, scoring, and confidence.")
                
                filter_choice = st.radio(
                    "Filter by Status:",
                    ["All 49", "Compliant (Pass)", "Needs Revision (Minor)", "Major Revision (Blocker)", "Non-Compliant", "NA"],
                    horizontal=True
                )
                
                filter_map = {
                    "Compliant (Pass)": StatusEnum.COMPLIANT,
                    "Needs Revision (Minor)": StatusEnum.NEEDS_REVISION,
                    "Major Revision (Blocker)": StatusEnum.MAJOR_REVISION,
                    "Non-Compliant": StatusEnum.NON_COMPLIANT,
                    "NA": StatusEnum.NA
                }
                
                display_findings = result.parameter_findings
                if filter_choice in filter_map:
                    display_findings = [f for f in display_findings if f.status == filter_map[filter_choice]]
                    
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

            # TAB 5: Area Breakdown
            with tab_areas:
                st.markdown("#### 📊 Area-Wise Compliance Breakdown (Areas A–I)")
                area_summary = aggregate_area_breakdown(result.parameter_findings)
                st.dataframe(pd.DataFrame(area_summary), use_container_width=True)
    else:
        st.info("👆 Upload an individual course TLEP file above to begin the official audit.")

# =========================================================================
# MODE 2: INSTITUTIONAL PORTFOLIO (2000+ COURSES)
# =========================================================================
else:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h3 style="font-size: 1.35rem; font-weight: 700; color: #0F172A; margin: 0;">Institutional TLEP Portfolio (2,000+ Courses)</h3>
        <p style="color: #64748B; margin: 2px 0 0 0; font-size: 0.95rem;">Hierarchical compliance monitoring across Schools, Departments, Programmes, and Semesters.</p>
    </div>
    """, unsafe_allow_html=True)

    p_tab1, p_tab2 = st.tabs(["📊 Portfolio Analytics & Leaderboard", "📥 Batch Ingestion (Google Drive & ZIP)"])

    # Batch Ingestion Tab
    with p_tab2:
        st.markdown("#### Ingest Course TLEPs at Scale")
        ingest_method = st.radio(
            "Select Source:",
            ["☁️ Google Drive Folder Link", "📁 Upload Multiple Files / ZIP"],
            horizontal=True
        )

        if ingest_method == "☁️ Google Drive Folder Link":
            st.markdown("##### Google Drive Integration")
            st.caption("Provide a shared Google Drive folder containing course files or nested department/programme folders.")
            
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
                gen_consolidated = st.checkbox("Generate department tabs", value=True)
                
            with st.expander("🔐 Drive Credentials (Optional for Public Folders)"):
                gdrive_api_key = st.text_input("Google Drive API Key", type="password")
                sa_file = st.file_uploader("Or Upload Service Account JSON", type=["json"])
                
            if st.button("🚀 INGEST & AUDIT GOOGLE DRIVE FOLDER", type="primary"):
                if not gdrive_url:
                    st.error("Please enter a valid Google Drive folder link.")
                else:
                    from integrations.google_drive import extract_folder_id_from_url, GoogleDriveConnector
                    folder_id = extract_folder_id_from_url(gdrive_url)
                    
                    if not folder_id:
                        st.error("Invalid Google Drive folder link format.")
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
                                status_box.text(f"Downloading from Drive ({cur}/{tot}): {fname}")
                                
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
                                status_box.success(f"🎉 Successfully audited all {len(results)} courses from Google Drive! Check Analytics tab.")
                                
                        except PermissionError as pe:
                            st.error(f"Access Denied: {str(pe)}")
                        except Exception as ex:
                            st.error(f"Error accessing Google Drive: {str(ex)}")
                        finally:
                            if sa_path and os.path.exists(sa_path):
                                os.remove(sa_path)

        else:
            st.markdown("##### Upload Multiple Files or ZIP Archive")
            st.caption("Upload files directly or provide a zip file structured by `School / Department / Programme / Semester / Course.xlsx`.")
            batch_upload = st.file_uploader(
                "Upload Batch (Multiple Files or ZIP)",
                type=["zip", "xlsx", "docx", "pdf"],
                accept_multiple_files=True
            )
            
            if batch_upload:
                if st.button("🚀 INGEST & AUDIT BATCH NOW", type="primary"):
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
                        
                    status_text.success(f"✅ Processed {len(results)} courses successfully! Check Analytics tab.")

    # Portfolio Analytics Tab
    with p_tab1:
        audits = get_all_audits()
        if not audits:
            st.info("ℹ️ No courses have been audited yet. Ingest a batch or Google Drive folder to view institutional performance.")
        else:
            df_audits = pd.DataFrame(audits)
            
            # High-Level KPIs
            tot_courses = len(df_audits)
            avg_comp = round(df_audits["compliance_pct"].mean(), 1)
            ready_count = (df_audits["overall_status"] == "Compliant").sum()
            minor_count = (df_audits["overall_status"] == "Needs Revision").sum()
            rework_count = (df_audits["overall_status"].isin(["Major Revision", "Non-Compliant"])).sum()
            
            st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-label">Total Courses Audited</div>
                    <div class="kpi-value">{tot_courses}</div>
                    <div class="kpi-sub">Across All Departments</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Average Compliance</div>
                    <div class="kpi-value" style="color: {'#15803D' if avg_comp >= 85 else ('#B45309' if avg_comp >= 70 else '#B91C1C')};">{avg_comp}%</div>
                    <div class="kpi-sub">Institutional Average</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Ready for BoS</div>
                    <div class="kpi-value" style="color: #15803D;">{ready_count}</div>
                    <div class="kpi-sub">Fully Compliant</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Minor Edits Needed</div>
                    <div class="kpi-value" style="color: #B45309;">{minor_count}</div>
                    <div class="kpi-sub">Conditional Revision</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Rework Required</div>
                    <div class="kpi-value" style="color: #B91C1C;">{rework_count}</div>
                    <div class="kpi-sub">Action Blockers</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Master Download Button
            consolidated_bytes = generate_consolidated_report(audits)
            st.download_button(
                label="📥 Download Master Institutional Audit Rollup (All Departments .xlsx)",
                data=consolidated_bytes,
                file_name="OOA_Institutional_TLEP_Rollup_AY_2026_27.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.divider()

            # Filters: School -> Department -> Programme -> Semester
            st.markdown("#### 🔍 Institutional Drill-Down")
            f_col0, f_col1, f_col2, f_col3 = st.columns(4)
            
            school_col = "school" if "school" in df_audits.columns else None
            school_list = ["All Schools"] + sorted(list(df_audits["school"].dropna().unique())) if school_col else ["All Schools"]
            with f_col0:
                sel_school = st.selectbox("School / Faculty:", school_list)
                
            filtered_df = df_audits
            if school_col and sel_school != "All Schools":
                filtered_df = filtered_df[filtered_df["school"] == sel_school]
            
            dept_list = ["All Departments"] + sorted(list(filtered_df["department"].dropna().unique()))
            with f_col1:
                sel_dept = st.selectbox("Department:", dept_list)
                
            if sel_dept != "All Departments":
                filtered_df = filtered_df[filtered_df["department"] == sel_dept]
            
            prog_list = ["All Programmes"] + sorted(list(filtered_df["programme"].dropna().unique()))
            with f_col2:
                sel_prog = st.selectbox("Programme:", prog_list)
                
            if sel_prog != "All Programmes":
                filtered_df = filtered_df[filtered_df["programme"] == sel_prog]
                
            sem_list = ["All Semesters"] + sorted(list(filtered_df["semester"].dropna().unique()))
            with f_col3:
                sel_sem = st.selectbox("Semester:", sem_list)
                
            if sel_sem != "All Semesters":
                filtered_df = filtered_df[filtered_df["semester"] == sel_sem]

            # Department Leaderboard
            st.markdown("#### 🏆 Department Performance Leaderboard")
            dept_summary = get_audit_summary_by_department()
            if dept_summary:
                st.dataframe(pd.DataFrame(dept_summary), use_container_width=True)

            # Course Records Table
            st.markdown(f"#### 📚 Course Compliance Records ({len(filtered_df)} Courses)")
            view_cols = ["course_code", "course_title", "school", "department", "programme", "semester", "compliance_pct", "overall_status", "major_revision_count", "needs_revision_count"]
            available_cols = [c for c in view_cols if c in filtered_df.columns]
            st.dataframe(
                filtered_df[available_cols].rename(columns={
                    "course_code": "Code",
                    "course_title": "Course Title",
                    "school": "School / Faculty",
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

            # Isolated Department Download Button
            if sel_dept != "All Departments":
                dept_records = filtered_df.to_dict('records')
                dept_bytes = generate_consolidated_report(dept_records)
                st.download_button(
                    label=f"📥 Download {sel_dept} Report Only (.xlsx)",
                    data=dept_bytes,
                    file_name=f"OOA_Audit_{sel_dept.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary"
                )
