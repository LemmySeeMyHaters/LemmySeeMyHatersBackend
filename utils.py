from __future__ import annotations

from typing import TypeVar, Literal, Optional

from async_lru import alru_cache
from asyncpg import Connection, Record
from fastapi import HTTPException
from typing_extensions import LiteralString

from data_models import VoteFilter, LemmyVote

T = TypeVar("T")


def paginate_data(all_votes: list[LemmyVote], offset: int, limit: int) -> tuple[list[LemmyVote], Optional[int]]:
    """Paginates a list of items based on offset and limit.

    :param all_votes: The list of items to paginate.
    :param offset: The offset from which to start paginating (0-based indexing).
    :param limit: The maximum number of items to return on each page.

    :returns: A tuple containing the paginated list of items and the next offset (or None if there are no more items).
    """
    if offset < 0 or offset >= len(all_votes):
        return [], None

    paginated_data = all_votes[offset : offset + limit]
    next_offset = offset + limit if offset + limit < len(all_votes) else None

    return paginated_data, next_offset


@alru_cache(ttl=180, maxsize=256)
async def get_local_id_from_ap_id(url: str, object_type: Literal["Post", "Comment"], pg_conn: Connection) -> int:
    if object_type == "Post":
        rslt = await pg_conn.fetchrow("SELECT id FROM public.post WHERE ap_id = $1", url)
    else:
        rslt = await pg_conn.fetchrow("SELECT id FROM public.comment WHERE ap_id = $1", url)

    local_id: int = rslt.get("id")
    if local_id is None:
        raise HTTPException(status_code=404, detail="Could not fetch the object from the URL.")
    else:
        return local_id


@alru_cache(ttl=60, maxsize=256)
async def get_scores_from_pg(query: LiteralString, object_id_local: int, pg_conn: Connection) -> list[Record]:
    rec: list[Record] = await pg_conn.fetch(query, object_id_local)
    return rec


async def get_votes_information(url: str, object_type: Literal["Post", "Comment"], votes_filter: VoteFilter, pg_conn: Connection) -> list[LemmyVote]:
    """Retrieve vote information for a post or comment.

    :param str url: The URL of the post or comment.
    :param Literal["Post", "Comment"] object_type: The type of object to retrieve votes for (Post or Comment).
    :param VoteFilter votes_filter: The vote filter option (All, Upvotes, Downvotes).
    :param Connection pg_conn: The PostgreSQL database connection.

    :returns: A list of dictionaries containing vote information. Each dictionary has the following keys: - 'name' (str): The name of the voter. - 'score'
        (int): The vote score (+1 for upvote, -1 for downvote). - 'actor_id' (str): The unique identifier of the voter.
    :note: If 'votes_filter' is 'VoteFilter.ALL', all votes (both upvotes and downvotes) are returned. If 'votes_filter' is 'VoteFilter.UPVOTES', only upvotes
        are returned. If 'votes_filter' is 'VoteFilter.DOWNVOTES', only downvotes are returned.

    """

    if object_type == "Post":
        query = """
            SELECT pe.name, pl.score, pe.actor_id
            FROM public.post_like pl
            JOIN public.person pe ON pl.person_id = pe.id
            WHERE pl.post_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            query = f"{query} AND pl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"
    else:
        query = """
            SELECT pe.name, cl.score, pe.actor_id
            FROM public.comment_like cl
            JOIN public.person pe ON cl.person_id = pe.id
            WHERE cl.comment_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            query = f"{query} AND cl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"

    object_local_id = await get_local_id_from_ap_id(url, object_type, pg_conn)
    result = await get_scores_from_pg(query, object_local_id, pg_conn)
    all_votes: list[LemmyVote] = [LemmyVote(name=record["name"], score=record["score"], actor_id=record["actor_id"]) for record in result]
    return all_votes
