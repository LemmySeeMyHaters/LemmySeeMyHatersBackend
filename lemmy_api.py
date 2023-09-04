from __future__ import annotations

from os import getenv
from urllib.parse import urlsplit

import aiosqlite
from aiohttp import ClientSession
from fastapi import HTTPException


async def lemmy_auth(aio_session: ClientSession) -> None:
    """Authenticate with the Lemmy API using an aiohttp session.

    :param ClientSession aio_session: The aiohttp ClientSession to use for the API request.

    :returns: None

    """
    auth = {"password": getenv("LEMMY_PASSWORD"), "totp_2fa_token": None, "username_or_email": getenv("LEMMY_USERNAME")}
    async with aio_session.post("https://lemmystats.lol/api/v3/user/login", json=auth) as resp:
        data = await resp.json()
        aio_session.headers["auth"] = data.get("jwt")


async def is_valid_lemmy_url(url: str) -> bool:
    """
    Check if a URL is a valid Lemmy instance URL by comparing it with a list of valid domains stored in an SQLite database.

    :param url: The URL to be checked.
    :type url: str
    :return: True if the URL is valid, False otherwise.
    :rtype: bool
    """
    if not url.startswith("https://"):
        return False

    async with aiosqlite.connect("lemmy_servers.db", check_same_thread=False) as db_conn:
        cursor = await db_conn.cursor()
        await cursor.execute("SELECT url FROM lemmy_instances")
        valid_domains = [row[0] for row in await cursor.fetchall()]

        parsed_user_url = urlsplit(url)
        user_domain = parsed_user_url.hostname

        if user_domain in valid_domains:
            return True
        return False


async def lemmy_search(url: str, aio_session: ClientSession) -> tuple[int, dict[object, object]]:
    """Search for an object in the Lemmy API using an aiohttp session.

    :param str url: The URL to search for.
    :param ClientSession aio_session: The aiohttp ClientSession to use for the API request.

    :returns: A tuple containing the HTTP status code and the search result as a dictionary. - int: The HTTP status code of the API response. - dict: A
        dictionary containing the search result data.

    """

    if not await is_valid_lemmy_url(url):
        raise HTTPException(status_code=422, detail="Not a valid Lemmy URL or url doesn't start with https://")

    params = {"q": url, "auth": aio_session.headers["auth"]}
    async with aio_session.get("https://lemmystats.lol/api/v3/resolve_object", params=params) as resp:
        search_result = await resp.json()
        return resp.status, search_result
