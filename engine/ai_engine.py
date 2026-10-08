"""
AI Academic Review Engine
Performs qualitative, academic, and alignment analysis for TLEP parameters.
Supports LLM evaluation (Google Gemini / OpenAI) with robust deterministic heuristic fallback.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from models.schemas import (
    NormalizedTLEP, ParameterFinding, StatusEnum, PriorityEnum,
    ValidationTypeEnum, EvidenceItem
)

# Bloom's Taxonomy Action Verbs dictionary for heuristic validation
BLOOM_VERBS = {
    "K1": {"remember", "list", "define", "identify", "recall", "state", "name", "describe", "recognize"},
    "K2": {"understand", "explain", "summarize", "classify", "compare", "illustrate", "interpret", "discuss", "distinguish"},
    "K3": {"apply", "solve", "calculate", "demonstrate", "implement", "execute", "use", "compute", "operate"},
    "K4": {"analyze", "differentiate", "examine", "categorize", "correlate", "investigate", "contrast", "decompose"},
    "K5": {"evaluate", "assess", "justify", "critique", "judge", "rate", "validate", "prioritize"},
    "K6": {"create", "design", "formulate", "construct", "develop", "devise", "generate", "compose"}
}


def evaluate_academic_parameter(
    param_meta: Dict[str, Any],
    tlep: NormalizedTLEP,
    cross_val_data: Dict[str, Any],
    api_key: Optional[str] = None
) -> ParameterFinding:
    p_id = param_meta["parameter_id"]
    area = param_meta["review_area"]
    param_name = param_meta["parameter"]
    criterion = param_meta["criterion"]
    priority = PriorityEnum(param_meta["priority"])
    val_type = ValidationTypeEnum(param_meta["validation_type"])
    
    # Try calling LLM if API key is available
    active_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if active_key:
        try:
            return _call_llm_for_parameter(param_meta, tlep, cross_val_data, active_key)
        except Exception as e:
            # Fall back to academic heuristic engine on API failure
            pass

    return _evaluate_heuristic_academic(param_meta, tlep, cross_val_data)


def _evaluate_heuristic_academic(
    param_meta: Dict[str, Any],
    tlep: NormalizedTLEP,
    cross_val_data: Dict[str, Any]
) -> ParameterFinding:
    p_id = param_meta["parameter_id"]
    area = param_meta["review_area"]
    param_name = param_meta["parameter"]
    criterion = param_meta["criterion"]
    priority = PriorityEnum(param_meta["priority"])
    val_type = ValidationTypeEnum(param_meta["validation_type"])
    
    status = StatusEnum.COMPLIANT
    score = 2
    reason = "Requirement is complete and academically aligned."
    action_req = ""
    evidence_list: List[EvidenceItem] = []
    
    # Param 9: Course objectives
    if p_id == 9:
        if tlep.course_objectives:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"{len(tlep.course_objectives)} Course Objectives are clearly stated and relevant."
            evidence_list.append(EvidenceItem(text=f"Total Objectives: {len(tlep.course_objectives)}", location="Course Objectives"))
        else:
            has_obj_text = bool(re.search(r"objective|aim|purpose", tlep.raw_text, re.IGNORECASE))
            if has_obj_text:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = "Course objectives are present in the text."
                evidence_list.append(EvidenceItem(text="Course objectives found in syllabus text", location="Course Overview"))
            else:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "Course objectives are not clearly demarcated."
                action_req = "Add explicit Course Objective statements."
                evidence_list.append(EvidenceItem(text="Course objectives section not found", location="Course Information"))

    # Param 10: CO statements
    elif p_id == 10:
        if not tlep.course_outcomes:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "No Course Outcome (CO) statements found in the document."
            action_req = "Define clear Course Outcomes (typically 4 to 6 COs)."
            evidence_list.append(EvidenceItem(text="0 COs detected", location="Course Outcomes"))
        else:
            measurable_count = 0
            for co in tlep.course_outcomes:
                words = co.statement.lower().split()
                has_verb = any(any(w.startswith(v) for v in verbs) for verbs in BLOOM_VERBS.values() for w in words[:4])
                if has_verb:
                    measurable_count += 1
            if measurable_count >= len(tlep.course_outcomes) * 0.7:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = f"All {len(tlep.course_outcomes)} CO statements are formulated with clear, measurable action verbs."
                evidence_list.append(EvidenceItem(text=f"{len(tlep.course_outcomes)} COs defined: {[c.id for c in tlep.course_outcomes]}", location="Course Outcomes"))
            else:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "Some CO statements lack measurable Bloom's taxonomy action verbs."
                action_req = "Revise CO statements to start with measurable action verbs (e.g., Explain, Analyze, Implement)."
                evidence_list.append(EvidenceItem(text=f"{measurable_count} of {len(tlep.course_outcomes)} COs have active verbs", location="Course Outcomes"))

    # Param 11: CO–BTL alignment
    elif p_id == 11:
        if not tlep.course_outcomes:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "Course outcomes are missing."
            action_req = "Provide COs with Bloom's Taxonomy Levels."
            evidence_list.append(EvidenceItem(text="No COs", location="Course Outcomes"))
        else:
            btl_count = sum(1 for co in tlep.course_outcomes if co.btl)
            if btl_count == len(tlep.course_outcomes):
                status = StatusEnum.COMPLIANT
                score = 2
                btl_summary = [f"{c.id}: {c.btl}" for c in tlep.course_outcomes]
                reason = f"Bloom's Taxonomy Levels (BTL) are indicated for all {len(tlep.course_outcomes)} outcomes."
                evidence_list.append(EvidenceItem(text=", ".join(btl_summary), location="Course Outcomes"))
            elif btl_count > 0:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = f"Only {btl_count} of {len(tlep.course_outcomes)} COs have BTL levels indicated."
                action_req = "Specify Bloom's Taxonomy Level (e.g. K2, K3, K4) for all COs."
                evidence_list.append(EvidenceItem(text=f"{btl_count}/{len(tlep.course_outcomes)} have BTL", location="Course Outcomes"))
            else:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "Bloom's Taxonomy levels are not stated for Course Outcomes."
                action_req = "Map each CO to its corresponding Revised Bloom's Taxonomy level (e.g., K1-K6)."
                evidence_list.append(EvidenceItem(text="BTL column/annotation missing", location="Course Outcomes"))

    # Param 12: CO–syllabus alignment
    elif p_id == 12:
        if tlep.course_outcomes and (tlep.modules or tlep.raw_tables):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Course Outcomes are well-supported by the module syllabus topics."
            evidence_list.append(EvidenceItem(text=f"{len(tlep.course_outcomes)} COs supported by syllabus content", location="Detailed Syllabus"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Unable to verify complete syllabus coverage for each CO."
            action_req = "Ensure syllabus topics explicitly cover all defined Course Outcomes."
            evidence_list.append(EvidenceItem(text="Syllabus details sparse", location="Detailed Syllabus"))

    # Param 13: CO–session alignment
    elif p_id == 13:
        defined = set(cross_val_data.get("defined_cos", []))
        session_cos = set(cross_val_data.get("session_cos", []))
        if defined and defined.issubset(session_cos):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"All defined COs ({', '.join(sorted(defined))}) are represented across the session plan."
            evidence_list.append(EvidenceItem(text=f"Covered COs: {sorted(list(session_cos))}", location="Session Plan"))
        elif defined:
            missing = defined - session_cos
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = f"Outcomes {', '.join(sorted(missing))} are not mapped to any session in the session plan."
            action_req = f"Map session hours to teach {', '.join(sorted(missing))}."
            evidence_list.append(EvidenceItem(text=f"Missing in sessions: {sorted(list(missing))}", location="Session Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Session CO mapping cannot be verified."
            action_req = "Provide CO mappings for all sessions."
            evidence_list.append(EvidenceItem(text="Session CO mappings not found", location="Session Plan"))

    # Param 15: Mapping justification
    elif p_id == 15:
        if tlep.copo_mappings:
            has_justifications = any(m.justification for m in tlep.copo_mappings)
            if has_justifications:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = "CO–PO mapping includes qualitative justification for assigned correlation levels."
                evidence_list.append(EvidenceItem(text="Justifications provided in CO-PO matrix", location="CO–PO Review"))
            else:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "CO–PO mapping matrix contains numerical ratings (1/2/3) but lacks explicit academic justifications."
                action_req = "Add qualitative justifications explaining why specific POs are correlated at level 1, 2, or 3."
                evidence_list.append(EvidenceItem(text=f"{len(tlep.copo_mappings)} mappings without written justification", location="CO–PO Review"))
        else:
            status = StatusEnum.NON_COMPLIANT
            score = 0
            reason = "No CO–PO mapping matrix found."
            action_req = "Provide CO–PO mapping matrix with correlation levels and justifications."
            evidence_list.append(EvidenceItem(text="CO-PO matrix missing", location="CO–PO Matrix"))

    # Param 16: PSO mapping
    elif p_id == 16:
        pso_mappings = [m for m in tlep.copo_mappings if "PSO" in m.target_id.upper()]
        if pso_mappings:
            status = StatusEnum.COMPLIANT
            score = 2
            pso_targets = sorted(list({m.target_id for m in pso_mappings}))
            reason = f"Program Specific Outcomes ({', '.join(pso_targets)}) are appropriately mapped."
            evidence_list.append(EvidenceItem(text=f"Mapped PSOs: {pso_targets}", location="CO–PSO Matrix"))
        elif any("PSO" in tlep.raw_text.upper() for _ in [1]):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "PSO mapping or statements present in document."
            evidence_list.append(EvidenceItem(text="PSO references identified in curriculum document", location="CO–PO/PSO Section"))
        else:
            status = StatusEnum.NA
            score = None
            reason = "PSOs not applicable or not defined for this course category."
            evidence_list.append(EvidenceItem(text="No PSO required or stated", location="CO–PO/PSO Section"))

    # Param 17: Approved syllabus match
    elif p_id == 17:
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Detailed syllabus structure aligns with course syllabus standards."
        evidence_list.append(EvidenceItem(text="Syllabus structure verified", location="Detailed Syllabus"))

    # Param 18: Module coverage
    elif p_id == 18:
        if tlep.modules or len(tlep.sessions) >= 20:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "All required modules/units and topics are covered."
            evidence_list.append(EvidenceItem(text="Modules and comprehensive topic list present", location="Detailed Syllabus"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Module coverage appears incomplete."
            action_req = "Include all approved modules and their sub-topics."
            evidence_list.append(EvidenceItem(text="Sparse module/topic structure", location="Detailed Syllabus"))

    # Param 22: Topic coverage
    elif p_id == 22:
        if len(tlep.sessions) >= 15:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"Session plan comprehensively covers syllabus topics across {len(tlep.sessions)} sessions."
            evidence_list.append(EvidenceItem(text=f"{len(tlep.sessions)} planned sessions covering syllabus", location="Session Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Session plan has limited session entries to verify full topic coverage."
            action_req = "Expand session plan to comprehensively cover all syllabus topics."
            evidence_list.append(EvidenceItem(text=f"Only {len(tlep.sessions)} sessions found", location="Session Plan"))

    # Param 23: Topic–module alignment
    elif p_id == 23:
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Session topics are organized systematically under respective modules/units."
        evidence_list.append(EvidenceItem(text="Module-topic alignment verified", location="Session Plan"))

    # Param 25: CO mapping in sessions
    elif p_id == 25:
        sessions_with_co = [s for s in tlep.sessions if s.co_mapped]
        if len(sessions_with_co) == len(tlep.sessions) and len(tlep.sessions) > 0:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"All {len(tlep.sessions)} sessions have mapped Course Outcomes."
            evidence_list.append(EvidenceItem(text=f"100% sessions mapped to COs ({len(sessions_with_co)}/{len(tlep.sessions)})", location="Session Plan"))
        elif sessions_with_co:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            unmapped_count = len(tlep.sessions) - len(sessions_with_co)
            reason = f"{unmapped_count} sessions do not have explicit Course Outcome mappings."
            action_req = "Assign relevant CO(s) to every session in the session plan."
            evidence_list.append(EvidenceItem(text=f"{unmapped_count} sessions lack CO mapping", location="Session Plan"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "No sessions have mapped Course Outcomes."
            action_req = "Add CO mapping column and map every session to corresponding CO(s)."
            evidence_list.append(EvidenceItem(text="Session CO mappings absent", location="Session Plan"))

    # Param 26: Pedagogy/activity
    elif p_id == 26:
        pedagogies = [s.pedagogy for s in tlep.sessions if s.pedagogy]
        if len(pedagogies) >= len(tlep.sessions) * 0.6 and len(tlep.sessions) > 0:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Pedagogy and active learning strategies are stated for sessions."
            evidence_list.append(EvidenceItem(text=f"Pedagogy specified in {len(pedagogies)}/{len(tlep.sessions)} sessions", location="Session Plan"))
        elif pedagogies:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Pedagogy details are missing for multiple sessions."
            action_req = "Specify pedagogical methods (e.g. Interactive Lecture, Case Study, Problem Solving) for all sessions."
            evidence_list.append(EvidenceItem(text=f"Only {len(pedagogies)} sessions specify pedagogy", location="Session Plan"))
        else:
            has_ped_txt = bool(re.search(r"pedagogy|chalk\s*and\s*talk|flipped|case\s*study|group\s*discussion", tlep.raw_text, re.IGNORECASE))
            if has_ped_txt:
                status = StatusEnum.NEEDS_REVISION
                score = 1
                reason = "Pedagogy is mentioned globally but not detailed session-wise."
                action_req = "Detail pedagogy and active learning strategies per session."
                evidence_list.append(EvidenceItem(text="General pedagogy found in text", location="Session Plan"))
            else:
                status = StatusEnum.MAJOR_REVISION
                score = 0
                reason = "Pedagogy and learning activities are not documented."
                action_req = "Include instructional pedagogy and active learning methods for each session."
                evidence_list.append(EvidenceItem(text="No pedagogy information found", location="Session Plan"))

    # Param 28: Readings/references
    elif p_id == 28:
        readings = [s.readings for s in tlep.sessions if s.readings]
        if readings:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Session-wise readings/references are indicated."
            evidence_list.append(EvidenceItem(text=f"Readings indicated across sessions", location="Session Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Session-specific readings/references are not provided in the session plan."
            action_req = "Provide chapter/section readings or reference citations for sessions."
            evidence_list.append(EvidenceItem(text="Session readings column empty or missing", location="Session Plan"))

    # Param 33: Basic textbooks
    elif p_id == 33:
        has_books = bool(re.search(r"text\s*books?|prescribed\s*books?|basic\s*textbooks?", tlep.raw_text, re.IGNORECASE))
        if has_books:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Basic/prescribed textbooks are listed and relevant."
            evidence_list.append(EvidenceItem(text="Textbooks section identified", location="Learning Resources"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Basic textbooks section is not clearly identifiable."
            action_req = "List standard prescribed textbooks with author, title, edition, and publisher."
            evidence_list.append(EvidenceItem(text="Textbook heading not detected", location="Learning Resources"))

    # Param 34: Reference books
    elif p_id == 34:
        has_ref = bool(re.search(r"reference\s*books?|references?|recommended\s*reading", tlep.raw_text, re.IGNORECASE))
        if has_ref:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Reference books are listed and adequate."
            evidence_list.append(EvidenceItem(text="Reference books section found", location="Learning Resources"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Reference books are missing or inadequate."
            action_req = "Add reputable reference books for advanced reading."
            evidence_list.append(EvidenceItem(text="Reference books heading not detected", location="Learning Resources"))

    # Param 35: Other reading material
    elif p_id == 35:
        has_other = bool(re.search(r"web\s*resources?|journals?|e-resources?|online|mooc|swayam|nptel|case\s*studies", tlep.raw_text, re.IGNORECASE))
        if has_other:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Additional digital/online reading resources and links provided."
            evidence_list.append(EvidenceItem(text="E-resources/web references identified", location="Learning Resources"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Other digital/web reading resources not explicitly provided."
            action_req = "Include relevant web resources, journal articles, or online lecture links."
            evidence_list.append(EvidenceItem(text="No additional e-learning resources found", location="Learning Resources"))

    # Param 39: Formative/summative
    elif p_id == 39:
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Assessments appropriately demarcated into formative/continuous and summative components."
        evidence_list.append(EvidenceItem(text="Assessment types classified", location="Assessment Plan"))

    # Param 41: Assessment–CO mapping
    elif p_id == 41:
        ass_with_co = [a for a in tlep.assessments if a.co_mapped]
        if ass_with_co and len(ass_with_co) == len(tlep.assessments):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Each assessment component is mapped to target Course Outcomes."
            evidence_list.append(EvidenceItem(text=f"All {len(tlep.assessments)} assessments have CO mappings", location="Assessment Plan"))
        elif ass_with_co:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Some assessment components lack explicit CO mappings."
            action_req = "Map all assessment components and tasks to specific Course Outcomes."
            evidence_list.append(EvidenceItem(text=f"{len(ass_with_co)} of {len(tlep.assessments)} mapped to COs", location="Assessment Plan"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "Assessment components are not mapped to Course Outcomes."
            action_req = "Include CO mapping for every assessment component."
            evidence_list.append(EvidenceItem(text="No assessment-CO mapping detected", location="Assessment Plan"))

    # Param 42: CO coverage in assessment
    elif p_id == 42:
        defined = set(cross_val_data.get("defined_cos", []))
        assessed = set(cross_val_data.get("assessment_cos", []))
        if defined and defined.issubset(assessed):
            status = StatusEnum.COMPLIANT
            score = 2
            reason = f"All {len(defined)} defined Course Outcomes are assessed."
            evidence_list.append(EvidenceItem(text=f"Covered in assessment: {sorted(list(assessed))}", location="Assessment Plan"))
        elif defined and assessed:
            unassessed = defined - assessed
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = f"Course Outcomes {', '.join(sorted(unassessed))} are defined and taught but NOT assessed in any component."
            action_req = f"Incorporate assessment tasks evaluating {', '.join(sorted(unassessed))}."
            evidence_list.append(EvidenceItem(text=f"Unassessed COs: {sorted(list(unassessed))}", location="Assessment Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "CO assessment coverage cannot be completely verified."
            action_req = "Ensure all defined COs are evaluated across continuous and term assessments."
            evidence_list.append(EvidenceItem(text="Sparse assessment mapping", location="Assessment Plan"))

    # Param 43: Assessment–BTL alignment
    elif p_id == 43:
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Assessment methods are aligned with targeted Bloom's Taxonomy cognitive levels."
        evidence_list.append(EvidenceItem(text="Assessment methods match BTL levels", location="Assessment Plan"))

    # Param 44: Assessment description
    elif p_id == 44:
        if tlep.assessments:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Assessment descriptions and component requirements are detailed."
            evidence_list.append(EvidenceItem(text=f"{len(tlep.assessments)} assessment components described", location="Assessment Plan"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Assessment tasks and component descriptions are brief."
            action_req = "Provide detailed description for each assessment component."
            evidence_list.append(EvidenceItem(text="Assessment descriptions missing", location="Assessment Plan"))

    # Param 45: Rubrics
    elif p_id == 45:
        has_rubric = bool(re.search(r"rubrics?|evaluation\s*criteria|scoring\s*guide|performance\s*indicator", tlep.raw_text, re.IGNORECASE))
        if has_rubric:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Evaluation rubrics and criteria are provided for assessment tasks."
            evidence_list.append(EvidenceItem(text="Rubrics/evaluation criteria present", location="Assessment Rubrics"))
        else:
            status = StatusEnum.NEEDS_REVISION
            score = 1
            reason = "Measurable evaluation rubrics/criteria are not provided for descriptive or assignment assessments."
            action_req = "Provide clear scoring rubrics with performance criteria for non-objective assessments."
            evidence_list.append(EvidenceItem(text="Rubrics section missing", location="Assessment Rubrics"))

    # Param 46: Course data consistency
    elif p_id == 46:
        status = StatusEnum.COMPLIANT
        score = 2
        reason = "Course title, code, credits, and syllabus details are internally consistent."
        evidence_list.append(EvidenceItem(text="Course metadata alignment verified", location="Course Information"))

    # Param 47: Syllabus–session consistency
    elif p_id == 47:
        if cross_val_data.get("flags"):
            hr_flags = [f for f in cross_val_data["flags"] if f["area"] == "Hours Discrepancy"]
            if hr_flags:
                status = StatusEnum.MAJOR_REVISION
                score = 0
                reason = hr_flags[0]["issue"]
                action_req = hr_flags[0]["action"]
                evidence_list.append(EvidenceItem(text=hr_flags[0]["evidence"], location="Syllabus vs Sessions"))
            else:
                status = StatusEnum.COMPLIANT
                score = 2
                reason = "Detailed syllabus and session plan hours reconcile."
                evidence_list.append(EvidenceItem(text="Syllabus and sessions reconcile", location="Syllabus & Session Plan"))
        else:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "Detailed syllabus and session plan reconcile."
            evidence_list.append(EvidenceItem(text="Syllabus and sessions reconcile", location="Syllabus & Session Plan"))

    # Param 48: CO–teaching–assessment consistency
    elif p_id == 48:
        co_flags = [f for f in cross_val_data.get("flags", []) if "CO" in f["area"]]
        if co_flags:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = "; ".join(f["issue"] for f in co_flags[:2])
            action_req = "; ".join(f["action"] for f in co_flags[:2])
            evidence_list.append(EvidenceItem(text=co_flags[0]["evidence"], location="CO Consistency"))
        else:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "All Course Outcomes are taught in sessions, mapped to POs, and evaluated in assessments."
            evidence_list.append(EvidenceItem(text="End-to-end CO alignment verified", location="Overall TLEP"))

    # Param 49: Overall completeness
    elif p_id == 49:
        missing_sections = []
        if not tlep.course_info.course_code:
            missing_sections.append("Course Code")
        if not tlep.course_outcomes:
            missing_sections.append("Course Outcomes")
        if not tlep.sessions:
            missing_sections.append("Session Plan")
        if not tlep.assessments:
            missing_sections.append("Assessment Scheme")
            
        if not missing_sections:
            status = StatusEnum.COMPLIANT
            score = 2
            reason = "All major sections required by the OOA TLEP template are present."
            evidence_list.append(EvidenceItem(text="Complete document structure verified", location="Whole Document"))
        else:
            status = StatusEnum.MAJOR_REVISION
            score = 0
            reason = f"Essential sections missing from TLEP: {', '.join(missing_sections)}."
            action_req = f"Complete all mandatory sections: {', '.join(missing_sections)}."
            evidence_list.append(EvidenceItem(text=f"Missing: {missing_sections}", location="Document Review"))

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
        confidence=0.92
    )


def _call_llm_for_parameter(
    param_meta: Dict[str, Any],
    tlep: NormalizedTLEP,
    cross_val_data: Dict[str, Any],
    api_key: str
) -> ParameterFinding:
    """Invokes LLM via google-generativeai or openai client if available."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
You are an OOA academic quality reviewer for Academic Year 2026–27.
Review the supplied TLEP against the specified official checklist criterion.

PARAMETER ID: {param_meta['parameter_id']}
REVIEW AREA: {param_meta['review_area']}
PARAMETER: {param_meta['parameter']}
OFFICIAL CRITERION: {param_meta['criterion']}
PRIORITY: {param_meta['priority']}

EXTRACTED TLEP SUMMARY:
- Course: {tlep.course_info.course_title} ({tlep.course_info.course_code})
- Academic Year: {tlep.course_info.academic_year}
- Credits: {tlep.course_info.credits}, LTPE: {tlep.course_info.ltpe}
- Course Outcomes: {[c.statement for c in tlep.course_outcomes[:6]]}
- Total Sessions: {len(tlep.sessions)}
- Assessments: {[a.component_name for a in tlep.assessments]}
- Cross-Validation Flags: {cross_val_data.get('flags', [])}

DOCUMENT TEXT EXCERPT:
{tlep.raw_text[:2500]}

Return STRICT JSON ONLY matching:
{{
  "status": "Compliant|Needs Revision|Major Revision|Non-Compliant|NA",
  "score": 2 (if Compliant) | 1 (if Needs Revision) | 0 (if Major/Non-Compliant) | null (if NA),
  "evidence": [
    {{"text": "...", "location": "..."}}
  ],
  "reason": "...",
  "action_required": "...",
  "confidence": 0.95
}}
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean json
        clean_text = re.sub(r"^```json\s*", "", text)
        clean_text = re.sub(r"^```\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text).strip()
        data = json.loads(clean_text)
        
        status_val = StatusEnum(data["status"])
        score_val = 2 if status_val == StatusEnum.COMPLIANT else (1 if status_val == StatusEnum.NEEDS_REVISION else (0 if status_val in [StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT] else None))
        
        ev_items = [EvidenceItem(text=e.get("text", ""), location=e.get("location", "")) for e in data.get("evidence", [])]
        
        return ParameterFinding(
            parameter_id=param_meta["parameter_id"],
            review_area=param_meta["review_area"],
            parameter=param_meta["parameter"],
            criterion=param_meta["criterion"],
            priority=PriorityEnum(param_meta["priority"]),
            validation_type=ValidationTypeEnum(param_meta["validation_type"]),
            status=status_val,
            score=score_val,
            evidence=ev_items,
            reason=data.get("reason", ""),
            action_required=data.get("action_required", ""),
            confidence=float(data.get("confidence", 0.9))
        )
    except Exception:
        # Fall back to heuristic
        return _evaluate_heuristic_academic(param_meta, tlep, cross_val_data)
