# Real Estate PF Liquidity Risk

[![CI](https://github.com/aestim/real-estate-pf-liquidity-risk/actions/workflows/ci.yml/badge.svg)](https://github.com/aestim/real-estate-pf-liquidity-risk/actions/workflows/ci.yml)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://real-estate-pf-liquidity-risk.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

한국 임대형 부동산 PF가 **준공 후 대환에 성공하고 매각까지 버틸 수 있는지** 계산하는 교육용 프로젝트입니다.

```text
토지 매입 → 브리지론 → 본PF → 공사·임대 → 대환 → 정상매각 또는 부실 처리
```

월별 현금흐름을 하나의 원장으로 연결하고, 금리·공사비·점유율 등이 달라지는 상황을
Monte Carlo 방식으로 반복 계산합니다.

> 모든 금액과 스트레스 범위는 합성 가정입니다. 실제 거래, 시장 전망, 투자·대출 의사결정에 사용할 수 없습니다.

## 빠르게 사용하기

### 웹에서 보기

[라이브 데모 열기](https://real-estate-pf-liquidity-risk.streamlit.app/)

현재 라이브 데모는 초기 V1 모델입니다. 국내 임대형 PF 거래구조를 반영한 V2는 아래 방법으로 실행합니다.

### 로컬에서 V2 실행

Python 3.10이 필요합니다.

```bash
git clone https://github.com/aestim/real-estate-pf-liquidity-risk.git
cd real-estate-pf-liquidity-risk

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

streamlit run pf_liquidity_risk/v2_app.py
```

Windows에서는 가상환경 활성화 명령만 `venv\Scripts\activate`를 사용하면 됩니다.

대시보드는 세 단계로 사용합니다.

1. `기준 / 보수적 / 낙관적` 중 하나를 고릅니다.
2. 대환 성공 여부와 필요한 대출금, 은행 대환한도를 확인합니다.
3. 필요하면 돈 흐름이나 가상 미래 테스트를 봅니다.

## 무엇을 계산하나

| 구간 | 계산 내용 |
| --- | --- |
| 개발 | 토지비, 공사비, 브리지론과 본PF 인출 |
| 운영 | 임대료, 점유율, 운영비와 월별 NOI |
| 대환 | LTV·Debt Yield·DSCR·은행 약정한도 중 가장 작은 대출한도 |
| 위기 대응 | 시행사 추가출자, 1회 만기연장, 부실매각 |
| 매각 | 대출 상환, 우선·보통 지분 배분, 시행사 IRR |
| 스트레스 | 공사비·지연·임대·금리·매각 cap rate의 동반 변화 |

핵심 질문은 간단합니다.

```text
은행 대환한도 ≥ 기존 대출 상환에 필요한 신규대출인가?
```

## 명령줄 실행

```bash
# 기준 시나리오
python -m pf_liquidity_risk.modeling.v2 base

# 월별 원장 저장
python -m pf_liquidity_risk.modeling.v2 base \
  --ledger-output reports/v2_base_ledger.csv

# 가상 시나리오 1,000개 생성
python -m pf_liquidity_risk.modeling.v2 simulate \
  --iterations 1000 --seed 42 \
  --output reports/v2_scenarios.csv
```

## 데이터 파이프라인

V1 Monte Carlo 결과는 별도의 재현 가능한 분석 파이프라인으로 처리합니다.

```text
금리 수집 → 품질검사 → 가정 보정 → 시뮬레이션 → DuckDB 적재 → dbt 마트
```

```bash
# 인터넷과 API 키 없이 전체 파이프라인 실행
python -m pipeline.cli run --offline --iterations 1000

# 결과 조회
python -m pipeline.cli query \
  "SELECT status, pct FROM mart_outcome_summary ORDER BY pct DESC"
```

## 프로젝트 구조

```text
pf_liquidity_risk/v2_app.py        초보자용 V2 대시보드
pf_liquidity_risk/modeling/v2/     월별 PF 모델과 Monte Carlo
pipeline/                           금리 수집·검증·적재 파이프라인
dbt/                                DuckDB 변환 모델과 데이터 테스트
tests/                              모델·파이프라인·대시보드 테스트
docs/                               V2 거래 가정과 코드 구조
```

## 검증

```bash
ruff format --check
ruff check
pytest -q
python -m pipeline.cli run --offline --iterations 1000
```

GitHub Actions에서도 같은 검사를 실행합니다.

## 더 자세히 보기

- [V2 거래 가정과 계산 규칙](docs/v2-deal-contract.md)
- [V2 코드와 데이터 흐름](docs/v2-architecture.md)
- [프로젝트 학습 체크리스트](STUDY_PLAN.md)

V1은 초기 아이디어와 데이터 파이프라인을 보존하기 위해 남겨두었습니다.
새로운 기능과 대시보드는 V2를 기준으로 봐주세요.

## License

[MIT License](LICENSE) · Minsung Kim
