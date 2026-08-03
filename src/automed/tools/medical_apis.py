"""Tool functions registered with AG2 agents for real-time medical lookups."""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Dict, List

import httpx
import structlog

from automed.config import get_settings
from automed.models.schemas import MedicalDataInsight

logger = structlog.get_logger(__name__)

# Educational mock corpus used when external APIs are unavailable.
_MOCK_GUIDELINES: Dict[str, List[str]] = {
    "fever": [
        "CDC: Seek care for fever >103°F (39.4°C) lasting >3 days in adults.",
        "Hydration and rest are first-line supportive measures for viral fever.",
    ],
    "headache": [
        "AHA/ASA: Sudden 'thunderclap' headache warrants emergency evaluation.",
        "Tension-type headaches often respond to hydration, sleep, and OTC analgesics.",
    ],
    "anxiety": [
        "APA: Evidence-based first-line options include CBT and SSRIs (clinician-prescribed).",
        "Breathing exercises and grounding techniques can reduce acute anxiety symptoms.",
    ],
    "default": [
        "WHO: Always verify medication dosing with a licensed clinician or pharmacist.",
        "Evidence-based care prioritizes red-flag screening before self-treatment.",
    ],
}


def fetch_medical_guidelines(query: str) -> MedicalDataInsight:
    """Fetch guideline-style insights for a clinical query.

    Attempts NIH ClinicalTables when reachable; falls back to curated mock data
    so local demos remain deterministic without API keys.
    """
    settings = get_settings()
    normalized = query.lower().strip()
    sources: List[str] = []
    findings: List[str] = []
    is_mock = False

    try:
        url = f"{settings.nih_api_base}/conditions/v3/search"
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, params={"terms": query, "maxList": 5})
            if response.status_code == 200:
                payload = response.json()
                # ClinicalTables returns [count, codes, extra, display_strings, ...]
                display = payload[3] if isinstance(payload, list) and len(payload) > 3 else []
                findings = [str(item) for item in display[:5]]
                sources.append("NIH ClinicalTables")
    except Exception as exc:  # noqa: BLE001 — soft-fail to mock corpus
        logger.warning("medical_api_fallback", error=str(exc), query=query)

    if not findings:
        is_mock = True
        sources.append("AutoMed curated educational corpus")
        for key, tips in _MOCK_GUIDELINES.items():
            if key in normalized:
                findings.extend(tips)
                break
        else:
            findings.extend(_MOCK_GUIDELINES["default"])

    return MedicalDataInsight(
        query=query,
        sources=sources,
        findings=findings,
        guidelines_referenced=sources,
        retrieved_at=datetime.now(timezone.utc),
        is_mock_data=is_mock,
    )


def check_drug_interactions(medications: List[str]) -> List[str]:
    """Return educational interaction notes for a medication list.

    Production deployments should replace this with FDA/RxNorm lookups.
    """
    if len(medications) < 2:
        return ["Insufficient medication list to evaluate interactions."]

    notes = [
        f"Review combination of {', '.join(medications)} with a pharmacist.",
        "Flag any anticoagulant + NSAID combinations for bleeding risk.",
        "Avoid duplicating active ingredients across OTC products (e.g., acetaminophen).",
    ]
    return notes
