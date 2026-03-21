import argparse

from ..domain.entities import UserHistory
from ..application.service_factory import create_recommendation_service
from ..env import load_project_env


def main():
    load_project_env()
    parser = argparse.ArgumentParser(description="Recommender System CLI")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--items", default="")

    args = parser.parse_args()

    items = args.items.split(",") if args.items else []

    history = UserHistory(
        user_id=args.user_id,
        last_items=items
    )

    service = create_recommendation_service()

    recommendation = service.get_recommendations(history)

    for idx, item in enumerate(recommendation.suggested_items, 1):
        print(f"{idx}. {item}")


if __name__ == "__main__":
    main()
