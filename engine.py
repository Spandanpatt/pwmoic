"""The Math Brain — PWMOIC V6.0 (Granular Precision + Supply Chain + Platform)."""

from typing import Any, TypedDict

# ——— P_Tech_Sub weights (V6: TRL 30%, IP 20%, Complexity 15%, Platform 20%, Integration 15%) ———
W_TRL, W_IP, W_COMPLEXITY = 0.30, 0.20, 0.15
W_PLATFORM, W_INTEGRATION = 0.20, 0.15

# ——— P_Market_Sub weights (V6: DualUse 30%, Urgency 25%, CAGR 20%, Moat 25%) ———
W_DUAL_USE, W_URGENCY, W_CAGR, W_MOAT = 0.30, 0.25, 0.20, 0.25

# ——— P_Scale_Sub weights (V6: Regulatory 20%, MRL 30%, R&D_Time 20%, Supply Chain 30%) ———
W_REGULATORY, W_MRL, W_RND, W_SUPPLY_CHAIN = 0.20, 0.30, 0.20, 0.30

# ——— Legacy mappings ———
IP_MAP = {"None": 0.0, "Pending": 0.5, "Granted": 1.0}
COMPLEXITY_MAP = {"New Science": 0.3, "Hard Eng": 0.6, "Software": 0.9}
CUSTOMER_MAP = {"Gov": 0.7, "Commercial": 0.5, "Dual": 0.95}
REGULATORY_MAP = {"Complex": 0.2, "Moderate": 0.5, "Clear": 0.8}
COMPOSITION_MAP = {"Balanced": (False, False), "All Scientists": (True, False), "All Biz": (False, True)}


class RiskOverrides(TypedDict, total=False):
    """V6.0 Granular overrides (all floats 0.0–1.0 where applicable)."""

    trl_level: int
    ip_score: float
    complexity_score: float
    platform_potential: float
    integration_friction: float
    dual_use_score: float
    urgency_score: float
    market_cagr: float
    moat_score: float
    regulatory_score: float
    mrl_score: int
    rnd_years: float
    supply_chain_risk: float
    is_miracle_tech: bool
    team_has_phd: bool
    team_has_exit: bool
    is_tier1_background: bool
    founders_worked_together: bool
    is_solo_founder: bool
    all_scientists: bool
    all_biz: bool
    composition: str
    sentiment: str
    ip_status: str
    tech_complexity: str
    customer_type: str
    traction_score: float
    traction_stage: str
    regulatory_path: str
    capex_score: float
    capex_intensity: str


def _clamp01(value: Any, default: float = 0.5) -> float:
    """Ensure value is float in [0.0, 1.0]."""
    if value is None:
        return default
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _resolve_score(value: Any, default: float, mapping: dict | None = None) -> tuple[float, str]:
    if mapping and isinstance(value, str) and value in mapping:
        return mapping[value], value
    if isinstance(value, (int, float)):
        num = float(value)
        if mapping:
            for k, v in mapping.items():
                if abs(v - num) < 0.15:
                    return num, k
        return max(0.0, min(1.0, num)), str(round(num, 2))
    return default, "—"


def _first_not_none(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


def _rnd_score(years: float) -> float:
    """R&D time score: 1.0 if <3 yrs, 0.5 if <7 yrs, 0.2 if >=7 yrs."""
    y = float(years)
    if y < 3:
        return 1.0
    if y < 7:
        return 0.5
    return 0.2


def calculate_risk_factors(
    overrides: RiskOverrides | dict[str, Any],
    reasons_dict: dict[str, str] | None = None,
) -> dict:
    """
    V6.0 Multiplicative Waterfall:
    - P_Tech_Sub: TRL 30%, IP 20%, Complexity 15%, Platform 20%, Integration 15%
    - P_Market_Sub: DualUse 30%, Urgency 25%, CAGR 20%, Moat 25% (Miracle Tech override)
    - P_Scale_Sub: Regulatory 20%, MRL 30%, R&D Time 20%, Supply Chain 30%
    - Team & Draper Alpha unchanged.
    reasons_dict: optional map of reason keys (e.g. dual_use_reason) to justification strings; missing keys default to "-".
    """
    reasons = reasons_dict if reasons_dict is not None else {}

    def _reason(key: str) -> str:
        val = reasons.get(key) if isinstance(reasons, dict) else None
        return (val.strip() if isinstance(val, str) and val.strip() else "-")

    trl_raw = overrides.get("trl_level") or overrides.get("trl_score") or 5
    TRL_Score = min(9, max(1, int(trl_raw))) / 9.0
    trl_label = str(int(min(9, max(1, trl_raw))))

    ip_val = _first_not_none(overrides.get("ip_score"), overrides.get("ip_status"))
    ip_score, ip_label = _resolve_score(ip_val, 0.5, IP_MAP)
    comp_score, comp_label = _resolve_score(
        _first_not_none(overrides.get("complexity_score"), overrides.get("tech_complexity")),
        0.5, COMPLEXITY_MAP,
    )
    platform_potential = _clamp01(overrides.get("platform_potential"), 0.5)
    integration_friction = _clamp01(overrides.get("integration_friction"), 0.5)

    dual_score, dual_label = _resolve_score(
        _first_not_none(overrides.get("dual_use_score"), overrides.get("customer_type")),
        0.5, CUSTOMER_MAP,
    )
    urgency_score = _clamp01(overrides.get("urgency_score"), 0.5)
    market_cagr = _clamp01(overrides.get("market_cagr"), 0.5)
    moat_score = _clamp01(overrides.get("moat_score"), 0.5)

    reg_val = _first_not_none(overrides.get("regulatory_score"), overrides.get("regulatory_path"))
    reg_score, reg_label = _resolve_score(reg_val, 0.5, REGULATORY_MAP)

    mrl_raw = overrides.get("mrl_score")
    if mrl_raw is None:
        mrl_raw = 5
    mrl_score = min(9, max(1, int(mrl_raw)))
    c_mrl = mrl_score / 9.0

    rnd_years = _first_not_none(overrides.get("rnd_years"), 5.0)
    c_rnd = _rnd_score(float(rnd_years))

    supply_chain_risk = _clamp01(overrides.get("supply_chain_risk"), 0.5)

    comp_tuple = COMPOSITION_MAP.get(
        str(overrides.get("composition", "")).strip() or "Balanced",
        (overrides.get("all_scientists", False), overrides.get("all_biz", False)),
    )
    all_scientists, all_biz = comp_tuple
    team_has_phd = overrides.get("team_has_phd", False)
    team_has_exit = overrides.get("team_has_exit", False)
    is_tier1_background = overrides.get("is_tier1_background", False)
    founders_worked_together = overrides.get("founders_worked_together", False)
    is_solo_founder = overrides.get("is_solo_founder", False)
    sentiment = overrides.get("sentiment", "Neutral")
    is_miracle_tech = bool(overrides.get("is_miracle_tech", False))

    # ——— P_Tech_Sub (V6) ———
    c_trl = TRL_Score * W_TRL
    c_ip = ip_score * W_IP
    c_comp = comp_score * W_COMPLEXITY
    c_platform = platform_potential * W_PLATFORM
    c_integration = integration_friction * W_INTEGRATION
    P_Tech_Sub = c_trl + c_ip + c_comp + c_platform + c_integration

    # ——— P_Market_Sub (V6) ———
    c_dual = dual_score * W_DUAL_USE
    c_urgency = urgency_score * W_URGENCY
    c_cagr = market_cagr * W_CAGR
    c_moat = moat_score * W_MOAT
    P_Market_Sub = c_dual + c_urgency + c_cagr + c_moat
    if is_miracle_tech:
        P_Market_Sub = 1.0

    # ——— P_Scale_Sub (V6) ———
    c_reg = reg_score * W_REGULATORY
    c_supply = supply_chain_risk * W_SUPPLY_CHAIN
    P_Scale_Sub = c_reg + (c_mrl * W_MRL) + (c_rnd * W_RND) + c_supply

    Base_Probability = P_Tech_Sub * P_Market_Sub * P_Scale_Sub

    Multiplier = 1.0
    if team_has_phd:
        Multiplier += 0.15
    if team_has_exit:
        Multiplier += 0.20
    if is_tier1_background:
        Multiplier += 0.10
    if founders_worked_together:
        Multiplier += 0.05
    if is_solo_founder:
        Multiplier -= 0.10
    if all_scientists:
        Multiplier -= 0.20
    if all_biz:
        Multiplier -= 0.50

    Draper_Alpha = 1.25 if (
        sentiment == "Negative" and P_Tech_Sub > 0.7 and urgency_score > 0.8
    ) else 1.0

    Raw_Success = Base_Probability * Multiplier * Draper_Alpha
    P_Success = min(0.99, max(0.01, Raw_Success))

    after_tech = P_Tech_Sub
    after_market = P_Tech_Sub * P_Market_Sub
    after_scale = Base_Probability
    marginal_market = after_market - after_tech
    marginal_scale = after_scale - after_market
    marginal_team = Base_Probability * (Multiplier - 1)
    marginal_alpha = Base_Probability * Multiplier * (Draper_Alpha - 1)

    trace = {
        "trl": f"Score {trl_label}/9 (-> {TRL_Score:.3f}) x 30% = {c_trl:.3f}",
        "ip": f"Score {ip_label} (-> {ip_score:.3f}) x 20% = {c_ip:.3f}",
        "complexity": f"Score {comp_label} (-> {comp_score:.3f}) x 15% = {c_comp:.3f}",
        "platform": f"Platform (-> {platform_potential:.3f}) x 20% = {c_platform:.3f}",
        "integration": f"Integration (-> {integration_friction:.3f}) x 15% = {c_integration:.3f}",
        "P_Tech_Sub": f"P_Tech_Sub = {c_trl:.3f} + {c_ip:.3f} + {c_comp:.3f} + {c_platform:.3f} + {c_integration:.3f} = {P_Tech_Sub:.3f}",
        "dual_use": f"DualUse {dual_label} (-> {dual_score:.3f}) x 30% = {c_dual:.3f}",
        "urgency": f"Urgency (-> {urgency_score:.3f}) x 25% = {c_urgency:.3f}",
        "cagr": f"CAGR (-> {market_cagr:.3f}) x 20% = {c_cagr:.3f}",
        "moat": f"Moat (-> {moat_score:.3f}) x 25% = {c_moat:.3f}",
        "P_Market_Sub": f"P_Market_Sub = {c_dual:.3f} + {c_urgency:.3f} + {c_cagr:.3f} + {c_moat:.3f} = {P_Market_Sub:.3f}",
        "regulatory": f"Regulatory {reg_label} (-> {reg_score:.3f}) x 20% = {c_reg:.3f}",
        "mrl": f"MRL {mrl_score}/9 (-> {c_mrl:.3f}) x 30% = {c_mrl * W_MRL:.3f}",
        "rnd": f"R&D {rnd_years} yrs (-> {c_rnd:.3f}) x 20% = {c_rnd * W_RND:.3f}",
        "supply_chain": f"Supply Chain (-> {supply_chain_risk:.3f}) x 30% = {c_supply:.3f}",
        "P_Scale_Sub": f"P_Scale_Sub = {c_reg:.3f} + {c_mrl * W_MRL:.3f} + {c_rnd * W_RND:.3f} + {c_supply:.3f} = {P_Scale_Sub:.3f}",
        "base": f"Base_Probability = P_Tech x P_Market x P_Scale = {Base_Probability:.4f}",
        "final": f"P_Success = Base x Mult x Alpha = {Base_Probability:.4f} x {Multiplier:.2f} x {Draper_Alpha:.2f} = {Raw_Success:.4f} -> capped = {P_Success:.2%}",
    }
    if is_miracle_tech:
        trace["miracle"] = "Miracle Tech enabled: P_Market_Sub = 1.0"

    math_tech = [
        ("TRL Level", trl_label, round(TRL_Score, 3), "30%", round(c_trl, 4), _reason("trl_reason")),
        ("IP Status", ip_label, round(ip_score, 3), "20%", round(c_ip, 4), _reason("ip_reason")),
        ("Tech Complexity", comp_label, round(comp_score, 3), "15%", round(c_comp, 4), _reason("complexity_reason")),
        ("Platform Potential", str(round(platform_potential, 2)), round(platform_potential, 3), "20%", round(c_platform, 4), _reason("platform_potential_reason")),
        ("Integration Friction", str(round(integration_friction, 2)), round(integration_friction, 3), "15%", round(c_integration, 4), _reason("integration_friction_reason")),
        ("P_Tech_Sub (sum)", "—", round(P_Tech_Sub, 4), "—", round(P_Tech_Sub, 4), "—"),
    ]
    math_market = [
        ("Dual Use", str(round(dual_score, 2)), round(dual_score, 3), "30%", round(c_dual, 4), _reason("dual_use_reason")),
        ("Urgency", str(round(urgency_score, 2)), round(urgency_score, 3), "25%", round(c_urgency, 4), _reason("urgency_reason")),
        ("Market CAGR", str(round(market_cagr, 2)), round(market_cagr, 3), "20%", round(c_cagr, 4), _reason("market_cagr_reason")),
        ("Moat Score", str(round(moat_score, 2)), round(moat_score, 3), "25%", round(c_moat, 4), _reason("moat_reason")),
        ("P_Market_Sub (sum)", "—", round(P_Market_Sub, 4), "—", round(P_Market_Sub, 4), "—"),
    ]
    math_scale = [
        ("Regulatory Path", str(round(reg_score, 2)), round(reg_score, 3), "20%", round(c_reg, 4), _reason("regulatory_reason")),
        ("MRL Score", str(mrl_score), round(c_mrl, 3), "30%", round(c_mrl * W_MRL, 4), _reason("mrl_reason")),
        ("R&D Time Risk", str(round(rnd_years, 1)), round(c_rnd, 3), "20%", round(c_rnd * W_RND, 4), _reason("rnd_reason")),
        ("Supply Chain Risk", str(round(supply_chain_risk, 2)), round(supply_chain_risk, 3), "30%", round(c_supply, 4), _reason("supply_chain_reason")),
        ("P_Scale_Sub (sum)", "—", round(P_Scale_Sub, 4), "—", round(P_Scale_Sub, 4), "—"),
    ]
    team_desc = []
    if team_has_phd:
        team_desc.append("PhD +0.15")
    if team_has_exit:
        team_desc.append("Exit +0.20")
    if is_tier1_background:
        team_desc.append("Tier1 +0.10")
    if founders_worked_together:
        team_desc.append("Shared +0.05")
    if is_solo_founder:
        team_desc.append("Solo -0.10")
    if all_scientists:
        team_desc.append("AllSci -0.20")
    if all_biz:
        team_desc.append("AllBiz -0.50")

    math_base = [
        ("Base_Probability", "P_Tech x P_Market x P_Scale", round(Base_Probability, 4), "multiplicative", round(Base_Probability, 4)),
        ("Multiplier", ", ".join(team_desc) or "1.0", round(Multiplier, 2), "—", round(Multiplier, 2)),
        ("Draper_Alpha", "1.25 if Negative + P_Tech>0.7 + Urgency>0.8 else 1.0", round(Draper_Alpha, 2), "—", round(Draper_Alpha, 2)),
        ("P_Success", "min(0.99, max(0.01, Base x Mult x Alpha))", round(P_Success, 4), "capped", round(P_Success, 4)),
    ]

    return {
        "p_success": round(P_Success, 4),
        "base_probability": round(Base_Probability, 4),
        "multiplier": round(Multiplier, 4),
        "draper_alpha": round(Draper_Alpha, 4),
        "breakdown": {
            "P_Tech_Sub": round(P_Tech_Sub, 4),
            "P_Market_Sub": round(P_Market_Sub, 4),
            "P_Scale_Sub": round(P_Scale_Sub, 4),
        },
        "sub_factors": {
            "TRL_Score": round(TRL_Score, 4),
            "IP_Score": round(ip_score, 4),
            "Complexity_Score": round(comp_score, 4),
            "Platform_Potential": round(platform_potential, 4),
            "Integration_Friction": round(integration_friction, 4),
            "DualUse_Score": round(dual_score, 4),
            "Urgency_Score": round(urgency_score, 4),
            "Market_CAGR": round(market_cagr, 4),
            "Moat_Score": round(moat_score, 4),
            "Regulatory_Score": round(reg_score, 4),
            "MRL_Score": round(c_mrl, 4),
            "RND_Score": round(c_rnd, 4),
            "Supply_Chain_Risk": round(supply_chain_risk, 4),
        },
        "waterfall_data": {
            "p_success": P_Success,
            "base_probability": Base_Probability,
            "step1_tech_start": P_Tech_Sub,
            "step2_market_marginal": marginal_market,
            "step3_scale_marginal": marginal_scale,
            "step4_team_marginal": marginal_team,
            "step5_alpha_marginal": marginal_alpha,
            "P_Tech_Sub": P_Tech_Sub,
            "P_Market_Sub": P_Market_Sub,
            "P_Scale_Sub": P_Scale_Sub,
            "multiplier": Multiplier,
            "draper_alpha": Draper_Alpha,
            "reason_step1_tech": " | ".join(x for x in [_reason("trl_reason"), _reason("ip_reason"), _reason("complexity_reason"), _reason("platform_potential_reason"), _reason("integration_friction_reason")] if x != "-") or "—",
            "reason_step2_market": " | ".join(x for x in [_reason("dual_use_reason"), _reason("urgency_reason"), _reason("market_cagr_reason"), _reason("moat_reason")] if x != "-") or "—",
            "reason_step3_scale": " | ".join(x for x in [_reason("regulatory_reason"), _reason("mrl_reason"), _reason("rnd_reason"), _reason("supply_chain_reason")] if x != "-") or "—",
            "reason_step4_team": "—",
            "reason_step5_alpha": "—",
        },
        "trace": trace,
        "math_tables": {
            "tech": math_tech,
            "market": math_market,
            "scale": math_scale,
            "base": math_base,
        },
    }


def calculate_pwmoic(
    p_success: float,
    entry_valuation: float,
    home_run_split: float,
    time_to_exit_years: int = 7,
    base_exit_val: float = 200.0,
    home_run_exit_val: float = 2000.0,
) -> dict:
    """PWMOIC + IRR (Time Value of Money). Uses dynamic base/home-run exit values ($M)."""
    p_success = min(1.0, max(0.0, p_success))
    home_run_split = min(1.0, max(0.0, home_run_split))
    entry_valuation = max(0.1, entry_valuation)
    time_to_exit_years = max(1, int(time_to_exit_years))
    exit_val_base = max(1.0, float(base_exit_val))
    exit_val_home_run = max(1.0, float(home_run_exit_val))

    prob_failure = 1.0 - p_success
    moic_failure = 0.5

    prob_base = p_success * (1.0 - home_run_split)
    dilution_base = 0.5
    moic_base = (exit_val_base / entry_valuation) * (1.0 - dilution_base)

    prob_home_run = p_success * home_run_split
    dilution_home_run = 0.7
    moic_home_run = (exit_val_home_run / entry_valuation) * (1.0 - dilution_home_run)

    final_pwmoic = prob_failure * moic_failure + prob_base * moic_base + prob_home_run * moic_home_run

    def irr(moic: float) -> float:
        return (float(moic) ** (1.0 / float(time_to_exit_years))) - 1.0

    return {
        "final_pwmoic": round(final_pwmoic, 4),
        "final_irr": round(irr(final_pwmoic), 4),
        "scenarios": {
            "failure": {"probability": round(prob_failure, 4), "moic": round(moic_failure, 4), "irr": round(irr(moic_failure), 4), "exit_val_m": None, "dilution": None},
            "base_case": {"probability": round(prob_base, 4), "moic": round(moic_base, 4), "irr": round(irr(moic_base), 4), "exit_val_m": exit_val_base, "dilution": dilution_base},
            "home_run": {"probability": round(prob_home_run, 4), "moic": round(moic_home_run, 4), "irr": round(irr(moic_home_run), 4), "exit_val_m": exit_val_home_run, "dilution": dilution_home_run},
        },
    }


def legacy_to_overrides(data: dict) -> RiskOverrides:
    """Convert legacy/mock data to RiskOverrides."""
    if not data:
        return RiskOverrides(
            trl_level=5,
            ip_score=0.5,
            complexity_score=0.6,
            platform_potential=0.5,
            integration_friction=0.5,
            dual_use_score=0.5,
            urgency_score=0.5,
            market_cagr=0.5,
            moat_score=0.5,
            regulatory_score=0.5,
            mrl_score=5,
            rnd_years=5.0,
            supply_chain_risk=0.5,
            is_miracle_tech=False,
            team_has_phd=False,
            team_has_exit=False,
            is_tier1_background=False,
            founders_worked_together=False,
            is_solo_founder=False,
            composition="Balanced",
            sentiment="Neutral",
        )

    trl = data.get("trl_score", 5)
    if isinstance(trl, float):
        trl = max(1, min(9, round(trl * 9)))
    comp = "All Scientists" if data.get("all_scientists") else ("All Biz" if data.get("all_biz") else "Balanced")

    return RiskOverrides(
        trl_level=int(trl),
        ip_score=float(data.get("ip_score", 0.5)),
        complexity_score=float(data.get("complexity_score", 0.6)),
        platform_potential=float(data.get("platform_potential", 0.5)),
        integration_friction=float(data.get("integration_friction", 0.5)),
        dual_use_score=float(data.get("dual_use_score", 0.5)),
        urgency_score=float(data.get("urgency_score", 0.5)),
        market_cagr=float(data.get("market_cagr", 0.5)),
        moat_score=float(data.get("moat_score", 0.5)),
        regulatory_score=float(data.get("regulatory_score", 0.5)),
        mrl_score=int(data.get("mrl_score", 5)),
        rnd_years=float(data.get("rnd_years", 5.0)),
        supply_chain_risk=float(data.get("supply_chain_risk", 0.5)),
        is_miracle_tech=bool(data.get("is_miracle_tech", False)),
        team_has_phd=bool(data.get("team_has_phd", False)),
        team_has_exit=bool(data.get("team_has_exit", False)),
        is_tier1_background=bool(data.get("is_tier1_background", False)),
        founders_worked_together=bool(data.get("founders_worked_together", False)),
        is_solo_founder=bool(data.get("is_solo_founder", False)),
        composition=comp,
        sentiment=str(data.get("sentiment", "Neutral")),
    )
