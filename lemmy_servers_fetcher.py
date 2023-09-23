#!venv/bin/python
from __future__ import annotations

import asyncio
from csv import DictReader
import re
import time

import aiohttp
import aioschedule as schedule
import aiosqlite
from tqdm import tqdm

markdown_url_pattren = re.compile(r"\[.*?\]\((.*?)\)")


async def save_to_database(communities: DictReader[str]) -> None:
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
            markdown_text = community.get("Instance", "lemmykekw.xyz")
            if result := markdown_url_pattren.search(markdown_text):
                extracted_url = result.group(1).removeprefix("https://")
            else:
                extracted_url = "lemmykekw.xyz"
            communities_pbar.set_description(f"Adding URL: {extracted_url}")
            await db_conn.execute("INSERT OR IGNORE INTO lemmy_instances (url) VALUES (?)", (extracted_url,))
        await db_conn.commit()


async def update_server_db() -> None:
    """
    Update the server database with information from a remote source.

    Fetches community data from a remote source and saves it to an SQLite database.

    :return: None
    """
    async with aiohttp.ClientSession() as session:
        async with session.get("https://raw.githubusercontent.com/maltfield/awesome-lemmy-instances/main/awesome-lemmy-instances.csv") as resp:
            raw_data = await resp.text()
            communities = DictReader(raw_data.splitlines())
            await save_to_database(communities)


def main() -> None:
    schedule.every().day.at("00:00").do(update_server_db)
    asyncio.run(update_server_db())
    while True:
        asyncio.run(schedule.run_pending())
        time.sleep(0.1)


if __name__ == "__main__":
    main()
