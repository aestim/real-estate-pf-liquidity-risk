-- Staging: light cleanup / column selection over the raw landing table.
select
    batch_id,
    scenario_id,
    status,
    month,
    final_equity,
    irr,
    exit_multiple,
    principal_at_refi,
    refi_loan_amount,
    run_ts,
    iterations,
    seed,
    config_type,
    cap_rate,
    pre_refi_min,
    pre_refi_mode,
    pre_refi_max,
    post_refi_min,
    post_refi_mode,
    post_refi_max
from {{ source('warehouse', 'raw_scenarios') }}
