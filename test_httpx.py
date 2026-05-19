import httpx
import asyncio

async def main():
    url = "https://cdn3.futbin.com/content/fifa26/img/sbc/sbc_set_image_1000548-57be79e2-82e1.png"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://www.futbin.com/",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    async with httpx.AsyncClient(http2=True) as client:
        resp = await client.get(url, headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Size: {len(resp.content)} bytes")

asyncio.run(main())
