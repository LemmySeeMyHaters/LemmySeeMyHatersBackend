from __future__ import annotations

import asyncio
from datetime import datetime
from os import getenv
from typing import TypeVar, Literal, Optional

import asyncpg
from async_lru import alru_cache
from asyncpg import Connection, Record
from fastapi import HTTPException
from typing_extensions import LiteralString

from data_models import VoteFilter, LemmyVote, LemmyObjectAggregate

T = TypeVar("T")


def get_unix_timestamp(published_datetime: datetime) -> float:
    """
    Converts a datetime object to a Unix timestamp.

    :param published_datetime: Python datetime object.
    :type published_datetime: datetime
    :return: The Unix timestamp representing the provided ISO 8601 date and time.
    :rtype: float

    """
    return published_datetime.timestamp()


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
    """
     Fetches the local ID of a Post or Comment object based on its ActivityPub URL.

    :param url: The ActivityPub URL of the object.
    :type url: str
    :param object_type: The type of object, either "Post" or "Comment".
    :type object_type: Literal["Post", "Comment"]
    :param pg_conn: An asyncpg database connection.
    :type pg_conn: asyncpg.Connection

    :return: The local ID of the object in the database.
    :rtype: int
    :raises HTTPException: If the object cannot be found in the database, raises a 404 error.

    """
    if object_type == "Post":
        rslt = await pg_conn.fetchrow("SELECT id FROM public.post WHERE ap_id = $1", url)
    else:
        rslt = await pg_conn.fetchrow("SELECT id FROM public.comment WHERE ap_id = $1", url)

    if rslt is None:
        raise HTTPException(status_code=404, detail="Could not fetch the object from the URL.")
    else:
        local_id: int = rslt.get("id")
        return local_id


@alru_cache(ttl=180, maxsize=256)
async def get_aggregates_from_pg(query: LiteralString, object_local_id: int) -> LemmyObjectAggregate:
    # Needs a new connection because it runs concurrently
    pg_conn = await asyncpg.connect(
        database=getenv("DB_USER"), user=getenv("DB_USER"), password=getenv("DB_PASSWORD"), host="localhost", port=getenv("DB_PORT")
    )
    rec: Record = await pg_conn.fetchrow(query, object_local_id)
    return LemmyObjectAggregate(*rec)


@alru_cache(ttl=60, maxsize=256)
async def get_scores_from_pg(query: LiteralString, object_local_id: int, username: Optional[str], pg_conn: Connection) -> list[Record]:
    """
     Retrieves scores associated with a Post or Comment from the database, optionally filtered by username.

    :param query: The SQL query to fetch scores.
    :type query: LiteralString
    :param object_local_id: The local ID of the Post or Comment object.
    :type object_local_id: int
    :param username: The username to filter by, or None to fetch all scores.
    :type username: Optional[str]
    :param pg_conn: An asyncpg database connection.
    :type pg_conn: asyncpg.Connection.

    :return: A list of records containing scores associated with the object.
    :rtype: list[asyncpg.Record]

    """
    if username is None:
        # If username is None, filter by post_id only
        rec: list[Record] = await pg_conn.fetch(query, object_local_id)
        return rec
    else:
        # If username is not None, filter by both post_id and username
        rec_with_user: list[Record] = await pg_conn.fetch(query, object_local_id, username)
        return rec_with_user


async def get_votes_information(
    url: str, object_type: Literal["Post", "Comment"], votes_filter: VoteFilter, username: Optional[str], pg_conn: Connection
) -> tuple[LemmyObjectAggregate, list[LemmyVote]]:
    """Retrieve vote information for a post or comment.

    :param str url: The URL of the post or comment.
    :param Literal["Post", "Comment"] object_type: The type of object to retrieve votes for (Post or Comment).
    :param VoteFilter votes_filter: The vote filter option (All, Upvotes, Downvotes).
    :param Optional[str] username: Username to filter by vote author.
    :param Connection pg_conn: The PostgreSQL database connection.

    :returns: A list of dictionaries containing vote information. Each dictionary has the following keys: - 'name' (str): The name of the voter. - 'score'
        (int): The vote score (+1 for upvote, -1 for downvote). - 'actor_id' (str): The unique identifier of the voter.
    :note: If 'votes_filter' is 'VoteFilter.ALL', all votes (both upvotes and downvotes) are returned. If 'votes_filter' is 'VoteFilter.UPVOTES', only upvotes
        are returned. If 'votes_filter' is 'VoteFilter.DOWNVOTES', only downvotes are returned.

    """

    if object_type == "Post":
        votes_query = """
            SELECT pe.name, pl.score, pe.actor_id, pl.published
            FROM public.post_like pl
            JOIN public.person pe ON pl.person_id = pe.id
            WHERE pl.post_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            votes_query = f"{votes_query} AND pl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"

        agg_query = """
        SELECT post_agg.score, post_agg.upvotes, post_agg.downvotes 
        FROM public.post_aggregates post_agg 
        WHERE post_agg.post_id = $1
        """
    else:
        votes_query = """
            SELECT pe.name, cl.score, pe.actor_id, cl.published
            FROM public.comment_like cl
            JOIN public.person pe ON cl.person_id = pe.id
            WHERE cl.comment_id = $1
            """
        if votes_filter != VoteFilter.ALL:
            votes_query = f"{votes_query} AND cl.score = {1 if votes_filter == VoteFilter.UPVOTES else -1}"

        agg_query = """
        SELECT comment_agg.score, comment_agg.upvotes, comment_agg.downvotes 
        FROM public.comment_aggregates comment_agg 
        WHERE comment_agg.comment_id = $1
        """

    if username is not None:
        votes_query = f"{votes_query} AND pe.name = $2"

    object_local_id = await get_local_id_from_ap_id(url, object_type, pg_conn)
    result = await asyncio.gather(get_aggregates_from_pg(agg_query, object_local_id), get_scores_from_pg(votes_query, object_local_id, username, pg_conn))
    all_votes: list[LemmyVote] = [
        LemmyVote(name=record["name"], score=record["score"], actor_id=record["actor_id"], created_utc=get_unix_timestamp(record["published"]))
        for record in result[1]
    ]
    return result[0], all_votes