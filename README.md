# Coorg Resort Revenue & Channel Performance Analytics (dbt + Power BI)

An end-to-end hospitality revenue management and channel profitability analytics pipeline built with **dbt**, **DuckDB**, **Python**, and **Power BI**. Designed around multi-channel resort operations in Coorg, Karnataka, this project transforms raw PMS reservations, room inventory, and OTA commission structures into an executive three-page Power BI semantic model.

---

## Key Business Findings & Strategic Recommendations

* **Strong Direct Demand Engine (`65.4%` Direct Share) vs. Direct Cancellation Concentration (`96.8%–97.1%`):** Direct channels—led by **WhatsApp (`₹1.15Cr` Gross)** and **Walk-In (`₹43.1L` Gross)**—drive nearly two-thirds of occupied room nights (`1,918` of `2,933` nights) at **`100.0%` Net Yield** (`₹0` estimated distribution cost). However, because Direct bookings carry no upfront OTA prepayment friction, Direct channels also account for **`96.83%`** (`97.07%` across all-time bookings; `₹39.05L` of `₹40.23L` all-time / `₹37.20L` historical) of pre-rebooking cancelled booking value, compared to **`3.17%`** from OTAs.
  * *Recommendation:* Introduce partial advance deposit links (e.g., 25% UPI payment link via WhatsApp) and automated 14-day pre-arrival reconfirmation workflows for Direct reservations booked `31+` days in advance.
* **OTA Commission Margin Compression (`79.04%` Blended Net Yield):** While OTAs represent `34.6%` of room nights, contractual commissions, GST, and TDS/TCS compress OTA net yield to **`77.8%–81.3%`** (`79.04%` blended average), generating **`₹16,70,142`** in estimated distribution cost across historical stays.
  * *Recommendation:* Run targeted post-stay WhatsApp loyalty incentives (complimentary breakfast or room upgrade on direct rebooking) to convert repeat OTA guests into zero-commission direct bookings.
* **Weekday vs. Weekend Occupancy Gap (`31.7%` vs. `54.5%`):** Weekend stays (Fri–Sat) achieve **`₹4,404` Net RevPAR** (`₹8,081` Net ADR) compared to **`₹2,351` Net RevPAR** (`₹7,409` Net ADR) on Sun–Thu nights—an **`87.3%` weekend RevPAR uplift**.
  * *Recommendation:* Launch 3-night mid-week workcation and couple packages during Shoulder and Monsoon seasons to lift weekday occupancy closer to `42%+`.
* **Lead-Time Cancellation Elasticity (`7.4%` vs. `41.5%`):** Across unique reservations, last-minute bookings (`0–3 days` lead time, `753` reservations) exhibit only a **`7.4%`** cancellation rate, rising steadily to **`18.6%`** (`4–14d`), **`29.2%`** (`15–30d`), and **`41.5%`** for early-bird bookings (`31+ days`, `323` reservations).
  * *Recommendation:* Require non-refundable partial prepayments or automated 14-day pre-arrival reconfirmation workflows for reservations booked `30+` days in advance.

---

## Architecture & Data Model

```text
Raw PMS & OTA Exports ─▶ Staging (stg_*) ─▶ Star Schema Marts (dbt + DuckDB) ─▶ Power BI Semantic Model (_Measures)
```

### Data Pipeline Flow
1. **Raw PMS Ingestion (`src/01_ingest_and_anonymize.py`)**: Cleans multi-format reservation dates, inventory logs, and revenue ledgers into DuckDB tables.
2. **dbt Transformation (`dbt_project/`)**:
   * **Staging (`stg_bookings`, `stg_daily_inventory`)**: Normalizes booking identifiers, cleans rates, discounts, room types, and parameterizes the historical cutoff date via `var('as_of_date')`.
   * **Intermediate (`int_booking_nights`)**: Explodes multi-night stays into daily night-level grains and joins commission seed rates.
   * **Dimensions (`dim_date`, `dim_channel`, `dim_room_type`)**: Calendar seasonality (Peak, Shoulder, Monsoon), channel classifications, and room hierarchies.
   * **Marts & Facts**:
     * `fct_daily_property_kpi`: Property-level occupancy, sellable inventory, RevPAR, and gross/net ADR.
     * `fct_daily_room_performance`: Room-category level occupancy and revenue distribution.
     * `fct_channel_economics`: Channel net yields, OTA commission/tax drag, and cancellation shares (bounded by `stay_date <= var('as_of_date')`).
     * `fct_booking_lifecycle`: Unique reservation grain (`booking_key` primary key) tracking lead time buckets, cancellation propensity, and booking status.
3. **Audit & Anonymized Export (`src/02_audit_and_export.py`)**: Reconciles PMS vs. dbt metrics and generates privacy-safe portfolio CSVs for Power BI.
4. **Power BI Semantic Model (`powerbi/resort_revenue_dashboard.pbix`)**: Star schema with DAX measures, dynamic filtering, and custom Coorg luxury resort theme.

---

## Data Quality, Testing & Cross-Mart Reconciliation

The pipeline enforces rigorous data integrity with **15 dbt tests** (schema tests, referential integrity, accepted values, and singular assertions):
* **PMS Occupancy Reconciliation (`assert_pms_occupancy_reconciliation.sql`)**: Asserts that dbt `realized_occupied_nights` reconciles within **`0.5%`** of PMS `pms_sold_rooms` across all historical stay dates (`stay_date <= var('as_of_date')`). Across 387 audited days, dbt achieves a **`0.068%` variance** (2,933 dbt realized nights vs. 2,931 PMS sold nights—a difference of only 2 nights).
* **Cross-Mart Alignment**:
  * **Realized Room Nights**: Exactly **`2,933`** in `fct_daily_property_kpi`, `fct_daily_room_performance`, and `fct_channel_economics`.
  * **Gross Room Revenue**: Exactly **`₹2,42,07,965`** across all three marts.
  * **Estimated Distribution Drag**: Exactly **`₹16,70,142`** across all three marts.
  * **Historical Cancelled Revenue Lost**: Exactly **`₹37,20,078`** across all three marts.
* **Stay Date vs. Check-in Date Cancellation Bridge**:
  * **Historical Night-Level Loss (`stay_date <= 2026-11-22`)**: **`₹37,20,078`** (387 cancellations with historical check-in dates).
  * **Future OTB Cancellations (`check_in_date > 2026-11-22`)**: **`₹3,03,003`** (18 cancellations scheduled for Dec 2026).
  * **All-Time Contracted Cancellation Value**: **`₹40,23,081` (`₹4.02M`)** across all 405 cancellations in `fct_booking_lifecycle`.

---

## Headline Executive KPIs Summary

Computed directly from the public portfolio semantic model (`data/public_portfolio/*.csv`):

| Metric | Portfolio Value | Historical Benchmark Period |
| :--- | :--- | :--- |
| **Occupancy Rate (Overall)** | **`38.27%`** | 2,933 occupied nights / 7,663 net sellable room nights |
| **Weekday Occupancy (Sun–Thu)** | **`31.7%`** | 276 historical days |
| **Weekend Occupancy (Fri–Sat)** | **`54.5%`** | 111 historical days |
| **Gross ADR** | **`₹8,254`** | Realized pre-GST room revenue / occupied nights |
| **Net ADR** | **`₹7,684`** | Net room revenue after OTA commissions / occupied nights |
| **Weekday Net ADR / RevPAR** | **`₹7,409` ADR / `₹2,351` RevPAR** | Mid-week performance |
| **Weekend Net ADR / RevPAR** | **`₹8,081` ADR / `₹4,404` RevPAR** | Weekend leisure premium (**`+87.3%` RevPAR uplift**) |
| **Total RevPAR (Rooms + Services)** | **`₹3,490`** | Total realized revenue / net sellable rooms |
| **Direct Demand Share** | **`65.39%`** | 1,918 of 2,933 total room nights |
| **Direct Channel Net Yield** | **`100.0%`** | Zero distribution drag (`₹0` commission) |
| **OTA Blended Net Yield** | **`79.04%`** | Range: `77.8%` (Goibibo/MMT) to `81.3%` (Agoda/Expedia) |
| **Estimated Distribution Drag** | **`₹16,70,142`** | Total OTA commissions, TDS, and GST |
| **Cancelled Revenue Lost (Historical)** | **`₹37,20,078`** | Scheduled room nights on or before `2026-11-22` |
| **Cancelled Booking Value (All-Time)** | **`₹40,23,081` (`₹4.02M`)** | Total contract value across 405 cancellations |
| **Cancellation Rate (Decided)** | **`20.98%`** | 405 cancelled / (1,525 realized + 405 cancelled reservations) |
| **Cancellation Rate (Total Volume)** | **`20.30%`** | 405 cancelled / 1,995 total unique reservations |
| **Average Lead Time / Length of Stay** | **`15.8 days` / `1.65 nights`** | Unique reservation grain across 1,995 bookings |
| **Future On-the-Books (OTB) Pipeline** | **`172 nights`** | 63 confirmed bookings beyond cutoff date |

---

## Dashboard Overview (powerbi/resort_revenue_dashboard.pbix)

### Page 1: Executive Overview & Property Performance
Tracks high-level property health: Occupancy Rate, Gross vs. Net ADR, RevPAR, and seasonal pace.
![Executive Overview](assets/page1_executive_overview.png)

### Page 2: Channel Economics & OTA Net Yield
Analyzes channel contribution, distribution cost drag (commissions + taxes), net yield efficiency, and revenue leakage from cancellations.
![Channel Economics](assets/page2_channel_economics.png)

### Page 3: Room Category Performance & Lead Time Elasticity
Explores room-type occupancy distribution, booking lead times (0–3 days vs. 31+ days), and cancellation elasticity.
![Room Performance & Lead Time](assets/page3_room_lead_time.png)

---

## Tech Stack & How to Run

### Tech Stack
* **Transformation & Testing:** dbt Core (`dbt-duckdb`), DuckDB
* **Data Processing & Scripting:** Python 3.10+, pandas
* **BI & Semantic Modeling:** Microsoft Power BI Desktop, DAX
* **Styling & Aesthetics:** Custom Power BI Theme (`powerbi/coorg_resort_theme.json`)

### How to Run

1. **Set Up Python Environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Ingest & Transform Data with dbt:**
   ```bash
   cd dbt_project && dbt build
   ```

3. **Audit & Export Public Portfolio Marts:**
   ```bash
   python src/02_audit_and_export.py --as-of-date 2026-11-22
   ```

4. **Launch the Power BI Dashboard:**
   * Open `powerbi/resort_revenue_dashboard.pbix` in Power BI Desktop.
   * Refresh data to load the latest DuckDB/CSV mart exports.

---

## Methodology & Data Governance Disclosures

1. **Commercial Data Privacy & Synthetic Scaling**: To protect resort trade secrets and commercial confidentiality, raw booking monetary totals are multiplied by an audit scaling factor (`1.137`), and room types are mapped to standard industry labels (`Deluxe Room` ➔ `Standard Room`, `Superior Cottages` ➔ `Garden Cottage`, `Mourya Heritage House` ➔ `Heritage Suite`, `Private Pool Villa` ➔ `Pool Villa`) during export via `src/02_audit_and_export.py`. All percentage ratios, occupancy rates, net yields, tax structures, and cancellation rates remain mathematically exact.
2. **Configurable As-Of Date (`var('as_of_date')`)**: The staging layer enforces `cast('{{ var("as_of_date") }}' as date)` (default: `'2026-11-22'`) in `dbt_project/dbt_project.yml` and CLI arguments in `src/02_audit_and_export.py` to cleanly partition historical realized stays from the forward on-the-books (`FUTURE_OTB`) pipeline.
3. **Unique Reservation Grain Alignment**: `fct_booking_lifecycle` is aggregated strictly at the unique reservation grain (`booking_key` primary key, `1,995` rows), ensuring that reservation volume counts and cancellation percentages share an identical grain without room-explosion distortion.
4. **Status Governance**: Unconfirmed holds (`ON_HOLD`) are strictly segregated from `REALIZED` stays and classified under `'OTHER'`, preventing uncollected revenue or pending inquiries from artificially inflating realized occupancy.
5. **Multi-Room Revenue Allocation**: Reservations with `no_of_rooms > 1` (12.4% of bookings) distribute booking-level totals equally across individual room nights, with residual fractional paise allocated to `room_seq = 1` to ensure zero rounding drift.
