from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()


def main(rows: int = 12000, seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    categories = ["grocery", "electronics", "travel", "gaming", "crypto", "gift-cards", "luxury"]
    data = []
    for i in range(rows):
        amount = float(np.round(np.random.lognormal(mean=4.2, sigma=0.9), 2))
        intl = int(np.random.rand() < 0.12)
        velocity_1h = int(np.random.poisson(1.5 + 2 * intl))
        velocity_24h = int(velocity_1h + np.random.poisson(5))
        is_fraud = int(np.random.rand() < (0.02 + 0.2 * (amount > 2500) + 0.08 * intl + 0.05 * (velocity_1h > 5)))
        data.append({
            "transaction_id": f"txn_{i+1:06d}",
            "user_id": f"user_{random.randint(1, 3000):05d}",
            "amount": amount,
            "merchant_category": random.choice(categories),
            "hour_of_day": random.randint(0, 23),
            "day_of_week": random.randint(0, 6),
            "is_international": intl,
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
            "is_fraud": is_fraud,
        })
    df = pd.DataFrame(data)
    out = Path("data/synthetic_transactions.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
