"""Unit tests for Pydantic schemas and HITL gating logic."""

from automed.hitl.review_gate import HITLGate
from automed.models.schemas import (
    ConsultationReport,
    MentalHealthAssessment,
    SymptomAnalysis,
    TreatmentSuggestion,
    UrgencyLevel,
)


def _settings(**overrides):
    from automed.config import Settings

    base = {
        "OPENAI_API_KEY": "test-key",
        "HITL_ENABLED": True,
        "HITL_REQUIRE_APPROVAL_FOR_TREATMENT": True,
        "HITL_REQUIRE_APPROVAL_FOR_MENTAL_HEALTH": True,
    }
    base.update(overrides)
    return Settings(**base)


def test_symptom_analysis_normalizes_symptoms():
    sa = SymptomAnalysis(
        chief_complaint="Headache",
        symptoms=["  Fever ", "Cough"],
        possible_conditions=["viral illness"],
        urgency=UrgencyLevel.ROUTINE,
        rationale="Mild presentation without red flags.",
    )
    assert sa.symptoms == ["fever", "cough"]


def test_consultation_report_format_contains_disclaimer():
    report = ConsultationReport(
        session_id="abc",
        patient_query="I have a mild headache",
        summary="Likely tension headache; hydrate and rest.",
    )
    text = report.format()
    assert "Disclaimer" in text
    assert "abc" in text


def test_hitl_requires_review_for_treatment():
    gate = HITLGate(_settings())
    report = ConsultationReport(
        session_id="s1",
        patient_query="sore throat",
        treatment=TreatmentSuggestion(
            condition_focus="pharyngitis",
            recommended_actions=["salt-water gargle"],
        ),
    )
    assert gate.requires_review(report) is True


def test_hitl_requires_review_for_crisis_mental_health():
    gate = HITLGate(_settings())
    report = ConsultationReport(
        session_id="s2",
        patient_query="I feel hopeless",
        mental_health=MentalHealthAssessment(
            concerns=["hopelessness"],
            risk_level="crisis",
            supportive_message="Please seek immediate help.",
            requires_human_escalation=True,
        ),
    )
    assert gate.requires_review(report) is True


def test_hitl_can_be_disabled():
    gate = HITLGate(_settings(HITL_ENABLED=False))
    report = ConsultationReport(
        session_id="s3",
        patient_query="fever",
        treatment=TreatmentSuggestion(
            condition_focus="fever",
            recommended_actions=["rest"],
        ),
    )
    assert gate.requires_review(report) is False
