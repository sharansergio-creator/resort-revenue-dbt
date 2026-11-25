# Coorg Resort Revenue & Channel Performance Analytics (dbt + Power BI)

An end-to-end hospitality revenue management and channel profitability analytics pipeline built with **dbt**, **DuckDB**, **Python**, and **Power BI**. Designed around multi-channel resort operations in Coorg, Karnataka, this project transforms raw PMS reservations, room inventory, and OTA commission structures into an executive three-page Power BI semantic model.

---

## Key Business Findings & Strategic Recommendations

* **Strong Direct Demand Engine (`65.4%` Direct Share):** Direct channels—led by **WhatsApp (`₹1.15Cr` Gross)** and **Walk-In (`₹43.1L` Gross)**—drive nearly two-thirds of occupied room nights at **`100.0%` Net Yield** (`₹0` distribution cost).
* **OTA Commission & Cancellation Leakage:** Online Travel Agencies (Goibibo, Agoda, MakeMyTrip, Cleartrip) compress net yield to **`77%–81%`**, generating **`₹16,72,953`** in direct commission/GST/TDS distribution costs and accounting for over **`95%` of the `₹4.0M`** in cancelled room revenue lost.
  * *Recommendation:* Introduce direct-booking incentives (complimentary breakfast or early check-in via WhatsApp/website) for repeat OTA guests and enforce stricter deposit rules on high-commission OTA rate plans.
* **Weekday vs. Weekend Occupancy Gap (`31.8%` vs. `54.5%`):** Weekend stays achieve **`₹4,404` Net RevPAR** (`₹8,081` Net ADR) compared to **`₹2,356` Net RevPAR** (`₹7,408` Net ADR) on Sun–Thu nights.
  * *Recommendation:* Launch workcation packages and 3-night mid-week couple bundles during Shoulder and Monsoon seasons to lift weekday occupancy closer to `42%+`.
* **Lead-Time Cancellation Elasticity (`7.6%` vs. `38.7%`):** Last-minute bookings (`0–3 days` lead time) represent the highest booking volume (`752` reservations) with only a **`7.6%`** cancellation rate, whereas early-bird bookings (`31+ days`) cancel at **`38.7%`**.
  * *Recommendation:* Require non-refundable partial prepayments or automated 14-day pre-arrival reconfirmation workflows for reservations booked `30+` days in advance.

---

## Architecture & Data Model

```text
Raw PMS & OTA Exports ─▶ Staging (stg_*) ─▶ Star Schema Marts (dbt + DuckDB) ─▶ Power BI Semantic Model (_Measures)
```
