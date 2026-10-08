"""
Canonical Pydantic Schemas for OOA TLEP Compliance Review System
AY 2026–27
"""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class StatusEnum(str, Enum):
    COMPLIANT = "Compliant"
    NEEDS_REVISION = "Needs Revision"
    MAJOR_REVISION = "Major Revision"
    NON_COMPLIANT = "Non-Compliant"
    NA = "NA"
    NOT_REVIEWED = "Not Reviewed"


class PriorityEnum(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ValidationTypeEnum(str, Enum):
    DETERMINISTIC = "deterministic"
    AI = "ai"
    HYBRID = "hybrid"


# --- Canonical Internal TLEP Representation ---

class CourseInfo(BaseModel):
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    credits: Optional[float] = None
    ltpe: Optional[str] = None  # e.g., "3-0-0-0" or "3:0:2:0"
    ca_ese: Optional[str] = None  # e.g., "50:50" or "40:60"
    pass_marks: Optional[str] = None
    ese_marks: Optional[str] = None
    department: Optional[str] = None
    programme: Optional[str] = None
    faculty_name: Optional[str] = None


class CourseObjective(BaseModel):
    id: Optional[str] = None
    text: str


class CourseOutcome(BaseModel):
    id: str  # e.g., "CO1"
    statement: str
    btl: Optional[str] = None  # e.g., "K3", "Level 3 - Apply", "Apply"
    raw_location: Optional[str] = None


class CopoMappingItem(BaseModel):
    co_id: str
    target_id: str  # e.g. "PO1", "PSO1"
    level: Optional[Union[int, str]] = None  # 1, 2, 3, or "-"
    justification: Optional[str] = None


class ModuleItem(BaseModel):
    module_number: Optional[Union[int, str]] = None
    module_title: Optional[str] = None
    allocated_hours: Optional[float] = None
    topics: List[str] = Field(default_factory=list)


class SessionItem(BaseModel):
    session_number: Optional[int] = None
    module: Optional[str] = None
    topic: Optional[str] = None
    hours: Optional[float] = 1.0
    co_mapped: List[str] = Field(default_factory=list)
    pedagogy: Optional[str] = None
    mode_of_delivery: Optional[str] = None  # L/T/P/E, Sync/Async
    readings: Optional[str] = None
    source_location: Optional[str] = None


class AssessmentComponent(BaseModel):
    component_name: str
    weightage: Optional[float] = None
    ca_or_ese: Optional[str] = None  # CA or ESE
    type_formative_summative: Optional[str] = None
    frequency: Optional[str] = None
    co_mapped: List[str] = Field(default_factory=list)
    btl: Optional[str] = None
    description: Optional[str] = None
    rubric_available: Optional[bool] = None


class LearningResource(BaseModel):
    resource_type: str  # "Textbook", "Reference", "Other"
    title_author: str


class LearningHoursSummary(BaseModel):
    approved_credits: Optional[float] = None
    tlep_credits: Optional[float] = None
    approved_ltpe: Optional[str] = None
    tlep_ltpe: Optional[str] = None
    lecture_hours: Optional[float] = None
    tutorial_hours: Optional[float] = None
    practical_hours: Optional[float] = None
    exp_sync_hours: Optional[float] = None
    exp_async_hours: Optional[float] = None
    total_sync_hours: Optional[float] = None
    total_async_hours: Optional[float] = None
    total_notional_hours: Optional[float] = None
    total_module_hours: Optional[float] = None
    total_session_hours: Optional[float] = None


class NormalizedTLEP(BaseModel):
    source_file: str
    file_type: str
    raw_text: str = ""
    raw_tables: List[Dict[str, Any]] = Field(default_factory=list)
    course_info: CourseInfo = Field(default_factory=CourseInfo)
    course_objectives: List[CourseObjective] = Field(default_factory=list)
    course_outcomes: List[CourseOutcome] = Field(default_factory=list)
    copo_mappings: List[CopoMappingItem] = Field(default_factory=list)
    modules: List[ModuleItem] = Field(default_factory=list)
    sessions: List[SessionItem] = Field(default_factory=list)
    assessments: List[AssessmentComponent] = Field(default_factory=list)
    resources: List[LearningResource] = Field(default_factory=list)
    hours_summary: LearningHoursSummary = Field(default_factory=LearningHoursSummary)
    parsing_notes: List[str] = Field(default_factory=list)


# --- Review Findings & Report Models ---

class EvidenceItem(BaseModel):
    text: str
    location: str


class ParameterFinding(BaseModel):
    parameter_id: int
    review_area: str
    parameter: str
    criterion: str
    priority: PriorityEnum
    validation_type: ValidationTypeEnum
    status: StatusEnum
    score: Optional[int] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reason: str = ""
    action_required: str = ""
    confidence: float = 1.0


class HoursValidationRow(BaseModel):
    parameter: str
    approved: Optional[Union[float, str]] = None
    tlep: Optional[Union[float, str]] = None
    variance: Optional[Union[float, str]] = None
    status: StatusEnum = StatusEnum.COMPLIANT
    remarks: str = ""
    evidence: str = ""
    action_required: str = ""


class CopoReviewRow(BaseModel):
    co_id: str
    co_statement: str
    btl: str
    po_pso: str
    mapping_level: str
    justification: str
    status: StatusEnum = StatusEnum.COMPLIANT
    remarks: str = ""


class TLEPReviewResult(BaseModel):
    review_id: str
    file_name: str
    review_date: str
    checklist_version: str = "AY 2026–27"
    model_used: str = "Hybrid (Rule Engine + AI)"
    total_parameters: int = 49
    compliant_count: int = 0
    needs_revision_count: int = 0
    major_revision_count: int = 0
    non_compliant_count: int = 0
    na_count: int = 0
    not_reviewed_count: int = 0
    applicable_parameters: int = 49
    score_obtained: int = 0
    maximum_score: int = 98
    compliance_percentage: float = 0.0
    overall_status: StatusEnum = StatusEnum.COMPLIANT
    parameter_findings: List[ParameterFinding] = Field(default_factory=list)
    hours_validation_rows: List[HoursValidationRow] = Field(default_factory=list)
    copo_review_rows: List[CopoReviewRow] = Field(default_factory=list)
    critical_issues: List[Dict[str, str]] = Field(default_factory=list)
    department_action_plan: List[Dict[str, str]] = Field(default_factory=list)
    normalized_tlep: Optional[NormalizedTLEP] = None
