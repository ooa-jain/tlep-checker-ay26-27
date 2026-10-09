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
        f"The TLEP is structured with a {contact_hours}-hour session-wise plan. {f_modules.reason if f_modules else 'Module coverage needs verification.'}",
        f"{f_pedagogy.reason if f_pedagogy else 'Pedagogical methods should be clearly indicated.'}",
        f"{f_co.reason if f_co else 'Course Outcomes alignment requires review.'}",
        f"{f_copo.reason if f_copo else 'CO-PO mappings need validation and justification.'}",
        f"{f_assess.reason if f_assess else 'Assessment structure requires clearer component breakdown.'}",
        "The practical and experiential learning components should be explicitly reflected in the teaching-learning plan.",
        "Evidence of student feedback analysis and resulting improvements should be incorporated.",
        "A formal continuous-improvement record linking previous course review actions is not fully evidenced.",
        f"{f_resources.reason if f_resources else 'Learning resources are adequate at a basic level, but standardizing references is recommended.'}",
        "Overall, the TLEP demonstrates a teaching-learning foundation but requires targeted revision in areas marked for action."
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
