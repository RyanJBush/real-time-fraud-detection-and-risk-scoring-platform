"""Generate a synthetic transaction dataset for offline model training and evaluation.

Produces a CSV file shaped like the transactions the FastAPI service ingests, with
a binary `is_fraud` label. The generator is deterministic given `--seed` and is
intentionally simple — it is NOT a substitute for real cardholder data.

Usage:
    python scripts/generate_synthetic_dataset.py --rows 5000 --out data/synthetic_transactions.csv
"""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

LEGIT_MERCHANTS = ["grocery", "coffee-shop", "streaming", "ride-share", "utilities", "pharmacy"]
RISKY_MERCHANTS = ["luxury-goods", "crypto-exchange", "gift-cards"]
LEGIT_COUNTRIES = ["US", "CA", "GB", "DE", "FR", "JP", "AU"]
RISKY_COUNTRIES = ["NK", "IR"]


def _legit_row(rng: random.Random) -> dict:
    return {
        "amount": round(rng.uniform(2.0, 400.0), 2),
        "merchant": rng.choice(LEGIT_MERCHANTS),
        "country": rng.choices(LEGIT_COUNTRIES, weights=[40, 12, 12, 10, 8, 8, 10])[0],
        "card_last4": f"{rng.randint(0, 9999):04d}",
        "is_fraud": 0,
    }


def _fraud_row(rng: random.Random) -> dict:
    # Mix of fraud signatures: high-amount, risky merchant, risky country, or combos.
    pattern = rng.choice(["high_amount", "risky_merchant", "risky_country", "combo"])
    if pattern == "high_amount":
        amount = round(rng.uniform(3200.0, 18000.0), 2)
        merchant = rng.choice(LEGIT_MERCHANTS + RISKY_MERCHANTS)
        country = rng.choice(LEGIT_COUNTRIES)
    elif pattern == "risky_merchant":
        amount = round(rng.uniform(150.0, 2500.0), 2)
        merchant = rng.choice(RISKY_MERCHANTS)
        country = rng.choice(LEGIT_COUNTRIES)
    elif pattern == "risky_country":
        amount = round(rng.uniform(80.0, 1500.0), 2)
        merchant = rng.choice(LEGIT_MERCHANTS)
        country = rng.choice(RISKY_COUNTRIES)
    else:
        amount = round(rng.uniform(4000.0, 20000.0), 2)
        merchant = rng.choice(RISKY_MERCHANTS)
        country = rng.choice(RISKY_COUNTRIES)
    return {
        "amount": amount,
        "merchant": merchant,
        "country": country,
        "card_last4": f"{rng.randint(0, 9999):04d}",
        "is_fraud": 1,
    }


def generate_rows(n_rows: int, fraud_rate: float, seed: int) -> list[dict]:
    if not 0.0 < fraud_rate < 1.0:
        raise ValueError("fraud_rate must be between 0 and 1 (exclusive)")
    rng = random.Random(seed)
    rows: list[dict] = []
    for _ in range(n_rows):
        rows.append(_fraud_row(rng) if rng.random() < fraud_rate else _legit_row(rng))
    return rows


def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["amount", "merchant", "country", "card_last4", "is_fraud"]
    with out_path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5000, help="Total rows to generate")
    parser.add_argument("--fraud-rate", type=float, default=0.08, help="Fraction of fraudulent rows")
    parser.add_argument("--seed", type=int, default=42)
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
    print(f"Wrote {len(rows)} rows to {args.out} (fraud={n_fraud}, legit={len(rows) - n_fraud})")


if __name__ == "__main__":
    main()
