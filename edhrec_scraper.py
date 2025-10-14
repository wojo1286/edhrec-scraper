import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time

# ------------------ CONFIG ------------------
COMMANDER_SLUG = "ojer-axonil-deepest-might"
OUTPUT_DIR = "decklists_html"
BASE_URL = "https://json.edhrec.com/pages/decks"
DECKPREVIEW_URL = "https://edhrec.com/deckpreview/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MAX_DECKS = 10  # limit for testing
# --------------------------------------------

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Fetch list of optimized decks
optimized_url = f"{BASE_URL}/{COMMANDER_SLUG}/optimized.json"
print(f"Fetching deck list from: {optimized_url}")
r = requests.get(optimized_url, headers=HEADERS)
r.raise_for_status()
data = r.json()

decks = data.get("table", [])
print(f"Found {len(decks)} total decks")

df = pd.json_normalize(decks)
df["deckpreview_url"] = DECKPREVIEW_URL + df["urlhash"]

# Use only first few for testing
sample_df = df.head(MAX_DECKS)
sample_df.to_csv(f"{COMMANDER_SLUG}_html_sample.csv", index=False)
print(f"Saved metadata for first {MAX_DECKS} decks.")

# Loop through each deck preview
for i, row in sample_df.iterrows():
    deck_id = row["urlhash"]
    deck_url = row["deckpreview_url"]
    print(f"\n[{i+1}/{len(sample_df)}] Fetching deck {deck_id}")
    print(f" → {deck_url}")

    try:
        res = requests.get(deck_url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"⚠️ Skipped (status {res.status_code})")
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")

        if not tables:
            print("⚠️ No tables found, skipping.")
            continue

        all_cards = []

        for t in tables:
            # Find category name from nearest heading
            category_tag = t.find_previous(["h2", "h3"])
            category = category_tag.get_text(strip=True) if category_tag else "Unknown"
            rows = t.find_all("tr")[1:]  # skip header row

            for row_tag in rows:
                cols = [c.get_text(strip=True) for c in row_tag.find_all("td")]
                if len(cols) >= 2:
                    try:
                        count = int(cols[0])
                    except ValueError:
                        count = 1
                    name = cols[1]
                    all_cards.append({"category": category, "count": count, "name": name})

        if not all_cards:
            print("⚠️ No cards parsed.")
            continue

        deck_df = pd.DataFrame(all_cards)
        out_path = os.path.join(OUTPUT_DIR, f"{deck_id}.csv")
        deck_df.to_csv(out_path, index=False)
        print(f"✅ Saved {len(deck_df)} cards to {out_path}")

        time.sleep(1)
    except Exception as e:
        print(f"❌ Error processing deck {deck_id}: {e}")

print("\n🎉 Done! Decklists saved in decklists_html/")
