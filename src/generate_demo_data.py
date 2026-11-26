import argparse
import datetime
import pathlib
import pandas as pd
import numpy as np


def generate_demo_dataset(output_dir: pathlib.Path = pathlib.Path("data/demo_sample")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    # 1. Generate dates for inventory: 2025-11-01 to 2026-11-30 (395 days)
    start_date = datetime.date(2025, 11, 1)
    date_list = [start_date + datetime.timedelta(days=i) for i in range(395)]
    
    # 2. Generate 120 synthetic reservations
    channels = ["WHATSAPP", "WALK-IN", "PHONE CALL", "MAKEMYTRIP", "GOIBIBO", "AGODA", "EXPEDIA"]
    channel_weights = [0.35, 0.15, 0.15, 0.15, 0.10, 0.05, 0.05]
    room_types_list = ["Deluxe Room", "Superior Cottages", "Private Pool Villa", "Mourya Heritage House"]
    rate_plans_list = ["CP", "MAP", "EP / Standard", "CP (Breakfast)"]
    
    master_records = []
    revenue_records = []
    
    # Inventory tracker
    daily_sold = {d: 0 for d in date_list}

    for i in range(1, 151):
        booking_id = f"100{i:04d}"
        ch = np.random.choice(channels, p=channel_weights)
        
        # Pick check-in date between 2025-11-05 and 2026-11-25
        stay_start_idx = np.random.randint(5, 380)
        check_in = date_list[stay_start_idx]
        los = np.random.choice([1, 2, 3, 4], p=[0.45, 0.40, 0.10, 0.05])
        check_out = check_in + datetime.timedelta(days=int(los))
        
        lead_time = int(np.random.choice([1, 3, 7, 14, 25, 45], p=[0.25, 0.20, 0.20, 0.15, 0.10, 0.10]))
        booking_date = check_in - datetime.timedelta(days=lead_time)
        
        # Booking status
        is_future = check_in > datetime.date(2026, 11, 22)
        if is_future:
            status = np.random.choice(["CONFIRMED", "CANCELLED"], p=[0.8, 0.2])
        else:
            status = np.random.choice(["CHECKED OUT", "CANCELLED"], p=[0.8, 0.2])
            
        num_rooms = int(np.random.choice([1, 2, 3], p=[0.85, 0.10, 0.05]))
        room_type = np.random.choice(room_types_list)
        rate_plan = np.random.choice(rate_plans_list)
        
        if num_rooms > 1:
            room_types_str = ",".join([room_type] * num_rooms)
            rate_plans_str = ",".join([rate_plan] * num_rooms)
        else:
            room_types_str = room_type
            rate_plans_str = rate_plan
            
        # Base pricing per room night ~ 6000 to 12000
        rate_per_night = float(np.random.choice([6500, 7500, 8500, 10500, 14000]))
        room_rev = round(rate_per_night * los * num_rooms, 2)
        room_tax = round(room_rev * 0.12, 2)
        services_amt = round(float(np.random.choice([0, 500, 1200, 2500])), 2)
        total_amt = round(room_rev + room_tax + services_amt, 2)
        
        # In inventory, record sold nights if realized
        if status in ("CHECKED OUT", "CONFIRMED"):
            for d_idx in range(stay_start_idx, min(stay_start_idx + los, len(date_list))):
                daily_sold[date_list[d_idx]] += num_rooms

        # Include some Excel serial dates (e.g. for row 10 to 15) to verify parser
        use_serial = (i % 25 == 0)
        def format_date(d):
            if use_serial:
                # Excel serial offset from 1899-12-30
                delta = d - datetime.date(1899, 12, 30)
                return delta.days
            return d.strftime("%d/%m/%Y") if i % 2 == 0 else d.strftime("%Y-%m-%d")

        # Master record with dummy PII columns to verify allowlist filter
        master_records.append({
            "booking_id": booking_id,
            "guest": f"Demo Guest {i}",
            "room_no": f"Room-{100+i%20}",
            "phone": "+91 9876543210",
            "booking_date": format_date(booking_date),
            "check_in_date": format_date(check_in),
            "check_out_date": format_date(check_out),
            "source": ch,
            "booking_status": status,
            "adults": int(num_rooms * 2),
            "no_of_rooms": num_rooms,
            "room_types": room_types_str,
            "rate_plans": rate_plans_str,
            "total_amount_inr": total_amt,
            "payment_made_inr": total_amt if status != "CANCELLED" else 0.0,
            "balance_due_inr": 0.0,
            "pre_booking_window": lead_time,
        })
        
        # Revenue record with dummy PII
        revenue_records.append({
            "booking_id": booking_id,
            "guest": f"Demo Guest {i}",
            "email": f"guest{i}@example.com",
            "custom_invoice_id": f"INV-2026-{i:05d}",
            "check_in": format_date(check_in),
            "check_out": format_date(check_out),
            "room_nights": los * num_rooms,
            "booking_status": status,
            "source": ch,
            "room_revenue_inr": room_rev,
            "room_taxes_inr": room_tax,
            "services_amt_inr": services_amt,
            "room_discount": 0.00,
            "room_discount_tax": 0.00,
            "total_amt_inr": total_amt,
            "booking_amt_inr": total_amt,
            "balance_amt_inr": 0.00,
            "total_refunds_inr": 0.00 if status != "CANCELLED" else total_amt,
        })

    # 3. Inventory records
    inventory_records = []
    total_physical = 20
    for d in date_list:
        sold = min(daily_sold[d], total_physical)
        blocked = 1 if d.weekday() == 1 else 0  # maintenance on Tuesdays
        net_sellable = total_physical - blocked
        avail = max(0, net_sellable - sold)
        occ = round(sold / net_sellable, 4) if net_sellable > 0 else 0.0
        
        inventory_records.append({
            "date": d.strftime("%d/%m/%Y"),
            "total_rooms": total_physical,
            "blocked_rooms": blocked,
            "net_rooms": net_sellable,
            "sold_rooms": sold,
            "available_rooms": avail,
            "occupancy": occ,
            "unassign_count": 0,
        })

    df_master = pd.DataFrame(master_records)
    df_rev = pd.DataFrame(revenue_records)
    df_inv = pd.DataFrame(inventory_records)

    master_path = output_dir / "Master_report_2025-11-01_2027-01-31.xlsx"
    rev_path = output_dir / "Room_Revenue_Report_2025-11-01_2027-01-31.xlsx"
    inv_path = output_dir / "Room_Inventory_Report_2025-11-01_2027-01-31.xlsx"

    df_master.to_excel(master_path, index=False)
    df_rev.to_excel(rev_path, index=False)
    df_inv.to_excel(inv_path, index=False)

    print(f"Generated synthetic demo PMS datasets in {output_dir}:")
    print(f"  - Master Bookings: {len(df_master)} rows -> {master_path.name}")
    print(f"  - Room Revenue:   {len(df_rev)} rows -> {rev_path.name}")
    print(f"  - Daily Inventory:{len(df_inv)} rows -> {inv_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic demo PMS dataset.")
    parser.add_argument(
        "--output-dir",
        default="data/demo_sample",
        type=pathlib.Path,
        help="Target directory for synthetic Excel reports",
    )
    args = parser.parse_args()
    generate_demo_dataset(args.output_dir)
