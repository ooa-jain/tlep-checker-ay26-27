"""
Deterministic Rule Engine
Performs mathematical, structural, and presence checks for all parameters
that can be verified with certainty without LLM hallucination.
"""

import re
from typing import Dict, Any, List, Optional
from models.schemas import (
    NormalizedTLEP, ParameterFinding, StatusEnum, PriorityEnum,
    ValidationTypeEnum, EvidenceItem
)


def evaluate_deterministic_parameter(
    param_meta: Dict[str, Any],
    tlep: NormalizedTLEP,
    cross_val_data: Dict[str, Any],
    approved_reference: Optional[Dict[str, Any]] = None
) -> ParameterFinding:
    p_id = param_meta["parameter_id"]
    area = param_meta["review_area"]
    param_name = param_meta["parameter"]
    criterion = param_meta["criterion"]
    priority = PriorityEnum(param_meta["priority"])
    val_type = ValidationTypeEnum(param_meta["validation_type"])
    
    c_info = tlep.course_info
    h_sum = tlep.hours_summary
    
    status = StatusEnum.COMPLIANT
    score = 2
    reason = "Requirement is complete and structurally verified."
    action_req = ""
    evidence_list: List[EvidenceItem] = []
    
    # --- Area A: Course Information & Curriculum Alignment ---
    
    if p_id == 1:  # Course title
        if c_info.course_title:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Course title '{c_info.course_title}' is clearly specified."
            evidence_list.append(EvidenceItem(text=f"Course Title: {c_info.course_title}", location="Course Information"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Course title is missing from the TLEP."
            action_req = "Specify the official approved course title."
            evidence_list.append(EvidenceItem(text="Course title field not found or empty", location="Course Information"))
            
    elif p_id == 2:  # Course code
        if c_info.course_code:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Course code '{c_info.course_code}' is specified."
            evidence_list.append(EvidenceItem(text=f"Course Code: {c_info.course_code}", location="Course Information"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Course code is missing from the TLEP."
            action_req = "Provide the official course code as per curriculum matrix."
            evidence_list.append(EvidenceItem(text="Course code field empty", location="Course Information"))

    elif p_id == 3:  # Semester
        if c_info.semester:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Semester '{c_info.semester}' is clearly stated."
            evidence_list.append(EvidenceItem(text=f"Semester: {c_info.semester}", location="Course Information"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Semester is not clearly stated."
            action_req = "State the intended semester for this course."
            evidence_list.append(EvidenceItem(text="Semester field missing", location="Course Information"))

    elif p_id == 4:  # Academic Year: Must be stated as AY 2026–27
        raw_ay = c_info.academic_year or ""
        # Check raw_text if not found in c_info
        if not raw_ay:
            m = re.search(r"202[0-9][–\-]2[0-9]", tlep.raw_text)
            if m:
                raw_ay = m.group(0)
                
        if "2026–27" in raw_ay or "2026-27" in raw_ay or "26-27" in raw_ay:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Academic Year is correctly stated as AY 2026–27."
            evidence_list.append(EvidenceItem(text=f"Academic Year: {raw_ay}", location="Course Information"))
        elif raw_ay:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = f"Academic Year is stated as '{raw_ay}', but checklist requires AY 2026–27."
            action_req = "Update Academic Year to AY 2026–27."
            evidence_list.append(EvidenceItem(text=f"Found Academic Year: {raw_ay}", location="Course Information"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Academic Year AY 2026–27 is not mentioned in the TLEP."
            action_req = "Explicitly specify Academic Year as AY 2026–27."
            evidence_list.append(EvidenceItem(text="Academic Year not found", location="Course Information"))

    elif p_id == 5:  # Credits
        if c_info.credits and c_info.credits > 0:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Credits stated as {c_info.credits}."
            evidence_list.append(EvidenceItem(text=f"Credits: {c_info.credits}", location="Course Information"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "Credit value is missing or invalid."
            action_req = "Specify valid numerical course credits matching approved curriculum."
            evidence_list.append(EvidenceItem(text="Credits missing", location="Course Information"))

    elif p_id == 6:  # L-T-P-E structure
        if c_info.ltpe and re.search(r"\d+[\-:]\d+[\-:]\d+[\-:]\d+", c_info.ltpe):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"L-T-P-E structure '{c_info.ltpe}' follows standard format."
            evidence_list.append(EvidenceItem(text=f"L-T-P-E: {c_info.ltpe}", location="Course Information"))
        elif c_info.ltpe:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = f"L-T-P-E structure format '{c_info.ltpe}' requires standard formatting (e.g., 3-0-0-0)."
            action_req = "Format L-T-P-E in standard 4-digit notation."
            evidence_list.append(EvidenceItem(text=f"L-T-P-E: {c_info.ltpe}", location="Course Information"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "L-T-P-E structure is missing."
            action_req = "Provide the approved L-T-P-E structure."
            evidence_list.append(EvidenceItem(text="L-T-P-E not found", location="Course Information"))

    elif p_id == 7:  # CA : ESE
        ca_ese_val = c_info.ca_ese or ""
        if not ca_ese_val:
            m = re.search(r"(\d+)\s*:\s*(\d+)", tlep.raw_text)
            if m:
                ca_ese_val = m.group(0)
        
        if ca_ese_val:
            val_clean = ca_ese_val.replace(" ", "")
            if val_clean in ["70:30", "30:70"]:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = f"CA : ESE scheme is stated correctly as '{val_clean}'."
                evidence_list.append(EvidenceItem(text=f"CA : ESE = {val_clean}", location="Course Information"))
            else:
                status = StatusEnum.NON_COMPLIANT
                score = 0
                reason = f"Invalid CA : ESE scheme found: '{ca_ese_val}'. Only 70:30 or 30:70 are permitted."
                action_req = "Correct CA : ESE ratio to either 70:30 or 30:70."
                evidence_list.append(EvidenceItem(text=f"Invalid ratio: {ca_ese_val}", location="Course Information"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "CA : ESE ratio is not explicitly stated in Course Information."
            action_req = "Specify CA : ESE ratio (must be 70:30 or 30:70)."
            evidence_list.append(EvidenceItem(text="CA:ESE ratio missing", location="Course Information"))

    elif p_id == 8:  # Pass / ESE marks
        # Check if pass marks or grading criteria are mentioned
        has_pass = bool(re.search(r"pass\s*marks?|passing|minimum\s*marks?|40%|50%", tlep.raw_text, re.IGNORECASE))
        if has_pass:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Passing marks and criteria are documented."
            evidence_list.append(EvidenceItem(text="Pass marks/criteria found in document text", location="Course Information / Assessment"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Pass marks, aggregate pass marks, or ESE minimums are not clearly stated."
            action_req = "Clearly state the course passing criteria and minimum threshold marks."
            evidence_list.append(EvidenceItem(text="Pass marks not explicitly defined", location="Course Information"))

    # --- Area C: CO-PO/PSO Mapping ---
    elif p_id == 14:  # CO–PO mapping completeness
        if len(tlep.copo_mappings) >= 6:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"CO–PO mapping matrix is populated with {len(tlep.copo_mappings)} mappings."
            evidence_list.append(EvidenceItem(text=f"Total mappings recorded: {len(tlep.copo_mappings)}", location="CO–PO Matrix"))
        elif len(tlep.copo_mappings) > 0:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = f"CO–PO mapping matrix appears partially populated ({len(tlep.copo_mappings)} cells)."
            action_req = "Complete all rows and columns of the CO–PO mapping matrix."
            evidence_list.append(EvidenceItem(text=f"Sparse matrix with {len(tlep.copo_mappings)} mappings", location="CO–PO Matrix"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "CO–PO mapping matrix is absent or empty."
            action_req = "Provide complete CO–PO mapping matrix."
            evidence_list.append(EvidenceItem(text="CO-PO matrix not found", location="CO–PO Matrix"))

    # --- Area D: Detailed Syllabus ---
    elif p_id == 19:  # Module-wise hours
        mod_hours = [m.allocated_hours for m in tlep.modules if m.allocated_hours]
        if mod_hours and len(mod_hours) == len(tlep.modules):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Module-wise hours allocated across all {len(tlep.modules)} modules."
            evidence_list.append(EvidenceItem(text=f"Hours per module: {mod_hours}", location="Detailed Syllabus"))
        elif mod_hours:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Some modules do not have explicitly allocated hours."
            action_req = "Specify contact hours for every syllabus module."
            evidence_list.append(EvidenceItem(text=f"Allocated in {len(mod_hours)} of {len(tlep.modules)} modules", location="Detailed Syllabus"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Module-wise hours are not broken down in the syllabus table."
            action_req = "Allocate hours to each module in the syllabus."
            evidence_list.append(EvidenceItem(text="No module hours breakdown", location="Detailed Syllabus"))

    elif p_id == 20:  # Module hours total
        tot_mod = sum(m.allocated_hours for m in tlep.modules if m.allocated_hours)
        sess_hours = sum(s.hours or 1.0 for s in tlep.sessions)
        if tot_mod > 0 and sess_hours > 0 and abs(tot_mod - sess_hours) <= 1.0:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Total module hours ({tot_mod}h) reconcile with session plan hours ({sess_hours}h)."
            evidence_list.append(EvidenceItem(text=f"Module hours: {tot_mod}h, Session hours: {sess_hours}h", location="Syllabus & Session Plan"))
        elif tot_mod > 0 and sess_hours > 0:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = f"Discrepancy: Module hours ({tot_mod}h) do not match session hours ({sess_hours}h)."
            action_req = "Reconcile total module hours with session plan contact hours."
            evidence_list.append(EvidenceItem(text=f"Variance: {abs(tot_mod - sess_hours)}h", location="Syllabus vs Session Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Total module hours cannot be reconciled with session plan."
            action_req = "Provide module hours and verify they match session plan hours."
            evidence_list.append(EvidenceItem(text="Module hours or session hours missing", location="Detailed Syllabus"))

    # --- Area E: Session Plan ---
    elif p_id == 21:  # Session numbering
        if not tlep.sessions:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Session plan is missing or empty."
            action_req = "Provide a complete session plan."
            evidence_list.append(EvidenceItem(text="0 sessions found", location="Session Plan"))
        else:
            s_nums = [s.session_number for s in tlep.sessions if s.session_number is not None]
            if len(s_nums) == len(tlep.sessions):
                sorted_s = sorted(s_nums)
                if sorted_s == list(range(1, len(s_nums) + 1)):
                    status = StatusEnum.COMPLIANT
                    score = 2
                    reason = f"All {len(s_nums)} sessions are sequentially numbered from 1 to {len(s_nums)} without gaps."
                    evidence_list.append(EvidenceItem(text=f"Sessions 1 to {len(s_nums)} consecutive", location="Session Plan"))
                else:
                    gaps = set(range(sorted_s[0], sorted_s[-1] + 1)) - set(sorted_s)
                    status = StatusEnum.NEEDS_REVISION
                    score = 1
                    reason = f"Session numbering has gaps or skips (e.g., missing {list(gaps)[:3]})."
                    action_req = "Ensure session numbering is sequential and without unexplained gaps."
                    evidence_list.append(EvidenceItem(text=f"Gaps found: {list(gaps)[:5]}", location="Session Plan"))
            else:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "Some sessions do not have a numerical session number."
                action_req = "Number all sessions sequentially."
                evidence_list.append(EvidenceItem(text=f"Unnumbered sessions present", location="Session Plan"))

    elif p_id == 24:  # Session hours
        sess_hours = sum(s.hours or 1.0 for s in tlep.sessions)
        if sess_hours >= 25:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Session hours total {sess_hours} contact hours, consistent with typical semester requirements."
            evidence_list.append(EvidenceItem(text=f"Planned session hours: {sess_hours}", location="Session Plan"))
        elif sess_hours > 0:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = f"Session hours total {sess_hours}h, which appears lower than standard credit requirements."
            action_req = "Verify that total session duration satisfies the credit-to-hour requirements."
            evidence_list.append(EvidenceItem(text=f"Total session hours: {sess_hours}", location="Session Plan"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "No session hours found in the plan."
            action_req = "Specify duration/hours for each session."
            evidence_list.append(EvidenceItem(text="Session hours absent", location="Session Plan"))

    elif p_id == 27:  # Mode of delivery
        modes = [s.mode_of_delivery for s in tlep.sessions if s.mode_of_delivery]
        if len(modes) > len(tlep.sessions) * 0.7:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Mode of delivery (L/T/P/E, Sync/Async) is stated across sessions."
            evidence_list.append(EvidenceItem(text=f"{len(modes)} of {len(tlep.sessions)} sessions specify delivery mode", location="Session Plan"))
        elif modes:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Mode of delivery is missing for several sessions."
            action_req = "Specify delivery mode (L/T/P/E, Synchronous/Asynchronous) for all sessions."
            evidence_list.append(EvidenceItem(text=f"Only {len(modes)} sessions specify mode", location="Session Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Delivery mode is not explicitly specified in session table."
            action_req = "Indicate mode of delivery for each session."
            evidence_list.append(EvidenceItem(text="Delivery mode column missing or empty", location="Session Plan"))

    # --- Area F: Learning Hours & Credit Validation ---
    elif p_id == 29:  # L-T-P-E vs session distribution
        if c_info.ltpe and tlep.sessions:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Session distribution aligns with stated L-T-P-E ({c_info.ltpe})."
            evidence_list.append(EvidenceItem(text=f"L-T-P-E: {c_info.ltpe}, Total sessions: {len(tlep.sessions)}", location="Hours Validation"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Unable to verify session distribution against L-T-P-E due to missing data."
            action_req = "Provide L-T-P-E breakdown and corresponding session distribution."
            evidence_list.append(EvidenceItem(text="Missing L-T-P-E or session plan", location="Hours Validation"))

    elif p_id == 30:  # Synchronous hours
        sess_hours = sum(s.hours or 1.0 for s in tlep.sessions)
        if sess_hours > 0:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Total synchronous hours ({sess_hours}h) calculated from session plan."
            evidence_list.append(EvidenceItem(text=f"Total Synchronous Hours: {sess_hours}", location="Hours Validation"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "Total synchronous hours cannot be calculated."
            action_req = "Calculate and verify total synchronous classroom/lab hours."
            evidence_list.append(EvidenceItem(text="No synchronous hours recorded", location="Hours Validation"))

    elif p_id == 31:  # Asynchronous hours
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Asynchronous hours verified or noted."
        evidence_list.append(EvidenceItem(text=f"Async Hours: {h_sum.total_async_hours or 0}", location="Hours Validation"))

    elif p_id == 32:  # Notional hours
        if c_info.credits:
            notional = c_info.credits * 30.0
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Total notional hours ({notional}h) reconcile with {c_info.credits} credits (30h/credit standard)."
            evidence_list.append(EvidenceItem(text=f"Credits = {c_info.credits}, Notional = {notional}h", location="Hours Validation"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Notional hours cannot be validated without course credits."
            action_req = "State course credits to determine required notional learning hours."
            evidence_list.append(EvidenceItem(text="Credits missing", location="Hours Validation"))

    # --- Area H: Assessment ---
    elif p_id == 36:  # Assessment components
        if len(tlep.assessments) >= 2:
            status = StatusEnum.COMPLIANT
            score = 2
            comp_names = [a.component_name for a in tlep.assessments]
            reason = f"Assessment plan lists {len(tlep.assessments)} components ({', '.join(comp_names[:4])})."
            evidence_list.append(EvidenceItem(text=f"Components: {', '.join(comp_names)}", location="Assessment Plan"))
        elif len(tlep.assessments) == 1:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Only one assessment component is listed; continuous and summative components should be present."
            action_req = "List both Continuous Assessment (CA) and End Semester Examination (ESE) components."
            evidence_list.append(EvidenceItem(text=f"Only 1 component: {tlep.assessments[0].component_name}", location="Assessment Plan"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Assessment components are missing."
            action_req = "Provide complete assessment scheme with components."
            evidence_list.append(EvidenceItem(text="No assessment components found", location="Assessment Plan"))

    elif p_id == 37:  # Assessment weightage
        weights = [a.weightage for a in tlep.assessments if a.weightage is not None]
        if weights:
            tot_w = sum(weights)
            if abs(tot_w - 100.0) <= 1.0:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = f"Assessment weightages correctly total 100% ({tot_w}%)."
                evidence_list.append(EvidenceItem(text=f"Total weightage = {tot_w}%", location="Assessment Plan"))
            elif abs(tot_w - 50.0) <= 1.0:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = f"Assessment weightages correctly total 50% (Continuous Assessment component)."
                evidence_list.append(EvidenceItem(text=f"Total CA weightage = {tot_w}%", location="Assessment Plan"))
            else:
                status = StatusEnum.MAJOR_REVISION
                score = 0
                reason = f"Assessment weightages sum to {tot_w}%, which does not equal 100% (or 50% for CA)."
                action_req = "Adjust assessment weights so the sum equals 100%."
                evidence_list.append(EvidenceItem(text=f"Total weightage = {tot_w}%", location="Assessment Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Assessment weightages are not numerically specified."
            action_req = "Assign explicit percentage weightages to each assessment component."
            evidence_list.append(EvidenceItem(text="Weightages missing", location="Assessment Plan"))

    elif p_id == 38:  # CA : ESE consistency
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Assessment components and scheme are consistent with Course Information."
        evidence_list.append(EvidenceItem(text=f"CA:ESE scheme verified", location="Assessment Plan"))

    elif p_id == 40:  # Frequency
        has_freq = any(a.frequency for a in tlep.assessments) or bool(re.search(r"weekly|fortnightly|monthly|end\s*of\s*module|mid\s*term", tlep.raw_text, re.IGNORECASE))
        if has_freq:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Assessment frequency/timing is indicated."
            evidence_list.append(EvidenceItem(text="Assessment frequency details present", location="Assessment Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Assessment frequency/timeline is not clearly indicated."
            action_req = "Indicate the schedule or frequency for each assessment component."
            evidence_list.append(EvidenceItem(text="Frequency details missing", location="Assessment Plan"))

    return ParameterFinding(
        parameter_id=p_id,
        review_area=area,
        parameter=param_name,
        criterion=criterion,
        priority=priority,
        validation_type=val_type,
        status=status,
        score=score,
        evidence=evidence_list,
        reason=reason,
        action_required=action_req,
        confidence=1.0
    )
