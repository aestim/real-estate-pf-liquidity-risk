-- Star schema built from the Parquet landing table `raw_scenarios`.
-- (raw_scenarios is registered by load.py before this script runs.)

-- ---------------------------------------------------------------------------
-- Dimension: one row per simulation batch (the run-level grain)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_batch AS
SELECT DISTINCT
    batch_id,
    run_ts,
    iterations,
    seed,
    config_type,
    cap_rate,
    pre_refi_min,  pre_refi_mode,  pre_refi_max,
    post_refi_min, post_refi_mode, post_refi_max
FROM raw_scenarios;

-- ---------------------------------------------------------------------------
-- Dimension: outcome statuses with human-readable descriptions
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_outcome AS
SELECT * FROM (VALUES
    ('exit',             'Successful sale/exit at end of horizon'),
    ('refi_fail',        'Refinancing gate not cleared at Month ~19'),
    ('default',          'Insolvency before refinancing'),
    ('survived_no_exit', 'Solvent at horizon but no exit transaction')
) AS t(status, description);

-- ---------------------------------------------------------------------------
-- Fact: one row per simulated scenario
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_scenario AS
SELECT
    batch_id,
    scenario_id,
    status,
    month,
    final_equity,
    irr,
    exit_multiple,
    principal_at_refi,
    refi_loan_amount
FROM raw_scenarios;
