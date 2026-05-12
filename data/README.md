# Data

This folder holds synthetic transaction datasets used for offline training and
evaluation. Real bank or cardholder data must **never** be committed here.

## Files

- `synthetic_transactions.csv` — 2,000 rows generated with `seed=42` and a
  ~7% fraud base rate. Regenerate (or scale up) with:

  ```bash
  python scripts/generate_synthetic_dataset.py --rows 10000 --out data/synthetic_transactions.csv
  ```

## Schema

| Column      | Type    | Notes                                        |
|-------------|---------|----------------------------------------------|
| amount      | float   | Transaction amount in USD                    |
| merchant    | string  | Merchant category (e.g. `gift-cards`)        |
| country     | string  | ISO-2 country code                           |
| card_last4  | string  | Last four digits, zero-padded (synthetic)    |
| is_fraud    | int     | Binary label (1 = fraud, 0 = legitimate)     |

## Limitations

The generator hand-codes fraud signatures (high amount, risky merchant, risky
country). It is useful for end-to-end demos and unit tests but is **not
representative** of real bank fraud, which involves device fingerprints,
velocity patterns, behavioral biometrics, network features, and adversarial
drift. Treat any metric computed on this data as illustrative.
