from bs4 import BeautifulSoup

with open("sbc_list.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")
cards = soup.select(".sbc-card-wrapper a[href*='squad-building-challenge/']")

for i, card in enumerate(cards[:5]):
    expires_label = card.find(string="Expires")
    expires_text = ""
    if expires_label:
        expires_div = expires_label.find_next("div", class_="bold")
        if expires_div:
            expires_text = expires_div.get_text(strip=True)
    print(f"Card {i}: Expires: {expires_text}")

