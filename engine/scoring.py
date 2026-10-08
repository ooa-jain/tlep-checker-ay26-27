"""
Scoring and Aggregation Engine
Implements the official OOA scoring rules from AY 2026–27 workbook.
"""

from typing import List, Dict, Any, Tuple
from models.schemas import ParameterFinding, StatusEnum, TLEPReviewResult, NormalizedTLEP


def calculate_scores(findings: List[ParameterFinding]) -> Dict[str, Any]:
    compliant = 0
    needs_revision = 0
    major_revision = 0
    non_compliant = 0
    na_count = 0
    not_reviewed = 0
    total_score = 0
    
    for f in findings:
        if f.status == StatusEnum.COMPLIANT:
            compliant += 1
            total_score += 2
        elif f.status == StatusEnum.NEEDS_REVISION:
            needs_revision += 1
            total_score += 1
        elif f.status == StatusEnum.MAJOR_REVISION:
            major_revision += 1
            total_score += 0
        elif f.status == StatusEnum.NON_COMPLIANT:
            non_compliant += 1
            total_score += 0
        elif f.status == StatusEnum.NA:
            na_count += 1
        elif f.status == StatusEnum.NOT_REVIEWED:
            not_reviewed += 1

    total_params = len(findings)
    applicable = total_params - na_count - not_reviewed
    max_score = applicable * 2
    compliance_pct = round((total_score / max_score * 100.0), 1) if max_score > 0 else 0.0
    
    # Overall status determination
    if major_revision >= 3 or non_compliant >= 2 or compliance_pct < 60.0:
        overall_status = StatusEnum.MAJOR_REVISION
    elif needs_revision > 0 or compliance_pct < 85.0:
        overall_status = StatusEnum.NEEDS_REVISION
    else:
        overall_status = StatusEnum.COMPLIANT
        
    return {
        "total_parameters": total_params,
        "compliant_count": compliant,
        "needs_revision_count": needs_revision,
        "major_revision_count": major_revision,
        "non_compliant_count": non_compliant,
        "na_count": na_count,
        "not_reviewed_count": not_reviewed,
        "applicable_parameters": applicable,
        "score_obtained": total_score,
        "maximum_score": max_score,
        "compliance_percentage": compliance_pct,
        "overall_status": overall_status
    }


def aggregate_area_breakdown(findings: List[ParameterFinding]) -> List[Dict[str, Any]]:
    """Groups findings by review area and calculates area-wise compliance."""
    areas = {}
    for f in findings:
        area = f.review_area
        if area not in areas:
            areas[area] = []
        areas[area].append(f)
        
    summary = []
    for area_name, a_findings in areas.items():
        comp = sum(1 for f in a_findings if f.status == StatusEnum.COMPLIANT)
        rev = sum(1 for f in a_findings if f.status == StatusEnum.NEEDS_REVISION)
        maj = sum(1 for f in a_findings if f.status == StatusEnum.MAJOR_REVISION)
        non = sum(1 for f in a_findings if f.status == StatusEnum.NON_COMPLIANT)
        na = sum(1 for f in a_findings if f.status == StatusEnum.NA)
        
        score = (comp * 2) + (rev * 1)
        app = len(a_findings) - na
        max_s = app * 2
        pct = round((score / max_s * 100.0), 1) if max_s > 0 else 100.0
        
        summary.append({
            "review_area": area_name,
            "total": len(a_findings),
            "compliant": comp,
            "needs_revision": rev,
            "major_revision": maj,
            "non_compliant": non,
            "na": na,
            "score": score,
            "max_score": max_s,
            "compliance_pct": pct
        })
    return summary
