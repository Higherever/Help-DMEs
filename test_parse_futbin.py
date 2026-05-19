import json
from bs4 import BeautifulSoup

with open("sbc_list.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")
cards = soup.select(".sbc-card-wrapper a[href*='squad-building-challenge/']")
results = []
for card in cards:
    raw_card_data_str = None
    player_card_el = card.select_one(".playercard-26")
    if player_card_el:
        card_info = {}
        bg_el = player_card_el.select_one(".playercard-26-bg")
        if bg_el:
            card_info["bg_url"] = bg_el.get("src")
        face_el = player_card_el.select_one(".playercard-26-special-img")
        if face_el:
            card_info["face_url"] = face_el.get("src")
        
        rating_el = player_card_el.select_one(".playercard-26-rating")
        if rating_el:
            card_info["rating"] = rating_el.get_text(strip=True)
        
        pos_el = player_card_el.select_one(".playercard-26-position")
        if pos_el:
            card_info["position"] = pos_el.get_text(strip=True)

        name_el = player_card_el.select_one(".playercard-26-name")
        if name_el:
            card_info["name"] = name_el.get_text(strip=True)

        stats = []
        stat_els = player_card_el.select(".playercard-26-stats")
        for s in stat_els:
            val = s.select_one(".playercard-stat-number")
            lbl = s.select_one(".playercard-26-stat-value")
            if val and lbl:
                stats.append({
                    "name": lbl.get_text(strip=True),
                    "value": val.get_text(strip=True)
                })
        if stats:
            card_info["stats"] = stats
        
        raw_card_data_str = json.dumps(card_info) if card_info else None
        if raw_card_data_str:
            results.append(raw_card_data_str)

print(len(results))
