#!/usr/bin/env python3
"""
Автоматическая проверка ЛР4: API жив, POST рекомендаций, GET результата до SUCCESS.

Использование:
  poetry run python scripts/lab4_verify.py
  poetry run python scripts/lab4_verify.py http://127.0.0.1:8000 42
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request


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


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    user_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print(f"[ЛР4] Базовый URL: {base}")
    print("[ЛР4] Проверка OpenAPI...")
    code, _ = _request(f"{base}/openapi.json")
    if code != 200:
        print(f"ОШИБКА: API недоступен (код {code}). Запустите API/worker/redis.")
        return 1
    print("  OK: /openapi.json")

    print(f"[ЛР4] POST /recommendations/generate_for_user (user_id={user_id})...")
    code, post_body = _request(
        f"{base}/api/v1/recommendations/generate_for_user",
        method="POST",
        body={"user_id": user_id},
    )
    if code not in (200, 202):
        print(f"ОШИБКА: ожидался 202, получен {code}: {post_body}")
        return 1
    if not isinstance(post_body, dict) or "task_id" not in post_body:
        print(f"ОШИБКА: нет task_id: {post_body}")
        return 1
    task_id = post_body["task_id"]
    print(f"  task_id: {task_id}")

    deadline = time.monotonic() + 60.0
    last_status = None
    while time.monotonic() < deadline:
        code, get_body = _request(f"{base}/api/v1/recommendations/results/{task_id}")
        if code != 200 or not isinstance(get_body, dict):
            print(f"ОШИБКА GET: {code} {get_body}")
            return 1
        last_status = get_body.get("status")
        print(f"  status={last_status}")
        if last_status == "SUCCESS":
            result = get_body.get("result")
            print(f"  result (первые 10 item_id): {result[:10] if isinstance(result, list) else result}")
            print("[ЛР4] Проверка пройдена.")
            return 0
        if last_status == "FAILURE":
            print(f"  error: {get_body.get('error')}")
            return 1
        time.sleep(0.5)

    print(f"Таймаут: последний статус {last_status}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
