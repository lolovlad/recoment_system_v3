#!/usr/bin/env python3
"""
End-to-end проверка всей системы рекомендаций:
- API доступен
- POST создает Celery-задачу
- worker отдает SUCCESS c item_id
- (опционально) проверка сценария загрузки модели worker-ом через MinIO

Примеры:
  poetry run python scripts/lab4_e2e_check.py
  poetry run python scripts/lab4_e2e_check.py --base-url http://127.0.0.1:8000 --user-id 7
  poetry run python scripts/lab4_e2e_check.py --force-minio-download
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def _request(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict | list | None]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, None


def _delete_local_models_if_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    onnx_path = root / "models" / "recommendation.onnx"
    meta_path = root / "models" / "recommendation_meta.json"
    for p in (onnx_path, meta_path):
        if p.exists():
            p.unlink()
            print(f"[e2e] удален локальный артефакт: {p}")


def _local_models_exist() -> bool:
    root = Path(__file__).resolve().parents[1]
    onnx_path = root / "models" / "recommendation.onnx"
    meta_path = root / "models" / "recommendation_meta.json"
    return onnx_path.is_file() and meta_path.is_file()


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E проверка API + worker + модели рекомендаций")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--timeout-sec", type=float, default=90.0)
    parser.add_argument(
        "--force-minio-download",
        action="store_true",
        help="удалить локальные артефакты модели перед проверкой, чтобы worker скачал их заново",
    )
    args = parser.parse_args()

    if args.force_minio_download:
        _delete_local_models_if_exists()

    print(f"[e2e] base_url={args.base_url}")
    code, _ = _request(f"{args.base_url}/openapi.json")
    if code != 200:
        print(f"[e2e] ОШИБКА: API недоступен, код={code}")
        return 1
    print("[e2e] OK: API доступен")

    code, post_body = _request(
        f"{args.base_url}/api/v1/recommendations/generate_for_user",
        method="POST",
        body={"user_id": args.user_id},
    )
    if code not in (200, 202):
        print(f"[e2e] ОШИБКА POST: code={code}, body={post_body}")
        return 1
    if not isinstance(post_body, dict) or "task_id" not in post_body:
        print(f"[e2e] ОШИБКА: нет task_id, body={post_body}")
        return 1

    task_id = str(post_body["task_id"])
    print(f"[e2e] task_id={task_id}")

    deadline = time.monotonic() + args.timeout_sec
    while time.monotonic() < deadline:
        code, get_body = _request(f"{args.base_url}/api/v1/recommendations/results/{task_id}")
        if code != 200 or not isinstance(get_body, dict):
            print(f"[e2e] ОШИБКА GET: code={code}, body={get_body}")
            return 1

        status = get_body.get("status")
        print(f"[e2e] status={status}")
        if status == "SUCCESS":
            result = get_body.get("result")
            if not isinstance(result, list) or not all(isinstance(x, int) for x in result):
                print(f"[e2e] ОШИБКА: неверный формат result: {result}")
                return 1
            print(f"[e2e] OK: SUCCESS, result_len={len(result)}, sample={result[:10]}")
            if args.force_minio_download:
                if _local_models_exist():
                    print("[e2e] OK: локальные артефакты снова появились (worker загрузил модель).")
                else:
                    print(
                        "[e2e] ПРЕДУПРЕЖДЕНИЕ: артефакты не появились локально. "
                        "Вероятно, worker отработал на mock (проверьте объекты в MinIO)."
                    )
            return 0
        if status == "FAILURE":
            print(f"[e2e] ОШИБКА task FAILURE: {get_body.get('error')}")
            return 1

        time.sleep(1.0)

    print("[e2e] ОШИБКА: таймаут ожидания SUCCESS")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

