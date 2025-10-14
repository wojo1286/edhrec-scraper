import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ========== CONFIG ==========
COMMANDER_SLUG = "ojer-axonil-deepest-might"
DECK_LIMIT = 10  # how many decks to scrape
OUTPUT_DIR = "decklists_html"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== FETCH LIST OF DECKS ==========
print(f"🔍 Fetching deck list from EDHREC optimized JSON...")
url = f"https://json.edhrec.com/pages/decks/{COMMANDER_SLUG}/optimized.json"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
r.raise_for_status()
data = r.json()

decks = data.get("table", [])
print(f"Found {len(decks)} total decks.")

# Convert to DataFrame and save manifest
df = pd.json_normalize(decks)
df["deckpreview_url"] = df["urlhash"].apply(lambda x: f"https://edhrec.com/deckpreview/{x}")
sample_df = df.head(DECK_LIMIT)
sample_df.to_csv(f"{COMMANDER_SLUG}_html_sample.csv", index=False)
print(f"💾 Saved metadata for first {len(sample_df)} decks.")

# ========== SCRAPE EACH DECK ==========
print("\n🧠 Launching Playwright (Chromium)...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for i, row in sample_df.iterrows():
        deck_id = row["urlhash"]
        deck_url = row["deckpreview_url"]
        print(f"\n[{i+1}/{len(sample_df)}] Fetching deck {deck_id}")
        print(f"🔗 {deck_url}")

        try:
            page.goto(deck_url, timeout=90000)
            time.sleep(5)  # wait for JS render
            html = page.content()
        except Exception as e:
            print(f"❌ Error loading {deck_url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")

        if not tables:
            print("⚠️ No tables found, skipping.")
            continue

        all_cards = []
        for t in tables:
            heading = t.find_previous(["h2", "h3"])
            category = heading.get_text(strip=True) if heading else "Unknown"
            rows = t.find_all("tr")[1:]
            for tr in rows:
                cols = [c.get_text(strip=True) for c in tr.find_all("td")]
                if len(cols) >= 2:
                    count = cols[0].replace("×", "").strip()
                    name = cols[1]
                    all_cards.append({"category": category, "count": count, "name": name})

        if all_cards:
            out_path = os.path.join(OUTPUT_DIR, f"{deck_id}.csv")
            pd.DataFrame(all_cards).to_csv(out_path, index=False)
            print(f"✅ Saved {len(all_cards)} cards to {out_path}")
        else:
            print("⚠️ Deck contained no cards after parsing.")

    browser.close()

print("\n📦 Merging all decklists into one CSV...")
import glob
merged = []

for f in glob.glob(os.path.join(OUTPUT_DIR, "*.csv")):
    df = pd.read_csv(f)
    df["deck_id"] = os.path.basename(f).replace(".csv", "")
    merged.append(df)

if merged:
    all_decks = pd.concat(merged, ignore_index=True)
    out_path = f"{COMMANDER_SLUG}_combined_decklists.csv"
    all_decks.to_csv(out_path, index=False)
    print(f"✅ Combined decklists saved as {out_path}")
else:
    print("⚠️ No decks were successfully parsed.")
