"""Pydantic schemas for structured agent outputs.

Every specialized agent emits a typed payload so downstream agents,
HITL gates, and the final consultation report remain schema-valid.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class UrgencyLevel(str, Enum):
    """Clinical urgency classification."""

    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"
    SELF_CARE = "self_care"


class ConfidenceLevel(str, Enum):
    """Model confidence for a recommendation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SymptomAnalysis(BaseModel):
    """Structured output from the Symptom Analyzer agent."""

    chief_complaint: str = Field(..., description="Primary symptom or concern")
    symptoms: List[str] = Field(default_factory=list, min_length=1)
    possible_conditions: List[str] = Field(default_factory=list)
    urgency: UrgencyLevel
    red_flags: List[str] = Field(
        default_factory=list,
        description="Warning signs requiring immediate care",
    )
    clarifying_questions: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    rationale: str = Field(..., description="Clinical reasoning summary")

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, value: List[str]) -> List[str]:
        return [s.strip().lower() for s in value if s.strip()]


class TreatmentSuggestion(BaseModel):
    """Structured output from the Treatment Advisor agent."""

    condition_focus: str
    recommended_actions: List[str] = Field(default_factory=list, min_length=1)
    otc_options: List[str] = Field(default_factory=list)
    lifestyle_advice: List[str] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    when_to_seek_care: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    requires_clinician_review: bool = True
    disclaimer: str = Field(
        default=(
            "This is not a medical diagnosis. Consult a licensed clinician "
            "before starting or stopping any treatment."
        ),
    )


class MedicalDataInsight(BaseModel):
    """Structured output from the Medical Data Fetcher agent."""

    query: str
    sources: List[str] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    drug_interactions: List[str] = Field(default_factory=list)
    guidelines_referenced: List[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    is_mock_data: bool = False


class FollowUpPlan(BaseModel):
    """Structured output from the Follow-Up Care agent."""

    monitoring_checklist: List[str] = Field(default_factory=list)
    follow_up_interval_days: int = Field(ge=1, le=365, default=7)
    escalation_triggers: List[str] = Field(default_factory=list)
    patient_education: List[str] = Field(default_factory=list)
    next_check_in_prompt: str


class MentalHealthAssessment(BaseModel):
    """Structured output from the Mental Health Care agent."""

    concerns: List[str] = Field(default_factory=list)
    risk_level: Literal["low", "moderate", "high", "crisis"] = "low"
    coping_strategies: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    crisis_hotline_notice: Optional[str] = None
    requires_human_escalation: bool = False
    supportive_message: str


class HITLDecision(BaseModel):
    """Human reviewer decision recorded by the HITL gate."""

    approved: bool
    reviewer_notes: str = ""
    modified_fields: List[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    reviewer_id: str = "human_reviewer"


class ConsultationReport(BaseModel):
    """Final synthesis report produced after multi-agent orchestration."""

    session_id: str
    patient_query: str
    symptom_analysis: Optional[SymptomAnalysis] = None
    treatment: Optional[TreatmentSuggestion] = None
    medical_data: Optional[MedicalDataInsight] = None
    follow_up: Optional[FollowUpPlan] = None
    mental_health: Optional[MentalHealthAssessment] = None
    hitl: Optional[HITLDecision] = None
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def format(self) -> str:
        """Human-readable consultation summary for chat UIs."""
        lines = [
            f"# AutoMed Consultation Report",
            f"**Session:** `{self.session_id}`",
            f"**Query:** {self.patient_query}",
            "",
            "## Summary",
            self.summary or "_Pending synthesis_",
        ]
        if self.symptom_analysis:
            sa = self.symptom_analysis
            lines += [
                "",
                "## Symptom Analysis",
                f"- **Chief complaint:** {sa.chief_complaint}",
                f"- **Urgency:** {sa.urgency.value}",
                f"- **Possible conditions:** {', '.join(sa.possible_conditions) or 'n/a'}",
                f"- **Red flags:** {', '.join(sa.red_flags) or 'none identified'}",
            ]
        if self.treatment:
            tx = self.treatment
            lines += [
                "",
                "## Treatment Guidance",
                *[f"- {a}" for a in tx.recommended_actions],
                f"- **Clinician review required:** {tx.requires_clinician_review}",
                f"- _{tx.disclaimer}_",
            ]
        if self.mental_health:
            mh = self.mental_health
            lines += [
                "",
                "## Mental Health Support",
                f"- **Risk level:** {mh.risk_level}",
                f"- {mh.supportive_message}",
            ]
        if self.hitl:
            lines += [
                "",
                "## HITL Review",
                f"- **Approved:** {self.hitl.approved}",
                f"- **Notes:** {self.hitl.reviewer_notes or '—'}",
            ]
        lines += [
            "",
            "---",
            "*Disclaimer: AutoMed is an educational multi-agent system. "
            "It is not a substitute for professional medical advice, diagnosis, or treatment.*",
        ]
        return "\n".join(lines)
