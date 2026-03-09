import argparse
import random
import csv
from pathlib import Path


def generate_user_history(num_rows: int, seed: int = None, output_path: str = "data/user_history.csv"):
    if seed is not None:
        random.seed(seed)
        print(f"Используется seed: {seed}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    users = [str(i) for i in range(1, 21)]  # 1 до 20
    items = [str(i) for i in range(1, 51)]  # 1 до 50

    history = []
    for _ in range(num_rows):
        user_id = random.choice(users)
        item_id = random.choice(items)
        history.append({"user_id": user_id, "item_id": item_id})

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "item_id"])
        writer.writeheader()
        writer.writerows(history)

    print(f"Файл {output_path} успешно создан!")
    print(f"Сгенерировано строк: {num_rows}")
    print(f"Уникальных пользователей: {len(set(h['user_id'] for h in history))}")
    print(f"Уникальных товаров: {len(set(h['item_id'] for h in history))}")


def main():
    parser = argparse.ArgumentParser(
        description="Генерация файла user_history.csv с историей взаимодействий пользователей с товарами"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=100,
        help="Количество строк для генерации (по умолчанию: 100)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed для генератора случайных чисел (для воспроизводимости). Если не указан, используется случайный seed"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/user_history.csv",
        help="Путь к выходному файлу (по умолчанию: data/user_history.csv)"
    )

    args = parser.parse_args()

    if args.rows < 1:
        print("ОШИБКА: Количество строк должно быть больше 0")
        return 1

    try:
        generate_user_history(
            num_rows=args.rows,
            seed=args.seed,
            output_path=args.output
        )
        return 0
    except Exception as e:
        print(f"ОШИБКА: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
