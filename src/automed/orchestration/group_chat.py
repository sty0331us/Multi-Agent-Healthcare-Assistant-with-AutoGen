"""GroupChat orchestration for AutoMed specialist agents."""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import structlog
from autogen import GroupChat, GroupChatManager

from automed.agents.factory import (
    create_coordinator,
    create_follow_up_agent,
    create_medical_data_fetcher,
    create_mental_health_agent,
    create_symptom_analyzer,
    create_treatment_advisor,
    create_user_proxy,
)
from automed.config import Settings
from automed.hitl.review_gate import HITLGate
from automed.models.schemas import (
    ConsultationReport,
    FollowUpPlan,
    MedicalDataInsight,
    MentalHealthAssessment,
    SymptomAnalysis,
    TreatmentSuggestion,
)

logger = structlog.get_logger(__name__)


def _try_parse(model: type, content: Optional[str]) -> Optional[Any]:
    if not content:
        return None
    text = content.strip()
    # Strip markdown fences if the model wrapped JSON.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return model.model_validate_json(text)
    except Exception:
        try:
            return model.model_validate(json.loads(text))
        except Exception:
            return None


def _speaker_selection(last_speaker, groupchat: GroupChat):  # noqa: ANN001
    """Lightweight round-robin with coordinator closing the loop."""
    order = [
        "SymptomAnalyzer",
        "MedicalDataFetcher",
        "TreatmentAdvisor",
        "MentalHealthCare",
        "FollowUpCare",
        "CareCoordinator",
    ]
    names = [a.name for a in groupchat.agents]
    if last_speaker is None:
        return next(a for a in groupchat.agents if a.name == "SymptomAnalyzer")

    try:
        idx = order.index(last_speaker.name)
    except ValueError:
        return next(a for a in groupchat.agents if a.name == "CareCoordinator")

    for name in order[idx + 1 :]:
        if name in names:
            return next(a for a in groupchat.agents if a.name == name)
    return next(a for a in groupchat.agents if a.name == "CareCoordinator")


class AutoMedOrchestrator:
    """Runs the multi-agent consultation pipeline end-to-end."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.hitl = HITLGate(settings)

        common = dict(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            api_base=settings.openai_api_base,
            temperature=settings.openai_temperature,
        )

        self.symptom_analyzer = create_symptom_analyzer(**common)
        self.treatment_advisor = create_treatment_advisor(**common)
        self.medical_data_fetcher = create_medical_data_fetcher(**common)
        self.follow_up = create_follow_up_agent(**common)
        self.mental_health = create_mental_health_agent(**common)
        self.coordinator = create_coordinator(**common)
        self.user_proxy = create_user_proxy()

        self.agents = [
            self.user_proxy,
            self.symptom_analyzer,
            self.medical_data_fetcher,
            self.treatment_advisor,
            self.mental_health,
            self.follow_up,
            self.coordinator,
        ]

    def run(self, patient_query: str) -> ConsultationReport:
        """Execute GroupChat collaboration and apply the HITL gate."""
        session_id = str(uuid.uuid4())
        logger.info("consultation_started", session_id=session_id)

        groupchat = GroupChat(
            agents=self.agents,
            messages=[],
            max_round=self.settings.max_group_chat_rounds,
            speaker_selection_method=_speaker_selection,
        )
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self.coordinator.llm_config,
            system_message=(
                "Manage AutoMed specialists. Ensure SymptomAnalyzer speaks first, "
                "then MedicalDataFetcher, TreatmentAdvisor, MentalHealthCare, "
                "FollowUpCare, and finally CareCoordinator who terminates."
            ),
        )

        kickoff = (
            "Patient consultation request:\n"
            f"{patient_query}\n\n"
            "Collaborate as a virtual care team. Each specialist must contribute "
            "its structured output. CareCoordinator synthesizes and TERMINates."
        )

        self.user_proxy.initiate_chat(
            manager,
            message=kickoff,
            clear_history=True,
        )

        report = ConsultationReport(
            session_id=session_id,
            patient_query=patient_query,
        )

        for message in groupchat.messages:
            name = message.get("name") or message.get("role")
            content = message.get("content")
            if name == "SymptomAnalyzer" and report.symptom_analysis is None:
                report.symptom_analysis = _try_parse(SymptomAnalysis, content)
            elif name == "TreatmentAdvisor" and report.treatment is None:
                report.treatment = _try_parse(TreatmentSuggestion, content)
            elif name == "MedicalDataFetcher" and report.medical_data is None:
                report.medical_data = _try_parse(MedicalDataInsight, content)
            elif name == "FollowUpCare" and report.follow_up is None:
                report.follow_up = _try_parse(FollowUpPlan, content)
            elif name == "MentalHealthCare" and report.mental_health is None:
                report.mental_health = _try_parse(MentalHealthAssessment, content)
            elif name == "CareCoordinator" and content and "TERMINATE" not in content:
                report.summary = content.replace("TERMINATE", "").strip()

        if not report.summary:
            report.summary = (
                "Multi-agent consultation completed. Review specialist sections below. "
                "This guidance is educational and not a clinical diagnosis."
            )

        report = self.hitl.review(report)
        logger.info(
            "consultation_completed",
            session_id=session_id,
            hitl_approved=bool(report.hitl and report.hitl.approved),
        )
        return report
