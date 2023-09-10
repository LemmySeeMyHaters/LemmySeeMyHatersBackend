from enum import Enum
from typing import Optional, NamedTuple

from pydantic import BaseModel


class LemmyVote(BaseModel):
    name: str
    score: int
    actor_id: str
    created_utc: float


class VotesResponse(BaseModel):
    votes: list[LemmyVote]
    total_count: int
    next_offset: Optional[int]
    total_score: int
    upvotes: int
    downvotes: int


class VoteFilter(str, Enum):
    ALL = "All"
    UPVOTES = "Upvotes"
    DOWNVOTES = "Downvotes"


class LemmyObjectAggregate(NamedTuple):
    total_score: int
    upvotes: int
    downvotes: int
