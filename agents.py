"""The AI Layer — V6.0 Investigator (Supply Chain, Platform, Moat, Integration)."""

import json
from typing import Any

from pydantic import BaseModel, Field


class CompanyMetrics(BaseModel):
    """V6.0 structured output from GPT-4o. All scores 0.0–1.0 unless noted."""

    trl_score: int = Field(..., ge=1, le=9, description="Technology Readiness Level 1-9")
    mrl_estimate: int = Field(..., ge=1, le=9, description="Manufacturing Readiness Level 1-9")
    has_patents: bool = Field(..., description="Whether the company has patents")
    is_dual_use: bool = Field(..., description="Whether technology has dual-use applications")
    team_has_phd: bool = Field(..., description="Whether team has PhD holders")
    team_has_exit: bool = Field(..., description="Whether team has prior exit experience")
    is_tier1: bool = Field(..., description="Team has Stanford/MIT/Google/SpaceX/McKinsey background")
    shared_history: bool = Field(..., description="Founders co-founded previously or worked together before")
    urgency_signal: bool = Field(..., description="Critical need: national security, life-saving, etc.")
    supply_chain_risk: float = Field(..., ge=0.0, le=1.0, description="1.0=Domestic/Friendly, 0.0=Hostile/Single-Source")
    integration_friction: float = Field(..., ge=0.0, le=1.0, description="1.0=Drop-in, 0.0=System Overhaul")
    platform_potential: float = Field(..., ge=0.0, le=1.0, description="1.0=Multiple product lines/ecosystem")
    moat_score: float = Field(..., ge=0.0, le=1.0, description="1.0=Network effects/switching costs/proprietary data")


def analyze_company_text(api_key: str, text_content: str) -> dict[str, Any]:
    """
    Analyze company text with GPT-4o and extract V6.0 metrics.
    Returns dict compatible with engine.calculate_risk_factors inputs.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Invalid API key: API key cannot be empty.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package is required. Install with: pip install openai")

    client = OpenAI(api_key=api_key.strip())

    system_prompt = (
        "You are a VC Diligence Analyst specializing in Deep Tech. "
        "Analyze the provided company text and extract the following metrics in JSON format.\n\n"
        "**Core metrics:**\n"
        "- trl_score (1-9): Technology Readiness Level\n"
        "- mrl_estimate (1-9): Manufacturing Readiness Level (Prototype, Pilot line, Mass production)\n"
        "- has_patents (bool), is_dual_use (bool)\n"
        "- team_has_phd (bool), team_has_exit (bool), is_tier1 (bool), shared_history (bool)\n"
        "- urgency_signal (bool): Critical need, national security, life-saving\n\n"
        "**V6 Deep Tech checks (output as floats 0.0–1.0):**\n"
        "- supply_chain_risk: **Supply Chain Check** — Look for 'rare earths,' 'China dependency,' "
        "'domestic sourcing,' 'vertical integration.' High score (1.0) = Domestic/Friendly supply; "
        "Low (0.0) = Hostile or single-source risk.\n"
        "- integration_friction: **Integration Check** — Look for 'drop-in replacement,' 'plug-and-play' "
        "(high = 1.0) vs 'requires new infrastructure,' 'retrofitting,' 'system overhaul' (low = 0.0). "
        "1.0 = Drop-in; 0.0 = Infrastructure Overhaul.\n"
        "- platform_potential: **Platform Check** — Look for 'ecosystem,' 'multiple verticals,' "
        "'licensing core tech,' 'platform play.' High = 1.0 (enables multiple product lines).\n"
        "- moat_score: **Moat Check** — Look for 'network effects,' 'high switching costs,' "
        "'proprietary data flywheels,' 'lock-in.' High = 1.0 (strong moat).\n\n"
        "Return ONLY valid JSON with these exact keys. Use floats for supply_chain_risk, "
        "integration_friction, platform_potential, moat_score. If ambiguous, use 0.5."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content or "No content provided."},
            ],
            temperature=0.1,
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "invalid" in err_msg or "api_key" in err_msg or "authentication" in err_msg:
            raise ValueError(f"Invalid API key: {e}") from e
        raise ValueError(f"OpenAI API error: {e}") from e

    content = response.choices[0].message.content.strip()

    try:
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        metrics = CompanyMetrics.model_validate_json(content)
    except Exception:
        try:
            data = json.loads(content)
            metrics = CompanyMetrics(**data)
        except Exception as parse_err:
            raise ValueError(f"Failed to parse AI response as JSON: {parse_err}") from parse_err

    return {
        "trl_score": metrics.trl_score,
        "mrl_score": metrics.mrl_estimate,
        "ip_score": 0.9 if metrics.has_patents else 0.2,
        "complexity_score": 0.7 if metrics.has_patents else 0.4,
        "platform_potential": max(0.0, min(1.0, float(metrics.platform_potential))),
        "integration_friction": max(0.0, min(1.0, float(metrics.integration_friction))),
        "dual_use_score": 0.9 if metrics.is_dual_use else 0.3,
        "urgency_score": 0.8 if metrics.urgency_signal else 0.4,
        "market_cagr": 0.4,
        "moat_score": max(0.0, min(1.0, float(metrics.moat_score))),
        "regulatory_score": 0.5,
        "rnd_years": 5.0,
        "supply_chain_risk": max(0.0, min(1.0, float(metrics.supply_chain_risk))),
        "team_has_phd": metrics.team_has_phd,
        "team_has_exit": metrics.team_has_exit,
        "is_tier1_background": metrics.is_tier1,
        "founders_worked_together": metrics.shared_history,
        "is_solo_founder": False,
        "all_scientists": False,
        "all_biz": False,
        "sentiment": "Neutral",
    }
