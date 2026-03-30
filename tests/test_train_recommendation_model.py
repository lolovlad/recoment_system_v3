"""Скрипт обучения рекомендаций: smoke-тест на временном CSV → ONNX + JSON."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_train_recommendation_saves_onnx_and_meta(tmp_path: Path) -> None:
    csv_path = tmp_path / "hist.csv"
    pd.DataFrame(
        {
            "user_id": [1, 1, 2, 2, 3, 3],
            "item_id": [10, 11, 10, 12, 11, 13],
        },
    ).to_csv(csv_path, index=False)

    out_onnx = tmp_path / "rec.onnx"
    out_meta = tmp_path / "rec_meta.json"

    from scripts.train_recommendation_model import train_and_save

    train_and_save(csv_path, out_onnx, out_meta, n_components=2, random_state=0)

    assert out_onnx.is_file()
    assert out_meta.is_file()
    try:
        from recommender_system.infrastructure.trained_recommender import TrainedRecommenderModel
        from recommender_system.domain.entities import UserHistory
    except ModuleNotFoundError:
        from src.recommender_system.infrastructure.trained_recommender import TrainedRecommenderModel
        from src.recommender_system.domain.entities import UserHistory

    m = TrainedRecommenderModel(out_onnx, out_meta, top_n=5)

    rec = m.get_recommendations(UserHistory(user_id="1", last_items=["10"]))
    assert isinstance(rec.suggested_items, list)
    assert "10" not in rec.suggested_items

    # cold start: пустая история — не пустой топ (tie-break по каталогу)
    rec_cold = m.get_recommendations(UserHistory(user_id="99", last_items=[]))
    assert len(rec_cold.suggested_items) > 0
