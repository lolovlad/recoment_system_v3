from __future__ import annotations

import logging
import os
from pathlib import Path

from ..env import load_project_env
from ..infrastructure.recommendation_artifacts import (
    MLFLOW_META_ARTIFACT_PATH,
    MLFLOW_ONNX_ARTIFACT_PATH,
    MLFLOW_ONNX_MODEL_FILENAME,
    META_FILENAME,
    ONNX_FILENAME,
    local_meta_path,
    local_onnx_path,
)

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

            # В разных версиях MLflow сигнатура get_latest_versions отличается.
            # Берём максимум 1 версию вручную.
            versions = client.get_latest_versions(model_name, stages=[model_stage])
            if not versions:
                logger.warning("MLflow: no %s stage model versions for %s", model_stage, model_name)
            else:
                mv = versions[0]
                # В MLflow ModelVersion обычно есть run_id.
                # mv.source иногда приходит как runs:/... либо как s3://.../artifacts/.../...,
                # поэтому парсинг source ненадёжен.
                run_id = getattr(mv, "run_id", None)
                if not run_id:
                    # fallback: старый формат mv.source: runs:/<run_id>/<artifact_path>
                    source = str(mv.source)
                    run_id = source.split("/")[1] if source.startswith("runs:/") else None
                    if not run_id:
                        raise RuntimeError(f"Cannot resolve run_id from model source: {source}")

                dst_dir = str(onnx_path.parent)
                meta_artifact_uri = f"runs:/{run_id}/{MLFLOW_META_ARTIFACT_PATH}/{META_FILENAME}"
                onnx_primary = f"runs:/{run_id}/{MLFLOW_ONNX_ARTIFACT_PATH}/{MLFLOW_ONNX_MODEL_FILENAME}"
                onnx_legacy = f"runs:/{run_id}/{MLFLOW_META_ARTIFACT_PATH}/{ONNX_FILENAME}"

                meta_tmp = download_artifacts(meta_artifact_uri, dst_path=dst_dir)
                try:
                    onnx_tmp = download_artifacts(onnx_primary, dst_path=dst_dir)
                except Exception:
                    onnx_tmp = download_artifacts(onnx_legacy, dst_path=dst_dir)

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
