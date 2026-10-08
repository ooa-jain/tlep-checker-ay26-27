"""
Plain English Simplifier Engine
Translates academic quality-assurance jargon into actionable, everyday plain English
so department heads and faculty can understand what to fix in seconds.
"""

from typing import Dict, Any, List
from models.schemas import ParameterFinding, StatusEnum, PriorityEnum

PLAIN_ENGLISH_GLOSSARY = {
    "Course title": "Subject Name",
    "Course code": "Subject Code",
    "Semester": "Semester Number",
    "Academic Year": "Academic Year (must be AY 2026–27)",
    "Credits": "Credits Count",
    "L-T-P-E structure": "Weekly Hours Format (Lecture-Tutorial-Practical-Experiential)",
    "CA : ESE": "Internal Marks vs Final Exam Ratio (e.g. 50:50)",
    "Pass / ESE marks": "Minimum Passing Marks",
    "Course objectives": "Overall Course Goals",
    "CO statements": "What Students Will Learn (Course Outcomes)",
    "CO–BTL alignment": "Thinking Level of Outcomes (Bloom's Taxonomy)",
    "CO–syllabus alignment": "Syllabus Content Covers Outcomes",
    "CO–session alignment": "Classes Scheduled to Teach Each Outcome",
    "CO–PO mapping completeness": "How Course Contributes to Program Goals (PO Matrix)",
    "Mapping justification": "Written Reason for Course-to-Program Link",
    "PSO mapping": "Link to Specialization Goals (PSOs)",
    "Approved syllabus match": "Syllabus Matches University Syllabus",
    "Module coverage": "All Units / Modules Included",
    "Module-wise hours": "Hours Given to Each Unit",
    "Module hours total": "Total Unit Hours Match Class Hours",
    "Session numbering": "Class Numbers (1, 2, 3... no skipped numbers)",
    "Topic coverage": "All Topics Taught in Scheduled Classes",
    "Topic–module alignment": "Topics Placed in Correct Units",
    "Session hours": "Total Class Duration",
    "CO mapping in sessions": "Outcomes Linked to Each Class",
    "Pedagogy/activity": "Teaching Method (e.g. Lecture, Discussion, Lab, Quiz)",
    "Mode of delivery": "Delivery Type (In-person, Online, Lab)",
    "Readings/references": "Book Chapters / Readings for Classes",
    "L-T-P-E vs session distribution": "Weekly Class Distribution",
    "Synchronous hours": "Live / In-Class Teaching Hours",
    "Asynchronous hours": "Self-Study / Online Task Hours",
    "Notional hours": "Total Student Workload (~30 hours per credit)",
    "Basic textbooks": "Primary Prescribed Textbooks",
    "Reference books": "Additional Reference Books",
    "Other reading material": "Online Links / Research Articles / MOOCs",
    "Assessment components": "List of Tests, Quizzes & Exams",
    "Assessment weightage": "Marks / Percentages Add Up to 100%",
    "CA : ESE consistency": "Internal vs Semester Exam Marks",
    "Formative/summative": "Continuous Tests vs Final Exam",
    "Frequency": "When Tests are Held (e.g. Week 4, Midterm)",
    "Assessment–CO mapping": "Which Outcomes Each Test Evaluates",
    "CO coverage": "Every Outcome is Tested in at Least One Exam/Quiz",
    "Assessment–BTL alignment": "Questions Match Intended Difficulty",
    "Assessment description": "Clear Instructions for Assignments/Tests",
    "Rubrics": "Marking Criteria / Scoring Rubric",
    "Course data consistency": "Consistency Across Title, Credits & Syllabus",
    "Syllabus–session consistency": "Syllabus Units Match Class Plan",
    "CO–teaching–assessment consistency": "Everything Taught is Tested, Everything Tested Was Taught",
    "Overall completeness": "All Required Sections Filled Out"
}


def simplify_finding(finding: ParameterFinding) -> Dict[str, str]:
    """Converts a technical finding into plain human language."""
    friendly_name = PLAIN_ENGLISH_GLOSSARY.get(finding.parameter, finding.parameter)
    
    # Simplify common reasons
    raw_reason = finding.reason
    raw_action = finding.action_required
    
    plain_what = raw_reason
    plain_action = raw_action
    
    if "AY 2026–27" in raw_reason:
        plain_what = "Academic year is not set to AY 2026–27."
        plain_action = "Change the academic year in the title to 'AY 2026–27'."
    elif "not represented in any assessment" in raw_reason:
        plain_what = f"An outcome ({raw_reason.split('Outcomes')[-1].split('are')[0].strip()}) is taught in class but never tested in quizzes or exams."
        plain_action = "Add at least one question or assignment task testing this outcome."
    elif "weightages sum to" in raw_reason:
        plain_what = "The assessment marks do not add up to 100%."
        plain_action = "Adjust component percentages so the total equals exactly 100%."
    elif "sequentially numbered" in raw_reason or "gaps" in raw_reason.lower():
        plain_what = "Some class session numbers are skipped or out of order."
        plain_action = "Renumber class sessions consecutively (1, 2, 3...) with no missing numbers."
    elif "rubrics" in finding.parameter.lower() and finding.status != StatusEnum.COMPLIANT:
        plain_what = "Assignments or projects don't have a grading guide (rubric)."
        plain_action = "Add a simple table explaining how assignment marks are awarded."

    return {
        "parameter_id": str(finding.parameter_id),
        "friendly_name": friendly_name,
        "academic_name": finding.parameter,
        "section": finding.review_area,
        "status": finding.status.value,
        "priority": finding.priority.value,
        "what_is_wrong": plain_what,
        "what_to_do": plain_action or "Review and confirm this section.",
        "where": finding.evidence[0].location if finding.evidence else "In document"
    }
