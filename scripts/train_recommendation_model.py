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


def _build_interaction_matrix(df: pd.DataFrame) -> tuple[sparse.csr_matrix, list[str]]:
    """
    Создаёт матрицу взаимодействий для TruncatedSVD.

    Совпадает по логике с train_and_save:
    - unique по (user_id, item_id)
    - user/item множества отсортированы
    """
    df = df.dropna(subset=["user_id", "item_id"]).copy()
    df["user_id"] = df["user_id"].astype(str)
    df["item_id"] = df["item_id"].astype(str)

    unique_users = sorted(df["user_id"].unique())
    unique_items = sorted(df["item_id"].unique())

    user_id_to_row = {u: i for i, u in enumerate(unique_users)}
    item_to_col = {it: j for j, it in enumerate(unique_items)}

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
    x = sparse.csr_matrix((data, (rows, cols)), shape=(len(unique_users), len(unique_items)))
    return x, unique_items





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


def _compute_ndcg_at_k(
    *,
    df: pd.DataFrame,
    components: np.ndarray,
    item_ids_ordered: list[str],
    user_id_to_seq: dict[str, list[str]],
    k: int = 10,
    history_limit: int = 50,
) -> float:
    """
    Quality metric NDCG@k с бинарной релевантностью.

    Поскольку производство использует TrainedRecommenderModel (score и tie-break по индексу),
    считаем скоринг по тем же формулам MatMul (см. export_recommendation_scores_onnx).
    """
    import math

    n_items = len(item_ids_ordered)
    if n_items == 0:
        return 0.0

    item_to_col = {it: j for j, it in enumerate(item_ids_ordered)}
    w1 = components.T  # (n_items, factors)
    w2 = components  # (factors, n_items)

    # Для бинарной релевантности idcg=1/log2(2)=1 => ndcg = dcg = 1/log2(rank+1) если попал в топ-k.
    ndcgs: list[float] = []
    for uid in sorted(user_id_to_seq.keys()):
        seq = user_id_to_seq[uid]
        if len(seq) < 2:
            continue
        positive_item = seq[-1]
        history_items = [it for it in seq[:-1] if it != positive_item][-history_limit:]
        x = np.zeros((1, n_items), dtype=np.float32)
        for it in history_items:
            col = item_to_col.get(it)
            if col is not None:
                x[0, col] = 1.0

        latent = x @ w1  # (1, factors)
        scores = latent @ w2  # (1, n_items)
        scores = np.asarray(scores).ravel()

        exclude = set(history_items)
        ranked: list[tuple[float, int]] = []
        for j in range(n_items):
            item_str = item_ids_ordered[j]
            if item_str in exclude:
                continue
            ranked.append((float(scores[j]), j))
        ranked.sort(key=lambda t: (-t[0], t[1]))
        top = ranked[:k]

        positive_col = item_to_col.get(positive_item)
        if positive_col is None:
            continue

        dcg = 0.0
        for idx, (_, col) in enumerate(top):
            if col == positive_col:
                rank = idx + 1
                dcg = 1.0 / math.log2(rank + 1.0)
                break
        ndcgs.append(dcg)

    if not ndcgs:
        return 0.0
    return float(np.mean(ndcgs))





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
    parser.add_argument("--ndcg-threshold", type=float, default=0.5)
    parser.add_argument("--ndcg-k", type=int, default=10)
    parser.add_argument("--register-model-name", type=str, default="recsys_model")

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

    # Загружаем df повторно, чтобы посчитать NDCG по последовательности из CSV.
    df = pd.read_csv(data_path)
    df = df.dropna(subset=["user_id", "item_id"]).copy()
    df["user_id"] = df["user_id"].astype(str)
    df["item_id"] = df["item_id"].astype(str)

    user_id_to_seq: dict[str, list[str]] = {}
    for uid, grp in df.groupby("user_id"):
        # order by appearance in CSV
        seq = grp["item_id"].astype(str).tolist()
        user_id_to_seq[str(uid)] = seq

    # item_ids_ordered будет получен внутри блока расчёта NDCG из обучаемой матрицы.

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
            # Восстановим SVD components для расчёта NDCG.
            x, item_ids_ordered_for_svd = _build_interaction_matrix(df)
            k_factors = int(metrics["n_components_actual"])
            svd_for_ndcg = TruncatedSVD(n_components=k_factors, random_state=args.seed)
            svd_for_ndcg.fit(x)
            ndcg = _compute_ndcg_at_k(
                df=df,
                components=svd_for_ndcg.components_.astype(np.float32),
                item_ids_ordered=item_ids_ordered_for_svd,
                user_id_to_seq=user_id_to_seq,
                k=args.ndcg_k,
            )

            mlflow_mod.log_params(
                {
                    "factors_actual": int(k_factors),
                    "ndcg_k": int(args.ndcg_k),
                }
            )
            mlflow_mod.log_metric(f"ndcg@{args.ndcg_k}", float(ndcg))
            mlflow_mod.log_metrics(metrics)
            mlflow_mod.log_artifact(str(out_onnx), artifact_path="recommendation_artifacts")
            mlflow_mod.log_artifact(str(out_meta), artifact_path="recommendation_artifacts")

            # Логируем sklearn-модель для регистрации и получения run_id при download из worker.
            try:
                mlflow_mod.sklearn.log_model(svd_for_ndcg, artifact_path="sklearn_model")
            except Exception as e:
                raise RuntimeError(f"Failed to log sklearn model to MLflow: {e}") from e

            # Register model under required name; promote to Production only if quality gate passed.
            from mlflow.tracking import MlflowClient

            run_id = mlflow_mod.active_run().info.run_id
            model_uri = f"runs:/{run_id}/sklearn_model"
            registered = mlflow_mod.register_model(model_uri, args.register_model_name)
            version = registered.version

            gate_passed = float(ndcg) > args.ndcg_threshold
            mlflow_mod.set_tag("quality_gate_passed", "true" if gate_passed else "false")

            if gate_passed:
                client = MlflowClient()
                client.transition_model_version_stage(
                    name=args.register_model_name,
                    version=str(version),
                    stage="Production",
                    archive_existing_versions=True,
                )
            else:
                raise RuntimeError(
                    f"Quality gate failed: ndcg@{args.ndcg_k}={ndcg:.4f} <= {args.ndcg_threshold}"
                )

        # синк артефактов рекомендаций в MinIO bucket models (fallback для worker)
        upload_recommendation_to_minio(out_onnx, out_meta)


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False





if __name__ == "__main__":

    main()


