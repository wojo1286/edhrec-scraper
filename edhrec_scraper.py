import os
import glob
import time
import random
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ==============================
# CONFIGURATION
# ==============================
COMMANDER_SLUG = "ojer-axonil-deepest-might"
DECK_LIMIT = 10
OUTPUT_DIR = "decklists_html"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# FETCH METADATA FROM EDHREC
# ==============================
print(f"🔍 Fetching deck list from EDHREC optimized JSON...")
json_url = f"https://json.edhrec.com/pages/decks/{COMMANDER_SLUG}/optimized.json"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(json_url, headers=headers)
r.raise_for_status()
data = r.json()

decks = data.get("table", [])
print(f"Found {len(decks)} total decks.")
df = pd.json_normalize(decks)
df["deckpreview_url"] = df["urlhash"].apply(lambda x: f"https://edhrec.com/deckpreview/{x}")
sample_df = df.head(DECK_LIMIT)
sample_df.to_csv(f"{COMMANDER_SLUG}_html_sample.csv", index=False)
print(f"💾 Saved metadata for first {len(sample_df)} decks.")

# ==============================
# PARSE DECK TABLE
# ==============================
def parse_table(html, deck_id, deck_source):
    soup = BeautifulSoup(html, "html.parser")
    cards = []

    for table in soup.find_all("table"):
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            # --- CMC ---
            cmc_el = tr.find("span", class_="float-right")
            cmc = cmc_el.get_text(strip=True) if cmc_el else None

            # --- Card Name ---
            name_el = tr.find("a")
            name = name_el.get_text(strip=True) if name_el else None

            # --- Card Type ---
            ctype = None
            for td in tds:
                text = td.get_text(strip=True)
                if text in ["Creature", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Land"]:
                    ctype = text
                    break

            # --- Card Price ---
            price = None
            for td in reversed(tds):
                txt = td.get_text(strip=True)
                if txt.startswith("$"):
                    price = txt
                    break

            if name:
                cards.append({
                    "deck_id": deck_id,
                    "deck_source": deck_source,
                    "cmc": cmc,
                    "name": name,
                    "type": ctype,
                    "price": price
                })
    return cards

# ==============================
# SCRAPE EACH DECKPREVIEW PAGE
# ==============================
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for i, row in sample_df.iterrows():
        deck_id = row["urlhash"]
        deck_url = row["deckpreview_url"]
        print(f"\n[{i+1}/{len(sample_df)}] Fetching {deck_url}")

        try:
            page.goto(deck_url, timeout=90000)

            # --- Switch to table view ---
            try:
                page.wait_for_selector('button.nav-link[aria-controls*="table"]', timeout=15000)
                print("🖱️ Switching to table view...")
                page.click('button.nav-link[aria-controls*="table"]')
                page.wait_for_selector("table", timeout=20000)
                print("✅ Table view loaded.")
            except Exception:
                print("⚠️ Could not switch to table view.")

            # --- Ensure Type column is visible ---
            try:
                print("🎛️ Ensuring 'Type' column is visible...")
                page.click("button#dropdown-item-button.dropdown-toggle", timeout=10000)
                page.wait_for_selector("button.dropdown-item", timeout=5000)
                for btn in page.query_selector_all("button.dropdown-item"):
                    if "Type" in btn.inner_text():
                        btn.click()
                        print("✅ 'Type' column toggled on.")
                        break
                page.wait_for_selector("th:has-text('Type')", timeout=5000)
            except Exception as e:
                print(f"⚠️ Could not confirm Type column: {e}")

            # --- Get deck source ---
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            src_el = soup.find("a", href=lambda x: x and any(domain in x for domain in ["moxfield.com", "archidekt.com", "tappedout.net"]))
            deck_source = src_el["href"] if src_el else "Unknown Source"

            # --- Parse deck cards ---
            cards = parse_table(html, deck_id, deck_source)

            if cards:
                out_path = os.path.join(OUTPUT_DIR, f"{deck_id}.csv")
                pd.DataFrame(cards).to_csv(out_path, index=False)
                print(f"✅ Saved {len(cards)} cards to {out_path}")
            else:
                print("⚠️ No cards parsed.")

            # --- Add small delay ---
            time.sleep(random.uniform(2.5, 4.5))

        except Exception as e:
            print(f"❌ Error loading {deck_url}: {e}")
            continue

    browser.close()

# ==============================
# MERGE ALL DECKS INTO ONE FILE
# ==============================
print("\n📦 Merging all decklists into one CSV...")
merged = [pd.read_csv(f) for f in glob.glob(os.path.join(OUTPUT_DIR, "*.csv")) if os.path.getsize(f) > 0]
if merged:
    all_decks = pd.concat(merged, ignore_index=True)
    out_path = f"{COMMANDER_SLUG}_combined_decklists.csv"
    all_decks.to_csv(out_path, index=False)
    print(f"✅ Combined decklists saved as {out_path}")
else:
    print("⚠️ No decks successfully parsed.")
