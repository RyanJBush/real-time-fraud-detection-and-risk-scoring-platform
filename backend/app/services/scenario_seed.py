from __future__ import annotations

import random

from app.models import Transaction

SCENARIOS = {"card_testing_burst", "high_value_geo_attack", "merchant_takeover"}


class ScenarioSeedError(ValueError):
    pass


def generate_seeded_transactions(scenario: str, count: int, seed: int) -> list[tuple[Transaction, str | None]]:
    if scenario not in SCENARIOS:
        msg = f"Unknown scenario '{scenario}'. Supported: {sorted(SCENARIOS)}"
        raise ScenarioSeedError(msg)

    rng = random.Random(seed)
    generated: list[tuple[Transaction, str | None]] = []

    for idx in range(count):
        if scenario == "card_testing_burst":
            tx = Transaction(
                amount=round(rng.uniform(5, 50), 2),
                merchant="gift-cards",
                country=rng.choice(["US", "GB", "US", "CA"]),
                card_last4=f"{rng.randint(1000, 9999)}",
            )
            label = "suspected_fraud"
        elif scenario == "high_value_geo_attack":
            tx = Transaction(
                amount=round(rng.uniform(5500, 18000), 2),
                merchant=rng.choice(["luxury-goods", "crypto-exchange", "electronics"]),
                country=rng.choice(["IR", "NK", "US"]),
                card_last4=f"{(4200 + idx) % 10000:04d}",
            )
            label = "confirmed_fraud"
        else:
            tx = Transaction(
                amount=round(rng.uniform(250, 4000), 2),
                merchant=rng.choice(["marketplace", "gift-cards", "travel-booking"]),
                country=rng.choice(["US", "DE", "FR", "BR"]),
                card_last4=f"{(7600 + idx) % 10000:04d}",
            )
            label = "chargeback" if idx % 4 == 0 else None

        generated.append((tx, label))

    return generated
