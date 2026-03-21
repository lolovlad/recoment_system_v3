"""
Экспорт скоринговой части TruncatedSVD в ONNX: scores = X @ W1 @ W2,
где ``components_`` sklearn имеет форму (k, n_items).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper


def export_recommendation_scores_onnx(components: np.ndarray, filepath: Path) -> None:
    """
    Сохраняет ONNX с входом ``X`` [batch, n_items] и выходом ``scores`` [batch, n_items].

    Parameters
    ----------
    components
        Матрица ``svd.components_`` формы (k, n_items).
    filepath
        Путь к ``*.onnx``.
    """
    components = np.asarray(components, dtype=np.float32)
    k, n_items = components.shape
    w1 = components.T  # (n_items, k)
    w2 = components  # (k, n_items)

    x_info = helper.make_tensor_value_info("X", TensorProto.FLOAT, [None, n_items])
    scores_info = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [None, n_items])

    init_w1 = numpy_helper.from_array(w1, name="W1")
    init_w2 = numpy_helper.from_array(w2, name="W2")

    node1 = helper.make_node("MatMul", ["X", "W1"], ["latent"], name="matmul_user_latent")
    node2 = helper.make_node("MatMul", ["latent", "W2"], ["scores"], name="matmul_item_scores")

    graph = helper.make_graph(
        [node1, node2],
        "recommendation_svd_scores",
        inputs=[x_info],
        outputs=[scores_info],
        initializer=[init_w1, init_w2],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 12)])
    onnx.checker.check_model(model)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, filepath)
