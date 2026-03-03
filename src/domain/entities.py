from pydantic import BaseModel


class UserHistory(BaseModel):
    user_id: str
    last_items: list[str]


class Recommendation(BaseModel):
    suggested_items: list[str]
    engine_version: str

