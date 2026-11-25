import pathlib
import duckdb
import pandas as pd

DB_PATH = pathlib.Path("data/processed_private/resort_private.duckdb")
PUB_DIR = pathlib.Path("data/public_portfolio")
PUB_DIR.mkdir(parents=True, exist_ok=True)

# Secret portfolio scaling factor & generic room-type mapping (protects resort commercial confidentiality)
SCALE_FACTOR = 1.137
ROOM_MAP = {
    "Deluxe Room": "Standard Room",
    "Superior Cottages": "Garden Cottage",
    "Mourya Heritage House": "Heritage Suite",
    "Private Pool Villa": "Pool Villa",
}

def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)

    print("=================================================================")
    print("1. PMS vs. DBT OCCUPANCY RECONCILIATION (2025-11-01 to 2026-11-22)")
    print("=================================================================")
    rec = con.execute("""
        select
            count(*) as days_audited,
            sum(net_sellable_rooms) as total_sellable_room_nights,
            sum(pms_sold_rooms) as pms_sold_room_nights,
            sum(realized_occupied_nights) as dbt_realized_room_nights,
            sum(realized_occupied_nights) - sum(pms_sold_rooms) as net_diff_nights
        from main_marts.fct_daily_property_kpi
        where stay_date <= date '2026-11-22'
    """).df()
    print(rec.to_string(index=False))

    print("\n=================================================================")
    print("2. HISTORICAL PROPERTY KPI SUMMARY (2025-11-01 to 2026-11-22)")
    print("=================================================================")
    kpi = con.execute("""
        select
            round(100.0 * sum(realized_occupied_nights) / nullif(sum(net_sellable_rooms), 0), 2) as occupancy_pct,
            round(sum(realized_room_revenue_pre_gst) / nullif(sum(realized_occupied_nights), 0), 0) as gross_adr_inr,
            round(sum(realized_net_room_revenue) / nullif(sum(realized_occupied_nights), 0), 0) as net_adr_inr,
            round(sum(realized_room_revenue_pre_gst) / nullif(sum(net_sellable_rooms), 0), 0) as gross_revpar_inr,
            round(sum(realized_net_room_revenue) / nullif(sum(net_sellable_rooms), 0), 0) as net_revpar_inr,
            round((sum(realized_room_revenue_pre_gst) + sum(realized_services_revenue)) / nullif(sum(net_sellable_rooms), 0), 0) as total_revpar_inr,
            round(sum(realized_distribution_cost), 0) as total_ota_drag_inr,
            round(sum(cancelled_room_revenue_lost), 0) as cancelled_rev_lost_inr
        from main_marts.fct_daily_property_kpi
        where stay_date <= date '2026-11-22'
    """).df()
    print(kpi.to_string(index=False))

    print("\n=================================================================")
    print("3. CHANNEL ECONOMICS & CANCELLATION LEAKAGE (HISTORICAL STAYS)")
    print("=================================================================")
    ch = con.execute("""
        select
            channel_name,
            channel_group,
            sum(realized_room_nights) as realized_nights,
            round(100.0 * sum(realized_room_nights) / sum(sum(realized_room_nights)) over (), 1) as share_nights_pct,
            round(sum(realized_room_revenue_pre_gst) / nullif(sum(realized_room_nights), 0), 0) as gross_adr,
            round(sum(net_room_revenue_after_ota) / nullif(sum(realized_room_nights), 0), 0) as net_adr,
            round(sum(distribution_cost_inr), 0) as ota_cost_inr,
            round(100.0 * sum(cancelled_room_bookings) / nullif(sum(realized_room_bookings + cancelled_room_bookings), 0), 1) as cancel_rate_pct
        from main_marts.fct_channel_economics
        where stay_year_month <= '2026-11'
        group by 1, 2
        order by realized_nights desc
    """).df()
    print(ch.to_string(index=False))

    print("\n=================================================================")
    print("4. WEEKDAY vs. WEEKEND PRICING & OCCUPANCY OPPORTUNITY")
    print("=================================================================")
    wk = con.execute("""
        select
            d.day_type,
            count(*) as days,
            round(100.0 * sum(k.realized_occupied_nights) / nullif(sum(k.net_sellable_rooms), 0), 1) as occ_pct,
            round(sum(k.realized_room_revenue_pre_gst) / nullif(sum(k.realized_occupied_nights), 0), 0) as gross_adr,
            round(sum(k.realized_room_revenue_pre_gst) / nullif(sum(k.net_sellable_rooms), 0), 0) as gross_revpar
        from main_marts.fct_daily_property_kpi k
        join main_marts.dim_date d on k.stay_date = d.stay_date
        where k.stay_date <= date '2026-11-22'
        group by 1
        order by 1
    """).df()
    print(wk.to_string(index=False))

    print("\n=================================================================")
    print("5. SEASONAL PERFORMANCE & FORWARD OTB PIPELINE")
    print("=================================================================")
    seas = con.execute("""
        select
            d.coorg_season,
            count(*) as days,
            round(100.0 * sum(k.realized_occupied_nights) / nullif(sum(k.net_sellable_rooms), 0), 1) as realized_occ_pct,
            round(sum(k.realized_room_revenue_pre_gst) / nullif(sum(k.realized_occupied_nights), 0), 0) as realized_adr,
            round(100.0 * sum(k.future_otb_nights) / nullif(sum(k.net_sellable_rooms), 0), 1) as future_otb_occ_pct
        from main_marts.fct_daily_property_kpi k
        join main_marts.dim_date d on k.stay_date = d.stay_date
        group by 1
        order by realized_occ_pct desc
    """).df()
    print(seas.to_string(index=False))

    # Export privacy-safe, scaled & room-anonymized Mart CSVs for Power BI & GitHub
    money_cols = [
        "realized_room_revenue_pre_gst", "realized_services_revenue",
        "realized_distribution_cost", "realized_net_room_revenue",
        "future_otb_room_revenue", "cancelled_room_revenue_lost",
        "room_revenue_pre_gst", "services_revenue", "room_taxes",
        "room_discount", "total_refunds", "estimated_distribution_cost",
        "net_room_revenue_after_ota", "distribution_cost_inr"
    ]

    for tbl in [
        "dim_date", "dim_channel", "dim_room_type",
        "fct_daily_room_performance", "fct_daily_property_kpi",
        "fct_booking_lifecycle", "fct_channel_economics"
    ]:
        df = con.execute(f"select * from main_marts.{tbl}").df()
        if "room_type" in df.columns:
            df["room_type"] = df["room_type"].map(lambda x: ROOM_MAP.get(x, x))
        for col in money_cols:
            if col in df.columns:
                df[col] = (df[col] * SCALE_FACTOR).round(2)
        df.to_csv(PUB_DIR / f"{tbl}.csv", index=False)

    con.close()
    print(f"\nExported 7 privacy-safe Power BI & GitHub mart tables to {PUB_DIR}/")

if __name__ == "__main__":
    main()
