# 학습 플랜 → 옵시디언으로 통합됨

마스터 플랜: **옵시디언 `DE-notes` → `01 - Curriculum` (v2, 10주)**. 이 파일은 저장소 전용 체크리스트만 유지.

## 이 저장소 자가 합격 기준

1. 코드 안 보고 6단계 파이프라인(extract→validate→calibrate→simulate→load→transform) 그리고 각 도구 선택 이유 설명
2. 아무 모듈이나 열어 줄 단위로 설명
3. dbt 테스트 하나를 15분 내 추가
4. "왜 DuckDB? 왜 삼각분포? 왜 Airflow 안 썼나?" 꼬리 질문 3단계까지
5. V2의 브리지→본PF→리스업→대환→연장→매각 상태를 원장 한 행씩 설명
6. LTV·Debt Yield·DSCR 대환한도와 fee 차감 후 필요 gross draw를 손으로 계산
7. 합성 Monte Carlo 경로 비율과 실제 시장확률이 다른 이유 설명

## 이 저장소로 할 실습 (커리큘럼 주차 연동)

- [ ] W1–2: `python -m pipeline.cli run --offline` 실행, 모듈 6개 통독, 일부러 고장 내기 (음수 금리 → validate, dbt test 실패시키기)
- [ ] W3: `dbt/models/marts/*.sql` 3개 빈 화면에서 재작성
- [ ] W4: 새 dbt 모델/테스트 1개 직접 추가 + 커밋
- [ ] W5–6 (선택): full refresh → `batch_id` 증분 적재(MERGE) 전환
- [ ] W7–8: INTERVIEW_NOTES Q&A를 이 코드 화면 짚으며 영어로 답변 (녹화)

## PF V2 학습 트랙

옵시디언 `DE-notes/Projects - PF`에서 순서대로 학습한다.

1. `01 - 국내 임대형 PF 거래구조`
2. `02 - Sources & Uses 월별 원장`
3. `03 - Bottom-up NOI와 리스업`
4. `04 - 대환, 추가출자, 연장과 매각 Waterfall`
5. `05 - 상관 스트레스 Monte Carlo와 결과 해석`

각 노트는 다음 순서로 끝낸다.

```text
개념 읽기
→ 계산식 손으로 검산
→ 연결 코드 한 함수씩 실행
→ 가정 하나 변경
→ 테스트 결과 예측 후 실행
→ 30초 설명 녹음
```

### 실행 체크리스트

- [ ] `python -m pf_liquidity_risk.modeling.v2 base` 결과를 종이 계산과 대조
- [ ] `reports/v2_base_ledger.csv`를 만들어 Month 0, 6, 25, 36, 60 검산
- [ ] 대환 LTV를 65%→55%로 바꾸기 전에 상태를 먼저 예측
- [ ] `lender_commitment_cap=400` 테스트의 Month 36·42 사건을 설명
- [ ] Seed 42, 1,000회 결과를 재현하고 regime별 outcome을 집계
- [ ] Streamlit V2에서 임대료·점유율·cap rate를 동시에 stress
- [ ] 현재 합성 가정을 실제 데이터로 보정하려면 필요한 자료 목록 작성
