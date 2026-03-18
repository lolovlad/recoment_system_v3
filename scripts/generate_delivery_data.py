from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES = ["distance", "hour", "day_of_week", "items_count"]
TARGET = "delivery_minutes"


def generate_synthetic_dataset(n_rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    distance = rng.uniform(0.3, 30.0, size=n_rows).astype(np.float32)
    hour = rng.integers(0, 24, size=n_rows).astype(np.int32)
    day_of_week = rng.integers(0, 7, size=n_rows).astype(np.int32)
    items_count = rng.integers(1, 15, size=n_rows).astype(np.int32)

    base = 12.0
    distance_part = distance * 2.8
    items_part = items_count * 1.6
    rush_hour = np.where((hour >= 17) & (hour <= 20), 8.0, 0.0)
    late_night = np.where((hour <= 6), 3.0, 0.0)
    weekend = np.where(day_of_week >= 5, 5.0, 0.0)
    noise = rng.normal(0.0, 3.0, size=n_rows).astype(np.float32)

    minutes = base + distance_part + items_part + rush_hour + late_night + weekend + noise
    minutes = np.clip(minutes, 5.0, None).astype(np.float32)

    return pd.DataFrame(
        {
            "distance": distance,
            "hour": hour,
            "day_of_week": day_of_week,
            "items_count": items_count,
            "delivery_minutes": minutes,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic delivery time dataset (CSV)")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=str(Path("data") / "delivery_train.csv"))
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_dataset(args.rows, args.seed)
    df.to_csv(out_path, index=False)
    print(f"Saved dataset to: {out_path}")


if __name__ == "__main__":
    main()

