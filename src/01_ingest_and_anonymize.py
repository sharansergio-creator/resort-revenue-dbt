import argparse
import pathlib
import sys

# Ensure repository root is in sys.path
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import duckdb
import pandas as pd
from src.generate_demo_data import generate_demo_dataset

DEFAULT_RAW_DIR = pathlib.Path("data/raw_private")
DEMO_DIR = pathlib.Path("data/demo_sample")
DEFAULT_OUT_DIR = pathlib.Path("data/processed_private")
DEFAULT_DB_PATH = DEFAULT_OUT_DIR / "resort_private.duckdb"

MASTER_FILE_NAME = "Master_report_2025-11-01_2027-01-31.xlsx"
REVENUE_FILE_NAME = "Room_Revenue_Report_2025-11-01_2027-01-31.xlsx"
INVENTORY_FILE_NAME = "Room_Inventory_Report_2025-11-01_2027-01-31.xlsx"

# Strict Analytical Allowlist - ONLY these non-identifying columns are permitted in processed tables
MASTER_ALLOWLIST = [
    "booking_key", "booking_date", "check_in_date", "check_out_date",
    "source", "booking_status", "adults", "no_of_rooms",
    "room_types", "rate_plans", "total_amount_inr",
    "payment_made_inr", "balance_due_inr", "pre_booking_window"
]

REVENUE_ALLOWLIST = [
    "booking_key", "check_in", "check_out", "room_nights",
    "booking_status", "source", "room_revenue_inr", "room_taxes_inr",
    "total_amt_inr", "services_amt_inr", "room_discount", "room_discount_tax",
    "booking_amt_inr", "balance_amt_inr", "external_ota_card_paid_inr",
    "offline_counter_paid_inr", "external_ota_cash_paid_inr",
    "online_pg_terminal_paid_inr", "fee_amount_inr", "total_refunds_inr",
    "partial_tax_exempt", "total_tax_exempt", "taxable_revenue_inr",
    "tax_exempt_revenue_inr", "excess_exempt"
]

INVENTORY_ALLOWLIST = [
    "stay_date", "total_rooms", "blocked_rooms", "net_rooms",
    "sold_rooms", "available_rooms", "occupancy", "unassign_count"
]

PROHIBITED_PII_PATTERNS = ["guest", "phone", "mobile", "email", "address", "room_no", "custom_invoice_id"]


def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def parse_stayflexi_date(series: pd.Series) -> pd.Series:
    """
    Parse dates from StayFlexi reports, supporting:
    - Excel numeric serial offsets (integers/floats between 30000 and 60000, e.g., 45620)
    - DD/MM/YYYY dates
    - Standard text date formats ('Nov 1, 2025', '2025-11-01')
    """
    numeric_s = pd.to_numeric(series, errors="coerce")
    excel_mask = numeric_s.notna() & numeric_s.between(30000, 60000)

    result = pd.Series(index=series.index, dtype="datetime64[ns]")
    if excel_mask.any():
        result.loc[excel_mask] = pd.to_datetime(numeric_s.loc[excel_mask], unit="D", origin="1899-12-30")

    rem_mask = ~excel_mask & series.notna()
    if rem_mask.any():
        s = series.loc[rem_mask].astype(str).str.strip()
        parsed = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
        unmatched = parsed.isna()
        if unmatched.any():
            parsed.loc[unmatched] = pd.to_datetime(s.loc[unmatched], format="%Y-%m-%d", errors="coerce")
            unmatched2 = parsed.isna()
            if unmatched2.any():
                parsed.loc[unmatched2] = pd.to_datetime(s.loc[unmatched2], errors="coerce", dayfirst=True)
        result.loc[rem_mask] = parsed

    return result.dt.date


def assert_no_pii(df: pd.DataFrame, table_name: str) -> None:
    """Defensive audit: raise ValueError if any identifying/PII columns appear in processed DataFrame."""
    for col in df.columns:
        for pattern in PROHIBITED_PII_PATTERNS:
            if pattern in col.lower():
                raise ValueError(
                    f"PII Leak Detected in {table_name}! Prohibited column pattern '{pattern}' matched column '{col}'."
                )


def run_pipeline(input_dir: pathlib.Path, db_path: pathlib.Path) -> None:
    master_file = input_dir / MASTER_FILE_NAME
    revenue_file = input_dir / REVENUE_FILE_NAME
    inventory_file = input_dir / INVENTORY_FILE_NAME

    for f in [master_file, revenue_file, inventory_file]:
        if not f.exists():
            raise FileNotFoundError(f"Required report file not found: {f}")

    print(f"Reading raw PMS exports from: {input_dir}")
    df_master = clean_cols(pd.read_excel(master_file))
    df_rev = clean_cols(pd.read_excel(revenue_file))
    df_inv = clean_cols(pd.read_excel(inventory_file))

    # Drop summary/footer rows where booking_id or date is null
    df_master = df_master[df_master["booking_id"].notna()].copy()
    df_rev = df_rev[df_rev["booking_id"].notna()].copy()
    df_inv = df_inv[df_inv["date"].notna()].copy()

    df_master["booking_id_raw"] = df_master["booking_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_rev["booking_id_raw"] = df_rev["booking_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    # Parse dates with robust Excel serial and string parser
    for col in ["booking_date", "check_in_date", "check_out_date"]:
        if col in df_master.columns:
            df_master[col] = parse_stayflexi_date(df_master[col])
    for col in ["check_in", "check_out"]:
        if col in df_rev.columns:
            df_rev[col] = parse_stayflexi_date(df_rev[col])
    df_inv["stay_date"] = parse_stayflexi_date(df_inv["date"])
    df_inv = df_inv[df_inv["stay_date"].notna()].copy()

    # Build deterministic synthetic booking_key sorted chronologically (zero PII retained)
    all_ids = (
        df_master[["booking_id_raw", "check_in_date", "booking_date"]]
        .drop_duplicates("booking_id_raw")
        .sort_values(["check_in_date", "booking_date", "booking_id_raw"], na_position="last")
        .reset_index(drop=True)
    )
    all_ids["booking_key"] = [f"BK-{i+1:05d}" for i in range(len(all_ids))]
    id_map = dict(zip(all_ids["booking_id_raw"], all_ids["booking_key"]))

    # Map synthetic keys
    df_master["booking_key"] = df_master["booking_id_raw"].map(id_map)
    df_rev["booking_key"] = df_rev["booking_id_raw"].map(id_map).fillna("UNMAPPED")

    # Enforce defensive PII allowlisting: keep ONLY allowed analytical columns
    df_master_clean = df_master[[c for c in MASTER_ALLOWLIST if c in df_master.columns]].copy()
    df_rev_clean = df_rev[[c for c in REVENUE_ALLOWLIST if c in df_rev.columns]].copy()
    df_inv_clean = df_inv[[c for c in INVENTORY_ALLOWLIST if c in df_inv.columns]].copy()

    # Validate zero PII columns exist in clean DataFrames
    assert_no_pii(df_master_clean, "master_bookings")
    assert_no_pii(df_rev_clean, "room_revenue")
    assert_no_pii(df_inv_clean, "daily_inventory")

    # Write to local DuckDB database
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    con.execute("CREATE TABLE raw.master_bookings AS SELECT * FROM df_master_clean;")
    con.execute("CREATE TABLE raw.room_revenue AS SELECT * FROM df_rev_clean;")
    con.execute("CREATE TABLE raw.daily_inventory AS SELECT * FROM df_inv_clean;")
    con.close()

    print(f"Success! Clean PII-free tables written to {db_path}")
    print(f"  - master_bookings: {len(df_master_clean)} rows, {len(df_master_clean.columns)} columns")
    print(f"  - room_revenue:   {len(df_rev_clean)} rows, {len(df_rev_clean.columns)} columns")
    print(f"  - daily_inventory:{len(df_inv_clean)} rows, {len(df_inv_clean.columns)} columns")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest, validate, and anonymize StayFlexi PMS reports.")
    parser.add_argument(
        "--input-dir",
        type=pathlib.Path,
        default=None,
        help="Input directory containing raw Excel reports",
    )
    parser.add_argument(
        "--output-db",
        type=pathlib.Path,
        default=None,
        help="Output DuckDB database path",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate synthetic demo data if missing and run ingestion against demo dataset",
    )
    args = parser.parse_args()

    if args.demo:
        input_dir = args.input_dir or DEMO_DIR
        if not (input_dir / MASTER_FILE_NAME).exists():
            generate_demo_dataset(input_dir)
        output_db = args.output_db or (DEFAULT_OUT_DIR / "resort_demo.duckdb")
    else:
        if args.input_dir:
            input_dir = args.input_dir
        elif DEFAULT_RAW_DIR.exists() and (DEFAULT_RAW_DIR / MASTER_FILE_NAME).exists():
            input_dir = DEFAULT_RAW_DIR
        else:
            input_dir = DEMO_DIR
            if not (input_dir / MASTER_FILE_NAME).exists():
                generate_demo_dataset(input_dir)
        output_db = args.output_db or DEFAULT_DB_PATH

    run_pipeline(input_dir=input_dir, db_path=output_db)


if __name__ == "__main__":
    main()
