-- Outcome distribution per batch, joined to readable descriptions.
CREATE OR REPLACE TABLE mart_outcome_summary AS
SELECT
    f.batch_id,
    f.status,
    o.description,
    COUNT(*)                                              AS n_scenarios,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY f.batch_id), 2) AS pct
FROM fact_scenario f
LEFT JOIN dim_outcome o USING (status)
GROUP BY f.batch_id, f.status, o.description
ORDER BY f.batch_id, n_scenarios DESC;
