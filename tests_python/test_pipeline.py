import datetime
import importlib
import pathlib
import pytest
import pandas as pd
import numpy as np
import duckdb

ingest_mod = importlib.import_module("src.01_ingest_and_anonymize")
parse_stayflexi_date = ingest_mod.parse_stayflexi_date
assert_no_pii = ingest_mod.assert_no_pii
run_pipeline = ingest_mod.run_pipeline
PROHIBITED_PII_PATTERNS = ingest_mod.PROHIBITED_PII_PATTERNS
MASTER_ALLOWLIST = ingest_mod.MASTER_ALLOWLIST
REVENUE_ALLOWLIST = ingest_mod.REVENUE_ALLOWLIST
INVENTORY_ALLOWLIST = ingest_mod.INVENTORY_ALLOWLIST

from src.generate_demo_data import generate_demo_dataset


class TestStayflexiDateParsing:
    def test_excel_serial_numeric_and_float(self):
        # 45620 days from 1899-12-30 is 2024-11-24
        s = pd.Series([45620, 45620.0, "45620"])
        parsed = parse_stayflexi_date(s)
        expected = datetime.date(2024, 11, 24)
        assert parsed.iloc[0] == expected
        assert parsed.iloc[1] == expected
        assert parsed.iloc[2] == expected

    def test_dd_mm_yyyy_format(self):
        s = pd.Series(["22/11/2026", "01/11/2025", "15/08/2026"])
        parsed = parse_stayflexi_date(s)
        assert parsed.iloc[0] == datetime.date(2026, 11, 22)
        assert parsed.iloc[1] == datetime.date(2025, 11, 1)
        assert parsed.iloc[2] == datetime.date(2026, 8, 15)

    def test_standard_iso_and_text_format(self):
        s = pd.Series(["2026-11-22", "Nov 1, 2025"])
        parsed = parse_stayflexi_date(s)
        assert parsed.iloc[0] == datetime.date(2026, 11, 22)
        assert parsed.iloc[1] == datetime.date(2025, 11, 1)

    def test_null_and_empty_values(self):
        s = pd.Series([None, np.nan, ""])
        parsed = parse_stayflexi_date(s)
        assert pd.isna(parsed.iloc[0])
        assert pd.isna(parsed.iloc[1])
        assert pd.isna(parsed.iloc[2])


class TestPIIAllowlisting:
    def test_assert_no_pii_clean_dataframe(self):
        clean_df = pd.DataFrame({
            "booking_key": ["BK-00001"],
            "room_revenue_pre_gst": [5000.0],
            "stay_date": ["2026-11-22"]
        })
        # Should not raise any error
        assert_no_pii(clean_df, "test_table")

    @pytest.mark.parametrize("bad_col", PROHIBITED_PII_PATTERNS)
    def test_assert_no_pii_raises_on_prohibited_columns(self, bad_col):
        dirty_df = pd.DataFrame({
            "booking_key": ["BK-00001"],
            bad_col: ["sensitive_data"]
        })
        with pytest.raises(ValueError, match="PII Leak Detected"):
            assert_no_pii(dirty_df, "test_table")

    def test_allowlist_matches_definitions(self):
        assert "booking_key" in MASTER_ALLOWLIST
        assert "guest" not in MASTER_ALLOWLIST
        assert "phone" not in MASTER_ALLOWLIST
        assert "email" not in REVENUE_ALLOWLIST
        assert "room_no" not in MASTER_ALLOWLIST


class TestMultiRoomResidualAllocation:
    def test_three_room_paise_exact_reconciliation(self):
        # Booking total = 10,000 INR across 3 rooms
        booking_revenue = 10000.00
        num_rooms = 3
        
        room_allocations = []
        for room_seq in range(1, num_rooms + 1):
            if room_seq == 1:
                amt = round(booking_revenue - round(booking_revenue / num_rooms, 2) * (num_rooms - 1), 2)
            else:
                amt = round(booking_revenue / num_rooms, 2)
            room_allocations.append(amt)

        assert room_allocations[0] == 3333.34
        assert room_allocations[1] == 3333.33
        assert room_allocations[2] == 3333.33
        assert sum(room_allocations) == booking_revenue

    def test_multi_night_stay_residual_allocation(self):
        # Room revenue = 10,000 INR across 3 nights
        room_rev = 10000.00
        los = 3
        
        night_allocations = []
        for night_index in range(los):
            if night_index + 1 == los:
                amt = round(room_rev - round(room_rev / los, 2) * (los - 1), 2)
            else:
                amt = round(room_rev / los, 2)
            night_allocations.append(amt)

        assert night_allocations == [3333.33, 3333.33, 3333.34]
        assert sum(night_allocations) == room_rev


class TestEndToEndSyntheticPipeline:
    def test_synthetic_demo_generation_and_ingestion(self, tmp_path):
        demo_raw_dir = tmp_path / "raw_demo"
        demo_db_path = tmp_path / "processed" / "test_resort.duckdb"

        # 1. Generate synthetic demo Excel reports
        generate_demo_dataset(output_dir=demo_raw_dir)
        assert (demo_raw_dir / "Master_report_2025-11-01_2027-01-31.xlsx").exists()
        assert (demo_raw_dir / "Room_Revenue_Report_2025-11-01_2027-01-31.xlsx").exists()
        assert (demo_raw_dir / "Room_Inventory_Report_2025-11-01_2027-01-31.xlsx").exists()

        # 2. Run ingestion pipeline into isolated temporary DuckDB
        run_pipeline(input_dir=demo_raw_dir, db_path=demo_db_path)
        assert demo_db_path.exists()

        # 3. Verify tables and absence of PII
        con = duckdb.connect(str(demo_db_path), read_only=True)
        tables = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw';").fetchall()]
        assert "master_bookings" in tables
        assert "room_revenue" in tables
        assert "daily_inventory" in tables

        for tbl in tables:
            cols = [c.lower() for c in con.execute(f"DESCRIBE raw.{tbl};").df()["column_name"]]
            for pattern in PROHIBITED_PII_PATTERNS:
                assert not any(pattern in c for c in cols), f"PII pattern '{pattern}' found in raw.{tbl} columns!"

        master_count = con.execute("SELECT count(*) FROM raw.master_bookings;").fetchone()[0]
        revenue_count = con.execute("SELECT count(*) FROM raw.room_revenue;").fetchone()[0]
        inv_count = con.execute("SELECT count(*) FROM raw.daily_inventory;").fetchone()[0]

        assert master_count > 0
        assert revenue_count > 0
        assert inv_count > 0
        con.close()
