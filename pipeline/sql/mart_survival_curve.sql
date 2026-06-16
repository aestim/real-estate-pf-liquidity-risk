-- Month-by-month survival rate per batch.
-- A scenario has "failed by month m" if it defaulted or failed refi at/before m.
CREATE OR REPLACE TABLE mart_survival_curve AS
WITH months AS (
    SELECT UNNEST(generate_series(1, 36)) AS month
),
batches AS (
    SELECT DISTINCT batch_id, iterations FROM dim_batch
)
SELECT
    b.batch_id,
    m.month,
    ROUND(
        1.0 - (
            SELECT COUNT(*) FROM fact_scenario f
            WHERE f.batch_id = b.batch_id
              AND f.status IN ('default', 'refi_fail')
              AND f.month <= m.month
        ) * 1.0 / b.iterations
    , 4) AS survival_rate
FROM batches b
CROSS JOIN months m
ORDER BY b.batch_id, m.month;
