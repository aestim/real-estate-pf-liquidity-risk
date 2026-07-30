"""Beginner-friendly dashboard for the contract-driven V2 PF model.

Run with:
    streamlit run pf_liquidity_risk/v2_app.py
"""

from dataclasses import replace

import pandas as pd
import streamlit as st

from pf_liquidity_risk.modeling.v2.monte_carlo import (
    run_v2_monte_carlo,
    summarize_v2_results,
)
from pf_liquidity_risk.modeling.v2.project import (
    ProjectV2Config,
    ProjectV2Result,
    build_base_project_config,
    run_project,
)

st.set_page_config(
    page_title="PF Risk Simulator",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
    <style>
    @media (max-width: 480px) {
        h1 {
            font-size: 2rem !important;
            line-height: 1.25 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


PRESETS = {
    "기준": {
        "rent_factor": 1.00,
        "stabilized_occupancy": 0.95,
        "takeout_rate": 0.055,
        "takeout_ltv": 0.65,
        "minimum_debt_yield": 0.08,
        "minimum_dscr": 1.40,
        "exit_cap_rate": 0.0575,
    },
    "보수적": {
        "rent_factor": 0.90,
        "stabilized_occupancy": 0.85,
        "takeout_rate": 0.075,
        "takeout_ltv": 0.58,
        "minimum_debt_yield": 0.09,
        "minimum_dscr": 1.50,
        "exit_cap_rate": 0.07,
    },
    "낙관적": {
        "rent_factor": 1.05,
        "stabilized_occupancy": 0.97,
        "takeout_rate": 0.045,
        "takeout_ltv": 0.70,
        "minimum_debt_yield": 0.075,
        "minimum_dscr": 1.30,
        "exit_cap_rate": 0.0525,
    },
}

PRESET_DESCRIPTIONS = {
    "기준": "현재 합성 기준값입니다. 사용법을 익힐 때 선택하세요.",
    "보수적": "임대는 약하고, 금리와 매각 cap rate는 높은 상황입니다.",
    "낙관적": "임대가 좋고, 금리와 매각 cap rate는 낮은 상황입니다.",
}

BINDING_LABELS = {
    "ltv": "LTV(건물가치 기준)",
    "debt_yield": "Debt Yield(NOI 기준)",
    "dscr": "DSCR(이자상환능력 기준)",
    "lender_commitment": "은행 약정한도",
}


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


def _render_status(result: ProjectV2Result) -> None:
    if result.status == "exit":
        st.success(
            f"**대환 성공 · M{result.terminal_month} 정상 매각**\n\n"
            "운영대출로 기존 PF를 갚았고 계획한 시점에 매각했습니다.",
            icon="✅",
        )
    elif result.status == "exit_after_extension":
        st.warning(
            f"**연장 후 대환 성공 · M{result.terminal_month} 매각**\n\n"
            "첫 대환은 부족했지만 6개월 연장 후 사업을 정상화했습니다.",
            icon="⚠️",
        )
    else:
        st.error(
            f"**자금 부족 · M{result.terminal_month} 부실 처리**\n\n"
            "대환 또는 운영자금이 부족해 부실매각이나 개발부도가 발생했습니다.",
            icon="🚨",
        )


def _simple_outcome(status: str) -> str:
    if status == "exit":
        return "정상 종료"
    if status == "exit_after_extension":
        return "연장 후 정상 종료"
    return "부실·부도"


st.title("PF 사업 안전성 계산기")
st.write("건물을 짓고 임대해 **기존 PF 대출을 갚을 수 있는지** 확인합니다.")
st.info(
    "**사용법** ① 상황을 고르고 → ② 결과를 확인하고 → ③ 필요하면 가상 미래 테스트를 실행하세요.",
    icon="👋",
)
st.caption("교육용 합성 사례입니다. 실제 시장 전망이나 투자·대출 의사결정에 사용할 수 없습니다.")

st.markdown("### 1. 사업 상황 선택")
preset_name = st.radio(
    "사업 상황",
    options=list(PRESETS),
    horizontal=True,
    label_visibility="collapsed",
)
st.caption(PRESET_DESCRIPTIONS[preset_name])
preset = PRESETS[preset_name]

with st.expander("숫자를 직접 바꾸고 싶다면"):
    st.caption("처음에는 건드리지 않아도 됩니다. 각 숫자의 설명은 ⓘ에 있습니다.")
    left_controls, right_controls = st.columns(2)
    with left_controls:
        rent_percent = st.slider(
            "임대료 수준",
            min_value=70,
            max_value=120,
            value=round(preset["rent_factor"] * 100),
            step=1,
            format="%d%%",
            help="100%가 기준 임대료입니다.",
            key=f"rent_percent_{preset_name}",
        )
        occupancy_percent = st.slider(
            "안정화 점유율",
            min_value=60,
            max_value=100,
            value=round(preset["stabilized_occupancy"] * 100),
            step=1,
            format="%d%%",
            help="임대가 안정된 뒤 일반 임차구역에 입주한 비율입니다.",
            key=f"occupancy_percent_{preset_name}",
        )
        takeout_rate_percent = st.slider(
            "대환대출 금리",
            min_value=3.0,
            max_value=12.0,
            value=preset["takeout_rate"] * 100,
            step=0.25,
            format="%.2f%%",
            help="준공 후 기존 PF를 갚기 위해 받는 운영대출 금리입니다.",
            key=f"takeout_rate_percent_{preset_name}",
        )
        takeout_ltv_percent = st.slider(
            "은행 최대 LTV",
            min_value=40,
            max_value=80,
            value=round(preset["takeout_ltv"] * 100),
            step=1,
            format="%d%%",
            help="은행이 건물가치 대비 빌려줄 수 있는 최대 비율입니다.",
            key=f"takeout_ltv_percent_{preset_name}",
        )
    with right_controls:
        debt_yield_percent = st.slider(
            "은행 최소 Debt Yield",
            min_value=5.0,
            max_value=15.0,
            value=preset["minimum_debt_yield"] * 100,
            step=0.5,
            format="%.1f%%",
            help="연 NOI를 대출금으로 나눈 값입니다. 높게 요구할수록 대출한도가 줄어듭니다.",
            key=f"debt_yield_percent_{preset_name}",
        )
        minimum_dscr = st.slider(
            "은행 최소 DSCR",
            min_value=1.0,
            max_value=2.0,
            value=preset["minimum_dscr"],
            step=0.05,
            format="%.2f배",
            help="NOI가 연간 채무상환액의 몇 배여야 하는지 나타냅니다.",
            key=f"minimum_dscr_{preset_name}",
        )
        exit_cap_rate_percent = st.slider(
            "매각 cap rate",
            min_value=3.5,
            max_value=10.0,
            value=preset["exit_cap_rate"] * 100,
            step=0.25,
            format="%.2f%%",
            help="같은 NOI라면 cap rate가 높을수록 건물가치는 낮아집니다.",
            key=f"exit_cap_rate_percent_{preset_name}",
        )

assumptions = {
    "rent_factor": rent_percent / 100,
    "stabilized_occupancy": occupancy_percent / 100,
    "takeout_rate": takeout_rate_percent / 100,
    "takeout_ltv": takeout_ltv_percent / 100,
    "minimum_debt_yield": debt_yield_percent / 100,
    "minimum_dscr": minimum_dscr,
    "exit_cap_rate": exit_cap_rate_percent / 100,
}
config = _build_user_config(**assumptions)
result = run_project(config)
first_refi = result.refinance_attempts[0] if result.refinance_attempts else None

st.markdown("### 2. 결과 확인")
overview_tab, cash_tab, stress_tab = st.tabs(["한눈에 보기", "돈 흐름 자세히", "가상 미래 테스트"])

with overview_tab:
    _render_status(result)

    annual_noi = first_refi.capacity.annual_underwritten_noi if first_refi is not None else 0.0
    refinance_capacity = first_refi.capacity.gross_capacity if first_refi is not None else 0.0
    debt_payoff = first_refi.debt_payoff_requirement if first_refi is not None else 0.0

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "연 NOI",
        _amount(annual_noi) if first_refi is not None else "-",
        help="최근 3개월 건물 순영업소득을 1년 금액으로 바꾼 값입니다.",
    )
    metric_columns[1].metric(
        "은행 대환한도",
        _amount(refinance_capacity) if first_refi is not None else "-",
        help="LTV·Debt Yield·DSCR·은행 약정한도 중 가장 작은 값입니다.",
    )
    metric_columns[2].metric(
        "갚을 기존 대출",
        _amount(debt_payoff) if first_refi is not None else "-",
        help="대환 시점의 선순위·후순위 PF 잔액입니다.",
    )
    metric_columns[3].metric(
        "시행사 투입 → 회수",
        f"{result.sponsor_equity_invested:,.1f} → {result.sponsor_distribution:,.1f}억",
        help="시행사가 실제로 넣은 총금액과 매각 때 받은 금액입니다.",
    )

    if first_refi is not None:
        required_draw = first_refi.required_gross_draw
        readiness = refinance_capacity / required_draw if required_draw > 0 else 1.0
        st.markdown("#### 대환 준비도")
        st.progress(
            min(readiness, 1.0),
            text=f"은행 대환한도는 필요한 신규대출의 {readiness:.0%}입니다.",
        )
        binding_label = BINDING_LABELS.get(
            first_refi.capacity.binding_constraint,
            first_refi.capacity.binding_constraint,
        )
        st.write(
            f"- 필요한 신규대출: **{_amount(required_draw)}**  \n"
            f"- 은행 대환한도: **{_amount(refinance_capacity)}**  \n"
            f"- 실제 한도를 결정한 조건: **{binding_label}**"
        )
    else:
        st.warning("대환 심사 전에 사업이 종료되어 대환한도를 계산하지 못했습니다.")

    st.markdown("#### 사업 일정")
    timeline = ["M0 토지 매입", "M6 본PF", "M24 준공", "M36 대환"]
    if result.status == "exit":
        timeline.append(f"M{result.terminal_month} 정상매각")
    elif result.status == "exit_after_extension":
        timeline.extend(["M42 대환 재심사", f"M{result.terminal_month} 정상매각"])
    else:
        timeline.append(f"M{result.terminal_month} 부실 처리")
    st.write(f"**{' → '.join(timeline)}**")

    with st.expander("투자수익과 부실금액 보기"):
        detail_columns = st.columns(3)
        detail_columns[0].metric("시행사 IRR", _percent(result.sponsor_irr))
        detail_columns[1].metric(
            "시행사 회수배수",
            f"{result.sponsor_equity_multiple:.2f}배",
        )
        detail_columns[2].metric(
            "은행 미회수액",
            _amount(result.lender_shortfall),
        )
        st.caption(
            "높은 IRR은 낮은 시행사 직접출자와 높은 레버리지의 결과입니다. "
            "실제 기대수익률이 아닙니다."
        )

    with st.expander("용어를 잘 모르겠다면"):
        st.markdown(
            """
            - **NOI**: 월세 등 건물수입에서 건물 운영비를 뺀 돈
            - **대환**: 비싼 건설대출을 준공 후 운영대출로 갈아타는 것
            - **LTV**: 건물가치에 비해 대출이 얼마나 큰지 나타내는 비율
            - **Debt Yield**: 연 NOI를 대출금으로 나눈 값
            - **DSCR**: NOI가 1년치 빚 상환액의 몇 배인지 나타내는 값
            - **IRR**: 돈을 넣고 회수한 시점까지 반영한 연 수익률
            """
        )

with cash_tab:
    st.write("처음에는 건너뛰어도 됩니다. 사업기간 동안 빚과 현금이 어떻게 변하는지 봅니다.")

    debt_chart = (
        result.ledger[
            [
                "month",
                "senior_closing_balance",
                "subordinate_closing_balance",
                "takeout_closing_balance",
            ]
        ]
        .rename(
            columns={
                "month": "월",
                "senior_closing_balance": "선순위 본PF",
                "subordinate_closing_balance": "후순위대출",
                "takeout_closing_balance": "운영 대환대출",
            }
        )
        .set_index("월")
    )
    st.markdown("#### 월별 대출잔액")
    st.area_chart(debt_chart)

    operating_chart = (
        result.ledger[["month", "property_noi", "interest_expense", "closing_cash"]]
        .rename(
            columns={
                "month": "월",
                "property_noi": "건물 NOI",
                "interest_expense": "대출이자",
                "closing_cash": "월말현금",
            }
        )
        .set_index("월")
    )
    st.markdown("#### 월별 NOI·이자·남은 현금")
    st.line_chart(operating_chart)

    milestone_rows = [
        {"시점": "M0", "무슨 일": "토지 매입", "왜 중요한가": "시행사 돈과 브리지론 투입"},
        {"시점": "M6", "무슨 일": "본PF 전환", "왜 중요한가": "브리지론 상환"},
        {"시점": "M24", "무슨 일": "준공", "왜 중요한가": "임대와 NOI 시작"},
        {"시점": "M36", "무슨 일": "대환 심사", "왜 중요한가": "기존 PF 상환 가능성 결정"},
        {
            "시점": f"M{result.terminal_month}",
            "무슨 일": "최종 처리",
            "왜 중요한가": "정상매각 또는 부실 처리",
        },
    ]
    st.markdown("#### 중요한 달")
    st.dataframe(pd.DataFrame(milestone_rows), hide_index=True, width="stretch")

    with st.expander("월별 원장과 CSV 다운로드"):
        st.dataframe(result.ledger, width="stretch", hide_index=True)
        st.download_button(
            "월별 원장 다운로드",
            data=result.ledger.to_csv(index=False).encode("utf-8-sig"),
            file_name="pf_v2_monthly_ledger.csv",
            mime="text/csv",
        )

with stress_tab:
    st.write("공사비·준공지연·임대·금리·건물가치가 달라지는 가상 미래를 여러 번 계산합니다.")
    iterations = st.select_slider(
        "몇 개의 가상 미래를 계산할까요?",
        options=[100, 250, 500, 1_000, 2_000],
        value=500,
        help="숫자가 클수록 결과가 안정적이지만 계산시간이 늘어납니다.",
    )
    with st.expander("재현 설정"):
        seed = int(
            st.number_input(
                "Random seed",
                min_value=0,
                value=42,
                step=1,
                help="같은 seed를 사용하면 같은 가상 경로를 다시 만들 수 있습니다.",
            )
        )

    simulation_key = (
        iterations,
        seed,
        *assumptions.values(),
    )
    if st.button(
        f"{iterations:,}개 가상 미래 계산하기",
        type="primary",
        width="stretch",
    ):
        with st.spinner("사업을 여러 번 다시 계산하고 있습니다..."):
            st.session_state["v2_simulation"] = _cached_simulation(
                iterations,
                seed,
                *assumptions.values(),
            )
            st.session_state["v2_simulation_key"] = simulation_key

    simulation = st.session_state.get("v2_simulation")
    stored_key = st.session_state.get("v2_simulation_key")
    if simulation is not None and stored_key == simulation_key:
        summary = summarize_v2_results(simulation)
        summary_columns = st.columns(3)
        summary_columns[0].metric(
            "대환 성공",
            _percent(summary["refi_success_rate"]),
        )
        summary_columns[1].metric(
            "연장 필요",
            _percent(summary["extension_rate"]),
        )
        summary_columns[2].metric(
            "부실·부도",
            _percent(summary["distressed_or_default_rate"]),
        )

        success_count = int(simulation["refi_succeeded"].sum())
        distress_count = int(
            simulation["status"]
            .str.contains(
                "distressed|default",
                case=False,
                regex=True,
            )
            .sum()
        )
        st.info(
            f"가상 미래 {len(simulation):,}개 중 **{success_count:,}개가 대환에 성공**했고, "
            f"**{distress_count:,}개에서 부실·부도**가 발생했습니다.",
            icon="📊",
        )

        outcome_counts = (
            simulation["status"]
            .map(_simple_outcome)
            .value_counts()
            .reindex(["정상 종료", "연장 후 정상 종료", "부실·부도"], fill_value=0)
            .rename("경로 수")
            .to_frame()
        )
        st.bar_chart(outcome_counts)
        st.warning(
            "이 비율은 학습용 합성 가정에서 나온 결과입니다. "
            "한국 PF 시장의 실제 부도확률이 아닙니다.",
            icon="⚠️",
        )

        with st.expander("시나리오별 상세 데이터와 CSV"):
            st.dataframe(simulation, width="stretch", hide_index=True)
            st.download_button(
                "가상 미래 결과 다운로드",
                data=simulation.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"pf_v2_scenarios_{iterations}_{seed}.csv",
                mime="text/csv",
            )
    elif simulation is not None:
        st.info("사업 가정이 바뀌었습니다. 새 가정으로 다시 계산하세요.")
