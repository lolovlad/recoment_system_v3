from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from recommender_system.env import load_project_env
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

import boto3


FEATURES = ["distance", "hour", "day_of_week", "items_count"]
TARGET = "delivery_minutes"


def upload_model_to_minio(local_model_path: Path) -> bool:
    """
    Загружает ONNX модель в MinIO (bucket models) при наличии env переменных.

    Required env:
      MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    Optional env:
      MINIO_MODEL_BUCKET (default: models)
      MODEL_REMOTE_PATH (default: delivery_estimator.onnx)
    """
    load_project_env()

    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    bucket = os.getenv("MINIO_MODEL_BUCKET", "models")
    remote_path = os.getenv("MODEL_REMOTE_PATH", "delivery_estimator.onnx")

    if not endpoint or not access_key or not secret_key:
        print("MinIO env is not set, skipping upload to MinIO.")
        return False

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    client.upload_file(str(local_model_path), bucket, remote_path)
    print(f"Uploaded model to MinIO: s3://{bucket}/{remote_path}")
    return True


def main() -> None:
    load_project_env()

    parser = argparse.ArgumentParser(description="Train delivery time model and export to ONNX")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-model", type=str, default=str(Path("models") / "delivery_estimator.onnx"))
    parser.add_argument("--data", type=str, default=str(Path("data") / "delivery_train.csv"))
    args = parser.parse_args()

    out_model = Path(args.out_model)
    out_model.parent.mkdir(parents=True, exist_ok=True)
    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {data_path}. "
            f"Generate it first: scripts\\generate_delivery_data.bat "
            f"(or poetry run python scripts/generate_delivery_data.py)."
        )

    df = pd.read_csv(data_path)

    X = df[FEATURES].to_numpy(dtype=np.float32)
    y = df[TARGET].to_numpy(dtype=np.float32)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=args.seed)

    model = GradientBoostingRegressor(random_state=args.seed)
    model.fit(X_train, y_train)

    pred = model.predict(X_val).astype(np.float32)
    mae = float(mean_absolute_error(y_val, pred))
    print(f"Validation MAE: {mae:.3f} minutes")

    initial_type = [("float_input", FloatTensorType([None, 4]))]
    onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)

    out_model.write_bytes(onnx_model.SerializeToString())
    print(f"Saved ONNX model to: {out_model}")
    print(f"Used training data: {data_path}")

    # Optional: automatically upload ONNX to MinIO bucket `models`
    upload_model_to_minio(out_model)


if __name__ == "__main__":
    main()

