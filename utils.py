from __future__ import annotations

from enum import Enum
from typing import TypeVar, Literal, Optional

from asyncpg import Connection

T = TypeVar("T")


class VoteFilter(str, Enum):
    ALL = "All"
    UPVOTES = "Upvotes"
    DOWNVOTES = "Downvotes"


def paginate_data(all_votes: list[T], offset: int, limit: int) -> tuple[list[T], Optional[int]]:
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


async def get_votes_information(url: str, object_type: Literal["Post", "Comment"], votes_filter: VoteFilter, pg_conn: Connection) -> list[dict[str, int | str]]:
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
        rslt = await pg_conn.fetchrow("SELECT id FROM public.post WHERE ap_id = $1", url)
        post_local_id = rslt.get("id")

        query = """
            SELECT pe.name, pl.score, pe.actor_id
            FROM public.post_like pl
            JOIN public.person pe ON pl.person_id = pe.id
            WHERE pl.post_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            query = f"{query} AND pl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"
        result = await pg_conn.fetch(query, post_local_id)
        return [dict(record) for record in result]
    else:
        rslt = await pg_conn.fetchrow("SELECT id FROM public.comment WHERE ap_id = $1", url)
        comment_local_id = rslt.get("id")

        query = """
            SELECT pe.name, cl.score, pe.actor_id
            FROM public.comment_like cl
            JOIN public.person pe ON cl.person_id = pe.id
            WHERE cl.comment_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            query = f"{query} AND cl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"
        result = await pg_conn.fetch(query, comment_local_id)
        return [dict(record) for record in result]
