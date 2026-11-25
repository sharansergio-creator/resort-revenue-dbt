import pathlib
import pandas as pd
import duckdb

RAW_DIR = pathlib.Path("data/raw_private")
OUT_DIR = pathlib.Path("data/processed_private")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = OUT_DIR / "resort_private.duckdb"

MASTER_FILE = RAW_DIR / "Master_report_2025-11-01_2027-01-31.xlsx"
REVENUE_FILE = RAW_DIR / "Room_Revenue_Report_2025-11-01_2027-01-31.xlsx"
INVENTORY_FILE = RAW_DIR / "Room_Inventory_Report_2025-11-01_2027-01-31.xlsx"


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
    # Handle DD/MM/YYYY, 'Nov 1, 2025', and Excel numeric serial dates cleanly
    s = series.astype(str).str.strip()
    parsed = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    mask = parsed.isna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(s.loc[mask], errors="coerce", dayfirst=True)
    return parsed.dt.date


def main() -> None:
    df_master = clean_cols(pd.read_excel(MASTER_FILE))
    df_rev = clean_cols(pd.read_excel(REVENUE_FILE))
    df_inv = clean_cols(pd.read_excel(INVENTORY_FILE))

    # Drop any footer/total summary rows where booking_id or date is null
    df_master = df_master[df_master["booking_id"].notna()].copy()
    df_rev = df_rev[df_rev["booking_id"].notna()].copy()
    df_inv = df_inv[df_inv["date"].notna()].copy()

    df_master["booking_id_raw"] = df_master["booking_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df_rev["booking_id_raw"] = df_rev["booking_id"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

    # Parse dates
    for col in ["booking_date", "check_in_date", "check_out_date"]:
        df_master[col] = parse_stayflexi_date(df_master[col])
    for col in ["check_in", "check_out"]:
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

    # Audit join coverage before dropping raw IDs
    master_ids = set(df_master["booking_id_raw"])
    rev_ids = set(df_rev["booking_id_raw"])
    print(f"Master rows: {len(df_master)} | Unique IDs: {len(master_ids)}")
    print(f"Revenue rows: {len(df_rev)} | Unique IDs: {len(rev_ids)}")
    print(f"Matched IDs: {len(master_ids & rev_ids)} | Master-only: {len(master_ids - rev_ids)} | Rev-only: {len(rev_ids - master_ids)}")
    print(f"Inventory rows: {len(df_inv)} | Date range: {df_inv['stay_date'].min()} -> {df_inv['stay_date'].max()}")

    # Map synthetic keys and strictly drop all PII / raw identifiers
    df_master["booking_key"] = df_master["booking_id_raw"].map(id_map)
    df_rev["booking_key"] = df_rev["booking_id_raw"].map(id_map).fillna("UNMAPPED")

    pii_master = ["booking_id", "booking_id_raw", "room_no", "guest"]
    pii_rev = ["booking_id", "booking_id_raw", "guest", "email", "room_no_s", "custom_invoice_id"]

    df_master_clean = df_master.drop(columns=[c for c in pii_master if c in df_master.columns])
    df_rev_clean = df_rev.drop(columns=[c for c in pii_rev if c in df_rev.columns])
    df_inv_clean = df_inv.drop(columns=["date"])

    # Write to private local DuckDB
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    con.execute("CREATE TABLE raw.master_bookings AS SELECT * FROM df_master_clean;")
    con.execute("CREATE TABLE raw.room_revenue AS SELECT * FROM df_rev_clean;")
    con.execute("CREATE TABLE raw.daily_inventory AS SELECT * FROM df_inv_clean;")

    print("\nDistinct Room Types in Master:", sorted(df_master_clean["room_types"].dropna().unique().tolist()))
    print("Booking Date Range:", df_master_clean["check_in_date"].min(), "->", df_master_clean["check_out_date"].max())
    con.close()
    print(f"\nSuccess! Clean PII-free tables written to {DB_PATH}")


if __name__ == "__main__":
    main()
