-- Month-by-month survival rate per batch.
with months as (
    select unnest(generate_series(1, 36)) as month
),
batches as (
    select distinct batch_id, iterations from {{ ref('dim_batch') }}
)
select
    b.batch_id,
    m.month,
    round(
        1.0 - (
            select count(*) from {{ ref('fct_scenario') }} f
            where f.batch_id = b.batch_id
              and f.status in ('default', 'refi_fail')
              and f.month <= m.month
        ) * 1.0 / b.iterations
    , 4) as survival_rate
from batches b
cross join months m
order by b.batch_id, m.month
