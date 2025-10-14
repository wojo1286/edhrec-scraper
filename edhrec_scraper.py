import requests
import csv
import time

# --- Configuration ---
COMMANDER_SLUG = "ojer-axonil-deepest-might"
DECKS_URL = f"https://json.edhrec.com/decks/{COMMANDER_SLUG}/optimized.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EDHREC-Scraper/1.0)"}

def fetch_decks():
    print("Fetching deck JSON from:", DECKS_URL)
    resp = requests.get(DECKS_URL, headers=HEADERS)
    if resp.status_code != 200:
        print("❌ Failed to fetch data:", resp.status_code)
        return []
    data = resp.json()
    # Sometimes deck data is under 'decks' or 'container' keys — check both
    if isinstance(data, dict):
        if "decks" in data:
            return data["decks"]
        elif "container" in data and "json_dict" in data["container"]:
            return data["container"]["json_dict"].get("decks", [])
    print("⚠️ Unexpected JSON structure")
    return []

def save_deck(deck):
    name = deck.get("deck_id") or str(int(time.time()))
    filename = f"{name}.csv"
    cards = deck.get("cards", [])
    if not cards:
        print(f"⚠️ No cards found for deck {name}")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Count", "Card"])
        for c in cards:
            # Each card entry may be a dict with name/count keys
            if isinstance(c, dict):
                writer.writerow([c.get("count", 1), c.get("name", "Unknown")])
            elif isinstance(c, str):
                writer.writerow(["1", c])
    print(f"✅ Saved {filename} with {len(cards)} cards")

def main():
    decks = fetch_decks()
    print(f"Found {len(decks)} optimized decks.")
    for i, deck in enumerate(decks[:4], 1):  # Only first 4 decks
        print(f"\n▶ Processing deck {i}/{min(4, len(decks))}")
        save_deck(deck)
        time.sleep(2)

if __name__ == "__main__":
    main()
