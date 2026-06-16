-- Outcome distribution per batch, joined to readable descriptions.
select
    f.batch_id,
    f.status,
    o.description,
    count(*) as n_scenarios,
    round(100.0 * count(*) / sum(count(*)) over (partition by f.batch_id), 2) as pct
from {{ ref('fct_scenario') }} f
left join {{ ref('dim_outcome') }} o using (status)
group by f.batch_id, f.status, o.description
order by f.batch_id, n_scenarios desc
