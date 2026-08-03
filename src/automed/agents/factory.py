"""Factory helpers for specialized AutoMed ConversableAgents."""

from __future__ import annotations

from typing import Any, Dict, Optional

from autogen import ConversableAgent, LLMConfig

from automed.models.schemas import (
    FollowUpPlan,
    MedicalDataInsight,
    MentalHealthAssessment,
    SymptomAnalysis,
    TreatmentSuggestion,
)
from automed.tools.medical_apis import check_drug_interactions, fetch_medical_guidelines

DISCLAIMER = (
    "You are part of AutoMed, an educational multi-agent system. "
    "Never claim to diagnose or replace a licensed clinician. "
    "Flag emergencies and urge immediate professional care when red flags appear."
)


def _base_llm_config(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
    response_format: Optional[type] = None,
) -> LLMConfig:
    entry: Dict[str, Any] = {
        "api_type": "openai",
        "model": model,
        "api_key": api_key,
        "base_url": api_base,
        "temperature": temperature,
    }
    if response_format is not None:
        entry["response_format"] = response_format
    return LLMConfig(config_list=[entry])


def create_symptom_analyzer(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    return ConversableAgent(
        name="SymptomAnalyzer",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Triage nurse / symptom analyst.\n"
            "Extract symptoms, list possible conditions, classify urgency, "
            "and surface red flags. Ask clarifying questions when information is incomplete. "
            "Return ONLY structured SymptomAnalysis JSON."
        ),
        llm_config=_base_llm_config(
            model, api_key, api_base, temperature, SymptomAnalysis
        ),
        human_input_mode="NEVER",
    )


def create_treatment_advisor(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    return ConversableAgent(
        name="TreatmentAdvisor",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Clinical treatment advisor (non-prescribing).\n"
            "Propose evidence-informed self-care, OTC considerations, lifestyle advice, "
            "contraindications, and escalation criteria. "
            "Always set requires_clinician_review=true for medication changes. "
            "Return ONLY structured TreatmentSuggestion JSON."
        ),
        llm_config=_base_llm_config(
            model, api_key, api_base, temperature, TreatmentSuggestion
        ),
        human_input_mode="NEVER",
    )


def create_medical_data_fetcher(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    agent = ConversableAgent(
        name="MedicalDataFetcher",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Medical knowledge retrieval specialist.\n"
            "Use tools to fetch guideline-oriented findings and drug-interaction notes. "
            "Cite sources. Prefer tool results over speculation. "
            "Return ONLY structured MedicalDataInsight JSON."
        ),
        llm_config=_base_llm_config(
            model, api_key, api_base, temperature, MedicalDataInsight
        ),
        human_input_mode="NEVER",
    )
    agent.register_for_llm(
        name="fetch_medical_guidelines",
        description="Retrieve guideline-style medical insights for a clinical query.",
    )(fetch_medical_guidelines)
    agent.register_for_execution(name="fetch_medical_guidelines")(fetch_medical_guidelines)
    agent.register_for_llm(
        name="check_drug_interactions",
        description="Return educational notes on potential medication interactions.",
    )(check_drug_interactions)
    agent.register_for_execution(name="check_drug_interactions")(check_drug_interactions)
    return agent


def create_follow_up_agent(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    return ConversableAgent(
        name="FollowUpCare",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Care continuity planner.\n"
            "Produce a monitoring checklist, follow-up interval, escalation triggers, "
            "and patient education points. Return ONLY structured FollowUpPlan JSON."
        ),
        llm_config=_base_llm_config(
            model, api_key, api_base, temperature, FollowUpPlan
        ),
        human_input_mode="NEVER",
    )


def create_mental_health_agent(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    return ConversableAgent(
        name="MentalHealthCare",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Compassionate mental health support specialist.\n"
            "Assess emotional concerns, estimate risk_level, share coping strategies "
            "and reputable resources. For crisis/high risk set requires_human_escalation=true "
            "and include crisis hotline guidance. Never provide therapy substitutes. "
            "Return ONLY structured MentalHealthAssessment JSON."
        ),
        llm_config=_base_llm_config(
            model, api_key, api_base, temperature, MentalHealthAssessment
        ),
        human_input_mode="NEVER",
    )


def create_user_proxy() -> ConversableAgent:
    """Patient-facing proxy; collects human input at HITL boundaries."""
    return ConversableAgent(
        name="PatientProxy",
        system_message=(
            "You represent the patient / human operator. "
            "Relay symptoms clearly and participate in HITL approvals when asked."
        ),
        human_input_mode="ALWAYS",
        llm_config=False,
        code_execution_config=False,
    )


def create_coordinator(
    model: str,
    api_key: str,
    api_base: str,
    temperature: float,
) -> ConversableAgent:
    return ConversableAgent(
        name="CareCoordinator",
        system_message=(
            f"{DISCLAIMER}\n"
            "Role: Multi-agent care coordinator / attending synthesizer.\n"
            "Orchestrate specialist agents, resolve conflicts, and produce a clear "
            "patient-facing summary. When the consultation is complete, reply with "
            "the single token: TERMINATE."
        ),
        llm_config=_base_llm_config(model, api_key, api_base, temperature),
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
    )
