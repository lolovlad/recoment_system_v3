"""
Загрузка переменных окружения из файла `.env` в **корне репозитория**.

Используется API, Celery worker, задачи (`tasks.py`), скрипты обучения и т.д.
Не перезаписывает переменные, уже заданные в ОС (`override=False`).
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ENV_LOADED = False


def get_project_root() -> Path:
    """Корень проекта (каталог с `pyproject.toml`)."""
    return Path(__file__).resolve().parents[2]


def load_project_env(*, override: bool = False) -> None:
    """
    Подгружает `.env` из корня проекта.

    Parameters
    ----------
    override
        Если True — значения из `.env` перезапишут уже установленные переменные.
        По умолчанию False (как в типичном dotenv: приоритет у окружения ОС / Docker).
    """
    global _ENV_LOADED
    env_path = get_project_root() / ".env"
    load_dotenv(env_path, override=override)
    _ENV_LOADED = True


def is_env_loaded() -> bool:
    """Флаг, что load_project_env уже вызывался (для отладки)."""
    return _ENV_LOADED
