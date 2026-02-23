"""
Interactive PF Liquidity Risk Dashboard

Run with: streamlit run pf_liquidity_risk/app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import replace
import time

# Import your simulation components
from pf_liquidity_risk.modeling.config_model import PFConfig
from pf_liquidity_risk.modeling.train import PFInvestmentModel

# ==========================================
# Translations
# ==========================================

TRANSLATIONS = {
    'en': {
        'title': '📊 PF Liquidity Risk Analyzer',
        'subtitle': 'Interactive Monte Carlo Simulation Dashboard',
        'simulation_params': '⚙️ Simulation Parameters',
        'simulation_settings': 'Simulation Settings',
        'num_iterations': 'Number of Iterations',
        'iterations_help': 'More iterations = more accurate but slower',
        'random_seed': 'Random Seed',
        'seed_help': 'For reproducibility',
        'capital_structure': '💰 Capital Structure',
        'use_normalized': 'Use Normalized Values (Index)',
        'initial_equity': 'Initial Equity',
        'senior_loan': 'Senior Loan',
        'monthly_fixed_cost': 'Monthly Fixed Cost',
        'ltv': 'LTV',
        'leverage': 'Leverage',
        'revenue_assumptions': '📈 Revenue Assumptions',
        'stabilization_phase': 'Stabilization Phase Revenue',
        'post_opening': 'Post-Opening Revenue',
        'min': 'Min',
        'mode': 'Mode',
        'max': 'Max',
        'interest_rates': '📊 Interest Rates',
        'pre_completion': 'Pre-Completion Rates',
        'stabilization': 'Stabilization Rates',
        'post_opening_rates': 'Post-Opening Rates',
        'min_rate': 'Min Rate',
        'mode_rate': 'Mode Rate',
        'max_rate': 'Max Rate',
        'run_simulation': '🚀 Run Simulation',
        'running': 'Running {:,} simulations...',
        'completed': '✅ Simulation completed in {:.2f} seconds',
        'key_metrics': '📊 Key Risk Metrics',
        'exit_success': 'Exit Success Rate',
        'default_rate': 'Default Rate',
        'refi_failure': 'Refi Failure Rate',
        'median_irr': 'Median IRR (Exits)',
        'var_95': '95% VaR',
        'of_equity': 'of Equity',
        'vs_base': 'vs base',
        'outcome_dist': 'Project Outcome Distribution',
        'irr_dist': 'Equity IRR Distribution (Exit Cases)',
        'survival_curve': 'Project Survival Rate Over Time',
        'exit_multiple_dist': 'Exit Multiple Distribution',
        'month': 'Month',
        'survival_rate': 'Survival Rate',
        'threshold': 'Threshold',
        'median': 'Median',
        'mean': 'Mean',
        'breakeven': 'Break-even',
        'multiple': 'Multiple (Exit Equity / Initial Equity)',
        'frequency': 'Frequency',
        'irr': 'IRR',
        'detailed_stats': '📈 Detailed Statistics',
        'return_metrics': 'Return Metrics',
        'risk_metrics': 'Risk Metrics',
        'raw_data': 'Raw Data',
        'irr_statistics': 'IRR Statistics (Exit Cases)',
        'exit_multiple_stats': 'Exit Multiple Statistics',
        'sample_size': 'Sample Size',
        'std_dev': 'Std Deviation',
        'percentile_25': '25th Percentile',
        'percentile_75': '75th Percentile',
        'iqr': 'Interquartile Range',
        'exits': 'exits',
        'var_metrics': 'Value at Risk (VaR)',
        'confidence_level': 'Confidence Level',
        'additional_risk': 'Additional Risk Metrics',
        'metric': 'Metric',
        'value': 'Value',
        'expected_loss': 'Expected Loss',
        'sharpe_ratio': 'Sharpe Ratio',
        'success_rate': 'Success Rate',
        'simulation_results': 'Simulation Results (First 100 rows)',
        'download_csv': '📥 Download Full Results (CSV)',
        'instructions_title': 'How to Use This Dashboard',
        'instructions': '''
        1. **Adjust Capital Structure**: Set equity and debt amounts (normalized or absolute)
        2. **Configure Revenue**: Set expected revenue ranges for each phase
        3. **Set Interest Rates**: Define interest rate distributions by project phase
        4. **Run Simulation**: Click the button to execute Monte Carlo analysis
        5. **Analyze Results**: Review charts, metrics, and detailed statistics
        ''',
        'key_features': 'Key Features',
        'features': '''
        - 📊 **Interactive Charts**: Hover for details on all visualizations
        - ⚡ **Fast Performance**: Caching ensures quick re-runs with same parameters
        - 📥 **Export Data**: Download full simulation results as CSV
        - 🎯 **Scenario Testing**: Quickly compare different assumptions
        ''',
        'adjust_params': '👈 Adjust parameters in the sidebar and click \'🚀 Run Simulation\' to start',
        'no_exits': 'No successful exits in this scenario - adjust parameters to improve outcomes',
        'index': 'Index',
        'billions': 'Billions',
        'millions': 'Millions',
        'pct_of_equity': '% of Equity',
        'timeline': 'Project Timeline',
        'project_timeline': 'Timeline Configuration',
        'completion_target': 'Target Completion Month',
        'completion_help': 'Expected month of construction completion',
        'court_opening': 'Court Opening Month',
        'court_opening_help': 'Month when district court opens (demand driver)',
        'exit_month': 'Exit Month',
        'exit_help': 'Target month for project exit/sale',
        'timeline_summary': 'Timeline Summary',
        'construction': 'Construction Phase',
        'stabilization': 'Stabilization Phase',
        'post_opening': 'Post-Opening Phase',
        'months_unit': ' months',
        'total_duration': 'Total Project Duration',
    },
    'ko': {
        'title': '📊 PF 유동성 리스크 분석기',
        'subtitle': '인터랙티브 몬테카를로 시뮬레이션 대시보드',
        'simulation_params': '⚙️ 시뮬레이션 파라미터',
        'simulation_settings': '시뮬레이션 설정',
        'num_iterations': '반복 횟수',
        'iterations_help': '반복 횟수가 많을수록 정확하지만 느립니다',
        'random_seed': '랜덤 시드',
        'seed_help': '재현성을 위한 설정',
        'capital_structure': '💰 자본 구조',
        'use_normalized': '정규화된 값 사용 (인덱스)',
        'initial_equity': '초기 자기자본',
        'senior_loan': '선순위 대출',
        'monthly_fixed_cost': '월 고정비',
        'ltv': 'LTV',
        'leverage': '레버리지',
        'revenue_assumptions': '📈 매출 가정',
        'stabilization_phase': '안정화 단계 매출',
        'post_opening': '개원 후 매출',
        'min': '최소',
        'mode': '최빈',
        'max': '최대',
        'interest_rates': '📊 금리',
        'pre_completion': '준공 전 금리',
        'stabilization': '안정화 금리',
        'post_opening_rates': '개원 후 금리',
        'min_rate': '최소 금리',
        'mode_rate': '최빈 금리',
        'max_rate': '최대 금리',
        'run_simulation': '🚀 시뮬레이션 실행',
        'running': '{:,}회 시뮬레이션 실행 중...',
        'completed': '✅ 시뮬레이션 완료 ({:.2f}초)',
        'key_metrics': '📊 핵심 리스크 지표',
        'exit_success': 'Exit 성공률',
        'default_rate': '부도율',
        'refi_failure': '리파이낸싱 실패율',
        'median_irr': '중앙값 IRR (Exit)',
        'var_95': '95% VaR',
        'of_equity': '자기자본 대비',
        'vs_base': '기준 대비',
        'outcome_dist': '프로젝트 결과 분포',
        'irr_dist': '자기자본 IRR 분포 (Exit 케이스)',
        'survival_curve': '프로젝트 생존율 추이',
        'exit_multiple_dist': 'Exit Multiple 분포',
        'month': '월',
        'survival_rate': '생존율',
        'threshold': '기준선',
        'median': '중앙값',
        'mean': '평균',
        'breakeven': '손익분기점',
        'multiple': '배수 (Exit 자본 / 초기 자본)',
        'frequency': '빈도',
        'irr': 'IRR',
        'detailed_stats': '📈 상세 통계',
        'return_metrics': '수익률 지표',
        'risk_metrics': '리스크 지표',
        'raw_data': '원본 데이터',
        'irr_statistics': 'IRR 통계 (Exit 케이스)',
        'exit_multiple_stats': 'Exit Multiple 통계',
        'sample_size': '표본 크기',
        'std_dev': '표준편차',
        'percentile_25': '25 백분위수',
        'percentile_75': '75 백분위수',
        'iqr': '사분위범위',
        'exits': '건',
        'var_metrics': 'Value at Risk (VaR)',
        'confidence_level': '신뢰수준',
        'additional_risk': '추가 리스크 지표',
        'metric': '지표',
        'value': '값',
        'expected_loss': '기대손실',
        'sharpe_ratio': 'Sharpe Ratio',
        'success_rate': '성공률',
        'simulation_results': '시뮬레이션 결과 (처음 100행)',
        'download_csv': '📥 전체 결과 다운로드 (CSV)',
        'instructions_title': '사용 방법',
        'instructions': '''
        1. **자본 구조 조정**: 자기자본과 부채 금액 설정 (정규화 또는 절대값)
        2. **매출 설정**: 각 단계별 예상 매출 범위 설정
        3. **금리 설정**: 프로젝트 단계별 금리 분포 정의
        4. **시뮬레이션 실행**: 버튼 클릭하여 몬테카를로 분석 수행
        5. **결과 분석**: 차트, 지표, 상세 통계 검토
        ''',
        'key_features': '주요 기능',
        'features': '''
        - 📊 **인터랙티브 차트**: 모든 시각화에서 상세 정보 확인
        - ⚡ **빠른 성능**: 캐싱으로 동일 파라미터 빠른 재실행
        - 📥 **데이터 내보내기**: 전체 시뮬레이션 결과 CSV 다운로드
        - 🎯 **시나리오 테스트**: 다양한 가정 빠르게 비교
        ''',
        'adjust_params': '👈 사이드바에서 파라미터를 조정하고 \'🚀 시뮬레이션 실행\' 버튼을 클릭하세요',
        'no_exits': '이 시나리오에서 성공적인 exit이 없습니다 - 파라미터를 조정하여 결과를 개선하세요',
        'index': '인덱스',
        'billions': '십억',
        'millions': '백만',
        'pct_of_equity': '자기자본 대비 %',
        'timeline': '프로젝트 타임라인',
        'project_timeline': '타임라인 설정',
        'completion_target': '목표 준공 시점',
        'completion_help': '예상 준공 완료 개월',
        'court_opening': '법원 개원 시점',
        'court_opening_help': '지방법원 개원 개월 (수요 발생 시점)',
        'exit_month': 'Exit 시점',
        'exit_help': '프로젝트 매각/종료 목표 개월',
        'timeline_summary': '타임라인 요약',
        'construction': '건설 단계',
        'stabilization': '안정화 단계',
        'post_opening': '개원 후 단계',
        'months_unit': '개월',
        'total_duration': '총 프로젝트 기간',
    }
}

def t(key: str, lang: str) -> str:
    """Translation helper function"""
    return TRANSLATIONS[lang].get(key, key)

# ==========================================
# Page Configuration
# ==========================================

st.set_page_config(
    page_title="PF Liquidity Risk Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# Helper Functions
# ==========================================

@st.cache_data(ttl=300)
def run_simulation_cached(config_dict: dict, iterations: int, seed: int) -> pd.DataFrame:
    """Run simulation with caching for performance"""
    config = PFConfig(**config_dict)
    np.random.seed(seed)
    model = PFInvestmentModel(config)
    results = [model.simulate_path() for _ in range(iterations)]
    return pd.DataFrame(results)


def create_outcome_chart(df: pd.DataFrame, lang: str) -> go.Figure:
    """Create interactive outcome distribution chart"""
    counts = df["status"].value_counts()
    percentages = (counts / len(df) * 100).round(2)
    
    color_map = {
        "exit": "#2ECC71",
        "default": "#E74C3C",
        "refi_fail": "#F1C40F",
        "survived_no_exit": "#3498DB"
    }
    
    colors = [color_map.get(status, "#BDC3C7") for status in counts.index]
    
    fig = go.Figure(data=[
        go.Bar(
            x=counts.index,
            y=counts.values,
            text=[f"{p}%" for p in percentages],
            textposition='outside',
            marker_color=colors,
            marker_line_color='black',
            marker_line_width=1.5
        )
    ])
    
    fig.update_layout(
        title=t('outcome_dist', lang),
        xaxis_title="Outcome",
        yaxis_title=t('frequency', lang),
        height=400,
        showlegend=False,
        hovermode='x'
    )
    
    return fig


def create_irr_histogram(df: pd.DataFrame, lang: str) -> go.Figure:
    """Create IRR distribution histogram"""
    exit_df = df[df["status"] == "exit"]
    
    if exit_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=t('no_exits', lang),
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    median_irr = exit_df["irr"].median()
    mean_irr = exit_df["irr"].mean()
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=exit_df["irr"],
        nbinsx=50,
        name=t('irr_dist', lang),
        marker_color='#3498DB',
        opacity=0.7
    ))
    
    fig.add_vline(
        x=median_irr,
        line_dash="dash",
        line_color="red",
        annotation_text=f"{t('median', lang)}: {median_irr:.1%}",
        annotation_position="top"
    )
    
    fig.add_vline(
        x=mean_irr,
        line_dash="dash",
        line_color="green",
        annotation_text=f"{t('mean', lang)}: {mean_irr:.1%}",
        annotation_position="bottom"
    )
    
    fig.update_layout(
        title=t('irr_dist', lang),
        xaxis_title=t('irr', lang),
        yaxis_title=t('frequency', lang),
        height=400,
        showlegend=False
    )
    
    return fig


def create_survival_curve(df: pd.DataFrame, iterations: int, lang: str) -> go.Figure:
    """Create survival rate curve"""
    months = np.arange(1, 37)
    survival_rates = []
    
    for m in months:
        failed = df[df["status"].isin(["default", "refi_fail"]) & (df["month"] <= m)]
        survival_rates.append((iterations - len(failed)) / iterations)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=months,
        y=survival_rates,
        mode='lines+markers',
        name=t('survival_rate', lang),
        line=dict(color='#8E44AD', width=3),
        fill='tozeroy',
        fillcolor='rgba(142, 68, 173, 0.3)'
    ))
    
    fig.add_hline(
        y=0.95,
        line_dash="dash",
        line_color="red",
        annotation_text=f"95% {t('threshold', lang)}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=t('survival_curve', lang),
        xaxis_title=t('month', lang),
        yaxis_title=t('survival_rate', lang),
        height=400,
        yaxis_range=[0, 1.05]
    )
    
    return fig


def create_exit_multiple_chart(df: pd.DataFrame, lang: str) -> go.Figure:
    """Create exit multiple distribution"""
    exit_df = df[df["status"] == "exit"]
    
    if exit_df.empty or "exit_multiple" not in exit_df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text=t('no_exits', lang),
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    median_mult = exit_df["exit_multiple"].median()
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=exit_df["exit_multiple"],
        nbinsx=40,
        name=t('exit_multiple_dist', lang),
        marker_color='#27AE60',
        opacity=0.7
    ))
    
    fig.add_vline(
        x=median_mult,
        line_dash="dash",
        line_color="red",
        annotation_text=f"{t('median', lang)}: {median_mult:.2f}x",
        annotation_position="top"
    )
    
    fig.add_vline(
        x=1.0,
        line_dash="dot",
        line_color="orange",
        annotation_text=f"{t('breakeven', lang)} (1.0x)",
        annotation_position="bottom"
    )
    
    fig.update_layout(
        title=t('exit_multiple_dist', lang),
        xaxis_title=t('multiple', lang),
        yaxis_title=t('frequency', lang),
        height=400,
        showlegend=False
    )
    
    return fig


# ==========================================
# Main Dashboard
# ==========================================

def main():
    # Language Toggle at the top
    col_lang1, col_lang2, col_lang3 = st.columns([6, 1, 1])
    with col_lang2:
        if st.button("🇺🇸 EN", width="stretch", 
                    type="primary" if st.session_state.get('lang', 'en') == 'en' else "secondary"):
            st.session_state['lang'] = 'en'
            st.rerun()
    with col_lang3:
        if st.button("🇰🇷 KO", width="stretch",
                    type="primary" if st.session_state.get('lang', 'en') == 'ko' else "secondary"):
            st.session_state['lang'] = 'ko'
            st.rerun()
    
    # Get current language
    lang = st.session_state.get('lang', 'en')
    
    # Header
    st.markdown(f'<p class="main-header">{t("title", lang)}</p>', unsafe_allow_html=True)
    st.markdown(f"### {t('subtitle', lang)}")
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header(t('simulation_params', lang))
        
        # Simulation Settings
        st.subheader(t('simulation_settings', lang))
        iterations = st.slider(
            t('num_iterations', lang),
            min_value=1000,
            max_value=50000,
            value=10000,
            step=1000,
            help=t('iterations_help', lang)
        )
        
        seed = st.number_input(t('random_seed', lang), value=42, help=t('seed_help', lang))
        
        st.markdown("---")
        
        # Capital Structure
        st.subheader(t('capital_structure', lang))
        
        use_normalized = st.checkbox(t('use_normalized', lang), value=True)
        
        if use_normalized:
            initial_equity = st.number_input(
                f"{t('initial_equity', lang)} ({t('index', lang)})",
                min_value=50.0,
                max_value=200.0,
                value=100.0,
                step=10.0
            )
            senior_loan = st.slider(
                f"{t('senior_loan', lang)} ({t('index', lang)})",
                min_value=200.0,
                max_value=500.0,
                value=339.3,
                step=10.0
            )
            monthly_fixed_cost = st.slider(
                f"{t('monthly_fixed_cost', lang)} ({t('pct_of_equity', lang)})",
                min_value=0.5,
                max_value=5.0,
                value=1.79,
                step=0.1
            )
            currency_display = t('index', lang)
        else:
            initial_equity = st.number_input(
                f"{t('initial_equity', lang)} (KRW {t('billions', lang)})",
                min_value=1.0,
                max_value=20.0,
                value=5.6,
                step=0.1
            ) * 1e9
            senior_loan = st.slider(
                f"{t('senior_loan', lang)} (KRW {t('billions', lang)})",
                min_value=5.0,
                max_value=30.0,
                value=19.0,
                step=0.5
            ) * 1e9
            monthly_fixed_cost = st.slider(
                f"{t('monthly_fixed_cost', lang)} (KRW {t('millions', lang)})",
                min_value=50,
                max_value=200,
                value=100,
                step=10
            ) * 1e6
            currency_display = "KRW"
        
        # Display calculated metrics
        ltv = senior_loan / (senior_loan + initial_equity)
        leverage = senior_loan / initial_equity
        
        col1, col2 = st.columns(2)
        col1.metric(t('ltv', lang), f"{ltv:.1%}")
        col2.metric(t('leverage', lang), f"{leverage:.2f}x")
        
        st.markdown("---")
        
        # Revenue Parameters
        st.subheader(t('revenue_assumptions', lang))
        
        with st.expander(t('stabilization_phase', lang)):
            if use_normalized:
                stab_min = st.slider(f"{t('min', lang)} ({t('index', lang)})", 0.5, 5.0, 0.89, 0.1, key="stab_min")
                stab_mode = st.slider(f"{t('mode', lang)} ({t('index', lang)})", 1.0, 5.0, 2.14, 0.1, key="stab_mode")
                stab_max = st.slider(f"{t('max', lang)} ({t('index', lang)})", 2.0, 8.0, 2.68, 0.1, key="stab_max")
            else:
                stab_min = st.slider(f"{t('min', lang)} (KRW {t('millions', lang)})", 30, 200, 50, 10, key="stab_min") * 1e6
                stab_mode = st.slider(f"{t('mode', lang)} (KRW {t('millions', lang)})", 50, 200, 120, 10, key="stab_mode") * 1e6
                stab_max = st.slider(f"{t('max', lang)} (KRW {t('millions', lang)})", 100, 300, 150, 10, key="stab_max") * 1e6
            
            stabilization_revenue_dist = (stab_min, stab_mode, stab_max)
        
        with st.expander(t('post_opening', lang)):
            if use_normalized:
                post_min = st.slider(f"{t('min', lang)} ({t('index', lang)})", 1.0, 5.0, 2.14, 0.1, key="post_min")
                post_mode = st.slider(f"{t('mode', lang)} ({t('index', lang)})", 2.0, 8.0, 3.57, 0.1, key="post_mode")
                post_max = st.slider(f"{t('max', lang)} ({t('index', lang)})", 3.0, 10.0, 4.46, 0.1, key="post_max")
            else:
                post_min = st.slider(f"{t('min', lang)} (KRW {t('millions', lang)})", 80, 250, 120, 10, key="post_min") * 1e6
                post_mode = st.slider(f"{t('mode', lang)} (KRW {t('millions', lang)})", 150, 300, 200, 10, key="post_mode") * 1e6
                post_max = st.slider(f"{t('max', lang)} (KRW {t('millions', lang)})", 200, 400, 250, 10, key="post_max") * 1e6
            
            post_court_revenue_dist = (post_min, post_mode, post_max)
        
        st.markdown("---")
        
        # Interest Rate Parameters
        st.subheader(t('interest_rates', lang))
        
        with st.expander(t('pre_completion', lang)):
            pre_min = st.slider(t('min_rate', lang), 0.05, 0.20, 0.10, 0.01, key="pre_min", format="%.2f")
            pre_mode = st.slider(t('mode_rate', lang), 0.08, 0.25, 0.14, 0.01, key="pre_mode", format="%.2f")
            pre_max = st.slider(t('max_rate', lang), 0.10, 0.30, 0.18, 0.01, key="pre_max", format="%.2f")
            pre_completion_rate = (pre_min, pre_mode, pre_max)
        
        with st.expander(t('stabilization', lang)):
            stab_rate_min = st.slider(t('min_rate', lang), 0.04, 0.15, 0.08, 0.01, key="stab_rate_min", format="%.2f")
            stab_rate_mode = st.slider(t('mode_rate', lang), 0.06, 0.18, 0.11, 0.01, key="stab_rate_mode", format="%.2f")
            stab_rate_max = st.slider(t('max_rate', lang), 0.08, 0.20, 0.14, 0.01, key="stab_rate_max", format="%.2f")
            stabilization_rate = (stab_rate_min, stab_rate_mode, stab_rate_max)
        
        with st.expander(t('post_opening_rates', lang)):
            post_rate_min = st.slider(t('min_rate', lang), 0.03, 0.10, 0.05, 0.01, key="post_rate_min", format="%.2f")
            post_rate_mode = st.slider(t('mode_rate', lang), 0.04, 0.12, 0.07, 0.01, key="post_rate_mode", format="%.2f")
            post_rate_max = st.slider(t('max_rate', lang), 0.06, 0.15, 0.09, 0.01, key="post_rate_max", format="%.2f")
            post_court_rate = (post_rate_min, post_rate_mode, post_rate_max)
        
        st.markdown("---")

        # Timeline Parameters
        st.subheader("⏱️ " + t('timeline', lang))
        
        with st.expander(t('project_timeline', lang)):
            completion_target_month = st.slider(
                t('completion_target', lang),
                min_value=6,
                max_value=30,
                value=16,
                step=1,
                help=t('completion_help', lang)
            )
            
            court_opening_month = st.slider(
                t('court_opening', lang),
                min_value=completion_target_month + 2,
                max_value=48,
                value=24,
                step=1,
                help=t('court_opening_help', lang)
            )
            
            exit_month = st.slider(
                t('exit_month', lang),
                min_value=court_opening_month + 2,
                max_value=60,
                value=36,
                step=1,
                help=t('exit_help', lang)
            )
            
            # Visual timeline summary
            st.markdown(f"""
            **{t('timeline_summary', lang)}**
            - {t('construction', lang)}: 0 → {completion_target_month}{t('months_unit', lang)}
            - {t('stabilization', lang)}: {completion_target_month} → {court_opening_month}{t('months_unit', lang)}
            - {t('post_opening', lang)}: {court_opening_month} → {exit_month}{t('months_unit', lang)}
            - **{t('total_duration', lang)}**: {exit_month}{t('months_unit', lang)}
            """)
        
        # Run Simulation Button
        run_button = st.button(t('run_simulation', lang), type="primary", width="stretch")
    
    # Main Content Area
    if run_button:
        # Build config dictionary
        config_dict = {
            "initial_equity": initial_equity,
            "senior_loan": senior_loan,
            "monthly_fixed_cost": monthly_fixed_cost,
            "stabilization_revenue_dist": stabilization_revenue_dist,
            "post_court_revenue_dist": post_court_revenue_dist,
            "pre_completion_rate": pre_completion_rate,
            "stabilization_rate": stabilization_rate,
            "post_court_rate": post_court_rate,
            "config_type": "Interactive Dashboard",
            "display_currency": currency_display,
            "completion_target_month": completion_target_month,
            "court_opening_month": court_opening_month,
            "exit_month": exit_month,
            "config_type": "Interactive Dashboard",
            "display_currency": currency_display
        }
        
        # Run simulation with progress bar
        with st.spinner(t('running', lang).format(iterations)):
            progress_bar = st.progress(0)
            start_time = time.time()
            
            df = run_simulation_cached(config_dict, iterations, seed)
            
            progress_bar.progress(100)
            elapsed_time = time.time() - start_time
            st.success(t('completed', lang).format(elapsed_time))
        
        st.markdown("---")
        
        # Key Metrics Row
        st.subheader(t('key_metrics', lang))
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Calculate metrics
        exit_prob = len(df[df["status"] == "exit"]) / len(df) * 100
        default_prob = len(df[df["status"] == "default"]) / len(df) * 100
        refi_fail_prob = len(df[df["status"] == "refi_fail"]) / len(df) * 100
        
        exit_df = df[df["status"] == "exit"]
        median_irr = exit_df["irr"].median() if not exit_df.empty else 0
        
        loss = initial_equity - df["final_equity"]
        var_95 = np.percentile(loss, 95) / initial_equity * 100
        
        col1.metric(t('exit_success', lang), f"{exit_prob:.1f}%", 
                   delta=f"{exit_prob - 65:.1f}% {t('vs_base', lang)}" if exit_prob != 65 else None)
        col2.metric(t('default_rate', lang), f"{default_prob:.1f}%",
                   delta=f"{25 - default_prob:.1f}% {t('vs_base', lang)}" if default_prob != 25 else None,
                   delta_color="inverse")
        col3.metric(t('refi_failure', lang), f"{refi_fail_prob:.1f}%",
                   delta=f"{10 - refi_fail_prob:.1f}% {t('vs_base', lang)}" if refi_fail_prob != 10 else None,
                   delta_color="inverse")
        col4.metric(t('median_irr', lang), f"{median_irr:.1%}")
        col5.metric(t('var_95', lang), f"{var_95:.1f}% {t('of_equity', lang)}")
        
        st.markdown("---")
        
        # Visualizations - 2x2 Grid
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(create_outcome_chart(df, lang), width="stretch")
            st.plotly_chart(create_survival_curve(df, iterations, lang), width="stretch")
        
        with col2:
            st.plotly_chart(create_irr_histogram(df, lang), width="stretch")
            st.plotly_chart(create_exit_multiple_chart(df, lang), width="stretch")
        
        st.markdown("---")
        
        # Detailed Statistics Table
        st.subheader(t('detailed_stats', lang))
        
        tab1, tab2, tab3 = st.tabs([t('return_metrics', lang), t('risk_metrics', lang), t('raw_data', lang)])
        
        with tab1:
            if not exit_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**{t('irr_statistics', lang)}**")
                    
                    # Calculate statistics
                    irr_data = {
                        t('metric', lang): [
                            t('sample_size', lang),
                            t('mean', lang),
                            t('median', lang),
                            t('std_dev', lang),
                            t('min', lang),
                            t('max', lang),
                            t('percentile_25', lang),
                            t('percentile_75', lang),
                            t('iqr', lang)
                        ],
                        t('value', lang): [
                            f"{len(exit_df):,} {t('exits', lang)}",
                            f"{exit_df['irr'].mean():.2%}",
                            f"{exit_df['irr'].median():.2%}",
                            f"{exit_df['irr'].std():.2%}",
                            f"{exit_df['irr'].min():.2%}",
                            f"{exit_df['irr'].max():.2%}",
                            f"{exit_df['irr'].quantile(0.25):.2%}",
                            f"{exit_df['irr'].quantile(0.75):.2%}",
                            f"{exit_df['irr'].quantile(0.75) - exit_df['irr'].quantile(0.25):.2%}"
                        ]
                    }
                    st.dataframe(pd.DataFrame(irr_data), width="stretch", hide_index=True)
                
                with col2:
                    if "exit_multiple" in exit_df.columns:
                        st.markdown(f"**{t('exit_multiple_stats', lang)}**")
                        
                        # Calculate statistics
                        mult_data = {
                            t('metric', lang): [
                                t('sample_size', lang),
                                t('mean', lang),
                                t('median', lang),
                                t('std_dev', lang),
                                t('min', lang),
                                t('max', lang),
                                t('percentile_25', lang),
                                t('percentile_75', lang),
                                t('iqr', lang)
                            ],
                            t('value', lang): [
                                f"{len(exit_df):,} {t('exits', lang)}",
                                f"{exit_df['exit_multiple'].mean():.2f}x",
                                f"{exit_df['exit_multiple'].median():.2f}x",
                                f"{exit_df['exit_multiple'].std():.2f}x",
                                f"{exit_df['exit_multiple'].min():.2f}x",
                                f"{exit_df['exit_multiple'].max():.2f}x",
                                f"{exit_df['exit_multiple'].quantile(0.25):.2f}x",
                                f"{exit_df['exit_multiple'].quantile(0.75):.2f}x",
                                f"{exit_df['exit_multiple'].quantile(0.75) - exit_df['exit_multiple'].quantile(0.25):.2f}x"
                            ]
                        }
                        st.dataframe(pd.DataFrame(mult_data), width="stretch", hide_index=True)
            else:
                st.warning(t('no_exits', lang))
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**{t('var_metrics', lang)}**")
                var_data = {
                    t('confidence_level', lang): ["90%", "95%", "99%"],
                    f"VaR (% {t('of_equity', lang)})": [
                        f"{np.percentile(loss, 90) / initial_equity * 100:.1f}%",
                        f"{np.percentile(loss, 95) / initial_equity * 100:.1f}%",
                        f"{np.percentile(loss, 99) / initial_equity * 100:.1f}%"
                    ]
                }
                st.dataframe(pd.DataFrame(var_data), width="stretch", hide_index=True)
            
            with col2:
                st.markdown(f"**{t('additional_risk', lang)}**")
                expected_loss = loss.mean() / initial_equity * 100
                
                # Sharpe Ratio
                if len(exit_df) > 0 and exit_df["irr"].std() > 0:
                    sharpe = exit_df["irr"].mean() / exit_df["irr"].std()
                else:
                    sharpe = 0
                
                risk_metrics = {
                    t('metric', lang): [t('expected_loss', lang), t('sharpe_ratio', lang), t('success_rate', lang)],
                    t('value', lang): [
                        f"{expected_loss:.1f}% {t('of_equity', lang)}",
                        f"{sharpe:.2f}",
                        f"{exit_prob:.1f}%"
                    ]
                }
                st.dataframe(pd.DataFrame(risk_metrics), width="stretch", hide_index=True)
        
        with tab3:
            st.markdown(f"**{t('simulation_results', lang)}**")
            st.dataframe(df.head(100), width="stretch")
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label=t('download_csv', lang),
                data=csv,
                file_name="pf_simulation_results.csv",
                mime="text/csv"
            )
    
    else:
        # Show instructions when no simulation run
        st.info(t('adjust_params', lang))
        
        st.markdown(f"### {t('instructions_title', lang)}")
        st.markdown(t('instructions', lang))
        
        st.markdown(f"### {t('key_features', lang)}")
        st.markdown(t('features', lang))


if __name__ == "__main__":
    main()