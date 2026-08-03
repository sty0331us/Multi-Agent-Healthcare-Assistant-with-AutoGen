"""Agent factory package."""

from automed.agents.factory import (
    create_coordinator,
    create_follow_up_agent,
    create_medical_data_fetcher,
    create_mental_health_agent,
    create_symptom_analyzer,
    create_treatment_advisor,
    create_user_proxy,
)

__all__ = [
    "create_coordinator",
    "create_follow_up_agent",
    "create_medical_data_fetcher",
    "create_mental_health_agent",
    "create_symptom_analyzer",
    "create_treatment_advisor",
    "create_user_proxy",
]
