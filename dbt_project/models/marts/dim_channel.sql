select
    channel_name,
    channel_group,
    base_commission_pct,
    gst_on_commission_pct,
    tcs_tds_pct,
    round(base_commission_pct * (1.0 + gst_on_commission_pct) + tcs_tds_pct, 4) as effective_distribution_cost_pct
from {{ ref('channel_commission_rates') }}
