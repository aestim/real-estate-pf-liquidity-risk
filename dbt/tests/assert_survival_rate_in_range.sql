-- Singular test: survival_rate must be a probability in [0, 1].
-- dbt passes the test when this query returns zero rows.
select batch_id, month, survival_rate
from {{ ref('mart_survival_curve') }}
where survival_rate < 0 or survival_rate > 1
