from __future__ import annotations

from os import getenv
from typing import Optional

import asyncpg
from aiohttp import ClientSession
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from data_models import VoteFilter, VotesResponse, SortOption
from lemmy_api import lemmy_auth, lemmy_search
from lemmy_db import paginate_data, get_votes_information

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)


@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/votes/post", summary="Get votes information for a post")
async def post_votes(
    url: HttpUrl = Query(..., description="URL of the post"),
    offset: int = Query(default=0, description="The offset from which to start paginating the data (0-based indexing)", ge=0),
    limit: int = Query(default=50, description="The maximum number of items to return per page", ge=1, le=250),
    votes_filter: VoteFilter = Query(VoteFilter.ALL, description="Vote filter option (All, Upvotes, Downvotes)"),
    sort_by: SortOption = Query(SortOption.DATETIME_DESC, description="Sort option (datetime_asc, datetime_desc)"),
    username: Optional[str] = Query(None, description="Username to filter by vote author"),
) -> VotesResponse:
    """Get votes for a post.

    :param str url: URL of the post.
    :param int offset: The offset from which to start paginating the data (0-based indexing).
    :param int limit: The maximum number of items to return per page.
    :param VoteFilter votes_filter: Vote filter option (All, Upvotes, Downvotes).
    :param SortOption sort_by: Vote Sort Option (datetime_asc, datetime_desc).
    :param Optional[str] username: Username to filter by vote author.

    :returns: Paginated votes information.
    :rtype: VotesResponse

    :raises: Raised if there is an error with the lemmy API.

    """
    decoded_url = str(url)
    resp_status, post_data = await lemmy_search(decoded_url, app.state.aio_session)

    if resp_status != 200:
        raise HTTPException(status_code=resp_status, detail=f"{post_data.get('error', 'External API Error')}. Make sure you are passing Activity Pub link.")

    obj_agg, all_votes = await get_votes_information(decoded_url, "Post", votes_filter, sort_by, username, app.state.pg_conn)
    paginated_votes, next_offset = paginate_data(all_votes, offset, limit)
    return VotesResponse(
        votes=paginated_votes,
        total_count=len(all_votes),
        next_offset=next_offset,
        total_score=obj_agg.total_score,
        upvotes=obj_agg.upvotes,
        downvotes=obj_agg.downvotes,
    )


@app.get("/votes/comment", summary="Get votes information for a comment")
async def comment_votes(
    url: HttpUrl = Query(..., description="URL of the comment"),
    offset: int = Query(default=0, description="The offset from which to start paginating the data (0-based indexing)", ge=0),
    limit: int = Query(default=50, description="The maximum number of items to return per page", ge=1, le=250),
    votes_filter: VoteFilter = Query(VoteFilter.ALL, description="Vote filter option (All, Upvotes, Downvotes)"),
    sort_by: SortOption = Query(SortOption.DATETIME_DESC, description="Sort option (datetime_asc, datetime_desc)"),
    username: Optional[str] = Query(None, description="Username to filter by vote author"),
) -> VotesResponse:
    """Get votes for a comment.

    :param str url: URL of the comment.
    :param int offset: The offset from which to start paginating the data (0-based indexing).
    :param int limit: The maximum number of items to return per page.
    :param VoteFilter votes_filter: Vote filter option (All, Upvotes, Downvotes).
    :param SortOption sort_by: Vote Sort Option (datetime_asc, datetime_desc).
    :param Optional[str] username: Username to filter by vote author.

    :returns: Paginated votes information.
    :rtype: VotesResponse

    :raises: Raised if there is an error with the lemmy API.

    """
    decoded_url = str(url)
    resp_status, comment_data = await lemmy_search(decoded_url, app.state.aio_session)

    if resp_status != 200:
        raise HTTPException(status_code=resp_status, detail=f"{comment_data.get('error', 'External API Error')}. Make sure you are passing Activity Pub link.")

    obj_agg, all_votes = await get_votes_information(decoded_url, "Comment", votes_filter, sort_by, username, app.state.pg_conn)
    paginated_votes, next_offset = paginate_data(all_votes, offset, limit)
    return VotesResponse(
        votes=paginated_votes,
        total_count=len(all_votes),
        next_offset=next_offset,
        total_score=obj_agg.total_score,
        upvotes=obj_agg.upvotes,
        downvotes=obj_agg.downvotes,
    )


@app.on_event("startup")
async def main() -> None:
    headers = {
        "User-Agent": "LemmySeeMyHaters",
        "Content-Type": "application/json",
    }
    app.state.aio_session = ClientSession(headers=headers)
    await lemmy_auth(app.state.aio_session)
    app.state.pg_conn = await asyncpg.connect(
        database=getenv("DB_USER"), user=getenv("DB_USER"), password=getenv("DB_PASSWORD"), host="localhost", port=getenv("DB_PORT")
    )


@app.on_event("shutdown")
async def shutdown_db() -> None:
    await app.state.aio_session.close()
    await app.state.pg_conn.close()
