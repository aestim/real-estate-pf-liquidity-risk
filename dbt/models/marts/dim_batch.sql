-- One row per simulation batch (the run-level grain).
select distinct
    batch_id,
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
from {{ ref('stg_scenarios') }}
