from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD


def _build_interaction_matrix(df: pd.DataFrame) -> tuple[sparse.csr_matrix, list[str]]:
    df = df.dropna(subset=["user_id", "item_id"]).copy()
    df["user_id"] = df["user_id"].astype(str)
    df["item_id"] = df["item_id"].astype(str)

    # Важно: TrainedRecommenderModel использует item_ids_ordered из meta и сортировку.
    item_ids_ordered = sorted(df["item_id"].unique())
    user_ids_ordered = sorted(df["user_id"].unique())

    user_id_to_row = {u: i for i, u in enumerate(user_ids_ordered)}
    item_id_to_col = {it: j for j, it in enumerate(item_ids_ordered)}

    rows: list[int] = []
    cols: list[int] = []
    seen: set[tuple[str, str]] = set()
    for _, r in df.iterrows():
        u = str(r["user_id"])
        it = str(r["item_id"])
        key = (u, it)
        if key in seen:
            continue
        seen.add(key)
        rows.append(user_id_to_row[u])
        cols.append(item_id_to_col[it])

    data = np.ones(len(rows), dtype=np.float32)
    x = sparse.csr_matrix((data, (rows, cols)), shape=(len(user_ids_ordered), len(item_ids_ordered)))
    return x, item_ids_ordered


def _ndcg_at_k_binary(
    *,
    components: np.ndarray,
    item_ids_ordered: list[str],
    user_items_seq: list[str],
    history_items: list[str],
    positive_item: str,
    k: int,
) -> float:
    """
    NDCG@k с бинарной релевантностью (relevance=1).

    Для бинарной релевантности при idcg=1:
    NDCG = 1/log2(rank+1) если positive попал в топ-k, иначе 0.
    """
    n_items = len(item_ids_ordered)
    if n_items == 0:
        return 0.0

    item_to_col = {it: j for j, it in enumerate(item_ids_ordered)}
    w1 = components.T  # (n_items, factors)
    w2 = components  # (factors, n_items)

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

    # Совпадает с TrainedRecommenderModel: score по убыванию, при равенстве — по индексу.
    ranked.sort(key=lambda t: (-t[0], t[1]))
    top = ranked[:k]

    positive_col = item_to_col.get(positive_item)
    if positive_col is None:
        return 0.0

    # Rank считается среди "ranked" (то есть среди не-исключенных).
    for idx, (_, col) in enumerate(top):
        if col == positive_col:
            rank = idx + 1  # 1-based
            return 1.0 / math.log2(rank + 1.0)

    return 0.0


def compute_ndcg_at_10(
    *,
    data_path: Path,
    components_requested: int,
    seed: int,
    k: int = 10,
) -> float:
    df = pd.read_csv(data_path)
    x, item_ids_ordered = _build_interaction_matrix(df)
    n_users, n_items = x.shape
    if n_users < 2 or n_items < 2:
        return 0.0

    k_factors = min(
        components_requested,
        n_users - 1,
        n_items - 1,
        max(1, min(n_users, n_items) - 1),
    )
    k_factors = max(1, k_factors)

    svd = TruncatedSVD(n_components=k_factors, random_state=seed)
    svd.fit(x)

    # Берём user "с последовательностью" из CSV (порядок строк).
    ndcgs: list[float] = []
    for uid in sorted(df["user_id"].dropna().astype(str).unique()):
        seq = df[df["user_id"].astype(str) == uid]["item_id"].dropna().astype(str).tolist()
        if len(seq) < 2:
            continue
        positive_item = seq[-1]
        history_items = [it for it in seq[:-1] if it != positive_item][-50:]

        ndcg = _ndcg_at_k_binary(
            components=svd.components_.astype(np.float32),
            item_ids_ordered=item_ids_ordered,
            user_items_seq=seq,
            history_items=history_items,
            positive_item=positive_item,
            k=k,
        )
        ndcgs.append(ndcg)

    if not ndcgs:
        return 0.0

    return float(np.mean(ndcgs))


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality gate: NDCG@10")
    parser.add_argument("--data", type=str, default=str(Path("data") / "user_history.csv"))
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--components", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    ndcg = compute_ndcg_at_10(
        data_path=data_path,
        components_requested=args.components,
        seed=args.seed,
        k=args.k,
    )

    print(f"[quality_gate] NDCG@{args.k}={ndcg:.4f} threshold={args.threshold}")
    if ndcg <= args.threshold:
        print("[quality_gate] FAILED")
        return 1
    print("[quality_gate] PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

