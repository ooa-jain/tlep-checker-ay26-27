import re

with open('engine/ai_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = """def generate_executive_narrative(result, api_key: str = None) -> str:
    \"\"\"
    Generates an executive narrative summary deterministically matching the specific format.
    No AI key is required.
    \"\"\"
    course_title = result.tlep.course_info.course_title or "Unknown Course"
    course_code = result.tlep.course_info.course_code or "Unknown Code"
    programme = getattr(result.tlep.course_info, 'programme', "Unknown Programme")
    credits_count = result.tlep.course_info.credits or "Unknown"
    ltpe = getattr(result.tlep.course_info, 'ltpe', "Unknown")
    contact_hours = sum(s.hours for s in result.tlep.sessions)
    
    def get_finding(param_id):
        return next((f for f in result.parameter_findings if getattr(f, 'parameter_id', None) == param_id), None)
        
    f_modules = get_finding(18)
    f_pedagogy = get_finding(26)
    f_co = get_finding(10)
    f_copo = get_finding(15)
    f_assess = get_finding(39)
    f_resources = get_finding(33)
    
    rmk_1 = f"The TLEP is structured with a {contact_hours}-hour session-wise plan. {f_modules.reason if f_modules else 'Module coverage needs verification.'}"
    rmk_2 = f"{f_pedagogy.reason if f_pedagogy else 'Pedagogical methods should be clearly indicated.'}"
    rmk_3 = f"{f_co.reason if f_co else 'Course Outcomes alignment requires review.'}"
    rmk_4 = f"{f_copo.reason if f_copo else 'CO-PO mappings need validation and justification.'}"
    rmk_5 = f"{f_assess.reason if f_assess else 'Assessment structure requires clearer component breakdown.'}"
    rmk_6 = "The practical and experiential learning components should be explicitly reflected in the teaching-learning plan."
    rmk_7 = "Evidence of student feedback analysis and resulting improvements should be incorporated."
    rmk_8 = "A formal continuous-improvement record linking previous course review actions is not fully evidenced."
    rmk_9 = f"{f_resources.reason if f_resources else 'Learning resources are adequate at a basic level, but standardizing references is recommended.'}"
    rmk_10 = "Overall, the TLEP demonstrates a teaching-learning foundation but requires targeted revision in areas marked for action."

    action = "Return for targeted revision." if result.overall_status.value in ["Needs Revision", "Major Revision", "Non-Compliant"] else "Approved without major revisions."
    
    def get_priority(findings_list):
        for f in findings_list:
            if f and f.status.value in ["Major Revision", "Non-Compliant"]: return "Critical"
        for f in findings_list:
            if f and f.status.value == "Needs Revision": return "Major"
        return "Strength"

    pri_tl = get_priority([f_modules, f_pedagogy])
    pri_obe = get_priority([f_co, f_copo])
    pri_assess = get_priority([f_assess])

    narrative = f\"\"\"TLEP REVIEW REMARKS
Sample Review: {course_title} ({course_code})
Programme: {programme}    Credits: {credits_count}    L-T-P-E: {ltpe}    Contact Hours: {contact_hours}
Overall Status    {result.overall_status.value.upper()}

Remarks
1. {rmk_1}
2. {rmk_2}
3. {rmk_3}
4. {rmk_4}
5. {rmk_5}
6. {rmk_6}
7. {rmk_7}
8. {rmk_8}
9. {rmk_9}
10. {rmk_10}

Recommended Action
{action}

Lead Team Quick View
| Area | Observation | Priority |
|---|---|---|
| Teaching-Learning Plan | Session planning and pedagogy review. | {pri_tl} |
| OBE Mapping | CO formulation and PO mapping review. | {pri_obe} |
| Assessment Alignment | Component mapping and rubrics review. | {pri_assess} |
| Feedback & Analysis | Feedback analysis and action taken. | Critical |
| Continuous Improvement | Formal improvement cycle documentation. | Critical |

Source: Submitted Teaching-Learning & Evaluation Plan - {course_title}, {programme}, Course Code {course_code}.
\"\"\"
    return narrative.strip()
"""

new_content = re.sub(r'def generate_executive_narrative\(.*', new_func, content, flags=re.DOTALL)

with open('engine/ai_engine.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
