from __future__ import annotations

import logging
import os
from pathlib import Path

from ..env import load_project_env
from ..infrastructure.recommendation_artifacts import local_meta_path, local_onnx_path

logger = logging.getLogger(__name__)


def ensure_recommendation_artifacts_local() -> tuple[Path, Path]:
    """
    Если ``recommendation.onnx`` и ``recommendation_meta.json`` уже есть локально (volume ``./models``),
    возвращает пути без сети.

    Иначе при настроенном MinIO пытается скачать объекты из бакета ``models``.
    При ошибке (объекта нет, сеть) **не бросает исключение** — worker сможет работать на mock.
    """
    load_project_env()
    onnx_path = local_onnx_path()
    meta_path = local_meta_path()

    # 1) Основной путь: MLflow Model Registry (Production) -> скачиваем в ./models
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    model_name = os.getenv("MLFLOW_MODEL_NAME", "recsys_model")
    model_stage = os.getenv("MLFLOW_MODEL_STAGE", "Production")
    skip_download_if_exists = os.getenv("MLFLOW_SKIP_DOWNLOAD_IF_EXISTS", "false").lower() in ("1", "true", "yes")

    if skip_download_if_exists and onnx_path.is_file() and meta_path.is_file():
        return onnx_path, meta_path

    if tracking_uri:
        try:
            import mlflow
            from mlflow.artifacts import download_artifacts
            from mlflow.tracking import MlflowClient

            mlflow.set_tracking_uri(tracking_uri)
            client = MlflowClient()

            versions = client.get_latest_versions(model_name, stages=[model_stage], max_results=1)
            if not versions:
                logger.warning("MLflow: no %s stage model versions for %s", model_stage, model_name)
            else:
                mv = versions[0]
                # source: runs:/<run_id>/sklearn_model
                source = str(mv.source)
                run_id = source.split("/")[1] if source.startswith("runs:/") else None
                if not run_id:
                    raise RuntimeError(f"Cannot parse run_id from model source: {source}")

                dst_dir = str(onnx_path.parent)
                onnx_artifact_uri = f"runs:/{run_id}/recommendation_artifacts/recommendation.onnx"
                meta_artifact_uri = f"runs:/{run_id}/recommendation_artifacts/recommendation_meta.json"

                onnx_tmp = download_artifacts(onnx_artifact_uri, dst_path=dst_dir)
                meta_tmp = download_artifacts(meta_artifact_uri, dst_path=dst_dir)

                # download_artifacts вернёт путь до файла, но может разложить по подпапкам.
                Path(onnx_tmp).replace(onnx_path)
                Path(meta_tmp).replace(meta_path)
                return onnx_path, meta_path
        except Exception as e:
            logger.warning("MLflow artifacts sync failed, fallback to local/MinIO: %s", e)

    # 2) fallback: если уже есть локально — работаем на них.
    if onnx_path.is_file() and meta_path.is_file():
        return onnx_path, meta_path

    return onnx_path, meta_path
