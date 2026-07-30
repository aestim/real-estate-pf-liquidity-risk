# V2 Deal Contract

Status: **v1.0 — deterministic engine and correlated stress wrapper implemented**

Model type: **synthetic, indexed educational case**

Base unit: **1 indexed unit; total development cost = 1,000**

Time grain: **calendar month**

This contract defines the transaction that the V2 engine will model. It is the
PF equivalent of a metric contract: code, tests, dashboards, and written claims
must use the same definitions.

It does not quote a real transaction or current market pricing. Market
parameters must later carry a source, observation date, unit, and calibration
method before they are described as calibrated assumptions.

## 1. Scope

V2 models one Korean income-producing commercial development through:

1. land acquisition and bridge financing;
2. main PF conversion and construction draws;
3. completion and lease-up;
4. operating-loan refinancing;
5. hold and sale; or
6. equity cure, extension, and disposal after a refinancing shortfall.

The decision question is:

> Under construction, leasing, rate, and valuation stress, how much additional
> sponsor capital is required, and can the project refinance without a forced
> disposal?

### Out of scope

- residential presales and purchaser interim-payment loans;
- HUG/HF presale-guarantee cash flows;
- portfolio diversification;
- corporate-level sponsor liquidity outside an explicit equity-cure limit;
- full tax and accounting statements;
- legal enforceability or guarantor default modeling in the first V2 slice.

## 2. Terminology contract

| Term | V2 definition |
|---|---|
| `total_development_cost` | Land, hard costs, soft costs, financing cost/interest reserve, and contingency. |
| `sponsor_common_equity` | Cash funded by the developer and first-loss common equity holder. |
| `external_preferred_equity` | Third-party equity capital senior to sponsor common equity but junior to all debt. |
| `bridge_loan` | Temporary land-stage debt repaid from the first permitted main-PF draw. It is not added again to final development sources. |
| `senior_pf_commitment` | Maximum cumulative principal that the senior main-PF lender may fund. |
| `subordinate_loan_commitment` | Maximum cumulative principal of development-stage debt junior to senior PF. |
| `loan_draw` | Cash funded in a month, not the total commitment and not the closing balance. |
| `property_noi` | Property revenue less vacancy, concessions, and property operating expenses; before project overhead, financing, tax, and capital expenditure. |
| `project_overhead` | Sponsor/project-company cost below property NOI. It must not reduce capitalized property value a second time. |
| `refinancing_requirement` | Debt principal, accrued amounts, and transaction costs that must be funded at take-out closing. |
| `funding_gap` | `max(0, refinancing requirement - project cash applied - net take-out proceeds - funded equity cure)`. An unfunded commitment is not cash. |

## 3. Base-case uses

| Use | Amount | Share of TDC |
|---|---:|---:|
| Land and acquisition costs | 300 | 30% |
| Direct construction costs | 500 | 50% |
| Design, supervision, permits, and other soft costs | 80 | 8% |
| Financing fees and interest reserve | 70 | 7% |
| Contingency | 50 | 5% |
| **Total uses** | **1,000** | **100%** |

The interest reserve is a budgeted use, not free liquidity. Capitalized interest
consumes the reserve and/or an eligible loan commitment under the financing
terms.

## 4. Final development-stage sources

| Source | Commitment | Share of TDC | Classification |
|---|---:|---:|---|
| Sponsor common equity | 50 | 5% | Equity |
| External preferred equity | 100 | 10% | Equity |
| Subordinate development loan | 100 | 10% | Debt |
| Senior main-PF loan | 750 | 75% | Debt |
| **Total sources** | **1,000** | **100%** | |

Derived ratios:

```text
sponsor equity ratio = 50 / 1,000 = 5%
total equity ratio = (50 + 100) / 1,000 = 15%
development debt ratio = (100 + 750) / 1,000 = 85%
```

These ratios describe the synthetic model case. They must not be described as
an estimate of a typical Korean transaction.

### Bridge treatment

The temporary bridge commitment is 300. At Month 0, sponsor equity of 50 and
an initial bridge draw of 250 fund the land purchase of 300. Before main-PF
closing, additional bridge draws may fund only approved predevelopment soft
costs, fees, and interest. At main-PF closing, an eligible senior-PF draw
repays the actual bridge balance.

The bridge is excluded from the final sources table because it is refinanced,
not cumulative permanent funding. Reporting may show gross bridge draws and
repayments separately, but must not double-count them as remaining capital.

## 5. Timeline and state transitions

| Month | State | Required event |
|---:|---|---|
| 0 | `land_acquisition` | Sponsor funds 50; the bridge makes its initial 250 draw; land is acquired. |
| 1–5 | `predevelopment` | Approved soft costs, fees, and bridge interest are funded within the bridge commitment. |
| 6 | `main_pf_conversion` | Main-PF conditions precedent pass and bridge principal/accrual is repaid. |
| 7–24 | `construction` | Eligible costs are funded against the construction schedule. |
| 24 | `completion` | Use approval occurs in the deterministic base case. |
| 25–36 | `lease_up` | Occupancy and NOI ramp toward stabilization. |
| 36 | `takeout_test` | Take-out proceeds are tested against the refinancing requirement. |
| 37–60 | `operations` | Successful projects service take-out debt and operate. |
| 60 | `exit` | The property is sold in the deterministic base case. |

Monte Carlo must later shock event dates rather than mutating state names.

## 6. Funding order and cash waterfall

### Development funding order

1. Sponsor common equity funds first.
2. Bridge proceeds may fund only approved land-stage uses.
3. Preferred equity and subordinate debt must satisfy their main-PF funding
   conditions before or alongside the senior loan, as encoded in a documented
   draw rule.
4. Senior PF funds only eligible uses and never above its remaining commitment.
5. Operating cash and the interest reserve fund interest before any unapproved
   principal capitalization.
6. A remaining shortfall requests sponsor equity cure.
7. A shortfall beyond the equity-cure commitment is a `funding_default`.

### Take-out and sale waterfall

Cash is allocated in this order:

1. transaction costs and statutory claims represented in the model;
2. senior debt;
3. subordinate debt;
4. preferred-equity capital and contractual preferred return;
5. sponsor common equity.

Every distribution must be capped at the unpaid claim immediately before that
distribution.

## 7. NOI and valuation contract

V2 will calculate property NOI bottom-up:

```text
gross potential rent
= leasable area × contracted/effective rent

effective property revenue
= gross potential rent
- vacancy loss
- rent-free and concessions
- uncollected rent
+ other property income

property NOI
= effective property revenue
- property operating expenses
```

Project overhead, interest, tax, leasing capital expenditure, and debt
repayment are below NOI unless a later contract explicitly reclassifies them.

Income-approach value:

```text
property value = annualized stabilized property NOI / capitalization rate
```

The model must disclose which NOI period is annualized. It must not silently
substitute one weak trailing month or a fully stabilized forecast.

## 8. Take-out sizing contract

The gross take-out commitment is the minimum of:

```text
LTV capacity
= property value × maximum takeout LTV

debt-yield capacity
= annualized underwritten NOI / minimum debt yield

DSCR capacity for an interest-only educational case
= annualized underwritten NOI / (takeout rate × minimum DSCR)

gross takeout commitment
= min(LTV capacity, debt-yield capacity, DSCR capacity, lender commitment cap)
```

For amortizing debt, the DSCR capacity must use the contractual annual debt
service rather than the interest-only shortcut.

Net take-out proceeds equal gross commitment less take-out fees and lender
deductions. Refinancing succeeds only if net proceeds plus funded equity cure
cover the complete refinancing requirement.

### Deterministic calculation fixture

The first V2 tests will use:

```text
annualized stabilized NOI = 75
capitalization rate = 5.5%
maximum takeout LTV = 65%
minimum debt yield = 8.0%
takeout interest rate = 5.5%
minimum DSCR = 1.40
refinancing requirement = 860
```

Expected values, before lender fees:

```text
property value = 1,363.6364
LTV capacity = 886.3636
debt-yield capacity = 937.5000
interest-only DSCR capacity = 974.0260
binding capacity = LTV
headroom before lender fees = 26.3636
```

This fixture proves arithmetic and constraint selection. It is not a market
forecast.

## 9. Failure-resolution contract

A failed first take-out test does not immediately trigger a sale.

The initial V2 resolution order is:

1. draw a contractually capped sponsor equity cure;
2. extend the development loan once for a fixed number of months with a
   documented extension fee and margin step-up;
3. rerun the take-out test using the later underwritten NOI and debt balance;
4. if it still fails, sell using the orderly-sale or distressed-sale scenario.

The implemented terminal statuses are:

- `development_default`: development sources and capped sponsor cure cannot
  meet a monthly use;
- `operating_default_sale`: operating cash, remaining senior commitment, and
  operating cure cannot pay current debt service;
- `extension_fee_default_sale`: the first refinancing fails and extension
  costs cannot be funded;
- `distressed_sale`: the second refinancing test fails after extension;
- `unrefinanced_distressed_sale`: no refinancing has closed by the contractual
  exit month;
- `exit` or `exit_after_extension`: refinancing closes and the property is
  sold at the modeled exit.

Each take-out attempt separately records its binding constraint, required gross
draw, fee, sponsor cure, and residual funding gap. A failed closing does not
pretend that partial take-out proceeds were funded.

## 10. Model invariants

These are required before stochastic simulation:

```text
total final development sources == total development uses
monthly opening cash + sources - uses == monthly closing cash
cumulative draws <= commitment for every facility
loan balances >= 0
repayment <= balance immediately before repayment
closing balance == opening balance + draws + capitalized interest - repayment
cash balance >= 0, otherwise an explicit funding-default event exists
sum of sale waterfall allocations == net sale proceeds
```

Amounts will be compared with an explicit currency tolerance rather than exact
binary floating-point equality.

## 11. V1 migration boundary

Reusable V1 components:

- seeded random-number generation;
- Monte Carlo batch execution;
- result aggregation and reporting helpers;
- pipeline landing, warehouse, dbt, and dashboard patterns;
- offline deterministic tests.

V1 behavior that must not be carried into V2:

- full senior debt outstanding from Month 1;
- unlimited principal growth from capitalized interest;
- top-down triangular monthly NOI as the sole property model;
- take-out sizing by LTV alone;
- immediate distressed sale after the first failed take-out test;
- equity return derived only from one initial outflow and one terminal receipt.

V2 will be implemented beside V1 until the deterministic ledger and contract
tests pass. No V1 result will be relabeled as a V2 result.

## 12. Research basis and limits

The transaction sequence and Korean structural context are informed by:

- [KDI — Reforming Korea's low-equity, guarantee-dependent PF structure](https://www.kdi.re.kr/research/focusView?pub_no=18371)
- [KDI — Real-estate PF equity-ratio reform report](https://www.kdi.re.kr/research/reportView?pub_no=19189)
- [Korean government — PF equity-ratio policy direction](https://www.korea.kr/news/policyNewsView.do?newsId=148936272)
- [Korean government — PF viability-assessment reform](https://www.korea.kr/news/policyNewsView.do?newsId=148929168)
- [OCC — Commercial Real Estate Lending 2.0](https://www.occ.treas.gov/publications-and-resources/publications/comptrollers-handbook/files/commercial-real-estate-lending/pub-ch-commercial-real-estate.pdf)
- [Federal Reserve — Regulation Q §217.2 HVCRE definition](https://www.federalreserve.gov/frrs/regulations/section-2172-definitions.htm)
- [Fannie Mae Multifamily Guide — Underwritten NOI](https://mfguide.fanniemae.com/node/1576)

These sources motivate the structure; they do not validate the synthetic
amounts, rents, rates, capitalization rate, or loss assumptions in this
contract. Those require separate calibration evidence.

### Korea–US interpretation

KDI reports approximately 3% sponsor equity in its Korean sample and describes
20–40% total project equity as common in advanced-market structures. The
comparison is directional rather than like-for-like: Korean statistics often
focus on sponsor capital, while US project equity may include sponsor/GP and
third-party LP or institutional capital.

## 13. Implemented base-case checkpoint

The deterministic engine currently produces the following reproducible
checkpoint. Amounts are in the model's indexed `억원` unit.

| Item | Implemented result |
|---|---:|
| Development cost actually incurred | 944.5797 |
| Senior PF drawn at completion | 694.5797 |
| Undrawn senior commitment | 55.4203 |
| Month 34–36 annualized NOI | 71.0692 |
| Take-out property value at 5.5% cap | 1,292.1670 |
| Gross take-out capacity | 839.9085 |
| Binding constraint | LTV |
| Gross take-out draw | 802.8385 |
| Take-out fee | 8.0284 |
| Month 60 gross sale proceeds | 1,368.2992 |
| Sponsor distribution | 463.9115 |
| Preferred distribution | 141.3862 |
| Sponsor monthly-timed annual IRR | 56.13% |
| Combined-equity monthly-timed annual IRR | 34.77% |

These values are regression checkpoints, not expected market returns.

## 14. Stochastic wrapper contract

Monte Carlo samples a macro regime first, then samples construction, leasing,
rates, cap rates, and take-out LTV from ranges conditional on that regime. This
creates directional dependence without presenting an unsupported empirical
correlation matrix.

```text
normal 60% / stress 30% / severe 10%
```

Those weights and all conditional ranges are deliberately synthetic stress
assumptions. Simulation output may be described as “the share of modeled
paths,” never as an estimated Korean PF default probability until the
parameters are calibrated and back-tested against dated observations.

The same deterministic engine runs every path. Monte Carlo is therefore a
wrapper around the contract, not a second cash-flow model.

US regulatory thresholds are also not market averages. The OCC supervisory LTV
limit for commercial, multifamily, and other non-residential construction is
80%. The Federal Reserve HVCRE definition includes a 15% borrower-contributed
capital condition for a qualifying exclusion, measured against appraised
as-completed value and subject to timing and retention requirements. LTV,
regulatory classification thresholds, and total-cost equity ratios use
different denominators and must not be presented as interchangeable measures.

The V2 case has 5% sponsor common equity and 15% total equity including external
preferred equity. It is therefore a synthetic Korean low-equity case with an
external-equity buffer, not a representative US institutional capital stack.

## 13. Decisions deferred to later steps

- exact asset subtype, location, leasable area, rent, and operating expenses;
- bridge, senior, subordinate, and take-out base rates and positive margins;
- fees, interest-reserve eligibility, and unused commitment fees;
- exact equity/preferred-return waterfall;
- contractor completion-support and trust-company mechanics;
- tax, VAT, depreciation, and accounting presentation;
- macro scenario correlation and probability calibration.

## 14. Step 2 implementation status

The deterministic development ledger implements Months 0–24 in
`pf_liquidity_risk/modeling/v2/`:

- one monthly row for cash Sources, Uses, and facility balances;
- a 300 bridge commitment with a 250 initial land draw;
- bridge take-out at Month 6;
- an 18-month hard-cost S-curve;
- need-based senior-PF draws rather than full debt outstanding from Month 1;
- explicit `funding_default` when committed sources cannot cover a monthly use;
- invariant validation for cash, balances, budgets, and commitments.

The initial annual rates (8.0% bridge, 5.5% senior PF, 9.0% subordinate) and
fees are synthetic arithmetic fixtures. They are not calibrated market claims.

## 15. Step 3 implementation status

The deterministic operating ledger implements Months 25–60 in
`pf_liquidity_risk/modeling/v2/leasing.py`.

Synthetic rent-roll fixture:

```text
anchor area = 4,000
anchor monthly base rent per area = 0.0009
anchor occupancy = 100%
anchor rent-free = Months 25–26

non-anchor area = 6,000
non-anchor monthly base rent per area = 0.0010
non-anchor occupancy = 20% at Month 25, linearly reaching 95% at Month 36

annual rent growth = 2%
collection loss = 1% of billed rent
other income = 2% of collected rent
fixed monthly property OPEX = 1.26
variable property OPEX = 20% of effective property revenue
```

The monthly contract is:

```text
occupied rent = gross potential rent × occupancy
billed rent = occupied rent - rent-free concessions
collected rent = billed rent - collection loss
effective property revenue = collected rent + other property income
property NOI = effective property revenue - property operating expenses
```

Interest, principal, sponsor/project overhead, income tax, and investor
distributions remain below property NOI.

At Month 36 the fixture produces monthly property NOI of 6.252912 and
annualized point-in-time NOI of 75.034944. The take-out input is deliberately
more conservative: the Month 34–36 average NOI, annualized to 71.069184.

All rent, area, OPEX, growth, and loss values are synthetic calculation
fixtures. They do not represent a quoted Korean property or a market forecast.
