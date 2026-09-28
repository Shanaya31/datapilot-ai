"""Day 1: generate synthetic source CSVs for N days, with injected failures on some days.

    python scripts/generate_data.py --start 2026-09-21 --days 14

Writes to <data_dir>/raw/<batch_date>/<entity>.csv (+ a .fault file on days that
should simulate an upstream extract failure). Failure types match models.FailureCategory
so the evaluation harness (scripts/run_eval.py) can check the agents' diagnoses against
the ground truth.
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from faker import Faker  # noqa: E402
import pandas as pd  # noqa: E402

from datapilot.config import get_settings  # noqa: E402

fake = Faker()
random.seed(42)
Faker.seed(42)

STATUSES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
SEGMENTS = ["consumer", "smb", "enterprise"]
COUNTRIES = ["IN", "US", "GB", "AE", "SG", "DE"]

# One injected failure per entry: (day_offset, entity, failure_category)
# day 0 = --start date. Spread across the run so the eval set covers every category.
INJECTED_FAILURES = {
    2: ("orders", "null_spike"),
    4: ("customers", "duplicate_spike"),
    6: ("orders", "schema_change"),
    8: ("inventory", "low_volume"),
    10: ("orders", "stale_data"),
    11: ("orders", "invalid_values"),
    12: ("inventory", "pipeline_timeout"),
    13: ("customers", "api_failure"),
}


def gen_orders(n: int, batch_date: dt.date, customer_ids: list[str], product_ids: list[str]) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        ts = dt.datetime.combine(batch_date, dt.time()) + dt.timedelta(seconds=random.randint(0, 86399))
        rows.append({
            "order_id": fake.unique.uuid4(),
            "customer_id": random.choice(customer_ids),
            "product_id": random.choice(product_ids),
            "order_ts": ts.isoformat(),
            "quantity": random.randint(1, 5),
            "amount": round(random.uniform(5, 500), 2),
            "status": random.choice(STATUSES),
        })
    fake.unique.clear()
    return pd.DataFrame(rows)


def gen_inventory(n: int, batch_date: dt.date, product_ids: list[str], warehouse_ids: list[str]) -> pd.DataFrame:
    rows = []
    for pid in product_ids[:n]:
        ts = dt.datetime.combine(batch_date, dt.time(6, 0))
        rows.append({
            "product_id": pid,
            "warehouse_id": random.choice(warehouse_ids),
            "stock_level": random.randint(0, 500),
            "reorder_level": random.randint(20, 100),
            "snapshot_ts": ts.isoformat(),
        })
    return pd.DataFrame(rows)


def gen_customers(n: int, batch_date: dt.date) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        ts = dt.datetime.combine(batch_date, dt.time()) - dt.timedelta(days=random.randint(0, 365))
        rows.append({
            "customer_id": fake.unique.uuid4(),
            "name": fake.name(),
            "email": fake.email(),
            "country": random.choice(COUNTRIES),
            "signup_ts": ts.isoformat(),
            "segment": random.choice(SEGMENTS),
        })
    fake.unique.clear()
    return pd.DataFrame(rows)


def inject(df: pd.DataFrame, entity: str, failure: str, batch_date: dt.date, out_dir: Path) -> None:
    """Corrupt the dataframe in place to match `failure`, and/or drop a .fault marker."""
    if failure == "null_spike":
        col = "customer_id" if entity == "orders" else df.columns[1]
        idx = df.sample(frac=0.15, random_state=1).index
        df.loc[idx, col] = None
    elif failure == "duplicate_spike":
        dupes = df.sample(frac=0.10, random_state=1)
        df = pd.concat([df, dupes], ignore_index=True)
    elif failure == "schema_change":
        df = df.rename(columns={df.columns[-1]: f"{df.columns[-1]}_v2"})
    elif failure == "low_volume":
        df = df.sample(frac=0.15, random_state=1)
    elif failure == "stale_data":
        ts_col = next(c for c in df.columns if c.endswith("_ts"))
        old = dt.datetime.combine(batch_date - dt.timedelta(days=3), dt.time())
        df[ts_col] = old.isoformat()
    elif failure == "invalid_values":
        col = "amount" if "amount" in df.columns else "stock_level"
        idx = df.sample(frac=0.05, random_state=1).index
        df.loc[idx, col] = -abs(df.loc[idx, col].fillna(1)) - 1
    elif failure in ("pipeline_timeout", "api_failure"):
        (out_dir / f"{entity}.fault").write_text(failure)
        return  # extract() raises before the CSV would even be read
    df.to_csv(out_dir / f"{entity}.csv", index=False)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--orders-per-day", type=int, default=2000)
    p.add_argument("--customers", type=int, default=500)
    p.add_argument("--products", type=int, default=120)
    p.add_argument("--warehouses", type=int, default=6)
    args = p.parse_args()

    start = dt.date.fromisoformat(args.start)
    data_dir = get_settings().data_dir
    customer_ids = [fake.unique.uuid4() for _ in range(args.customers)]
    fake.unique.clear()
    product_ids = [fake.unique.uuid4() for _ in range(args.products)]
    fake.unique.clear()
    warehouse_ids = [f"WH-{i:02d}" for i in range(args.warehouses)]

    for offset in range(args.days):
        batch_date = start + dt.timedelta(days=offset)
        out_dir = data_dir / "raw" / batch_date.isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)

        orders = gen_orders(args.orders_per_day, batch_date, customer_ids, product_ids)
        inventory = gen_inventory(args.products, batch_date, product_ids, warehouse_ids)
        customers = gen_customers(max(5, args.customers // args.days), batch_date)

        frames = {"orders": orders, "inventory": inventory, "customers": customers}
        fault = INJECTED_FAILURES.get(offset)
        for entity, df in frames.items():
            if fault and fault[0] == entity:
                inject(df, entity, fault[1], batch_date, out_dir)
            else:
                df.to_csv(out_dir / f"{entity}.csv", index=False)

        tag = f" [INJECTED: {fault[0]}/{fault[1]}]" if fault else ""
        print(f"{batch_date} -> {out_dir}{tag}")

    print(f"\nDone. {args.days} days written under {data_dir / 'raw'}")
    print("Ground-truth failures (for evaluation/run_eval.py):")
    for offset, (entity, failure) in INJECTED_FAILURES.items():
        print(f"  {start + dt.timedelta(days=offset)}  {entity:<10} {failure}")


if __name__ == "__main__":
    main()
