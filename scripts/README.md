# Скрипты лабораторной работы №2

Скрипты выстроены в порядке использования: сначала генерация данных, затем настройка и работа с версиями.

---

## 1. Генерация данных

### generate_user_history.py / generate_user_history.bat

Создаёт файл `data/user_history.csv` с колонками `user_id` и `item_id` (история взаимодействий пользователей с товарами). Выполнять **до** добавления данных в DVC.

**Параметры:**
- `--rows` — количество строк (по умолчанию: 100)
- `--seed` — seed для воспроизводимости
- `--output` — путь к файлу (по умолчанию: `data/user_history.csv`)

**Примеры:**
```bash
# Интерактивный режим (bat)
scripts\generate_user_history.bat

# С параметрами
scripts\generate_user_history.bat 100 42
scripts\generate_user_history.bat 50

# Через Python
poetry run python scripts/generate_user_history.py --rows 100 --seed 42
poetry run python scripts/generate_user_history.py --rows 50
poetry run python scripts/generate_user_history.py
```

**Формат данных:**
```csv
user_id,item_id
1,5
1,12
2,3
...
```

Папка `data` создаётся автоматически, если её нет.

---

## 2. Первичная настройка

### setup.bat

Полная автоматическая настройка проекта (запускать после генерации данных при необходимости):

- Установка зависимостей (`poetry install`)
- Запуск MinIO (`docker compose up -d`)
- Инициализация DVC и настройка remote
- Генерация `user_history.csv`, если файла ещё нет
- Добавление данных в DVC (версия v1.0 — октябрь) и отправка в MinIO

```bash
scripts\setup.bat
```

---

## 3. Подготовка и отправка данных в DVC/MinIO

### prepare_data.bat

Добавляет текущий `data/user_history.csv` в DVC и отправляет в MinIO. Использовать после изменений в данных.

```bash
scripts\prepare_data.bat
```

---

## 4. Проверка работы системы

### demo.bat

Демонстрация работы: проверка MinIO, конфигурации DVC и скрипта инициализации данных.

```bash
scripts\demo.bat
```

---

## 5. Версия v2.0 (добавление данных за ноябрь)

### add_november_data.bat

Добавляет данные за ноябрь в `user_history.csv`, обновляет версию в DVC (v2.0) и отправляет в MinIO.

```bash
scripts\add_november_data.bat
```

---

## 6. Переключение между версиями данных

### switch_to_october.bat

Переключение на версию v1.0 (только октябрь).

```bash
scripts\switch_to_october.bat
```

### switch_to_november.bat

Переключение на версию v2.0 (октябрь + ноябрь).

```bash
scripts\switch_to_november.bat
```

---

## 7. Очистка и сброс

### clean_and_reset.bat

Остановка MinIO, удаление локальных данных и подготовка к перезапуску с нуля.

```bash
scripts\clean_and_reset.bat
```

---

## Последовательность проверки (кратко)

1. **Генерация данных:** `scripts\generate_user_history.bat` (или с параметрами).
2. **Настройка:** `scripts\setup.bat`.
3. **Проверка:** `scripts\demo.bat`.
4. **Версия v2.0:** `scripts\add_november_data.bat`.
5. **Переключение версий:** `scripts\switch_to_october.bat` / `scripts\switch_to_november.bat`.

---

## Ручная настройка (без .bat)

После настройки DVC remote:

1. Сгенерировать данные:
   ```bash
   poetry run python scripts/generate_user_history.py --rows 100 --seed 42
   ```
2. Добавить в DVC и отправить в MinIO:
   ```bash
   dvc add data/user_history.csv
   dvc push
   ```

---

## Версии данных

- **v1.0 (октябрь):** только данные за октябрь  
- **v2.0 (октябрь + ноябрь):** данные за октябрь и ноябрь
