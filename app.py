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
from reports.excel_report import generate_excel_report, generate_consolidated_report, generate_multiple_reports_zip
from engine.scoring import aggregate_area_breakdown
from engine.simplifier import simplify_finding
from engine.batch_processor import process_batch_files, extract_and_process_zip
from engine.db import get_all_audits, get_audit_summary_by_department
from engine.index_scraper import audit_index_inventory, generate_index_reconciliation_excel, audit_directory_or_batch, is_index_file
from integrations.google_drive import GoogleDriveConnector, extract_folder_id_from_url, parse_drive_url_type
from models.schemas import StatusEnum

# Page Configuration
st.set_page_config(
    page_title="OOA TLEP Compliance Portal — AY 2026–27",
    page_icon=None,
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

# Authentication Security Lock
APP_PASSWORD = os.environ.get("PORTAL_PASSWORD", "null")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # Suppress sidebar display while portal is locked
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    _, col_auth, _ = st.columns([1, 1.2, 1])
    with col_auth:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; padding: 36px 32px 24px 32px; box-shadow: 0 10px 25px rgba(15, 41, 74, 0.08); margin-top: 50px;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-size: 0.8rem; font-weight: 800; letter-spacing: 0.12em; color: #1E3A8A; text-transform: uppercase;">Office of Academics</div>
                <div style="font-size: 1.45rem; font-weight: 800; color: #0F294A; margin-top: 4px; letter-spacing: -0.02em;">TLEP Compliance Portal</div>
                <div style="font-size: 0.85rem; color: #64748B; margin-top: 4px;">AY 2026–27 • Quality Assurance Division</div>
                <div style="margin-top: 14px; display: inline-block; background: #EFF6FF; color: #1D4ED8; font-size: 0.75rem; font-weight: 700; padding: 4px 12px; border-radius: 12px; border: 1px solid #DBEAFE;">PORTAL ACCESS LOCKED</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("auth_form", clear_on_submit=False):
            entered_pwd = st.text_input("Security Access Password", type="password", placeholder="Enter portal password")
            submitted = st.form_submit_button("UNLOCK SYSTEM", use_container_width=True, type="primary")

            if submitted:
                if entered_pwd == APP_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Authentication failed. Invalid password.")

    st.stop()

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 12px 0 16px 0;">
        <div style="font-size: 0.95rem; font-weight: 800; letter-spacing: 0.1em; color: #1E3A8A; margin-bottom: 6px;">OOA QUALITY ASSURANCE</div>
        <div style="font-weight: 800; font-size: 1.15rem; color: #0F294A; letter-spacing: -0.01em;">OFFICE OF ACADEMICS</div>
        <div style="font-size: 0.78rem; font-weight: 600; color: #64748B; letter-spacing: 0.05em; text-transform: uppercase;">Quality Assurance Division</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown("**Academic Year:** `AY 2026–27`")
    st.markdown("**Standards:** `49 Official Criteria`")
    st.markdown("**Audit Engine:** `Deterministic Rule Engine`")
    st.divider()
    st.caption("Verified OOA Template Baseline • Zero Fabricated Data")
    api_key_input = None
    if st.button("LOCK PORTAL", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# Top Navigation Header Banner
st.markdown("""
<div class="top-nav">
    <div>
        <div class="top-nav-title">
            OOA Academic Compliance Portal
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

mode = st.radio(
    "Select Operating Mode:",
    ["Single Course Review", "Institutional Portfolio (2,000+ Courses)"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("<br>", unsafe_allow_html=True)

# =========================================================================
# MODE 1: SINGLE COURSE TLEP REVIEW
# =========================================================================
if mode == "Single Course Review":
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
        if "uploaded_file_name" in st.session_state and st.session_state["uploaded_file_name"] != uploaded_file.name:
            if "last_result" in st.session_state:
                del st.session_state["last_result"]
            st.session_state["uploaded_file_name"] = uploaded_file.name

        col_btn, _ = st.columns([1.5, 4])
        with col_btn:
            check_clicked = st.button("EXECUTE COMPLIANCE AUDIT", use_container_width=True, type="primary")
            
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
                    <div style="font-size: 0.75rem; font-weight: 800; padding: 4px 8px; border-radius: 4px; background: #15803D; color: #FFFFFF; letter-spacing: 0.05em; text-align: center;">PASS</div>
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
                    <div style="font-size: 0.75rem; font-weight: 800; padding: 4px 8px; border-radius: 4px; background: #B45309; color: #FFFFFF; letter-spacing: 0.05em; text-align: center;">REVISION</div>
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
                    <div style="font-size: 0.75rem; font-weight: 800; padding: 4px 8px; border-radius: 4px; background: #B91C1C; color: #FFFFFF; letter-spacing: 0.05em; text-align: center;">REWORK</div>
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

            # UI Chart and Export Buttons
            # UI Charts and Export Buttons
            c_chart1, c_chart2, c_export = st.columns([1, 1.5, 0.8])
            
            with c_chart1:
                status_counts = pd.Series([f.status.value for f in result.parameter_findings]).value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                import plotly.express as px
                color_discrete_map = {
                    "Compliant": "#16A34A", 
                    "Needs Revision": "#CA8A04", 
                    "Major Revision": "#DC2626", 
                    "Non-Compliant": "#991B1B",
                    "NA": "#64748B"
                }
                fig1 = px.pie(
                    status_counts, 
                    values="Count", 
                    names="Status", 
                    hole=0.45,
                    color="Status",
                    color_discrete_map=color_discrete_map,
                    title="<b>Parameter Compliance Status</b>"
                )
                fig1.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
                fig1.update_layout(margin=dict(t=40, b=10, l=0, r=0), height=300, showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)

            with c_chart2:
                area_summary = aggregate_area_breakdown(result.parameter_findings)
                df_areas = pd.DataFrame(area_summary)
                # Keep Area names short for the chart axis
                df_areas['Short Area'] = df_areas['review_area'].apply(lambda x: x.split("–")[0].strip() if "–" in x else (x.split("-")[0].strip() if "-" in x else x))
                
                fig2 = px.bar(
                    df_areas, 
                    x="compliance_pct", 
                    y="Short Area", 
                    orientation='h',
                    title="<b>Area-Wise Compliance (%)</b>",
                    text="compliance_pct",
                    color="compliance_pct",
                    color_continuous_scale=["#DC2626", "#CA8A04", "#16A34A"],
                    range_color=[0, 100]
                )
                fig2.update_traces(texttemplate='%{text}%', textposition='outside')
                fig2.update_layout(
                    margin=dict(t=40, b=10, l=0, r=20), 
                    height=300, 
                    xaxis_title=None, 
                    yaxis_title=None, 
                    showlegend=False,
                    coloraxis_showscale=False,
                    xaxis=dict(range=[0, 115], showgrid=False, zeroline=False, showticklabels=False),
                    yaxis={'categoryorder':'total ascending'}
                )
                st.plotly_chart(fig2, use_container_width=True)

            with c_export:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if getattr(result, "executive_summary_docx", None):
                    report_bytes = result.executive_summary_docx
                    st.download_button(
                        label="Download Executive Narrative Report (.docx)",
                        data=report_bytes,
                        file_name=f"Executive_Narrative_{result.file_name}_{result.review_id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    report_bytes = generate_excel_report(result)
                    st.download_button(
                        label="Download Official Audit Report (.xlsx)",
                        data=report_bytes,
                        file_name=f"OOA_TLEP_Audit_{result.file_name}_{result.review_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
            
            st.write("")

            # Progressive Tabs
            tab_exec, tab_audit_actions, tab_hours, tab_outcomes, tab_areas = st.tabs([
                "Executive Narrative",
                "Audit & Action Checklist",
                "Learning Hours & Credits",
                "Outcome & Assessment Alignment",
                "Area Breakdown"
            ])

            # TAB 0: Executive Narrative
            with tab_exec:
                if getattr(result, "executive_summary", None):
                    st.markdown(result.executive_summary)
                else:
                    st.info("Executive narrative summary is not available.")

            actionable_findings = [f for f in result.parameter_findings if f.status in [StatusEnum.NEEDS_REVISION, StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT]]

            # MERGED TAB: Audit & Actions
            with tab_audit_actions:
                st.markdown("#### Comprehensive Quality Audit & Action Plan")
                view_mode = st.radio("View Mode:", ["🚨 Faculty Action Checklist (Actionable Items)", "📋 Official 49-Parameter Log (All Items)"], horizontal=True, label_visibility="collapsed")
                st.write("")
                if "Faculty Action" in view_mode:
                    st.markdown("##### Priority Department Action Items")
                    st.caption("Consolidated actionable list for the course facilitator and department head.")
                
                    simplified_items = [simplify_finding(f) for f in actionable_findings]
                    if not simplified_items:
                        st.success("Complete Compliance: No corrective actions are required for this course.")
                    else:
                        high_fixes = [item for item in simplified_items if item["priority"] == "High" or item["status"] in ["Major Revision", "Non-Compliant"]]
                        other_fixes = [item for item in simplified_items if item not in high_fixes]
                    
                        if high_fixes:
                            st.markdown("##### Critical Blockers (Must Fix for BoS Sign-Off)")
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
                                            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">Location: <code>{fix['where']}</code></div>
                                        </div>
                                        <div style="background: #F8FAFC; border-radius: 8px; padding: 10px 14px; border: 1px dashed #CBD5E1;">
                                            <div style="font-size: 0.8rem; font-weight: 700; color: #0284C7; text-transform: uppercase;">Required Action</div>
                                            <div style="font-size: 0.95rem; font-weight: 600; color: #0F172A; margin-top: 2px;">{fix['what_to_do']}</div>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                        if other_fixes:
                            st.markdown("##### Recommended Adjustments (Quality Refinements)")
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
                                            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">Location: <code>{fix['where']}</code></div>
                                        </div>
                                        <div style="background: #F8FAFC; border-radius: 8px; padding: 10px 14px; border: 1px dashed #CBD5E1;">
                                            <div style="font-size: 0.8rem; font-weight: 700; color: #0284C7; text-transform: uppercase;">Required Action</div>
                                            <div style="font-size: 0.95rem; font-weight: 600; color: #0F172A; margin-top: 2px;">{fix['what_to_do']}</div>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                else:
                    st.markdown("##### Complete 49-Parameter Quality Assurance Audit")
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

            # TAB 2: Hours & Credits
            with tab_hours:
                st.markdown("#### Credit & Contact Hours Validation (Sheet 5)")
                st.caption("Reconciles approved curriculum credits, L-T-P-E distribution, session contact hours, and notional learning hours.")
                hours_display = []
                for hr in result.hours_validation_rows:
                    # Status values
                    hours_display.append({
                        "Parameter": str(hr.parameter),
                        "Approved Curriculum": str(hr.approved) if hr.approved is not None else "-",
                        "As per TLEP": str(hr.tlep) if hr.tlep is not None else "-",
                        "Variance": str(hr.variance) if hr.variance is not None else "-",
                        "Status": hr.status.value,
                        "Remarks": str(hr.remarks) if hr.remarks else "",
                        "Required Action": str(hr.action_required) if hr.action_required else "-"
                    })
                st.dataframe(pd.DataFrame(hours_display), use_container_width=True)

            # TAB 3: Outcomes vs Assessments
            with tab_outcomes:
                st.markdown("#### Course Outcome Alignment Matrix")
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
                            "Taught in Sessions": f"{len(taught_in)} Sessions" if taught_in else "0 Sessions Mapped",
                            "Evaluated in Assessments": f"{len(tested_in)} Assessments" if tested_in else "Unassessed Outcome"
                        })
                    st.dataframe(pd.DataFrame(co_matrix), use_container_width=True)
                else:
                    st.info("No Course Outcomes detected in the document to analyze.")

            # TAB 5: Area Breakdown
            with tab_areas:
                st.markdown("#### Area-Wise Compliance Breakdown (Areas A–I)")
                area_summary = aggregate_area_breakdown(result.parameter_findings)
                st.dataframe(pd.DataFrame(area_summary), use_container_width=True)
    else:
        st.info("Upload an individual course TLEP file above to begin the official audit.")

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

    p_tab1, p_tab2 = st.tabs([
        "Portfolio Analytics & Leaderboard", 
        "Batch Ingestion & Master Index Reconciliation (Drive, ZIP, Indexes)"
    ])

    # Portfolio Analytics Tab
    with p_tab1:
        audits = get_all_audits()
        if not audits:
            st.info("No courses have been audited yet. Ingest a batch, index, or Google Drive folder to view institutional performance.")
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
                label="Download Master Institutional Audit Rollup (All Departments .xlsx)",
                data=consolidated_bytes,
                file_name="OOA_Institutional_TLEP_Rollup_AY_2026_27.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
            st.divider()

            # Filters: School -> Department -> Programme -> Semester
            st.markdown("#### Institutional Drill-Down")
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
            st.markdown("#### Department Performance Leaderboard")
            dept_summary = get_audit_summary_by_department()
            if dept_summary:
                st.dataframe(pd.DataFrame(dept_summary), use_container_width=True)

            # Course Records Table
            st.markdown(f"#### Course Compliance Records ({len(filtered_df)} Courses)")
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
                    label=f"Download {sel_dept} Report Only (.xlsx)",
                    data=dept_bytes,
                    file_name=f"OOA_Audit_{sel_dept.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary"
                )

    # TAB 2: Batch Ingestion & Master Index Reconciliation
    with p_tab2:
        st.markdown("""
        <div style="margin-bottom: 14px;">
            <h4 style="font-size: 1.25rem; font-weight: 700; color: #0F172A; margin: 0;">Institutional Intake & Master Index Reconciliation</h4>
            <p style="color: #64748B; margin: 3px 0 0 0; font-size: 0.93rem;">
                Ingest departmental course portfolios at scale. Provide a Google Drive folder link, Master Index spreadsheet (Google Sheet or Excel), 
                or upload a batch of course files or ZIP archive. The engine reconciles curriculum indexes, checks document availability, 
                downloads referenced files from Google Drive, and executes the official 49-parameter audit.
            </p>
        </div>
        """, unsafe_allow_html=True)

        ingest_method = st.radio(
            "Select Intake Source:",
            ["Google Drive (Folder or Master Index Sheet)", "Upload Files (Master Index, Course TLEPs, or ZIP Archive)"],
            horizontal=True
        )

        mode_options_map = {
            "Auto-Detect (Reconcile Indexes or Audit Direct Courses)": "auto",
            "Master Index Reconciliation (Scrape links & reconcile inventory)": "index",
            "Direct Course Documents (Audit standalone TLEPs)": "courses"
        }

        # Source 1: Google Drive Integration
        if ingest_method == "Google Drive (Folder or Master Index Sheet)":
            st.markdown("##### Google Drive Ingestion")
            st.caption("Provide a shared Google Drive folder containing course files or index sheets, OR a direct Google Sheet / Master Index link.")
            
            gdrive_url = st.text_input(
                "Google Drive Link (Folder, Google Sheet, or Document):",
                placeholder="https://drive.google.com/drive/folders/1A2B... or https://docs.google.com/spreadsheets/d/1X2Y..."
            )
            
            if "last_gdrive_url" not in st.session_state:
                st.session_state["last_gdrive_url"] = ""
                
            if gdrive_url != st.session_state["last_gdrive_url"]:
                st.session_state["last_gdrive_url"] = gdrive_url
                if "unified_batch_result" in st.session_state:
                    del st.session_state["unified_batch_result"]
            
            col_gd1, col_gd2 = st.columns([2, 1])
            with col_gd1:
                selected_mode_label = st.selectbox(
                    "Ingestion Strategy:",
                    list(mode_options_map.keys()),
                    index=0,
                    help="Auto-Detect will inspect downloaded files for curriculum indexes; if found, it scrapes embedded course links and reconciles inventory."
                )
            with col_gd2:
                inc_subfolders = st.checkbox("Include subfolders (Dept/Prog)", value=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("INGEST & RECONCILE FROM GOOGLE DRIVE", type="primary"):
                if not gdrive_url.strip():
                    st.error("Please enter a valid Google Drive link.")
                else:
                    try:
                        connector = GoogleDriveConnector()
                        
                        status_box = st.empty()
                        p_bar = st.progress(0.0)
                        
                        status_box.info("Connecting to Google Drive and fetching resources...")
                        temp_sync_dir = tempfile.mkdtemp(prefix="tlep_gdrive_sync_")
                        
                        def on_gd_progress(cur, tot, fname):
                            p_bar.progress(cur / tot)
                            status_box.text(f"Fetching from Drive ({cur}/{tot}): {fname}")
                            
                        res_type, downloaded_files = connector.fetch_drive_resource(
                            url_or_id=gdrive_url,
                            target_dir=temp_sync_dir,
                            include_subfolders=inc_subfolders,
                            progress_callback=on_gd_progress
                        )
                        
                        if not downloaded_files:
                            status_box.warning("No supported documents (.xlsx, .docx, .pdf) found in this Drive resource.")
                        else:
                            status_box.info(f"Auditing & reconciling {len(downloaded_files)} files from Google Drive...")
                            
                            def on_audit_prog(cur, tot, fname):
                                p_bar.progress(cur / tot)
                                status_box.text(f"Auditing ({cur}/{tot}): {fname}")
                                
                            unified_result = audit_directory_or_batch(api_key=api_key_input,
                                files_or_dir=downloaded_files,
                                base_dir=temp_sync_dir,
                                gdrive_connector=connector,
                                mode=mode_options_map[selected_mode_label],
                                progress_callback=on_audit_prog)
                            p_bar.progress(1.0)
                            st.session_state["unified_batch_result"] = unified_result
                            status_box.success("Google Drive ingestion and compliance reconciliation completed successfully.")
                            
                    except PermissionError as pe:
                        st.error(f"Access Denied: {str(pe)}")
                    except Exception as ex:
                        st.error(f"Error accessing Google Drive: {str(ex)}")

        # Source 2: Upload Multiple Files, Indexes, or ZIP
        else:
            st.markdown("##### Upload Files, Master Index, or ZIP Archive")
            st.caption("Upload a Master Index spreadsheet (.xlsx, .docx), individual course files, or a ZIP archive containing curriculum folders.")
            batch_upload = st.file_uploader(
                "Upload Batch (Master Index, Course TLEPs, or ZIP)",
                type=["zip", "xlsx", "xls", "docx", "pdf"],
                accept_multiple_files=True,
                key="batch_file_uploader"
            )
            
            # Clear batch cache if file uploader state changes
            if "last_batch_files" not in st.session_state:
                st.session_state["last_batch_files"] = []
                
            current_batch_names = [f.name for f in batch_upload] if batch_upload else []
            if current_batch_names != st.session_state["last_batch_files"]:
                st.session_state["last_batch_files"] = current_batch_names
                if "unified_batch_result" in st.session_state:
                    del st.session_state["unified_batch_result"]
            
            col_up1, col_up2 = st.columns([2, 1])
            with col_up1:
                selected_up_mode_label = st.selectbox(
                    "Ingestion Strategy:",
                    list(mode_options_map.keys()),
                    index=0,
                    help="Auto-Detect automatically checks uploaded files for index spreadsheets with course links."
                )
            with col_up2:
                st.markdown("<br>", unsafe_allow_html=True)

            if batch_upload:
                if st.button("INGEST & RECONCILE BATCH NOW", type="primary"):
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    import zipfile
                    temp_dir = tempfile.mkdtemp(prefix="tlep_batch_upload_")
                    all_paths = []
                    
                    for f in batch_upload:
                        dest = os.path.join(temp_dir, f.name)
                        with open(dest, "wb") as buffer:
                            buffer.write(f.getbuffer())
                        all_paths.append(dest)
                        
                    # If single zip file, extract it
                    if len(all_paths) == 1 and all_paths[0].endswith(".zip"):
                        status_text.info(f"Extracting ZIP archive: {os.path.basename(all_paths[0])}...")
                        extract_dir = os.path.join(temp_dir, "extracted")
                        os.makedirs(extract_dir, exist_ok=True)
                        with zipfile.ZipFile(all_paths[0], 'r') as z:
                            z.extractall(extract_dir)
                        scan_target = extract_dir
                    else:
                        scan_target = temp_dir
                        
                    def on_upload_prog(cur, tot, fname):
                        progress_bar.progress(cur / tot)
                        status_text.text(f"Auditing & Reconciling ({cur}/{tot}): {fname}")
                        
                    drive_conn = GoogleDriveConnector()
                    
                    unified_result = audit_directory_or_batch(api_key=api_key_input,
                        files_or_dir=scan_target,
                        base_dir=scan_target,
                        gdrive_connector=drive_conn,
                        mode=mode_options_map[selected_up_mode_label],
                        progress_callback=on_upload_prog)
                    progress_bar.progress(1.0)
                    st.session_state["unified_batch_result"] = unified_result
                    status_text.success("Batch ingestion and document audit completed successfully.")

        # Unified Result Display (Reconciliation KPIs, Excel Download, & Tables)
        if "unified_batch_result" in st.session_state:
            res = st.session_state["unified_batch_result"]
            st.divider()

            if res.get("type") == "index_inventory":
                inv = res.get("inventory_summary", {})
                entries = inv.get("entries", [])
                tot_listed = inv.get("total_listed_in_index", 0)
                tot_avail = inv.get("total_documents_available", 0)
                tot_missing = inv.get("total_documents_missing", 0)
                tot_inacc = inv.get("total_inaccessible", 0)
                tot_audited = inv.get("total_audited", 0)
                sub_rate = inv.get("submission_rate_pct", 0.0)

                st.markdown("#### Master Index & Document Inventory Reconciliation")
                st.caption(f"Reconciled from Master Index: `{os.path.basename(res.get('primary_index_path', 'Index File'))}`")

                st.markdown(f"""
                <div class="kpi-container">
                    <div class="kpi-card">
                        <div class="kpi-label">Courses in Index</div>
                        <div class="kpi-value">{tot_listed}</div>
                        <div class="kpi-sub">Total Cataloged</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Documents Available</div>
                        <div class="kpi-value" style="color: #15803D;">{tot_avail}</div>
                        <div class="kpi-sub">Audited & Verified</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Missing / Not Submitted</div>
                        <div class="kpi-value" style="color: #B91C1C;">{tot_missing}</div>
                        <div class="kpi-sub">Pending Facilitator</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Inaccessible Links</div>
                        <div class="kpi-value" style="color: #B45309;">{tot_inacc}</div>
                        <div class="kpi-sub">URL / Access Error</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">Submission Rate</div>
                        <div class="kpi-value">{sub_rate}%</div>
                        <div class="kpi-sub">Department Intake</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    reconciliation_bytes = generate_index_reconciliation_excel(inv)
                    st.download_button(
                        label="Download Master Index Reconciliation Report (.xlsx)",
                        data=reconciliation_bytes,
                        file_name="OOA_Index_Inventory_Reconciliation.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True
                    )
                with col_dl2:
                    current_audits = get_all_audits()
                    if current_audits:
                        rollup_bytes = generate_consolidated_report(current_audits)
                        st.download_button(
                            label="Download Full Institutional Audit Rollup (.xlsx)",
                            data=rollup_bytes,
                            file_name="OOA_Institutional_TLEP_Rollup.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary",
                            use_container_width=True
                        )

                # Zip Download
                audited_results = [e.audit_result for e in entries if hasattr(e, 'audit_result') and e.audit_result]
                if audited_results:
                    st.download_button(
                        label="Download All Individual Course Audit Reports (.zip)",
                        data=generate_multiple_reports_zip(audited_results),
                        file_name="OOA_Individual_Audit_Reports.zip",
                        mime="application/zip",
                        type="secondary",
                        use_container_width=True
                    )
                    from reports.batch_docx_report import generate_programme_executive_docx
                    st.download_button(
                        label="Download Programme Executive Report with Charts (.docx)",
                        data=generate_programme_executive_docx(audited_results),
                        file_name="OOA_Programme_Executive_Report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="secondary",
                        use_container_width=True
                    )
                st.markdown("#### Course Document Reconciliation Table")
                if audited_results:
                    from ui.dashboard import render_batch_dashboard
                    render_batch_dashboard(audited_results)
                inv_filter = st.radio(
                    "Filter Inventory Records:",
                    ["All Courses", "Documents Available", "Missing / Not Submitted", "Inaccessible Links"],
                    horizontal=True
                )

                filtered_entries = entries
                if inv_filter == "Documents Available":
                    filtered_entries = [e for e in entries if e.availability_status == "Available"]
                elif inv_filter == "Missing / Not Submitted":
                    filtered_entries = [e for e in entries if "Missing" in e.availability_status]
                elif inv_filter == "Inaccessible Links":
                    filtered_entries = [e for e in entries if e.availability_status not in ["Available"] and "Missing" not in e.availability_status]

                rows_data = []
                for e in filtered_entries:
                    rows_data.append({
                        "Index Row": e.row_number,
                        "Course Code": e.course_code,
                        "Course Title": e.course_title,
                        "Department": e.department,
                        "Facilitator": e.faculty,
                        "Document Status": e.availability_status,
                        "Link / Path": e.target_url_or_path or e.raw_reference or "None",
                        "Audit Status": e.audit_status or "Not Audited",
                        "Score %": f"{e.compliance_percentage}%" if e.compliance_percentage is not None else "-",
                        "Detail / Deficiencies": e.error_detail or ("Compliant" if e.audit_status == "Compliant" else "")
                    })

                st.dataframe(pd.DataFrame(rows_data), use_container_width=True)
                st.info("Tip: All audited courses are recorded in the central database. Switch to 'Portfolio Analytics & Leaderboard' for institutional rankings, BoS approvals, and department rollups.")

            elif res.get("type") == "direct_batch":
                aud_count = res.get("audited_count", 0)
                st.markdown(f"#### Batch Audit Results ({aud_count} Courses)")
                st.success(f"Successfully audited all {aud_count} standalone course TLEPs. Results recorded in central database.")
                
                current_audits = get_all_audits()
                full_results = []
                if current_audits:
                    rollup_bytes = generate_consolidated_report(current_audits)
                    st.download_button(
                        label="Download Full Institutional Audit Rollup (.xlsx)",
                        data=rollup_bytes,
                        file_name="OOA_Institutional_TLEP_Rollup.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
                    
                    full_results = [r.get("full_result") for r in res.get("results", []) if r.get("full_result")]
                    if full_results:
                        st.download_button(
                            label="Download All Individual Course Audit Reports (.zip)",
                            data=generate_multiple_reports_zip(full_results),
                            file_name="OOA_Individual_Audit_Reports.zip",
                            mime="application/zip",
                            type="secondary"
                        )
                        from reports.batch_docx_report import generate_programme_executive_docx
                        st.download_button(
                            label="Download Programme Executive Report with Charts (.docx)",
                            data=generate_programme_executive_docx(full_results),
                            file_name="OOA_Programme_Executive_Report.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="secondary"
                        )

                if full_results:
                    from ui.dashboard import render_batch_dashboard
                    render_batch_dashboard(full_results)
                    
                st.info("Tip: Switch to 'Portfolio Analytics & Leaderboard' to view department breakdowns and institutional performance.")






