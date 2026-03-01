import argparse
from ..domain.entities import UserHistory
from ..infrastructure.collaborative import CollaborativeMockModel
from ..application.recommendation_service import RecommendationService


def main():
    parser = argparse.ArgumentParser(description="Recommender System CLI")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--items", default="")

    args = parser.parse_args()

    items = args.items.split(",") if args.items else []

    history = UserHistory(
        user_id=args.user_id,
        last_items=items
    )

    model = CollaborativeMockModel()
    service = RecommendationService(model)

    recommendation = service.get_recommendations(history)

    for idx, item in enumerate(recommendation.suggested_items, 1):
        print(f"{idx}. {item}")


if __name__ == "__main__":
    main()