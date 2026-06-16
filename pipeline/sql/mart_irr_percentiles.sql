-- IRR distribution for successful exits, per batch.
CREATE OR REPLACE TABLE mart_irr_percentiles AS
SELECT
    batch_id,
    COUNT(*)                                  AS n_exits,
    ROUND(MEDIAN(irr), 4)                     AS irr_median,
    ROUND(AVG(irr), 4)                        AS irr_mean,
    ROUND(QUANTILE_CONT(irr, 0.25), 4)        AS irr_p25,
    ROUND(QUANTILE_CONT(irr, 0.75), 4)        AS irr_p75,
    ROUND(MEDIAN(exit_multiple), 3)           AS exit_multiple_median
FROM fact_scenario
WHERE status = 'exit'
GROUP BY batch_id;
