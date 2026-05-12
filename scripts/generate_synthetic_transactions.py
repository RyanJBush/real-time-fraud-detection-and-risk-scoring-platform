"""Generate synthetic transaction rows for Meridian demos.

Synthetic-only data generator for portfolio/testing workflows.
This script does NOT generate or use real banking/customer data.
"""
from __future__ import annotations

from pathlib import Path

from generate_synthetic_dataset import generate_rows, write_csv


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1200, help="Total synthetic rows")
    parser.add_argument("--fraud-rate", type=float, default=0.10, help="Synthetic fraud fraction")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/synthetic_transactions.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    rows = generate_rows(args.rows, args.fraud_rate, args.seed)
    write_csv(rows, args.out)
    n_fraud = sum(r["is_fraud"] for r in rows)
    print(
        f"Synthetic dataset written: {args.out} | rows={len(rows)} fraud={n_fraud} legit={len(rows)-n_fraud}"
    )


if __name__ == "__main__":
    main()
