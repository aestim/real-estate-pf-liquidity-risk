-- Fact: one row per simulated scenario.
select
    batch_id,
    scenario_id,
    status,
    month,
    final_equity,
    irr,
    exit_multiple,
    principal_at_refi,
    refi_loan_amount
from {{ ref('stg_scenarios') }}
