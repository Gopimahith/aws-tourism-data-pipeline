"""Generate a SYNTHETIC tourism visits file, including deliberate data problems.

This data is randomly generated for demonstration. It is not real traveller
data. About 8% of rows are corrupted on purpose so the validation rules and
the quality report have something to catch.

Usage: python src/generate_sample_data.py --rows 5000 --out data/sample_visits.csv
"""
import argparse
import os
import random

import pandas as pd

ATTRACTION_TYPES = ["Beach", "Museum", "Nature Park", "Heritage Site", "Water Sports", "Market"]
COUNTRIES = ["India", "France", "Japan", "Brazil", "Egypt", "Australia", "Canada"]
MODES = ["Business", "Couples", "Family", "Friends", "Solo"]


def generate(rows: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    data = []
    for i in range(1, rows + 1):
        data.append(
            {
                "visit_id": f"V{i:06d}",
                "user_id": f"U{rng.randint(1, max(2, rows // 4)):05d}",
                "attraction_id": f"A{rng.randint(1, 60):03d}",
                "attraction_type": rng.choice(ATTRACTION_TYPES),
                "country": rng.choice(COUNTRIES),
                "visit_year": rng.choice([2022, 2023, 2024]),
                "visit_month": rng.randint(1, 12),
                "visit_mode": rng.choice(MODES),
                "rating": rng.choices([1, 2, 3, 4, 5], weights=[3, 6, 16, 35, 40])[0],
            }
        )
    df = pd.DataFrame(data)

    # Inject problems into roughly 8% of rows.
    bad = rng.sample(range(rows), k=int(rows * 0.08))
    for n, idx in enumerate(bad):
        kind = n % 4
        if kind == 0:
            df.loc[idx, "rating"] = rng.choice([0, 6, 9])
        elif kind == 1:
            df.loc[idx, "visit_month"] = 13
        elif kind == 2:
            df.loc[idx, "country"] = ""
        else:
            df.loc[idx, "visit_id"] = df.loc[max(0, idx - 1), "visit_id"]  # duplicate id
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--out", default="data/sample_visits.csv")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    generate(args.rows).to_csv(args.out, index=False)
    print(f"Wrote {args.rows} synthetic rows to {args.out}")
