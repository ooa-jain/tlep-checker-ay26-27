"""
Cross-Validation Engine
Builds and verifies the relational consistency graph:
COURSE -> MODULE -> TOPIC -> SESSION -> CO -> BTL -> PO/PSO -> ASSESSMENT -> RUBRIC
"""

from typing import List, Dict, Any, Set
from models.schemas import NormalizedTLEP, StatusEnum


def perform_cross_validation(tlep: NormalizedTLEP) -> Dict[str, Any]:
    """
    Performs cross-entity relational analysis and returns a dictionary of flags,
    inconsistencies, and relationship graph summaries.
    """
    flags = []
    
    # 1. CO Set Analysis
    defined_cos: Set[str] = {co.id.upper() for co in tlep.course_outcomes}
    
    # Sessions CO usage
    session_cos: Set[str] = set()
    for s in tlep.sessions:
        for co in s.co_mapped:
            session_cos.add(co.upper())
            
    # Assessment CO usage
    assessment_cos: Set[str] = set()
    for a in tlep.assessments:
        for co in a.co_mapped:
            assessment_cos.add(co.upper())
            
    # PO Mapping CO usage
    mapped_cos_in_copo: Set[str] = {m.co_id.upper() for m in tlep.copo_mappings}

    # Cross check 1: Defined COs taught in sessions?
    if defined_cos:
        untaught_cos = defined_cos - session_cos
        if untaught_cos:
            flags.append({
                "severity": "MAJOR",
                "area": "CO–Session Alignment",
                "issue": f"Outcomes {', '.join(sorted(untaught_cos))} are defined in Course Outcomes but have no sessions mapped in the session plan.",
                "evidence": f"Defined: {sorted(list(defined_cos))}, Mapped in Sessions: {sorted(list(session_cos))}",
                "action": f"Map sessions to cover {', '.join(sorted(untaught_cos))}."
            })
            
        # Cross check 2: Defined COs assessed in assessment plan?
        unassessed_cos = defined_cos - assessment_cos
        if unassessed_cos and tlep.assessments:
            flags.append({
                "severity": "MAJOR",
                "area": "CO–Assessment Alignment",
                "issue": f"Outcomes {', '.join(sorted(unassessed_cos))} are defined but are NOT represented in any assessment component.",
                "evidence": f"Defined: {sorted(list(defined_cos))}, Assessed: {sorted(list(assessment_cos))}",
                "action": f"Add an assessment component covering {', '.join(sorted(unassessed_cos))}."
            })

    # Cross check 3: Phantom COs in assessments (Assessed but not in session plan or defined COs)
    if assessment_cos and defined_cos:
        phantom_assessment_cos = assessment_cos - defined_cos
        if phantom_assessment_cos:
            flags.append({
                "severity": "HIGH",
                "area": "Assessment Inconsistency",
                "issue": f"Assessment maps to {', '.join(sorted(phantom_assessment_cos))} which are not defined in Course Outcomes.",
                "evidence": f"Phantom COs in assessment: {sorted(list(phantom_assessment_cos))}",
                "action": "Ensure assessment only targets approved defined COs."
            })

    # Cross check 4: Module Hours vs Session Hours
    total_mod_hours = sum(m.allocated_hours for m in tlep.modules if m.allocated_hours)
    total_sess_hours = sum(s.hours or 1.0 for s in tlep.sessions)
    if total_mod_hours > 0 and total_sess_hours > 0:
        if abs(total_mod_hours - total_sess_hours) > 0.5:
            flags.append({
                "severity": "HIGH",
                "area": "Hours Discrepancy",
                "issue": f"Module hours ({total_mod_hours}h) do not match Session Plan hours ({total_sess_hours}h). Variance: {abs(total_mod_hours - total_sess_hours)}h.",
                "evidence": f"Module Hours = {total_mod_hours}, Session Hours = {total_sess_hours}",
                "action": "Reconcile module hour allocation with the session plan total hours."
            })

    # Cross check 5: Assessment weightage total
    ass_weights = [a.weightage for a in tlep.assessments if a.weightage is not None]
    if ass_weights:
        total_weight = sum(ass_weights)
        if abs(total_weight - 100.0) > 1.0 and abs(total_weight - 50.0) > 1.0:
            flags.append({
                "severity": "HIGH",
                "area": "Assessment Weightage",
                "issue": f"Assessment weightages total {total_weight}% instead of 100% (or 50% for CA).",
                "evidence": f"Components sum to {total_weight}%",
                "action": "Adjust assessment component weightages so they total exactly 100% (or approved CA weight)."
            })

    # Cross check 6: Session Numbering continuity
    if tlep.sessions:
        s_nums = [s.session_number for s in tlep.sessions if s.session_number is not None]
        if s_nums:
            sorted_nums = sorted(s_nums)
            expected_range = list(range(sorted_nums[0], sorted_nums[-1] + 1))
            missing_sessions = set(expected_range) - set(sorted_nums)
            if missing_sessions:
                flags.append({
                    "severity": "MEDIUM",
                    "area": "Session Numbering",
                    "issue": f"Gaps detected in session numbering: Missing sessions {sorted(list(missing_sessions))[:5]}...",
                    "evidence": f"Found sessions from {sorted_nums[0]} to {sorted_nums[-1]} with {len(missing_sessions)} gaps",
                    "action": "Renumber sessions consecutively without unexplained gaps."
                })

    return {
        "defined_cos": sorted(list(defined_cos)),
        "session_cos": sorted(list(session_cos)),
        "assessment_cos": sorted(list(assessment_cos)),
        "copo_cos": sorted(list(mapped_cos_in_copo)),
        "flags": flags
    }
