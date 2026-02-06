"""The Draper Scout — Deep Tech Edition. War Room PWMOIC Dashboard."""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from data import MOCK_COMPANIES
from engine import calculate_risk_factors, calculate_pwmoic, legacy_to_overrides
from agents import analyze_company_text

st.set_page_config(
    page_title="The Draper Scout | Deep Tech",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling
st.markdown("""
<style>
    .main-header { font-size: 1.8rem; font-weight: 600; color: var(--text-color, #0e1117) !important; margin-bottom: 0.25rem; }
    .sub-header { font-size: 0.95rem; color: var(--text-color, #0e1117) !important; opacity: 0.85; margin-bottom: 1rem; }
    .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; margin-right: 0.5rem; }
    .miracle-on { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
    .miracle-off { background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
        padding: 1rem 1.25rem !important; border-radius: 10px !important;
        border: 1px solid #94a3b8 !important; box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricLabel"] { color: #1e293b !important; font-size: 0.9rem !important; font-weight: 600 !important; }
    div[data-testid="stMetricValue"] { color: #0f172a !important; font-size: 2rem !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] { color: #475569 !important; font-size: 0.85rem !important; }
    h2, h3, h4 { color: var(--text-color, #f8fafc) !important; }
    hr { border-color: rgba(148, 163, 184, 0.3) !important; }
</style>
""", unsafe_allow_html=True)


def build_waterfall_chart(risk_result: dict) -> go.Figure:
    """
    Multiplicative Waterfall: each bar shows the absolute probability change.
    Bar 1: P_Tech (Start)
    Bar 2: P_Market impact (negative red)
    Bar 3: P_Scale impact (negative red)
    Bar 4: Team Multiplier impact (green boost in absolute terms)
    Bar 5: Draper Alpha impact
    Final: P_Success
    """
    wf = risk_result.get("waterfall_data", {})
    p_success = risk_result.get("p_success", 0)

    step1 = wf.get("step1_tech_start", 0)
    step2 = wf.get("step2_market_marginal", 0)
    step3 = wf.get("step3_scale_marginal", 0)
    step4 = wf.get("step4_team_marginal", 0)
    step5 = wf.get("step5_alpha_marginal", 0)

    x_labels = [
        "P_Tech<br>(Start)",
        "P_Market<br>Impact",
        "P_Scale<br>Impact",
        "Team<br>Multiplier",
        "Draper<br>Alpha",
        "P_Success",
    ]
    y_values = [step1, step2, step3, step4, step5, p_success]
    measure = ["absolute", "relative", "relative", "relative", "relative", "total"]

    def fmt(v: float) -> str:
        if abs(v) < 0.001:
            return "0"
        return f"{v:.2%}" if abs(v) < 2 else f"{v:.2f}"

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measure,
            x=x_labels,
            y=y_values,
            text=[fmt(v) for v in y_values],
            textposition="outside",
            connector={"line": {"color": "#6c757d", "width": 1, "dash": "dot"}},
            increasing={"marker": {"color": "#22c55e"}},
            decreasing={"marker": {"color": "#ef4444"}},
            totals={"marker": {"color": "#3b82f6"}},
        )
    )
    fig.update_layout(
        title="Multiplicative Waterfall — Absolute Probability Change per Step",
        xaxis_title="",
        yaxis_title="Probability",
        yaxis_tickformat=".2%",
        showlegend=False,
        height=420,
        margin=dict(t=60, b=80),
        plot_bgcolor="#334155",
        paper_bgcolor="#1e293b",
        font=dict(size=12, color="#e2e8f0"),
        title_font=dict(color="#f8fafc", size=14),
        xaxis=dict(tickfont=dict(color="#94a3b8")),
        yaxis=dict(tickfont=dict(color="#94a3b8"), gridcolor="rgba(148, 163, 184, 0.25)"),
    )
    return fig


def render_main_panel(
    risk_result: dict,
    pwmoic_result: dict,
    company_name: str = "",
    is_miracle_tech: bool = False,
):
    """War Room transparency view."""
    st.subheader(f"Results{f' — {company_name}' if company_name else ''}")

    # Status badges — visible at a glance
    miracle_class = "miracle-on" if is_miracle_tech else "miracle-off"
    miracle_label = "🧪 Miracle Tech ON" if is_miracle_tech else "Standard Mode"
    st.markdown(
        f'<span class="status-badge {miracle_class}">{miracle_label}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("")
    if is_miracle_tech:
        st.warning("⚠️ **Miracle Tech Override Active:** Market Risk is set to 0%. P_Market_Sub = 1.0 regardless of Urgency/CAGR.")

    # Top Row — Big Metrics (Smart delta colors)
    col1, col2, col3, col4 = st.columns(4)
    p_success = risk_result.get("p_success", 0)
    irr_val = float(pwmoic_result.get("final_irr", 0.0))

    with col1:
        st.metric("Final PWMOIC", f"{pwmoic_result['final_pwmoic']:.2f}x", delta=None)
    with col2:
        if p_success >= 0.5:
            surv_delta, surv_color = f"{(p_success - 0.5):+.0%} vs 50%", "normal"  # Green
        elif p_success < 0.2:
            surv_delta, surv_color = f"{(p_success - 0.2):+.0%} vs 20%", "inverse"  # Red
        else:
            surv_delta, surv_color = None, "off"  # Neutral
        st.metric(
            "Survival Probability (P_Success)",
            f"{p_success:.2%}",
            delta=surv_delta,
            delta_color=surv_color,
        )
    with col3:
        irr_delta = f"{(irr_val - 0.20):+.1%} vs 20%"
        irr_color = "off" if 0.20 <= irr_val <= 0.25 else "normal"  # Green if >25%, Red if <20%
        st.metric(
            "Implied IRR",
            f"{irr_val:.1%}",
            delta=irr_delta,
            delta_color=irr_color,
        )
    with col4:
        t = pwmoic_result.get("time_to_exit_years", None)
        st.metric("Time to Exit", f"{int(t)} yrs" if t is not None else "—", delta=None)

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📈 Visual Waterfall", "🧮 The Math (Detailed Breakdown)", "💵 Financial Scenarios"])

    with tab1:
        fig = build_waterfall_chart(risk_result)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🔴 Red bars = Risk penalties (Market, Scale). 🟢 Green bars = Team/Alpha multipliers.")

    with tab2:
        with st.expander("📚 Definitions & Methodology", expanded=False):
            st.markdown("""
            **V6 Logic — Four Pillars (Multiplicative):**
            - **The Physics:** TRL (30%) + IP (20%) + Complexity (15%) + Platform Potential (20%) + Integration Friction (15%)
            - **The Future:** Dual Use (30%) + Urgency (25%) + CAGR (20%) + Moat Score (25%). Miracle Tech → 1.0
            - **The Scale:** Regulatory (20%) + MRL (30%) + R&D Time (20%) + Supply Chain (30%)
            - **The Team:** Founder–Market Fit + Super Founder signals (PhD, Exit, Tier 1, Shared History)
            """)
        st.markdown("")
        math_tables = risk_result.get("math_tables", {})
        cols = ["Factor", "User Input", "Assigned Score", "Weight", "Contribution"]

        st.markdown("#### 1. Sub-Factors (Weighted Averages, 0–1 Quality Scores)")
        st.markdown("**P_Tech_Sub** = TRL (30%) + IP (20%) + Complexity (15%) + Platform (20%) + Integration (15%)")
        df_tech = pd.DataFrame(math_tables.get("tech", []), columns=cols)
        st.dataframe(df_tech, use_container_width=True, hide_index=True)

        st.markdown("**P_Market_Sub** = Dual Use (30%) + Urgency (25%) + CAGR (20%) + Moat (25%)  *(Miracle Tech → 1.0)*")
        df_market = pd.DataFrame(math_tables.get("market", []), columns=cols)
        st.dataframe(df_market, use_container_width=True, hide_index=True)

        st.markdown("**P_Scale_Sub** = Regulatory (20%) + MRL (30%) + R&D Time (20%) + Supply Chain (30%)")
        df_scale = pd.DataFrame(math_tables.get("scale", []), columns=cols)
        st.dataframe(df_scale, use_container_width=True, hide_index=True)

        st.markdown("#### 2. Base Probability & Final (Multiplicative Waterfall)")
        st.markdown("**Base_Probability** = P_Tech_Sub × P_Market_Sub × P_Scale_Sub  *(if any pillar = 0, deal dies)*")
        st.markdown("**P_Success** = min(0.99, max(0.01, Base × Multiplier × Draper_Alpha))  *(hard cap 1%–99%)*")
        df_base = pd.DataFrame(math_tables.get("base", []), columns=["Factor", "Formula", "Value", "Type", "Result"])
        st.dataframe(df_base, use_container_width=True, hide_index=True)

    with tab3:
        with st.expander("📚 How We Calculate Valuation (First Chicago Method)", expanded=False):
            st.markdown("""
            **The Logic:** We don't just guess probabilities — we derive them from the Risk Engine (P_Success).  
            The three scenarios below are the possible futures; their probabilities sum to 100%.

            - **Scenario 1 (Failure):** Probability = 100% − Survival Rate. Assumes 0.5× recovery (partial recoup).
            - **Scenario 2 (Base Case):** Probability = Survival Rate × (1 − Home Run Split). Assumes 2–3× modest exit ($200M).
            - **Scenario 3 (Home Run):** Probability = Survival Rate × Home Run Split. The Power Law outcome (>10×, $2B).

            **IRR Formula:** $IRR = (MOIC)^{\\frac{1}{Years}} - 1$  
            *(Annualized return from the multiple over the hold period.)*
            """)
        st.markdown("")
        scenarios = pwmoic_result["scenarios"]
        scenario_data = [
            {
                "Scenario": "Failure",
                "Probability": f"{scenarios['failure']['probability']:.2%}",
                "Implied MOIC": f"{scenarios['failure']['moic']:.2f}x",
                "IRR": f"{float(scenarios['failure'].get('irr', 0.0)):.1%}",
                "Exit Value ($M)": "—",
                "Dilution": "—",
            },
            {
                "Scenario": "Base Case",
                "Probability": f"{scenarios['base_case']['probability']:.2%}",
                "Implied MOIC": f"{scenarios['base_case']['moic']:.2f}x",
                "IRR": f"{float(scenarios['base_case'].get('irr', 0.0)):.1%}",
                "Exit Value ($M)": f"{scenarios['base_case']['exit_val_m']:.0f}",
                "Dilution": f"{scenarios['base_case']['dilution']:.0%}",
            },
            {
                "Scenario": "Home Run",
                "Probability": f"{scenarios['home_run']['probability']:.2%}",
                "Implied MOIC": f"{scenarios['home_run']['moic']:.2f}x",
                "IRR": f"{float(scenarios['home_run'].get('irr', 0.0)):.1%}",
                "Exit Value ($M)": f"{scenarios['home_run']['exit_val_m']:.0f}",
                "Dilution": f"{scenarios['home_run']['dilution']:.0%}",
            },
        ]
        st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)
        st.caption("Note: Probabilities sum to 100%. PWMOIC is the weighted average of these three futures.")


# ——— Sidebar ———
st.sidebar.markdown("### ⚙️ Configuration")
mode = st.sidebar.selectbox("Choose Mode", ["Demo Data", "Live Analysis"], index=0)
company = st.sidebar.selectbox("Select Company", list(MOCK_COMPANIES.keys()), index=0)

data = MOCK_COMPANIES.get(company, {}) if mode == "Demo Data" else {}
defaults = legacy_to_overrides(data)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Overrides")

with st.sidebar.expander("🔬 The Physics (Technical Inputs)", expanded=True):
    trl = st.slider(
        "TRL Level (1–9)",
        1, 9, defaults.get("trl_level", 5), 1,
        help="Technology Readiness Level. 1=Concept, 5=Lab Validated, 9=System Proven.",
    )
    ip_score = st.slider(
        "IP Score (0.0=None, 0.5=Pending, 1.0=Granted)",
        0.0, 1.0, float(defaults.get("ip_score", 0.5)), 0.05,
        help="Patent strength. Granted IP protects defensibility; Pending shows intent.",
    )
    complexity_score = st.slider(
        "Complexity Score (0.3=New Science … 0.9=Software)",
        0.0, 1.0, float(defaults.get("complexity_score", 0.6)), 0.05,
        help="New Science (0.3) = unproven physics. Software (0.9) = faster iteration.",
    )
    platform_potential = st.slider(
        "Platform Potential (0.0–1.0)",
        0.0, 1.0, float(defaults.get("platform_potential", 0.5)), 0.05,
        help="Does it enable multiple product lines? 0.2=Single product, 0.5=Some extensibility, 1.0=Ecosystem/vertical expansion.",
    )
    integration_friction = st.slider(
        "Integration Friction (0.0–1.0)",
        0.0, 1.0, float(defaults.get("integration_friction", 0.5)), 0.05,
        help="1.0=Drop-in / plug-and-play. 0.2=Infrastructure overhaul / system retrofit required.",
    )

with st.sidebar.expander("📊 The Market (Future Bet Pillar)", expanded=True):
    dual_use_score = st.slider(
        "Dual-Use Score (0.5=Commercial … 0.95=Dual)",
        0.0, 1.0, float(defaults.get("dual_use_score", 0.5)), 0.05,
        help="Dual Use = Gov + Commercial demand (defense, energy). Higher = more TAM.",
    )
    urgency_score = st.slider(
        "Urgency Score (0.0–1.0)",
        0.0, 1.0, float(defaults.get("urgency_score", 0.5)), 0.05,
        help="How critical is the problem? 0.1=Vitamin (nice to have), 0.9=Painkiller (critical/life-saving).",
    )
    market_cagr = st.slider(
        "Market CAGR (0.0–1.0)",
        0.0, 1.0, float(defaults.get("market_cagr", 0.5)), 0.05,
        help="Compound Annual Growth Rate. VCs target >20%. 0.5 ≈ 20%, 0.8 ≈ 30%+.",
    )
    moat_score = st.slider(
        "Moat Score (0.0–1.0)",
        0.0, 1.0, float(defaults.get("moat_score", 0.5)), 0.05,
        help="Network effects, switching costs, proprietary data. 0.2=Commodity, 1.0=Strong lock-in.",
    )
    is_miracle_tech = st.checkbox(
        "🧪 Miracle Tech (Infinite Demand)",
        value=bool(defaults.get("is_miracle_tech", False)),
        help="If checked, assumes infinite demand (Market = 1.0) regardless of other factors. Use for Fusion/Cure for Cancer.",
    )

with st.sidebar.expander("🏭 The Scale (Lab-to-Fab Pillar)", expanded=True):
    mrl_score = st.slider(
        "MRL Level (1–9)",
        1, 9, int(defaults.get("mrl_score", 5)), 1,
        help="Manufacturing Readiness Level. 1=Basic Research, 4=Prototype, 8=Pilot Line, 9=Mass Production.",
    )
    rnd_years = st.slider(
        "Years to Launch",
        0.0, 10.0, float(defaults.get("rnd_years", 5.0)), 0.5,
        help="Years until commercial launch. Deep Tech avg is 5–7 years.",
    )
    regulatory_score = st.slider(
        "Regulatory Score (0.0–1.0)",
        0.0, 1.0, float(defaults.get("regulatory_score", 0.5)), 0.05,
        help="0.2=Complex (FDA, NRC). 0.8=Clear path to market.",
    )
    supply_chain_risk = st.slider(
        "Supply Chain Risk (0.0–1.0)",
        0.0, 1.0, float(defaults.get("supply_chain_risk", 0.5)), 0.05,
        help="1.0=Domestic/Friendly sourcing. 0.0=Hostile dependency or single-source (e.g. rare earths, China).",
    )

with st.sidebar.expander("👥 The Team (Super Founder Matrix)", expanded=True):
    phd = st.toggle("PhD in Field?", defaults.get("team_has_phd", False), help="Technical depth in the domain.")
    exit_ = st.toggle("Previous Exit?", defaults.get("team_has_exit", False), help="Prior successful exit (M&A or IPO).")
    is_tier1 = st.checkbox(
        "Tier 1 Background? (Stanford/SpaceX/etc)",
        value=bool(defaults.get("is_tier1_background", False)),
        help="Tier 1 = Ex-Google, SpaceX, Stanford, MIT, McKinsey — proven pedigree.",
    )
    founders_worked_together = st.checkbox(
        "Founders have Shared History?",
        value=bool(defaults.get("founders_worked_together", False)),
        help="Co-founded previous company or worked together at prior employer.",
    )
    is_solo_founder = st.checkbox(
        "Solo Founder?",
        value=bool(defaults.get("is_solo_founder", False)),
        help="Single founder increases execution risk.",
    )
    composition = st.selectbox(
        "Composition",
        ["Balanced", "All Scientists", "All Biz"],
        index=["Balanced", "All Scientists", "All Biz"].index(defaults.get("composition", "Balanced")),
        help="Balanced = best. All Scientists = execution risk. All Biz = technical credibility risk.",
    )

with st.sidebar.expander("💰 The Money (Financial Scenarios)", expanded=True):
    entry_val = data.get("entry_valuation", 15.0) if data else 15.0
    entry_valuation = st.slider(
        "Entry Valuation ($M)", 5.0, 100.0, float(entry_val), 1.0,
        help="Pre-money valuation at investment. Affects MOIC directly.",
    )
    home_run_split = st.slider(
        "Home Run Ratio", 0.1, 0.9, 0.2, 0.05,
        help="Split of success cases that become Home Run ($2B exit) vs Base Case ($200M).",
    )
    time_to_exit_years = st.slider(
        "Time to Exit (Years)", 3, 15, 7, 1,
        help="Expected hold period. Used for IRR calculation.",
    )

api_key = st.sidebar.text_input("OpenAI API Key", type="password", placeholder="sk-...")

overrides = {
    "trl_level": trl,
    "ip_score": ip_score,
    "complexity_score": complexity_score,
    "platform_potential": platform_potential,
    "integration_friction": integration_friction,
    "dual_use_score": dual_use_score,
    "urgency_score": urgency_score,
    "market_cagr": market_cagr,
    "moat_score": moat_score,
    "regulatory_score": regulatory_score,
    "mrl_score": mrl_score,
    "rnd_years": rnd_years,
    "supply_chain_risk": supply_chain_risk,
    "is_miracle_tech": is_miracle_tech,
    "team_has_phd": phd,
    "team_has_exit": exit_,
    "is_tier1_background": is_tier1,
    "founders_worked_together": founders_worked_together,
    "is_solo_founder": is_solo_founder,
    "composition": composition,
    "sentiment": defaults.get("sentiment", "Neutral"),
}

st.markdown('<p class="main-header">The Draper Scout</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">V6.0 Robustness — Granular Precision + Supply Chain + Platform (Multiplicative Model)</p>', unsafe_allow_html=True)

with st.expander("📖 What is PWMOIC? Understanding the Model", expanded=False):
    st.markdown("""
    **PWMOIC** = *Probability-Weighted Multiple on Invested Capital* — the expected return (in multiples) accounting for risk.

    **How it works:** We model three scenarios and weight each by its probability:
    - **Failure** (1 − P_Success): Recoup 0.5x. The deal doesn't work out.
    - **Base Case** (P_Success × (1 − Home Run Ratio)): Exit at $200M, 50% dilution. Steady outcome.
    - **Home Run** (P_Success × Home Run Ratio): Exit at $2B, 70% dilution. Deep Tech unicorn.

    **Key parameters** (set in the sidebar under "The Money"):
    - **Entry Valuation ($M):** Pre-money valuation. Lower = higher MOIC potential.
    - **Home Run Ratio:** Share of success cases that become Home Run vs Base Case. Higher = more upside concentration.
    - **Time to Exit:** Years until liquidity. Drives IRR from MOIC.

    **Top metrics explained:**
    - **Final PWMOIC:** Expected multiple (e.g. 2.5x = $1 invested → $2.50 expected).
    - **Survival Probability (P_Success):** Odds the company reaches a successful outcome (Base or Home Run).
    - **Implied IRR:** Annualized return; VCs typically target >20%.
    - **Time to Exit:** Hold period used for IRR calculation.
    """)
st.markdown("---")

# ——— Main Panel ———
if mode == "Demo Data":
    risk_result = calculate_risk_factors(overrides)
    pwmoic_result = calculate_pwmoic(
        risk_result["p_success"],
        entry_valuation,
        home_run_split,
        time_to_exit_years,
    )
    pwmoic_result["time_to_exit_years"] = time_to_exit_years
    render_main_panel(risk_result, pwmoic_result, company or "", is_miracle_tech)
else:
    st.markdown("**Live Analysis** — Paste company text below.")
    text_content = st.text_area("Paste Company Homepage/About Us Text", height=180, placeholder="Paste text...")
    if st.button("Run Draper Scout", type="primary"):
        if not api_key:
            st.error("Please enter your OpenAI API key.")
        elif not (text_content or "").strip():
            st.error("Please paste company text.")
        else:
            with st.spinner("Analyzing with GPT-4o..."):
                try:
                    metrics = analyze_company_text(api_key, text_content)
                    ai_overrides = {
                        "trl_level": int(metrics.get("trl_score", 5)),
                        "mrl_score": int(metrics.get("mrl_score", 5)),
                        "ip_score": float(metrics.get("ip_score", 0.5)),
                        "complexity_score": float(metrics.get("complexity_score", 0.6)),
                        "platform_potential": float(metrics.get("platform_potential", 0.5)),
                        "integration_friction": float(metrics.get("integration_friction", 0.5)),
                        "dual_use_score": float(metrics.get("dual_use_score", 0.5)),
                        "urgency_score": float(metrics.get("urgency_score", 0.5)),
                        "market_cagr": float(metrics.get("market_cagr", 0.5)),
                        "moat_score": float(metrics.get("moat_score", 0.5)),
                        "regulatory_score": float(metrics.get("regulatory_score", 0.5)),
                        "rnd_years": float(metrics.get("rnd_years", 5.0)),
                        "supply_chain_risk": float(metrics.get("supply_chain_risk", 0.5)),
                        "is_miracle_tech": bool(overrides.get("is_miracle_tech", False)),
                        "team_has_phd": metrics.get("team_has_phd", False),
                        "team_has_exit": metrics.get("team_has_exit", False),
                        "is_tier1_background": metrics.get("is_tier1_background", False),
                        "founders_worked_together": metrics.get("founders_worked_together", False),
                        "is_solo_founder": metrics.get("is_solo_founder", False),
                        "composition": "Balanced",
                        "sentiment": "Neutral",
                    }
                    merged = {**ai_overrides, **overrides}
                    risk_result = calculate_risk_factors(merged)
                    pwmoic_result = calculate_pwmoic(
                        risk_result["p_success"],
                        entry_valuation,
                        home_run_split,
                        time_to_exit_years,
                    )
                    pwmoic_result["time_to_exit_years"] = time_to_exit_years
                    render_main_panel(risk_result, pwmoic_result, "", is_miracle_tech)
                except (ValueError, Exception) as e:
                    st.error(str(e))
