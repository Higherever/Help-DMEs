import asyncio
import aiohttp

async def main():
    url = "https://www.futbin.com/squad-building-challenges"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            with open("sbc_list.html", "w") as f:
                f.write(text)

asyncio.run(main())
