#!venv/bin/python
from __future__ import annotations

import asyncio
import time

import aiohttp
import aioschedule as schedule
import aiosqlite
from tqdm import tqdm


async def save_to_database(communities: dict[str, dict[object, object]]) -> None:
    """
    Save a list of communities to an SQLite database.

    :param communities: A dictionary containing community information.
    :type communities: dict[str, dict[object, object]])
    :return: None
    """
    async with aiosqlite.connect("lemmy_servers.db", check_same_thread=False) as db_conn:
        await db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lemmy_instances (
                url TEXT PRIMARY KEY
            )
        """
        )
        await db_conn.commit()
        communities_pbar = tqdm(communities)
        for community in communities_pbar:
            url = community.get("url", "lemmystats.lol")
            communities_pbar.set_description(f"Adding URL: {url}")
            await db_conn.execute("INSERT OR IGNORE INTO lemmy_instances (url) VALUES (?)", (url,))
        await db_conn.commit()


async def update_server_db() -> None:
    """
    Update the server database with information from a remote source.

    Fetches community data from a remote source and saves it to an SQLite database.

    :return: None
    """
    async with aiohttp.ClientSession() as session:
        async with session.get("https://browse.feddit.de/communities.json") as resp:
            communities = await resp.json()
            if resp.status == 200:
                await save_to_database(communities)
            else:
                print(communities)


def main() -> None:
    schedule.every().day.at("00:00").do(update_server_db)
    asyncio.run(update_server_db())
    while True:
        asyncio.run(schedule.run_pending())
        time.sleep(0.1)


if __name__ == "__main__":
    main()
