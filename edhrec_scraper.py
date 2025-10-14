import os
import time
import glob
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ====== CONFIG ======
COMMANDER_SLUG = "ojer-axonil-deepest-might"
DECK_LIMIT = 10  # how many decks to scrape
OUTPUT_DIR = "decklists_html"
DEBUG_DIR = "debug_screens"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

# ====== FETCH LIST OF DECKS ======
print(f"🔍 Fetching deck list from EDHREC optimized JSON...")
url = f"https://json.edhrec.com/pages/decks/{COMMANDER_SLUG}/optimized.json"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
r.raise_for_status()
data = r.json()

decks = data.get("table", [])
print(f"Found {len(decks)} total decks.")
df = pd.json_normalize(decks)
df["deckpreview_url"] = df["urlhash"].apply(lambda x: f"https://edhrec.com/deckpreview/{x}")
sample_df = df.head(DECK_LIMIT)
sample_df.to_csv(f"{COMMANDER_SLUG}_html_sample.csv", index=False)
print(f"💾 Saved metadata for first {len(sample_df)} decks.")

# ====== SCRAPE EACH DECK ======
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for i, row in sample_df.iterrows():
        deck_id = row["urlhash"]
        deck_url = row["deckpreview_url"]
        print(f"\n[{i+1}/{len(sample_df)}] Fetching {deck_url}")

        try:
            page.goto(deck_url, timeout=90000)

            # ✅ Wait up to 25s for tables to actually render
            try:
                page.wait_for_selector("table", timeout=5000)
                print("✅ Tables detected in DOM.")
            except Exception:
                print("⚠️ Timed out waiting for tables to render; capturing fallback HTML.")

            # optional screenshot for debugging
            screenshot_path = os.path.join(DEBUG_DIR, f"{deck_id}.png")
            page.screenshot(path=screenshot_path, full_page=True)

            html = page.content()

        except Exception as e:
            print(f"❌ Error loading {deck_url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")

        # --- Deck title ---
        title_el = soup.find("h1")
        deck_title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # --- Source link (Moxfield, Archidekt, etc.) ---
        src_el = soup.find("a", href=lambda x: x and ("moxfield.com" in x or "archidekt.com" in x or "tappedout.net" in x))
        deck_source = src_el["href"] if src_el else "Unknown Source"

        # --- Extract all tables ---
        tables = soup.find_all("table")
        if not tables:
            print("⚠️ No tables found in HTML, skipping.")
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
                    all_cards.append({
                        "deck_id": deck_id,
                        "deck_title": deck_title,
                        "deck_source": deck_source,
                        "category": category,
                        "count": count,
                        "name": name
                    })

        if all_cards:
            out_path = os.path.join(OUTPUT_DIR, f"{deck_id}.csv")
            pd.DataFrame(all_cards).to_csv(out_path, index=False)
            print(f"✅ Saved {len(all_cards)} cards to {out_path}")
        else:
            print("⚠️ Deck contained no cards after parsing.")

    browser.close()

# ====== MERGE ALL DECKLISTS ======
print("\n📦 Merging all decklists into one CSV...")
merged = []

for f in glob.glob(os.path.join(OUTPUT_DIR, "*.csv")):
    df = pd.read_csv(f)
    merged.append(df)

if merged:
    all_decks = pd.concat(merged, ignore_index=True)
    out_path = f"{COMMANDER_SLUG}_combined_decklists.csv"
    all_decks.to_csv(out_path, index=False)
    print(f"✅ Combined decklists saved as {out_path}")
else:
    print("⚠️ No decks were successfully parsed.")
