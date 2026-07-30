"""Interactive dashboard for the contract-driven V2 PF model.

Run with:
    streamlit run pf_liquidity_risk/v2_app.py
"""

from dataclasses import replace

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pf_liquidity_risk.modeling.v2.monte_carlo import (
    run_v2_monte_carlo,
    summarize_v2_results,
)
from pf_liquidity_risk.modeling.v2.project import (
    ProjectV2Config,
    build_base_project_config,
    run_project,
)

st.set_page_config(
    page_title="PF Liquidity Risk V2",
    page_icon="🏗️",
    layout="wide",
)


def _percent(value: float) -> str:
    return f"{value:.1%}"


def _amount(value: float) -> str:
    return f"{value:,.1f}억"


def _build_user_config(
    *,
    rent_factor: float,
    stabilized_occupancy: float,
    takeout_rate: float,
    takeout_ltv: float,
    minimum_debt_yield: float,
    minimum_dscr: float,
    exit_cap_rate: float,
) -> ProjectV2Config:
    base = build_base_project_config()
    operating = replace(
        base.operating,
        anchor=replace(
            base.operating.anchor,
            monthly_base_rent_per_area=(
                base.operating.anchor.monthly_base_rent_per_area * rent_factor
            ),
        ),
        non_anchor=replace(
            base.operating.non_anchor,
            monthly_base_rent_per_area=(
                base.operating.non_anchor.monthly_base_rent_per_area * rent_factor
            ),
            stabilized_occupancy=stabilized_occupancy,
        ),
    )
    takeout = replace(
        base.takeout,
        annual_interest_rate=takeout_rate,
        maximum_ltv=takeout_ltv,
        minimum_debt_yield=minimum_debt_yield,
        minimum_dscr=minimum_dscr,
    )
    sale = replace(base.sale, exit_capitalization_rate=exit_cap_rate)
    return replace(base, operating=operating, takeout=takeout, sale=sale)


@st.cache_data(show_spinner=False)
def _cached_simulation(
    iterations: int,
    seed: int,
    rent_factor: float,
    stabilized_occupancy: float,
    takeout_rate: float,
    takeout_ltv: float,
    minimum_debt_yield: float,
    minimum_dscr: float,
    exit_cap_rate: float,
) -> pd.DataFrame:
    config = _build_user_config(
        rent_factor=rent_factor,
        stabilized_occupancy=stabilized_occupancy,
        takeout_rate=takeout_rate,
        takeout_ltv=takeout_ltv,
        minimum_debt_yield=minimum_debt_yield,
        minimum_dscr=minimum_dscr,
        exit_cap_rate=exit_cap_rate,
    )
    return run_v2_monte_carlo(
        iterations=iterations,
        seed=seed,
        base=config,
    )


with st.sidebar:
    st.header("Underwriting assumptions")
    rent_factor = st.slider("임대료 배수", 0.70, 1.20, 1.00, 0.01)
    stabilized_occupancy = st.slider("비앵커 안정화 점유율", 0.60, 1.00, 0.95, 0.01)
    takeout_rate = st.slider("대환 금리", 0.03, 0.12, 0.055, 0.0025)
    takeout_ltv = st.slider("대환 최대 LTV", 0.40, 0.80, 0.65, 0.01)
    minimum_debt_yield = st.slider("최소 Debt Yield", 0.05, 0.15, 0.08, 0.005)
    minimum_dscr = st.slider("최소 DSCR", 1.00, 2.00, 1.40, 0.05)
    exit_cap_rate = st.slider("Exit cap rate", 0.035, 0.10, 0.0575, 0.0025)
    st.divider()
    iterations = st.select_slider(
        "Monte Carlo 반복",
        options=[100, 250, 500, 1_000, 2_000],
        value=1_000,
    )
    seed = st.number_input("Random seed", min_value=0, value=42, step=1)


config = _build_user_config(
    rent_factor=rent_factor,
    stabilized_occupancy=stabilized_occupancy,
    takeout_rate=takeout_rate,
    takeout_ltv=takeout_ltv,
    minimum_debt_yield=minimum_debt_yield,
    minimum_dscr=minimum_dscr,
    exit_cap_rate=exit_cap_rate,
)
result = run_project(config)

st.title("PF Liquidity Risk V2")
st.caption(
    "국내 임대형 PF의 브리지–본PF–리스업–대환–매각을 월별 계약으로 연결한 "
    "교육용 합성 사례입니다. 시장 전망이나 투자 권유가 아닙니다."
)

st.subheader("Deterministic underwriting")
metric_columns = st.columns(6)
metric_columns[0].metric("경로", result.status)
metric_columns[1].metric("종료 월", f"M{result.terminal_month}")
metric_columns[2].metric("Sponsor 투자", _amount(result.sponsor_equity_invested))
metric_columns[3].metric("Sponsor 회수", _amount(result.sponsor_distribution))
metric_columns[4].metric("Sponsor IRR", _percent(result.sponsor_irr))
metric_columns[5].metric("Lender shortfall", _amount(result.lender_shortfall))

first_refi = result.refinance_attempts[0] if result.refinance_attempts else None
left, right = st.columns((3, 2))
with left:
    chart_ledger = result.ledger[
        [
            "month",
            "senior_closing_balance",
            "subordinate_closing_balance",
            "takeout_closing_balance",
        ]
    ].melt(id_vars="month", var_name="facility", value_name="balance")
    debt_chart = px.area(
        chart_ledger,
        x="month",
        y="balance",
        color="facility",
        title="Debt balance by facility (억원)",
    )
    debt_chart.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(debt_chart, width="stretch")

with right:
    if first_refi is not None:
        capacities = first_refi.capacity
        capacity_chart = go.Figure(
            go.Bar(
                x=[
                    capacities.ltv_capacity,
                    capacities.debt_yield_capacity,
                    capacities.dscr_capacity,
                    capacities.lender_commitment_cap,
                ],
                y=["LTV", "Debt yield", "DSCR", "Commitment"],
                orientation="h",
                marker_color=["#2563EB", "#0EA5E9", "#14B8A6", "#64748B"],
            )
        )
        capacity_chart.add_vline(
            x=first_refi.debt_payoff_requirement,
            line_dash="dash",
            line_color="#DC2626",
            annotation_text="Debt payoff",
        )
        capacity_chart.update_layout(
            title=(f"Take-out capacity · binding: {capacities.binding_constraint}"),
            xaxis_title="억원",
            yaxis_title="",
        )
        st.plotly_chart(capacity_chart, width="stretch")
    else:
        st.info("대환 심사 전 프로젝트가 종료되었습니다.")

cash_chart = px.line(
    result.ledger,
    x="month",
    y=["property_noi", "interest_expense", "closing_cash"],
    title="Monthly NOI, interest, and retained cash (억원)",
)
cash_chart.update_layout(legend_title_text="", hovermode="x unified")
st.plotly_chart(cash_chart, width="stretch")

with st.expander("월별 통합 원장"):
    st.dataframe(result.ledger, width="stretch", hide_index=True)
    st.download_button(
        "원장 CSV 다운로드",
        data=result.ledger.to_csv(index=False).encode("utf-8-sig"),
        file_name="pf_v2_base_ledger.csv",
        mime="text/csv",
    )

st.divider()
st.subheader("Regime-correlated Monte Carlo")
st.caption(
    "Normal 60% / Stress 30% / Severe 10%는 관측 빈도가 아니라 학습용 스트레스 "
    "가중치입니다. 같은 regime 안에서 공사비·지연·임대·금리·cap rate가 함께 악화됩니다."
)

simulation_key = (
    iterations,
    int(seed),
    rent_factor,
    stabilized_occupancy,
    takeout_rate,
    takeout_ltv,
    minimum_debt_yield,
    minimum_dscr,
    exit_cap_rate,
)
if st.button("Monte Carlo 실행", type="primary"):
    with st.spinner(f"{iterations:,}개 경로 계산 중..."):
        st.session_state["v2_simulation"] = _cached_simulation(*simulation_key)
        st.session_state["v2_simulation_key"] = simulation_key

simulation = st.session_state.get("v2_simulation")
stored_key = st.session_state.get("v2_simulation_key")
if simulation is not None and stored_key == simulation_key:
    summary = summarize_v2_results(simulation)
    summary_columns = st.columns(5)
    summary_columns[0].metric("대환 성공률", _percent(summary["refi_success_rate"]))
    summary_columns[1].metric("연장 사용률", _percent(summary["extension_rate"]))
    summary_columns[2].metric(
        "Distress/default",
        _percent(summary["distressed_or_default_rate"]),
    )
    summary_columns[3].metric(
        "정상 Exit",
        _percent(summary["successful_exit_rate"]),
    )
    summary_columns[4].metric(
        "Portfolio sponsor loss",
        _percent(summary["portfolio_sponsor_loss_pct"]),
    )

    outcome = (
        simulation.groupby(["regime", "status"], observed=True).size().reset_index(name="count")
    )
    outcome_chart = px.bar(
        outcome,
        x="regime",
        y="count",
        color="status",
        barmode="stack",
        title="Outcome distribution by macro regime",
    )
    st.plotly_chart(outcome_chart, width="stretch")

    successful = simulation[simulation["status"].isin(["exit", "exit_after_extension"])]
    if not successful.empty:
        irr_chart = px.histogram(
            successful,
            x="sponsor_irr",
            color="regime",
            nbins=40,
            title="Sponsor IRR distribution · successful exits",
        )
        irr_chart.update_xaxes(tickformat=".0%")
        st.plotly_chart(irr_chart, width="stretch")

    with st.expander("Scenario-level 결과"):
        st.dataframe(simulation, width="stretch", hide_index=True)
        st.download_button(
            "Scenario CSV 다운로드",
            data=simulation.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"pf_v2_monte_carlo_{iterations}_{int(seed)}.csv",
            mime="text/csv",
        )
elif simulation is not None:
    st.info("가정이 바뀌었습니다. 새 가정으로 Monte Carlo를 다시 실행하세요.")
