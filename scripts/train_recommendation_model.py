"""
Обучение модели рекомендаций по ``user_history.csv`` (ЛР1-ЛР4).

Обучает TruncatedSVD, экспортирует скоринг в ONNX + JSON метаданные
и опционально загружает оба файла в MinIO (бакет ``models``).
"""

from __future__ import annotations



import argparse

import json

import os

from pathlib import Path



import numpy as np

import pandas as pd

from scipy import sparse

from sklearn.decomposition import TruncatedSVD



import boto3

try:
    from recommender_system.env import load_project_env
    from recommender_system.infrastructure.recommendation_artifacts import (
        local_meta_path,
        local_onnx_path,
        remote_meta_key,
        remote_onnx_key,
    )
    from recommender_system.infrastructure.recommendation_onnx_export import export_recommendation_scores_onnx
except ModuleNotFoundError:
    from src.recommender_system.env import load_project_env
    from src.recommender_system.infrastructure.recommendation_artifacts import (
        local_meta_path,
        local_onnx_path,
        remote_meta_key,
        remote_onnx_key,
    )
    from src.recommender_system.infrastructure.recommendation_onnx_export import export_recommendation_scores_onnx





def upload_recommendation_to_minio(onnx_path: Path, meta_path: Path) -> bool:

    """Загружает ``recommendation.onnx`` и ``recommendation_meta.json`` в MinIO."""

    load_project_env()



    endpoint = os.getenv("MINIO_ENDPOINT")

    access_key = os.getenv("MINIO_ACCESS_KEY")

    secret_key = os.getenv("MINIO_SECRET_KEY")

    bucket = os.getenv("MINIO_MODEL_BUCKET", "models")

    remote_onnx = remote_onnx_key()

    remote_meta = remote_meta_key()



    if not endpoint or not access_key or not secret_key:

        print("MinIO env is not set, skipping upload of recommendation artifacts.")

        return False



    client = boto3.client(

        "s3",

        endpoint_url=endpoint,

        aws_access_key_id=access_key,

        aws_secret_access_key=secret_key,

    )

    client.upload_file(str(onnx_path), bucket, remote_onnx)

    client.upload_file(str(meta_path), bucket, remote_meta)

    print(f"Uploaded recommendation ONNX: s3://{bucket}/{remote_onnx}")

    print(f"Uploaded recommendation meta: s3://{bucket}/{remote_meta}")

    return True





def train_and_save(

    data_path: Path,

    out_onnx: Path,

    out_meta: Path,

    n_components: int,

    random_state: int,
) -> dict[str, float]:

    df = pd.read_csv(data_path)

    if "user_id" not in df.columns or "item_id" not in df.columns:

        raise ValueError("CSV must contain user_id and item_id columns")



    df = df.dropna(subset=["user_id", "item_id"])

    df["user_id"] = df["user_id"].astype(str)

    df["item_id"] = df["item_id"].astype(str)



    unique_users = sorted(df["user_id"].unique())

    unique_items = sorted(df["item_id"].unique())

    n_users = len(unique_users)

    n_items = len(unique_items)



    if n_users < 2 or n_items < 2:

        raise ValueError("Need at least 2 users and 2 items to train SVD")



    user_id_to_row = {u: i for i, u in enumerate(unique_users)}

    item_to_col = {it: j for j, it in enumerate(unique_items)}

    item_ids_ordered = unique_items



    rows: list[int] = []

    cols: list[int] = []

    seen: set[tuple[str, str]] = set()

    for _, r in df.iterrows():

        u, it = str(r["user_id"]), str(r["item_id"])

        key = (u, it)

        if key in seen:

            continue

        seen.add(key)

        rows.append(user_id_to_row[u])

        cols.append(item_to_col[it])



    data = np.ones(len(rows), dtype=np.float32)

    x = sparse.csr_matrix((data, (rows, cols)), shape=(n_users, n_items))



    k = min(

        n_components,

        n_users - 1,

        n_items - 1,

        max(1, min(n_users, n_items) - 1),

    )

    k = max(1, k)



    svd = TruncatedSVD(n_components=k, random_state=random_state)

    svd.fit(x)



    out_onnx.parent.mkdir(parents=True, exist_ok=True)

    export_recommendation_scores_onnx(svd.components_, out_onnx)



    meta = {

        "item_ids_ordered": item_ids_ordered,

        "engine_version": f"trained-svd-onnx-k{k}-rs{random_state}",

        "schema_version": 2,

    }

    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")



    print(f"Saved ONNX: {out_onnx}")

    print(f"Saved meta: {out_meta}")

    print(f"  users={n_users}, items={n_items}, n_components={k}")

    return {
        "users_count": float(n_users),
        "items_count": float(n_items),
        "n_components_actual": float(k),
        "explained_variance_ratio_sum": float(np.sum(svd.explained_variance_ratio_)),
    }





def main() -> None:

    load_project_env()

    parser = argparse.ArgumentParser(

        description="Train TruncatedSVD recommender → ONNX + JSON (Lab 1–2 data)",

    )

    parser.add_argument(

        "--data",

        type=str,

        default=str(Path("data") / "user_history.csv"),

        help="Path to user_history CSV",

    )

    parser.add_argument(

        "--out",

        type=str,

        default=str(local_onnx_path()),

        help="Output ONNX path (по умолчанию models/recommendation.onnx)",

    )

    parser.add_argument(

        "--out-meta",

        type=str,

        default=None,

        help="Output JSON meta (по умолчанию models/recommendation_meta.json)",

    )

    parser.add_argument("--components", type=int, default=32, help="SVD components (capped by data size)")

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--mlflow-experiment",
        type=str,
        default=os.getenv("MLFLOW_EXPERIMENT_NAME", "lab5_variant7_recommender"),
        help="Имя MLflow experiment",
    )
    parser.add_argument(
        "--require-mlflow",
        action="store_true",
        help="Падать с ошибкой, если MLFLOW_TRACKING_URI задан, но mlflow недоступен.",
    )

    args = parser.parse_args()



    data_path = Path(args.data)

    if not data_path.exists():

        raise FileNotFoundError(

            f"Dataset not found: {data_path}. Generate with scripts/generate_user_history.py or dvc pull.",

        )



    out_onnx = Path(args.out)

    out_meta = Path(args.out_meta) if args.out_meta else local_meta_path()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    mlflow_mod = None
    if tracking_uri:
        try:
            import mlflow as _mlflow  # type: ignore

            mlflow_mod = _mlflow
            mlflow_mod.set_tracking_uri(tracking_uri)
            mlflow_mod.set_experiment(args.mlflow_experiment)
        except Exception as e:
            if args.require_mlflow:
                raise RuntimeError(f"MLFLOW_TRACKING_URI задан, но mlflow недоступен: {e}") from e
            print(f"WARNING: MLFLOW_TRACKING_URI задан, но mlflow недоступен: {e}. Продолжаю без логирования.")
            mlflow_mod = None

    with (mlflow_mod.start_run(run_name="train_recommendation_model") if mlflow_mod else _nullcontext()):
        if mlflow_mod:
            mlflow_mod.log_params(
                {
                    "components_requested": int(args.components),
                    "seed": int(args.seed),
                    "data_path": str(data_path),
                }
            )

        # обучаем и сохраняем артефакты в models/
        metrics = train_and_save(
            data_path=data_path,
            out_onnx=out_onnx,
            out_meta=out_meta,
            n_components=args.components,
            random_state=args.seed,
        )

        # логируем артефакты в MLflow (MinIO через mlflow server)
        if mlflow_mod:
            mlflow_mod.log_metrics(metrics)
            mlflow_mod.log_artifact(str(out_onnx), artifact_path="recommendation_artifacts")
            mlflow_mod.log_artifact(str(out_meta), artifact_path="recommendation_artifacts")

        # синк артефактов рекомендаций в MinIO bucket models (для worker)
        upload_recommendation_to_minio(out_onnx, out_meta)


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False





if __name__ == "__main__":

    main()


