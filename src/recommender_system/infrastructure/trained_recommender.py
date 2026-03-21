"""
Обучаемая модель рекомендаций: ONNX (скоринг) + JSON метаданные (каталог item_id).

Обучение: ``scripts/train_recommendation_model.py`` → ``recommendation.onnx`` + ``recommendation_meta.json``.

Worker при старте синхронизирует файлы из MinIO (``ModelSyncService``), если локально нет
(см. ``create_recommendation_service``). В Docker каталог ``models`` монтируется как volume.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort

from ..domain.entities import Recommendation, UserHistory
from ..domain.interfaces import Recommender

logger = logging.getLogger(__name__)


class TrainedRecommenderModel(Recommender):
    """Инференс через ONNX Runtime: один forward на бинарный вектор истории пользователя."""

    def __init__(self, onnx_path: Path, meta_path: Path, top_n: int = 5) -> None:
        self._onnx_path = Path(onnx_path)
        self._meta_path = Path(meta_path)
        self._top_n = top_n

        meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
        self._item_ids_ordered: list[str] = meta["item_ids_ordered"]
        self._engine_version: str = meta.get("engine_version", "trained-svd-v1")

        self._session = ort.InferenceSession(
            str(self._onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

        self._n_items = len(self._item_ids_ordered)
        self._item_to_col: dict[str, int] = {it: j for j, it in enumerate(self._item_ids_ordered)}

    def get_recommendations(self, history: UserHistory) -> Recommendation:
        last_items = [str(x) for x in history.last_items]
        n_items = self._n_items
        if n_items == 0:
            return Recommendation(suggested_items=[], engine_version=self._engine_version)

        row = np.zeros((1, n_items), dtype=np.float32)
        for it in last_items:
            col = self._item_to_col.get(it)
            if col is not None:
                row[0, col] = 1.0

        if float(row.sum()) == 0.0:
            # Cold start / нет пересечения с каталогом: всё равно считаем скоринги (нулевой профиль
            # даёт одинаковые скоринги — ниже tie-break по индексу товара).
            logger.warning(
                "Cold start or no catalog overlap for user %s — using zero profile",
                history.user_id,
            )

        out = self._session.run(
            [self._output_name],
            {self._input_name: row},
        )[0]
        scores = np.asarray(out).ravel()

        exclude = set(last_items)
        ranked: list[tuple[float, int]] = []
        for j in range(n_items):
            item_str = self._item_ids_ordered[j]
            if item_str in exclude:
                continue
            ranked.append((float(scores[j]), j))

        # score по убыванию; при равных скорингах — стабильный порядок по индексу (cold start)
        ranked.sort(key=lambda t: (-t[0], t[1]))
        top = [self._item_ids_ordered[j] for _, j in ranked[: self._top_n]]

        return Recommendation(suggested_items=top, engine_version=self._engine_version)
