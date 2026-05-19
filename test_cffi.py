from curl_cffi import requests

url = "https://cdn3.futbin.com/content/fifa26/img/sbc/sbc_set_image_1000548-57be79e2-82e1.png"
headers = {
    "Referer": "https://www.futbin.com/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
}
resp = requests.get(url, headers=headers, impersonate="chrome120")
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"Size: {len(resp.content)} bytes")
