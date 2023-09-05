from enum import Enum

from typing_extensions import TypedDict
from typing import Optional


class LemmyVote(TypedDict):
    name: str
    score: int
    actor_id: str


class VotesResponse(TypedDict):
    votes: list[LemmyVote]
    total_count: int
    next_offset: Optional[int]


class VoteFilter(str, Enum):
    ALL = "All"
    UPVOTES = "Upvotes"
    DOWNVOTES = "Downvotes"
