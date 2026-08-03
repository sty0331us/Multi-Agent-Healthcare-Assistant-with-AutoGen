"""Human-in-the-Loop (HITL) compliance gate.

Before treatment or mental-health recommendations are released to the user,
a human reviewer must approve, edit, or reject the draft — supporting
regulatory/compliance workflows and clinical accuracy checks.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from automed.config import Settings
from automed.models.schemas import (
    ConsultationReport,
    HITLDecision,
    MentalHealthAssessment,
    TreatmentSuggestion,
)

console = Console()


class HITLGate:
    """Interactive approval gate for high-stakes agent outputs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def requires_review(self, report: ConsultationReport) -> bool:
        if not self.settings.hitl_enabled:
            return False

        if (
            self.settings.hitl_require_approval_for_treatment
            and report.treatment is not None
        ):
            return True

        if (
            self.settings.hitl_require_approval_for_mental_health
            and report.mental_health is not None
            and (
                report.mental_health.requires_human_escalation
                or report.mental_health.risk_level in {"high", "crisis"}
            )
        ):
            return True

        if report.symptom_analysis and report.symptom_analysis.urgency.value == "emergency":
            return True

        return False

    def review(self, report: ConsultationReport) -> ConsultationReport:
        """Present draft report to a human reviewer and attach their decision."""
        if not self.requires_review(report):
            report.hitl = HITLDecision(
                approved=True,
                reviewer_notes="HITL skipped (not required for this session).",
                reviewer_id="system_auto_approve",
            )
            return report

        console.print(
            Panel.fit(
                report.format(),
                title="[bold yellow]HITL Review Required[/bold yellow]",
                border_style="yellow",
            )
        )

        approved = Confirm.ask(
            "[bold]Approve this consultation draft for the patient?[/bold]",
            default=False,
        )
        notes = Prompt.ask("Reviewer notes (optional)", default="")

        if not approved:
            # Soften treatment / mental-health payloads when rejected.
            if report.treatment:
                report.treatment = TreatmentSuggestion(
                    condition_focus=report.treatment.condition_focus,
                    recommended_actions=[
                        "Human reviewer rejected automated treatment suggestions.",
                        "Please consult a licensed healthcare professional.",
                    ],
                    requires_clinician_review=True,
                    confidence=report.treatment.confidence,
                )
            if report.mental_health and report.mental_health.risk_level in {
                "high",
                "crisis",
            }:
                report.mental_health = MentalHealthAssessment(
                    concerns=report.mental_health.concerns,
                    risk_level=report.mental_health.risk_level,
                    coping_strategies=[],
                    resources=[
                        "https://www.iasp.info/suicidalthoughts/",
                        "Local emergency services / 988 (US)",
                    ],
                    crisis_hotline_notice=(
                        "If you are in crisis, contact local emergency services "
                        "or a suicide prevention hotline immediately."
                    ),
                    requires_human_escalation=True,
                    supportive_message=(
                        "A human clinician must review this case before further guidance."
                    ),
                )
            report.summary = (
                "Draft withheld pending clinician follow-up. "
                + (notes or "Reviewer did not approve automated recommendations.")
            )

        report.hitl = HITLDecision(
            approved=approved,
            reviewer_notes=notes,
            reviewer_id="human_reviewer",
        )
        return report
