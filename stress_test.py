import asyncio

from aiohttp import ClientSession


async def main() -> None:
    async with ClientSession() as session:
        next_offset = 0
        while next_offset is not None:
            async with session.get(
                "http://localhost:8000/votes/post", params={"url": "https://lemmy.world/post/4556641", "offset": next_offset, "limit": 250}
            ) as resp:
                response = await resp.json()
                print(response)
                next_offset = response["next_offset"]


if __name__ == "__main__":
    asyncio.run(main())
