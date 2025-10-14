import requests
import csv
import time

COMMANDER_SLUG = "ojer-axonil-deepest-might"
BASE_URL = f"https://edhrec.com/decks/{COMMANDER_SLUG}/optimized"
API_URL = f"https://json.edhrec.com/decks/{COMMANDER_SLUG}/optimized.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EDHREC-Scraper/1.0)"}


def fetch_json():
    print(f"Fetching deck data for commander: {COMMANDER_SLUG}")
    resp = requests.get(API_URL, headers=HEADERS)
    if resp.status_code != 200:
        print("❌ Failed to fetch JSON:", resp.status_code)
        return None
    try:
        data = resp.json()
        return data
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        return None


def save_deck_table(json_data):
    if not json_data:
        print("⚠️ No JSON data to save.")
        return

    # Try to find deck list entries
    decks = json_data.get("container", {}).get("json_dict", {}).get("decks", [])
    if not decks:
        decks = json_data.get("decks", [])

    if not decks:
        print("⚠️ No decks found in JSON.")
        return

    filename = f"{COMMANDER_SLUG}_optimized_decks.csv"
    print(f"✅ Found {len(decks)} optimized decks. Saving to {filename}")

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Deck ID",
                "Price",
                "Tags",
                "Salt",
                "Creatures",
                "Instants",
                "Sorceries",
                "Artifacts",
                "Enchantments",
                "Planeswalkers",
                "Save Date",
                "Deck URL",
            ]
        )

        for deck in decks:
            deck_id = deck.get("deck_id", "")
            deck_url = deck.get("url", "")
            tags = ", ".join(deck.get("tags", []))
            row = [
                deck_id,
                deck.get("price", ""),
                tags,
                deck.get("salt", ""),
                deck.get("creature_count", ""),
                deck.get("instant_count", ""),
                deck.get("sorcery_count", ""),
                deck.get("artifact_count", ""),
                deck.get("enchantment_count", ""),
                deck.get("planeswalker_count", ""),
                deck.get("savedate", ""),
                deck_url,
            ]
            writer.writerow(row)

    print(f"💾 Saved deck table with {len(decks)} rows.")
    return filename


def main():
    print(f"Fetching from: {API_URL}")
    data = fetch_json()
    save_deck_table(data)
    time.sleep(1)


if __name__ == "__main__":
    main()
