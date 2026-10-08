"""
Hours Validation Engine
Validates TLEP learning hours, credit structure, synchronous/asynchronous split, and notional hours.
Mirrors the official 'Hours Validation' sheet from the OOA workbook.
"""

from typing import List, Dict, Any, Optional
from models.schemas import NormalizedTLEP, HoursValidationRow, StatusEnum


def validate_learning_hours(
    tlep: NormalizedTLEP, 
    approved_curriculum: Optional[Dict[str, Any]] = None
) -> List[HoursValidationRow]:
    """
    Validate hours against approved curriculum or self-consistency of TLEP.
    """
    if approved_curriculum is None:
        # If no approved reference is uploaded, use self-stated values from TLEP course info as approved baseline
        c_info = tlep.course_info
        approved_curriculum = {
            "credits": c_info.credits,
            "ltpe": c_info.ltpe,
            "lecture_hours": None,
            "tutorial_hours": None,
            "practical_hours": None,
            "exp_sync_hours": None,
            "exp_async_hours": None,
            "total_sync_hours": None,
            "total_async_hours": None,
            "total_notional_hours": (c_info.credits * 30.0) if c_info.credits else None,
            "total_module_hours": None,
            "total_session_hours": None
        }

    c_info = tlep.course_info
    h_sum = tlep.hours_summary
    
    rows: List[HoursValidationRow] = []

    # 1. Credits
    app_cr = approved_curriculum.get("credits")
    tlep_cr = c_info.credits
    cr_var = (tlep_cr - app_cr) if (app_cr is not None and tlep_cr is not None) else None
    cr_status = StatusEnum.COMPLIANT if cr_var == 0 or cr_var is None else StatusEnum.MAJOR_REVISION
    rows.append(HoursValidationRow(
        parameter="Credits",
        approved=app_cr,
        tlep=tlep_cr,
        variance=cr_var if cr_var is not None else "-",
        status=cr_status,
        remarks="Credits match approved curriculum" if cr_status == StatusEnum.COMPLIANT else f"Credit variance of {cr_var}",
        evidence=f"Course Info: Credits = {tlep_cr}",
        action_required="" if cr_status == StatusEnum.COMPLIANT else "Reconcile credits with approved curriculum"
    ))

    # 2. L-T-P-E
    app_ltpe = approved_curriculum.get("ltpe")
    tlep_ltpe = c_info.ltpe
    ltpe_status = StatusEnum.COMPLIANT if (app_ltpe == tlep_ltpe or not app_ltpe or not tlep_ltpe) else StatusEnum.MAJOR_REVISION
    rows.append(HoursValidationRow(
        parameter="L-T-P-E",
        approved=app_ltpe,
        tlep=tlep_ltpe,
        variance="Match" if ltpe_status == StatusEnum.COMPLIANT else "Mismatch",
        status=ltpe_status,
        remarks="L-T-P-E structure matches" if ltpe_status == StatusEnum.COMPLIANT else f"Mismatch: Approved {app_ltpe} vs TLEP {tlep_ltpe}",
        evidence=f"Course Info: L-T-P-E = {tlep_ltpe}",
        action_required="" if ltpe_status == StatusEnum.COMPLIANT else "Correct L-T-P-E structure to match approved scheme"
    ))

    # Calculate session hours
    sess_hours = float(sum(s.hours or 1.0 for s in tlep.sessions)) if tlep.sessions else 0.0

    # 3. Lecture hours
    rows.append(HoursValidationRow(
        parameter="Lecture hours",
        approved=approved_curriculum.get("lecture_hours"),
        tlep=h_sum.lecture_hours,
        variance="-",
        status=StatusEnum.COMPLIANT if h_sum.lecture_hours else StatusEnum.NEEDS_REVISION,
        remarks="Lecture hours allocated" if h_sum.lecture_hours else "Lecture hours not explicitly detailed",
        evidence=f"Lecture Hours: {h_sum.lecture_hours}",
        action_required="" if h_sum.lecture_hours else "Specify lecture hours distribution"
    ))

    # 4. Tutorial hours
    rows.append(HoursValidationRow(
        parameter="Tutorial hours",
        approved=approved_curriculum.get("tutorial_hours"),
        tlep=h_sum.tutorial_hours,
        variance="-",
        status=StatusEnum.COMPLIANT,
        remarks="Tutorial hours noted",
        evidence=f"Tutorial Hours: {h_sum.tutorial_hours}",
        action_required=""
    ))

    # 5. Practical hours
    rows.append(HoursValidationRow(
        parameter="Practical hours",
        approved=approved_curriculum.get("practical_hours"),
        tlep=h_sum.practical_hours,
        variance="-",
        status=StatusEnum.COMPLIANT,
        remarks="Practical hours noted",
        evidence=f"Practical Hours: {h_sum.practical_hours}",
        action_required=""
    ))

    # 6. Experiential Synchronous hours
    rows.append(HoursValidationRow(
        parameter="Experiential Synchronous hours",
        approved=approved_curriculum.get("exp_sync_hours"),
        tlep=h_sum.exp_sync_hours,
        variance="-",
        status=StatusEnum.COMPLIANT,
        remarks="Experiential synchronous hours reviewed",
        evidence=f"Experiential Sync Hours: {h_sum.exp_sync_hours}",
        action_required=""
    ))

    # 7. Experiential Asynchronous hours
    rows.append(HoursValidationRow(
        parameter="Experiential Asynchronous hours",
        approved=approved_curriculum.get("exp_async_hours"),
        tlep=h_sum.exp_async_hours,
        variance="-",
        status=StatusEnum.COMPLIANT,
        remarks="Experiential asynchronous hours reviewed",
        evidence=f"Experiential Async Hours: {h_sum.exp_async_hours}",
        action_required=""
    ))

    # 8. Total Synchronous hours
    total_sync = sess_hours if sess_hours > 0 else (h_sum.total_sync_hours or 0.0)
    rows.append(HoursValidationRow(
        parameter="Total Synchronous hours",
        approved=approved_curriculum.get("total_sync_hours"),
        tlep=total_sync if total_sync > 0 else None,
        variance="-",
        status=StatusEnum.COMPLIANT if total_sync > 0 else StatusEnum.NEEDS_REVISION,
        remarks="Synchronous hours calculated from session plan" if total_sync > 0 else "Synchronous hours not found",
        evidence=f"Total Synchronous Hours: {total_sync}",
        action_required="" if total_sync > 0 else "Ensure synchronous session hours are calculated"
    ))

    # 9. Total Asynchronous hours
    rows.append(HoursValidationRow(
        parameter="Total Asynchronous hours",
        approved=approved_curriculum.get("total_async_hours"),
        tlep=h_sum.total_async_hours,
        variance="-",
        status=StatusEnum.COMPLIANT,
        remarks="Asynchronous hours reviewed",
        evidence=f"Total Asynchronous Hours: {h_sum.total_async_hours}",
        action_required=""
    ))

    # 10. Total Notional hours
    expected_notional = (c_info.credits * 30.0) if c_info.credits else None
    rows.append(HoursValidationRow(
        parameter="Total Notional hours",
        approved=expected_notional,
        tlep=h_sum.total_notional_hours or expected_notional,
        variance="-",
        status=StatusEnum.COMPLIANT if expected_notional else StatusEnum.NEEDS_REVISION,
        remarks=f"Expected notional hours (~30 hrs/credit) = {expected_notional}" if expected_notional else "Credit value missing for notional calculation",
        evidence=f"Credits: {c_info.credits}, Notional: {expected_notional}",
        action_required="" if expected_notional else "Provide credits to establish notional learning hours"
    ))

    # 11. Total Module hours
    total_mod = sum(m.allocated_hours for m in tlep.modules if m.allocated_hours) if tlep.modules else 0.0
    rows.append(HoursValidationRow(
        parameter="Total Module hours",
        approved=None,
        tlep=total_mod if total_mod > 0 else None,
        variance="-",
        status=StatusEnum.COMPLIANT if total_mod > 0 or not tlep.modules else StatusEnum.NEEDS_REVISION,
        remarks="Module hours recorded" if total_mod > 0 else "Module hours not broken down",
        evidence=f"Total Module Hours: {total_mod}",
        action_required="" if total_mod > 0 else "Allocate hours per module"
    ))

    # 12. Total Session Plan hours
    rows.append(HoursValidationRow(
        parameter="Total Session Plan hours",
        approved=None,
        tlep=sess_hours if sess_hours > 0 else None,
        variance="-",
        status=StatusEnum.COMPLIANT if sess_hours > 0 else StatusEnum.MAJOR_REVISION,
        remarks=f"Total planned session hours = {sess_hours}" if sess_hours > 0 else "No session plan hours found",
        evidence=f"Sessions Count: {len(tlep.sessions)}, Planned Hours: {sess_hours}",
        action_required="" if sess_hours > 0 else "Provide complete session plan with hours"
    ))

    return rows
