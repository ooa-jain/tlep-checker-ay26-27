"""
Master TLEP Compliance Reviewer
Coordinates the complete review pipeline across all 49 parameters.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

from models.schemas import (
    NormalizedTLEP, TLEPReviewResult, ParameterFinding,
    StatusEnum, PriorityEnum, ValidationTypeEnum, CopoReviewRow
)
from extractors.base import extract_tlep_document
from engine.checklist_engine import get_parameters
from engine.rule_engine import evaluate_deterministic_parameter
from engine.ai_engine import evaluate_academic_parameter
from engine.cross_validation import perform_cross_validation
from engine.hours_validation import validate_learning_hours
from engine.scoring import calculate_scores


def review_tlep_document(
    file_path: str,
    approved_reference: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> TLEPReviewResult:
    """
    Complete end-to-end audit of a single TLEP document against all 49 official parameters.
    """
    # 1. Document Extraction
    tlep = extract_tlep_document(file_path)
    file_name = os.path.basename(file_path)
    
    # 2. Relational Cross-Validation Graph
    cross_val_data = perform_cross_validation(tlep)
    
    # 3. Parameter-by-Parameter Review
    params_meta = get_parameters()
    findings: List[ParameterFinding] = []
    
    for p_meta in params_meta:
        val_type = p_meta.get("validation_type", "hybrid")
        if val_type == "deterministic":
            finding = evaluate_deterministic_parameter(p_meta, tlep, cross_val_data, approved_reference)
        else:
            finding = evaluate_academic_parameter(p_meta, tlep, cross_val_data, api_key)
        findings.append(finding)
        
    # 4. Hours Validation Table
    hours_rows = validate_learning_hours(tlep, approved_reference)
    
    # 5. CO-PO Review Table
    copo_rows: List[CopoReviewRow] = []
    for mapping in tlep.copo_mappings:
        co_item = next((c for c in tlep.course_outcomes if c.id == mapping.co_id), None)
        copo_rows.append(CopoReviewRow(
            co_id=mapping.co_id,
            co_statement=co_item.statement if co_item else "",
            btl=co_item.btl if (co_item and co_item.btl) else "-",
            po_pso=mapping.target_id,
            mapping_level=str(mapping.level) if mapping.level is not None else "-",
            justification=mapping.justification or "Standard curriculum correlation",
            status=StatusEnum.COMPLIANT,
            remarks="Correlation level recorded"
        ))
        
    # 6. Scoring and Aggregation
    scores = calculate_scores(findings)
    
    # 7. Compile Critical Issues
    critical_issues = []
    for f in findings:
        if f.status in [StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT] and f.priority == PriorityEnum.HIGH:
            critical_issues.append({
                "parameter_id": str(f.parameter_id),
                "review_area": f.review_area,
                "parameter": f.parameter,
                "issue": f.reason,
                "action": f.action_required,
                "evidence": f.evidence[0].text if f.evidence else ""
            })
            
    # Also add relational cross-validation flags to critical issues
    for flag in cross_val_data.get("flags", []):
        if flag["severity"] in ["MAJOR", "HIGH"]:
            critical_issues.append({
                "parameter_id": "-",
                "review_area": flag["area"],
                "parameter": flag["area"],
                "issue": flag["issue"],
                "action": flag["action"],
                "evidence": flag["evidence"]
            })
            
    # 8. Department Action Plan
    action_plan = []
    for f in findings:
        if f.status in [StatusEnum.NEEDS_REVISION, StatusEnum.MAJOR_REVISION, StatusEnum.NON_COMPLIANT]:
            action_plan.append({
                "priority": f.priority.value.upper(),
                "section": f.review_area,
                "parameter": f.parameter,
                "issue": f.reason,
                "evidence": f.evidence[0].text if f.evidence else "-",
                "action": f.action_required,
                "status": f.status.value
            })
            
    # Sort action plan by priority (HIGH first)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    action_plan.sort(key=lambda x: priority_order.get(x["priority"], 3))

    review_id = str(uuid.uuid4())[:8]
    review_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return TLEPReviewResult(
        review_id=review_id,
        file_name=file_name,
        review_date=review_date,
        checklist_version="AY 2026–27",
        model_used="Hybrid (Rule Engine + AI Academic Review)",
        total_parameters=scores["total_parameters"],
        compliant_count=scores["compliant_count"],
        needs_revision_count=scores["needs_revision_count"],
        major_revision_count=scores["major_revision_count"],
        non_compliant_count=scores["non_compliant_count"],
        na_count=scores["na_count"],
        not_reviewed_count=scores["not_reviewed_count"],
        applicable_parameters=scores["applicable_parameters"],
        score_obtained=scores["score_obtained"],
        maximum_score=scores["maximum_score"],
        compliance_percentage=scores["compliance_percentage"],
        overall_status=scores["overall_status"],
        parameter_findings=findings,
        hours_validation_rows=hours_rows,
        copo_review_rows=copo_rows,
        critical_issues=critical_issues,
        department_action_plan=action_plan,
        normalized_tlep=tlep
    )
