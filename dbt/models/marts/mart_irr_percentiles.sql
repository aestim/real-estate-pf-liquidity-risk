-- IRR distribution for successful exits, per batch.
select
    batch_id,
    count(*) as n_exits,
    round(median(irr), 4) as irr_median,
    round(avg(irr), 4) as irr_mean,
    round(quantile_cont(irr, 0.25), 4) as irr_p25,
    round(quantile_cont(irr, 0.75), 4) as irr_p75,
    round(median(exit_multiple), 3) as exit_multiple_median
from {{ ref('fct_scenario') }}
where status = 'exit'
group by batch_id
