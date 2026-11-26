# Coorg Resort Revenue & Channel Performance Analytics (dbt + Power BI)

An end-to-end hospitality revenue management and channel profitability analytics pipeline built with **dbt**, **DuckDB**, **Python**, and **Power BI**. Designed around multi-channel resort operations in Coorg, Karnataka, this project transforms raw PMS reservations, room inventory, and OTA commission structures into an executive three-page Power BI semantic model.

---

## Key Business Findings & Strategic Recommendations

* **Strong Direct Demand Engine (`65.4%` Direct Share) vs. Direct Cancellation Concentration (`96.8%–97.1%`):**
  * *Observation:* Direct channels—led by **WhatsApp (`₹1.15Cr` Gross)** and **Walk-In (`₹43.1L` Gross)**—drive nearly two-thirds of occupied room nights (`1,918` of `2,933` nights) at **`100.0%` Net Yield** (`₹0` distribution deductions). Concurrently, Direct channels account for **`96.83%`** (`97.07%` across all-time bookings; `₹39.05L` of `₹40.23L` all-time / `₹37.20L` historical) of pre-rebooking cancelled booking value, compared to just **`3.17%`** from OTAs.
  * *Testable Hypothesis:* The absence of upfront payment friction (zero booking deposit via WhatsApp and manual front-desk reservations) may drive lower guest commitment relative to prepaid OTA channels, encouraging speculative holds and elevated cancellation propensity on early-bird reservations.
  * *Pilot Recommendation:* Deploy a controlled 60-day pilot testing partial advance deposit links (e.g., a 25% UPI payment link sent via automated WhatsApp message) alongside a 14-day pre-arrival reconfirmation workflow for Direct reservations booked `31+` days in advance, evaluating conversion rate retention and cancellation reduction against the unmanaged baseline.
* **OTA Net Settlement Yield & Deduction Breakdown (`79.04%` Net Settlement Yield):** While OTAs represent `34.6%` of room nights, contractual terms and statutory deductions compress property cash flow to **`77.8%–81.3%`** (**`79.04%`** blended average Net Settlement Yield after Estimated Deductions), generating **`₹16,70,142`** in total estimated distribution deductions across historical stays:
  * *Contractual OTA Commission (`15.0%–18.0%`):* Represents **`₹13,54,307`** in pure operating distribution expense payable to third-party platforms (MakeMyTrip, Goibibo, Agoda, Expedia).
  * *GST on Commission (`18.0%` of commission):* Totals **`₹2,43,775`**; while deducted by the portal at settlement, this GST charge may be eligible for Input Tax Credit (ITC) offsetting the resort's outward GST liabilities if supported by valid tax invoices.
  * *Statutory Tax Withholdings (TDS/TCS @ `1.0%`):* Totals **`₹72,060`** withheld under Section 194-O of the Income Tax Act and Section 52 of the CGST Act; these are refundable or creditable prepayments against annual corporate tax obligations rather than permanent operating expenses.
  * *Recommendation:* Run targeted post-stay WhatsApp loyalty incentives (complimentary breakfast or room upgrade on direct rebooking) to systematically convert repeat OTA guests into zero-commission direct bookings.
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
1. **Raw PMS Ingestion & Defensive Anonymization (`src/01_ingest_and_anonymize.py`)**:
   * Cleans multi-format reservation dates, inventory logs, and revenue ledgers into DuckDB tables.
   * Parses Excel serial numeric offsets, `DD/MM/YYYY`, and standard ISO dates cleanly.
   * Enforces an explicit analytical allowlist and programmatic assertions raising `ValueError` on any PII leaks (`guest`, `phone`, `email`, `room_no`, etc.).
   * Supports a `--demo` flag that generates synthetic PMS datasets in `data/demo_sample/` for zero-setup execution.
2. **dbt Transformation (`dbt_project/`)**:
   * **Staging (`stg_bookings`, `stg_daily_inventory`)**: Validates positive room counts, valid stay date ordering, clean rates, discounts, and parameterizes the historical cutoff date via `var('as_of_date')`.
   * **Intermediate (`int_booking_nights`)**: Explodes multi-night stays into daily night-level grains, applies paise-exact residual allocation across rooms/nights, and breaks down OTA distribution costs into base commission, GST, and TDS/TCS.
   * **Dimensions (`dim_date`, `dim_channel`, `dim_room_type`)**: Calendar seasonality (Peak, Shoulder, Monsoon), channel classifications, and room hierarchies.
   * **Marts & Facts**:
     * `fct_daily_property_kpi`: Property-level occupancy, sellable inventory, RevPAR, and gross/net ADR.
     * `fct_daily_room_performance`: Room-category level occupancy and revenue distribution.
     * `fct_channel_economics`: Channel net settlement yields, explicit deduction component breakdowns, and cancellation shares (bounded by `stay_date <= var('as_of_date')`).
     * `fct_booking_lifecycle`: Unique reservation grain (`booking_key` primary key) tracking lead time buckets, cancellation propensity, and booking status.
3. **Audit & Anonymized Export (`src/02_audit_and_export.py`)**: Reconciles PMS vs. dbt metrics and generates privacy-safe portfolio CSVs for Power BI.
4. **Power BI Semantic Model (`powerbi/resort_revenue_dashboard.pbix`)**: Star schema with DAX measures, dynamic filtering, and custom Coorg luxury resort theme.

---

## Data Quality, Testing & Cross-Mart Reconciliation

The pipeline enforces rigorous data integrity with **51 dbt tests** (schema tests, referential integrity, accepted values, positive room counts, date order validation, join cardinality, and singular assertions):
* **PMS Occupancy Reconciliation (`assert_pms_occupancy_reconciliation.sql`)**: Asserts that dbt `realized_occupied_nights` reconciles within **`0.5%`** of PMS `pms_sold_rooms` across all historical stay dates (`stay_date <= var('as_of_date')`). Across 387 audited days, dbt achieves a **`0.068%` variance** (2,933 dbt realized nights vs. 2,931 PMS sold nights—a difference of only 2 nights).
* **Positive Room Counts & Date Ordering (`assert_positive_room_counts.sql`, `assert_valid_stay_dates.sql`)**: Asserts all booking records have `no_of_rooms > 0` and `check_out_date > check_in_date`.
* **Join Cardinality Assertion (`assert_stg_bookings_join_cardinality.sql`)**: Asserts zero cartesian explosion across master reservations and room sequence allocations.
* **Cross-Mart Alignment & Tolerance-Based Reconciliation**:
  All three star-schema marts (`fct_daily_property_kpi`, `fct_daily_room_performance`, `fct_channel_economics`) reconcile exactly to the nearest whole rupee across the historical period (`stay_date <= 2026-11-22`), with small sub-10 paise floating-point differences (`< ₹0.10`) attributable to differing aggregation levels (property-daily vs. room-type-daily vs. channel-monthly):
  * **Realized Room Nights**: Exactly **`2,933`** across all three marts (zero drift).
  * **Gross Room Revenue**: **`₹2,42,07,965`** across all three marts (Max delta: `₹0.05` — `₹2,42,07,965.26` vs. `₹2,42,07,965.21` vs. `₹2,42,07,965.23`).
  * **Estimated Distribution Cost**: **`₹16,70,142`** across all three marts (Max delta: `₹0.03` — `₹16,70,142.08` vs. `₹16,70,142.08` vs. `₹16,70,142.05`).
  * **Historical Pre-Rebooking Cancelled Booking Value**: **`₹37,20,078`** across all three marts (Max delta: `₹0.07` — `₹37,20,077.98` vs. `₹37,20,078.01` vs. `₹37,20,077.94`).
* **Stay Date vs. Check-in Date Cancellation Bridge**:
  * **Historical Pre-Rebooking Cancelled Booking Value (`stay_date <= 2026-11-22`)**: **`₹37,20,078`** (387 cancellations with historical check-in dates).
  * **Future OTB Cancellations (`check_in_date > 2026-11-22`)**: **`₹3,03,003`** (18 cancellations scheduled for Dec 2026).
  * **All-Time Pre-Rebooking Cancelled Booking Value**: **`₹40,23,081` (`₹4.02M`)** across all 405 cancellations in `fct_booking_lifecycle`.

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
| **OTA Net Settlement Yield (after Deductions)** | **`79.04%`** | Range: `77.8%` (Goibibo/MMT) to `81.3%` (Agoda/Expedia) |
| **Estimated Distribution Deductions** | **`₹16,70,142`** | Total OTA base commissions, TDS/TCS, and GST on commissions |
| **Pre-Rebooking Cancelled Booking Value (Historical)** | **`₹37,20,078`** | Scheduled room nights on or before `2026-11-22` |
| **Pre-Rebooking Cancelled Booking Value (All-Time)** | **`₹40,23,081` (`₹4.02M`)** | Total contract value across 405 cancellations |
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
Analyzes channel contribution, distribution cost drag (commissions + taxes), net yield efficiency, and pre-rebooking booking value leakage from cancellations.
![Channel Economics](assets/page2_channel_economics.png)

### Page 3: Room Category Performance & Lead Time Elasticity
Explores room-type occupancy distribution, booking lead times (0–3 days vs. 31+ days), and cancellation elasticity.
![Room Performance & Lead Time](assets/page3_room_lead_time.png)

---

## Tech Stack & How to Run

### Tech Stack
* **Transformation & Testing:** dbt Core (`dbt-duckdb`), DuckDB
* **Data Processing & Scripting:** Python 3.10+, pandas, openpyxl
* **Testing & CI/CD:** pytest, GitHub Actions
* **BI & Semantic Modeling:** Microsoft Power BI Desktop, DAX
* **Styling & Aesthetics:** Custom Power BI Theme (`powerbi/coorg_resort_theme.json`)

### How to Run

#### 1. Set Up Python Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows
pip install -r requirements.txt
```

#### 2. Run with Synthetic Demo Dataset (Zero Private Files Required)
Anyone cloning this repository can execute the entire pipeline end-to-end using the included synthetic demo generator:
```bash
# Generate realistic sample StayFlexi PMS reports in data/demo_sample/
python src/00_generate_demo_data.py

# Ingest and anonymize demo reports into local DuckDB
python src/01_ingest_and_anonymize.py --demo

# Transform and run all 51 data tests via dbt
dbt build --project-dir dbt_project --profiles-dir dbt_project

# Export privacy-safe portfolio CSVs
python src/02_audit_and_export.py
```

#### 3. Run with Private Production PMS Files (For Resort Operators)
If you have access to proprietary StayFlexi PMS exports:
```bash
# Place raw Excel files into data/raw_private/, then ingest:
python src/01_ingest_and_anonymize.py

# Build marts and validate integrity
dbt build --project-dir dbt_project --profiles-dir dbt_project

# Re-export public portfolio CSVs
python src/02_audit_and_export.py
```

#### 4. Running with a Custom Cutoff Date (Paired CLI Workflow)
When testing or backtesting against a non-default as-of date (e.g., `2026-11-15`), pass matching parameters to both `dbt build` and the Python export script:
```bash
dbt build --project-dir dbt_project --profiles-dir dbt_project --vars '{"as_of_date": "2026-11-15"}'
python src/02_audit_and_export.py --as-of-date 2026-11-15
```

#### 5. Execute Automated Test Suite
Run the Python regression test suite covering date parsing, Excel serial conversions, PII allowlist enforcement, and multi-room residual allocation:
```bash
pytest tests_python/
```

#### 6. Launch the Power BI Dashboard
* Open `powerbi/resort_revenue_dashboard.pbix` in Power BI Desktop.
* Refresh data to load the latest DuckDB/CSV mart exports.

---

## Methodology & Data Governance Disclosures

1. **Commercial Data Privacy & Synthetic Scaling**: To protect resort trade secrets and commercial confidentiality, raw booking monetary totals are multiplied by an audit scaling factor (`1.137`), and room types are mapped to standard industry labels (`Deluxe Room` → `Standard Room`, `Superior Cottages` → `Garden Cottage`, `Mourya Heritage House` → `Heritage Suite`, `Private Pool Villa` → `Pool Villa`) during export via `src/02_audit_and_export.py`. All percentage ratios, occupancy rates, net yields, tax structures, and cancellation rates remain mathematically exact.
2. **Defensive PII Allowlisting**: Raw StayFlexi reports are processed through an explicit allowlist of required analytical columns (`booking_key`, `room_revenue_inr`, `stay_date`, etc.). Ingestion automatically strips identifying fields and executes programmatic assertions raising `ValueError` if any prohibited PII patterns (`guest`, `phone`, `email`, `address`, `room_no`, `custom_invoice_id`) are detected in processed tables.
3. **Contractual Commission vs. Tax Deductions**: The pipeline distinguishes between pure contractual OTA commission expense (15%–18%), statutory GST on commissions (18%, potentially recoverable as Input Tax Credit), and statutory tax withholdings (1% TDS under Section 194-O / Section 52 of CGST Act). The blended `79.04%` figure reflects the **Net Settlement Yield after Estimated Deductions**.
4. **Configurable As-Of Date (`var('as_of_date')`) & Paired CLI**: The staging layer enforces `cast('{{ var("as_of_date") }}' as date)` (default: `'2026-11-22'`) in `dbt_project/dbt_project.yml` and CLI arguments in `src/02_audit_and_export.py` to cleanly partition historical realized stays from the forward on-the-books (`FUTURE_OTB`) pipeline. For non-default dates, running `dbt build --project-dir dbt_project --profiles-dir dbt_project --vars '{"as_of_date": "<DATE>"}'` must be paired with `python src/02_audit_and_export.py --as-of-date <DATE>` to ensure seamless synchronization.
5. **Unique Reservation Grain Alignment**: `fct_booking_lifecycle` is aggregated strictly at the unique reservation grain (`booking_key` primary key, `1,995` rows), ensuring that reservation volume counts and cancellation percentages share an identical grain without room-explosion distortion.
6. **Status Governance**: Unconfirmed holds (`ON_HOLD`) are strictly segregated from `REALIZED` stays and classified under `'OTHER'`, preventing uncollected revenue or pending inquiries from artificially inflating realized occupancy.
7. **Multi-Room Revenue Allocation & Rounding Tolerance**: Reservations with `no_of_rooms > 1` (12.4% of bookings) distribute booking-level totals equally across individual room nights, with residual fractional paise allocated to `room_seq = 1`. Across all three star-schema marts, revenue and distribution figures match identically at the rupee level with a `< ₹0.10` paise rounding tolerance due to differing aggregation levels.
8. **Pre-Rebooking Cancellation Terminology**: Cancelled booking amounts represent pre-rebooking contract value and do not imply permanent, unrecoverable revenue loss, as raw PMS logs do not track whether cancelled inventory slots were subsequently resold or reallocated.
