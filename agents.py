"""The AI Layer — V6.0 Investigator (Supply Chain, Platform, Moat, Integration)."""

import json
import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ——— Tier 3: Sector-aware valuation defaults (base $M by stage) ———
VALUATION_DEFAULTS = {
    "Pre-Seed": 6.0,
    "Seed": 12.0,
    "Series A": 40.0,
}

# Sector multipliers: Premium (AI/SaaS), CapEx discount (Hardware/Robotics/Deep Tech), Neutral (Bio/Pharma)
SECTOR_MULTIPLIERS = {
    "premium": 1.5,   # "AI", "SaaS"
    "capex": 0.8,     # "Hardware", "Robotics", "Deep Tech"
    "neutral": 1.0,   # "Bio", "Pharma", default
}

FUNDRAISING_KEYWORDS = (
    "Raising", "Targeting", "Pre-money", "Post-money", "Cap", "Valuation",
    "pre-money", "post-money", "valuation", "raising", "targeting", "cap",
)


class CompanyMetrics(BaseModel):
    """V6.0 structured output from GPT-4o. All scores 0.0–1.0 unless noted. Include one-sentence _reason for each."""

    trl_score: int = Field(..., ge=1, le=9, description="Technology Readiness Level 1-9")
    trl_reason: str = Field(default="", description="One-sentence justification for trl_score")
    mrl_estimate: int = Field(..., ge=1, le=9, description="Manufacturing Readiness Level 1-9")
    mrl_reason: str = Field(default="", description="One-sentence justification for mrl_estimate")
    has_patents: bool = Field(..., description="Whether the company has patents")
    ip_reason: str = Field(default="", description="One-sentence justification for IP/patent strength")
    is_dual_use: bool = Field(..., description="Whether technology has dual-use applications")
    dual_use_reason: str = Field(default="", description="One-sentence justification for dual-use score")
    team_has_phd: bool = Field(..., description="Whether team has PhD holders")
    team_has_exit: bool = Field(..., description="Whether team has prior exit experience")
    is_tier1: bool = Field(..., description="Team has Stanford/MIT/Google/SpaceX/McKinsey background")
    shared_history: bool = Field(..., description="Founders co-founded previously or worked together before")
    urgency_signal: bool = Field(..., description="Critical need: national security, life-saving, etc.")
    urgency_reason: str = Field(default="", description="One-sentence justification for urgency")
    supply_chain_risk: float = Field(..., ge=0.0, le=1.0, description="1.0=Domestic/Friendly, 0.0=Hostile/Single-Source")
    supply_chain_reason: str = Field(default="", description="One-sentence justification for supply_chain_risk")
    integration_friction: float = Field(..., ge=0.0, le=1.0, description="1.0=Drop-in, 0.0=System Overhaul")
    integration_friction_reason: str = Field(default="", description="One-sentence justification for integration_friction")
    platform_potential: float = Field(..., ge=0.0, le=1.0, description="1.0=Multiple product lines/ecosystem")
    platform_potential_reason: str = Field(default="", description="One-sentence justification for platform_potential")
    moat_score: float = Field(..., ge=0.0, le=1.0, description="1.0=Network effects/switching costs/proprietary data")
    moat_reason: str = Field(default="", description="One-sentence justification for moat_score")
    complexity_reason: str = Field(default="", description="One-sentence justification for tech complexity")
    regulatory_reason: str = Field(default="", description="One-sentence justification for regulatory path")
    market_cagr_reason: str = Field(default="", description="One-sentence justification for market growth")
    rnd_reason: str = Field(default="", description="One-sentence justification for years to launch")


def _extract_valuation_from_money_string(s: str) -> Optional[float]:
    """Parse strings like '$20M', '$20M Cap', '20 million', '20M' into float millions."""
    s = (s or "").strip()
    # Normalize: $20M, 20M, $20 million, 20 million
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:M|million|MM)\b", s, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*B\b", s, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 1000.0
    return None


def _tier0_extract_valuation(document_text: str) -> tuple[Optional[float], bool]:
    """
    Tier 0: Scan document for fundraising keywords and extract entry valuation (cap / pre-money).
    Returns (valuation_millions or None, is_stale).
    """
    if not (document_text or "").strip():
        return None, False

    text = document_text
    # Check for fundraising context
    has_keyword = any(kw in text for kw in FUNDRAISING_KEYWORDS)
    if not has_keyword:
        return None, False

    # Prefer patterns that explicitly state cap/valuation (entry = cap)
    # e.g. "Raising $5M at $20M Cap" -> entry = $20M
    cap_patterns = [
        r"(?:at|@)\s*(?:a?\s*)?\$?\s*(\d+(?:\.\d+)?)\s*(?:M|million|MM)\s*(?:cap|valuation|pre-?money)",
        r"(?:cap|valuation|pre-?money)\s*(?:of|@|at)?\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:M|million|MM)",
        r"\$?\s*(\d+(?:\.\d+)?)\s*(?:M|million|MM)\s*(?:cap|valuation|pre-?money)",
        r"(?:raising|targeting)\s+\$?\s*\d+(?:\s*M)?\s*(?:at|@)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:M|million)",
    ]
    for pat in cap_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 0.5 < val < 10000:
                from utils import extract_document_date
                year_str = extract_document_date(text)
                is_stale = False
                if year_str:
                    try:
                        y = int(year_str)
                        is_stale = (datetime.now().year - y) > 1
                    except ValueError:
                        pass
                return val, is_stale

    # Fallback: any $XM or XM in same sentence as a keyword
    for chunk in re.split(r"[.\n]", text):
        if any(kw in chunk for kw in FUNDRAISING_KEYWORDS):
            v = _extract_valuation_from_money_string(chunk)
            if v and 0.5 < v < 10000:
                from utils import extract_document_date
                year_str = extract_document_date(text)
                is_stale = False
                if year_str:
                    try:
                        is_stale = (datetime.now().year - int(year_str)) > 1
                    except ValueError:
                        pass
                return v, is_stale
    return None, False


def _infer_stage_and_sector(text: str) -> tuple[str, str]:
    """Infer funding stage and sector from text for Tier 3 fallback. Returns (stage, sector_key)."""
    t = (text or "").lower()
    stage = "Seed"
    if re.search(r"\bpre-?seed\b", t):
        stage = "Pre-Seed"
    elif re.search(r"\bseries\s*a\b", t):
        stage = "Series A"
    elif re.search(r"\bseed\b", t):
        stage = "Seed"

    sector = "neutral"
    if re.search(r"\b(?:ai|artificial intelligence|saas|software as a service)\b", t):
        sector = "premium"
    elif re.search(r"\b(?:hardware|robotics|deep tech)\b", t):
        sector = "capex"
    elif re.search(r"\b(?:bio|pharma|biotech|life science)\b", t):
        sector = "neutral"
    return stage, sector


def _tier3_fallback(document_text: str) -> float:
    """
    Tier 3: Sector-aware granular fallback.
    Base: Pre-Seed $6M, Seed $12M, Series A $40M.
    Multipliers: AI/SaaS x1.5, Hardware/Robotics/Deep Tech x0.8, Bio/Pharma x1.0.
    """
    stage, sector = _infer_stage_and_sector(document_text or "")
    base = VALUATION_DEFAULTS.get(stage, VALUATION_DEFAULTS["Seed"])
    mult = SECTOR_MULTIPLIERS.get(sector, SECTOR_MULTIPLIERS["neutral"])
    return round(base * mult, 1)


def _web_validation_valuation(api_key: str, company_name: Optional[str], document_valuation: Optional[float], document_text: str) -> tuple[Optional[float], str]:
    """
    Tier 1 & 2: Web validation placeholder. Uses LLM to simulate cross-check vs external source.
    Returns (web_valuation_or_None, cross_check_message).
    """
    try:
        from openai import OpenAI
    except ImportError:
        return None, ""

    client = OpenAI(api_key=api_key.strip())
    prompt = (
        "You are a VC analyst cross-checking a pitch deck's stated valuation against public data. "
        "Based on general knowledge (PitchBook, Crunchbase, press), what valuation or round size "
        "would typically be reported for a company like the one described? "
        "If the document states a valuation, compare it to what might be in public sources.\n\n"
        "Document excerpt (pitch deck / company description):\n" + (document_text or "")[:4000]
    )
    if document_valuation is not None:
        prompt += f"\n\nStated valuation in deck: ${document_valuation:.0f}M (pre-money/cap)."
    if company_name:
        prompt += f"\nCompany name: {company_name}"

    prompt += (
        "\n\nReply with ONLY a short cross-check note. "
        "If there is a discrepancy, start with: '⚠️ Discrepancy: ' and state what the pitch deck says vs what "
        "a source like PitchBook (2025) might show (e.g. 'Pitch Deck says $20M val, but PitchBook (2025) shows they raised a flat round at $20M previously.'). "
        "If no clear discrepancy, say 'No significant discrepancy found.' Do not include JSON or other formatting."
    )
    try:
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )
        msg = (r.choices[0].message.content or "").strip()
        return None, msg
    except Exception:
        return None, ""


# Fallback multiples for exit targets when Agent has no data
BASE_EXIT_MULTIPLE = 4.0   # Base Case = Strategic Sale (e.g. 4x entry)
HOME_RUN_EXIT_MULTIPLE = 40.0   # Home Run = Category King (e.g. 40x entry)


def _estimate_exit_targets(
    api_key: Optional[str],
    document_text: str,
    entry_valuation: float,
    sector_key: str,
) -> tuple[float, float]:
    """
    Exit Analyst: estimate Base Exit (Strategic Sale) and Home Run Exit (Category King).
    Logic: LLM searches for 'average M&A exit price in [Sector]' and 'Market Cap of leading public [Sector] company'.
    Fallback: Base = 4x entry, Home Run = 40x entry.
    Returns (estimated_base_exit_m, estimated_home_run_exit_m).
    """
    fallback_base = max(10.0, entry_valuation * BASE_EXIT_MULTIPLE)
    fallback_home_run = max(500.0, entry_valuation * HOME_RUN_EXIT_MULTIPLE)

    if not api_key or not api_key.strip():
        return round(fallback_base, 1), round(fallback_home_run, 1)

    sector_label = {"premium": "AI/SaaS", "capex": "Hardware/Robotics/Deep Tech", "neutral": "General Tech"}.get(sector_key, "this sector")
    prompt = (
        "You are a VC Exit Analyst. Based on the following company/pitch context, estimate two exit values in $M (millions).\n\n"
        "1. **Strategic Sale (Base Case):** Typical M&A exit — e.g. 'average M&A exit price in [sector]'. "
        "Think: acquired by Google, Lockheed, etc. Return a single number in $M.\n"
        "2. **Category King (Home Run):** IPO / power-law outcome — e.g. 'Market Cap of leading public [sector] company'. "
        "Think: category-defining public company. Return a single number in $M.\n\n"
        f"Company/sector context: {sector_label}. Entry valuation: ${entry_valuation:.0f}M.\n\n"
        "Document excerpt:\n" + (document_text or "")[:3000]
    )
    prompt += (
        "\n\nRespond with ONLY a JSON object with exactly two keys: "
        '"estimated_base_exit" (float, $M for strategic sale) and "estimated_home_run_exit" (float, $M for category king). '
        "Use null for a key if you cannot estimate; we will use fallbacks (4x entry for base, 40x entry for home run). "
        "No other text or markdown."
    )
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key.strip())
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        raw = (r.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        base = data.get("estimated_base_exit")
        home_run = data.get("estimated_home_run_exit")
        base_val = float(base) if base is not None else fallback_base
        home_run_val = float(home_run) if home_run is not None else fallback_home_run
        base_val = max(10.0, base_val)
        home_run_val = max(500.0, home_run_val)
        return round(base_val, 1), round(home_run_val, 1)
    except Exception:
        return round(fallback_base, 1), round(fallback_home_run, 1)


def estimate_valuation_metrics(
    api_key: str,
    document_text: str,
    company_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Valuation V2: Tier 0 (document) -> Tier 1 & 2 (web validation) -> Tier 3 (sector fallback).
    Returns dict: entry_valuation (float), source_tier (str), is_stale (bool),
    discrepancy_note (str), sector (str), stage (str).
    """
    entry_m: Optional[float] = None
    source_tier = "tier3"
    is_stale = False
    discrepancy_note = ""

    # Tier 0: Document extraction
    doc_val, is_stale = _tier0_extract_valuation(document_text)
    if doc_val is not None:
        entry_m = doc_val
        source_tier = "tier0"

    # Tier 1 & 2: Web validation (cross-check); if no Tier 0, we still use Tier 3 for number
    if api_key and (document_text or company_name):
        _web_val, cross_msg = _web_validation_valuation(api_key, company_name, entry_m, document_text or "")
        discrepancy_note = cross_msg
        if _web_val is not None and entry_m is None:
            entry_m = _web_val
            source_tier = "tier1"

    # Tier 3: Sector-aware fallback
    if entry_m is None:
        entry_m = _tier3_fallback(document_text)
        source_tier = "tier3"

    stage, sector = _infer_stage_and_sector(document_text)
    entry_final = round(float(entry_m), 1)

    # Exit Analyst: estimated_base_exit (Strategic Sale) and estimated_home_run_exit (Category King)
    base_exit, home_run_exit = _estimate_exit_targets(
        api_key, document_text, entry_final, sector
    )

    return {
        "entry_valuation": entry_final,
        "source_tier": source_tier,
        "is_stale": is_stale,
        "discrepancy_note": discrepancy_note.strip(),
        "sector": sector,
        "stage": stage,
        "estimated_base_exit": base_exit,
        "estimated_home_run_exit": home_run_exit,
    }


def analyze_company_text(
    api_key: str,
    text_content: str,
    *,
    pitch_deck_text: Optional[str] = None,
    company_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Analyze company text with GPT-4o and extract V6.0 metrics.
    When pitch_deck_text is provided, it is used as the Ground Truth and valuation is estimated (Tier 0/1/2/3).
    Returns dict compatible with engine.calculate_risk_factors inputs, plus entry_valuation, discrepancy_note when applicable.
    """
    if not api_key or not api_key.strip():
        raise ValueError("Invalid API key: API key cannot be empty.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai package is required. Install with: pip install openai")

    client = OpenAI(api_key=api_key.strip())

    # Ground Truth: prefer pitch deck content when provided
    content_to_analyze = (pitch_deck_text or "").strip() or (text_content or "").strip()
    if not content_to_analyze:
        content_to_analyze = text_content or "No content provided."

    system_prompt = (
        "You are a VC Diligence Analyst specializing in Deep Tech. "
        "Analyze the provided company text (pitch deck or description) as the Ground Truth and extract the following metrics in JSON format. "
        "For every score you output, also provide a one-sentence justification (e.g. trl_reason, mrl_reason, dual_use_reason).\n\n"
        "**Core metrics (with _reason for each):**\n"
        "- trl_score (1-9), trl_reason (string)\n"
        "- mrl_estimate (1-9), mrl_reason (string)\n"
        "- has_patents (bool), ip_reason (string)\n"
        "- is_dual_use (bool), dual_use_reason (string)\n"
        "- team_has_phd (bool), team_has_exit (bool), is_tier1 (bool), shared_history (bool)\n"
        "- urgency_signal (bool), urgency_reason (string)\n\n"
        "**V6 Deep Tech checks (floats 0.0–1.0, each with _reason):**\n"
        "- supply_chain_risk, supply_chain_reason\n"
        "- integration_friction, integration_friction_reason\n"
        "- platform_potential, platform_potential_reason\n"
        "- moat_score, moat_reason\n"
        "- complexity_reason, regulatory_reason, market_cagr_reason, rnd_reason (optional one-sentence each)\n\n"
        "Return ONLY valid JSON with these keys. Use floats for supply_chain_risk, integration_friction, platform_potential, moat_score. "
        "If ambiguous, use 0.5. Every score must have a short, specific justification (e.g. 'Strong evidence of...' or 'Manufacturing line observed...')."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_to_analyze},
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

    def _reason(m: Any, key: str) -> str:
        return (getattr(m, key, None) or "") if hasattr(m, key) else ""

    out = {
        "trl_score": metrics.trl_score,
        "trl_reason": _reason(metrics, "trl_reason"),
        "mrl_score": metrics.mrl_estimate,
        "mrl_reason": _reason(metrics, "mrl_reason"),
        "ip_score": 0.9 if metrics.has_patents else 0.2,
        "ip_reason": _reason(metrics, "ip_reason"),
        "complexity_score": 0.7 if metrics.has_patents else 0.4,
        "complexity_reason": _reason(metrics, "complexity_reason"),
        "platform_potential": max(0.0, min(1.0, float(metrics.platform_potential))),
        "platform_potential_reason": _reason(metrics, "platform_potential_reason"),
        "integration_friction": max(0.0, min(1.0, float(metrics.integration_friction))),
        "integration_friction_reason": _reason(metrics, "integration_friction_reason"),
        "dual_use_score": 0.9 if metrics.is_dual_use else 0.3,
        "dual_use_reason": _reason(metrics, "dual_use_reason"),
        "urgency_score": 0.8 if metrics.urgency_signal else 0.4,
        "urgency_reason": _reason(metrics, "urgency_reason"),
        "market_cagr": 0.4,
        "market_cagr_reason": _reason(metrics, "market_cagr_reason"),
        "moat_score": max(0.0, min(1.0, float(metrics.moat_score))),
        "moat_reason": _reason(metrics, "moat_reason"),
        "regulatory_score": 0.5,
        "regulatory_reason": _reason(metrics, "regulatory_reason"),
        "rnd_years": 5.0,
        "rnd_reason": _reason(metrics, "rnd_reason"),
        "supply_chain_risk": max(0.0, min(1.0, float(metrics.supply_chain_risk))),
        "supply_chain_reason": _reason(metrics, "supply_chain_reason"),
        "team_has_phd": metrics.team_has_phd,
        "team_has_exit": metrics.team_has_exit,
        "is_tier1_background": metrics.is_tier1,
        "founders_worked_together": metrics.shared_history,
        "is_solo_founder": False,
        "all_scientists": False,
        "all_biz": False,
        "sentiment": "Neutral",
    }

    # Valuation V2: when pitch deck text is provided, run Tier 0/1/2/3 and cross-check
    if pitch_deck_text and (pitch_deck_text.strip() or content_to_analyze.strip()):
        try:
            val_metrics = estimate_valuation_metrics(
                api_key, pitch_deck_text.strip() or content_to_analyze, company_name
            )
            out["entry_valuation"] = val_metrics["entry_valuation"]
            out["valuation_source_tier"] = val_metrics["source_tier"]
            out["valuation_is_stale"] = val_metrics["is_stale"]
            out["discrepancy_note"] = val_metrics["discrepancy_note"]
            out["valuation_stage"] = val_metrics["stage"]
            out["valuation_sector"] = val_metrics["sector"]
            out["estimated_base_exit"] = val_metrics["estimated_base_exit"]
            out["estimated_home_run_exit"] = val_metrics["estimated_home_run_exit"]
        except Exception:
            entry_fb = _tier3_fallback(pitch_deck_text or content_to_analyze)
            out["entry_valuation"] = entry_fb
            out["discrepancy_note"] = ""
            out["estimated_base_exit"] = round(max(10.0, entry_fb * BASE_EXIT_MULTIPLE), 1)
            out["estimated_home_run_exit"] = round(max(500.0, entry_fb * HOME_RUN_EXIT_MULTIPLE), 1)

    return out
