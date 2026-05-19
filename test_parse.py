import re
from bs4 import BeautifulSoup
import json

with open("sbc_list.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")
cards = soup.select(".sbc-card-wrapper a[href*='squad-building-challenge/']")

results = []
for card in cards:
    # try to find playercard
    pc = card.select_one(".playercard-26")
    if pc:
        bg = pc.select_one(".playercard-26-bg")
        face = pc.select_one(".playercard-26-special-img")
        rating = pc.select_one(".playercard-26-rating")
        pos = pc.select_one(".playercard-26-position")
        name = pc.select_one(".playercard-26-name")
        
        stats = []
        stat_els = pc.select(".playercard-26-stats")
        for s in stat_els:
            val = s.select_one(".playercard-stat-number")
            lbl = s.select_one(".playercard-26-stat-value")
            if val and lbl:
                stats.append({"name": lbl.get_text(strip=True), "value": val.get_text(strip=True)})
                
        results.append({
            "name": name.get_text(strip=True) if name else None,
            "rating": rating.get_text(strip=True) if rating else None,
            "pos": pos.get_text(strip=True) if pos else None,
            "bg": bg.get("src").split("?")[0] if bg else None,
            "face": face.get("src").split("?")[0] if face else None,
            "stats": stats
        })

print(json.dumps(results[:2], indent=2))
