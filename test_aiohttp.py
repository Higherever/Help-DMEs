import asyncio
import aiohttp

async def main():
    url = "https://cdn3.futbin.com/content/fifa26/img/sbc/sbc_set_image_1000548-57be79e2-82e1.png"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.futbin.com/"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                print(f"Size: {len(await resp.read())} bytes")

asyncio.run(main())
