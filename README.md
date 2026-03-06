# Recommender System (Lab 1)

Проект демонстрирует скелет ИИ-системы, реализованный по принципам Clean Architecture.

## Структура

- domain — сущности и интерфейсы
- application — бизнес-логика
- infrastructure — реализация модели (Mock)
- presentation — CLI-интерфейс

## Запуск

```bash
poetry install
poetry run python -m src.recommender_system.presentation.cli --user-id u1 --items itemA,itemB
```

Для запуска unit-тестов используется pytest.

```bash
poetry run pytest
```

Тесты проверяют бизнес-логику слоя Application и не зависят от инфраструктурных реализаций моделей.
