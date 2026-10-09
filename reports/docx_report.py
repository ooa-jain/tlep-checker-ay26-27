import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

def generate_executive_narrative_docx(result) -> bytes:
    doc = Document()
    
    # Title
    title = doc.add_paragraph("TLEP REVIEW – REMARKS")
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    for run in title.runs:
        run.bold = True
        run.font.size = Pt(14)
    
    course_title = result.normalized_tlep.course_info.course_title or "Unknown Course"
    course_code = result.normalized_tlep.course_info.course_code or "Unknown Code"
    programme = getattr(result.normalized_tlep.course_info, 'programme', "Unknown Programme")
    credits_count = result.normalized_tlep.course_info.credits or "Unknown"
    ltpe = getattr(result.normalized_tlep.course_info, 'ltpe', "Unknown")
    contact_hours = sum(s.hours for s in result.normalized_tlep.sessions)
    
    p = doc.add_paragraph()
    p.add_run(f"Sample Review: {course_title} ({course_code})\n").bold = True
    p.add_run(f"Programme: {programme}    Credits: {credits_count}    L-T-P-E: {ltpe}    Contact Hours: {contact_hours}")
    
    doc.add_paragraph()
    
    # Generate Pie Chart for Parameter Statuses
    import matplotlib.pyplot as plt
    import pandas as pd
    
    status_counts = pd.Series([f.status.value for f in result.parameter_findings]).value_counts()
    colors = {"Compliant": "#16A34A", "Needs Revision": "#CA8A04", "Major Revision": "#DC2626", "Non-Compliant": "#991B1B", "NA": "#64748B"}
    plot_colors = [colors.get(s, "#888888") for s in status_counts.index]
    
    plt.figure(figsize=(5, 3.5))
    
    # Clean donut chart styling
    wedges, texts, autotexts = plt.pie(
        status_counts.values, 
        labels=status_counts.index, 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=plot_colors,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
        textprops=dict(color='#1E293B', fontsize=9, fontweight='500')
    )
    
    # Make percentages bold and white if inside dark slices, or just dark bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
        autotext.set_fontsize(8)

    plt.title("Parameter Compliance Status", pad=15, fontsize=11, fontweight='bold', color='#0F172A')
    
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', bbox_inches='tight', dpi=300, transparent=True)
    buf1.seek(0)
    plt.close()
    
    doc.add_picture(buf1, width=Inches(4.5))
    doc.paragraphs[-1].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_paragraph()
    
    # Generate Area Breakdown Bar Chart
    from engine.scoring import aggregate_area_breakdown
    area_summary = aggregate_area_breakdown(result.parameter_findings)
    df_areas = pd.DataFrame(area_summary)
    df_areas['Short Area'] = df_areas['review_area'].apply(lambda x: x.split("–")[0].strip() if "–" in x else (x.split("-")[0].strip() if "-" in x else x))
    df_areas = df_areas.sort_values(by='compliance_pct', ascending=True)
    
    plt.figure(figsize=(6, 3.5))
    # Map colors: <70 red, 70-85 yellow, 85+ green
    bar_colors = ['#DC2626' if p < 70 else ('#CA8A04' if p < 85 else '#16A34A') for p in df_areas['compliance_pct']]
    bars = plt.barh(df_areas['Short Area'], df_areas['compliance_pct'], color=bar_colors)
    plt.title("Area-Wise Compliance (%)", pad=15, fontsize=11, fontweight='bold', color='#0F172A')
    plt.xlim(0, 115)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().spines['bottom'].set_visible(False)
    plt.gca().xaxis.set_visible(False)
    plt.tick_params(left=False)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 2, bar.get_y() + bar.get_height()/2, f'{width:.1f}%', va='center', fontsize=9, fontweight='bold', color='#334155')
        
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png', bbox_inches='tight', dpi=300, transparent=True)
    buf2.seek(0)
    plt.close()
    
    doc.add_picture(buf2, width=Inches(5.0))
    doc.paragraphs[-1].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_paragraph()
    
    doc.add_paragraph("Remarks").runs[0].bold = True
    
    def get_finding(param_id):
        return next((f for f in result.parameter_findings if getattr(f, 'parameter_id', None) == param_id), None)
        
    f_modules = get_finding(18)
    f_pedagogy = get_finding(26)
    f_co = get_finding(10)
    f_copo = get_finding(15)
    f_assess = get_finding(39)
    f_resources = get_finding(33)
    
    remarks = [
        f"Teaching & Learning Plan: {f_modules.action_required if f_modules and f_modules.action_required else 'Ensure module coverage is properly distributed across sessions.'}",
        f"Pedagogy: {f_pedagogy.action_required if f_pedagogy and f_pedagogy.action_required else 'Clearly indicate pedagogical methods for each session.'}",
        f"Course Outcomes: {f_co.action_required if f_co and f_co.action_required else 'Review and properly align Course Outcomes.'}",
        f"CO-PO Mapping: {f_copo.action_required if f_copo and f_copo.action_required else 'Validate and justify CO-PO mappings.'}",
        f"Assessment: {f_assess.action_required if f_assess and f_assess.action_required else 'Define assessment structure and component breakdown clearly.'}",
        "Practical Learning: Explicitly incorporate experiential learning components into the teaching plan.",
        "Feedback Analysis: Incorporate evidence of student feedback analysis and resulting improvements.",
        "Continuous Improvement: Document a formal continuous-improvement record linking previous course review actions.",
        f"Learning Resources: {f_resources.action_required if f_resources and f_resources.action_required else 'Standardize and update learning references.'}",
        "General: Address all highlighted parameters to achieve full compliance before final submission."
    ]
    
    for i, rmk in enumerate(remarks, 1):
        doc.add_paragraph(f"{i}. {rmk}")
        
    doc.add_paragraph()
    doc.add_paragraph("Recommended Action").runs[0].bold = True
    
    action = "Return for targeted revision." if result.overall_status.value in ["Needs Revision", "Major Revision", "Non-Compliant"] else "Approved without major revisions."
    if action.startswith("Return"):
        action += " The course may be considered for final review after the critical OBE mapping inconsistencies, CO-assessment alignment and feedback/continuous-improvement documentation are addressed."
        
    doc.add_paragraph(action)
    
    doc.add_paragraph()
    doc.add_paragraph("Lead Team Quick View").runs[0].bold = True
    doc.add_paragraph(f"Source: Submitted Teaching-Learning & Evaluation Plan – {course_title}, {programme}, Course Code {course_code}.")
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
