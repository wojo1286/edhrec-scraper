import os
import glob
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

COMMANDER_SLUG = "ojer-axonil-deepest-might"
DECK_LIMIT = 10
OUTPUT_DIR = "decklists_html"
DEBUG_DIR = "debug_screens"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

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


def parse_table(html, deck_id, deck_source):
    """Extract count, name, type, and price from each table."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    cards = []

    for table in tables:
        rows = table.find_all("tr")[1:]
        for tr in rows:
            tds = tr.find_all("td")
            if not tds or len(tds) < 3:
                continue

            # --- safer extraction ---
            text_cells = [td.get_text(" ", strip=True) for td in tds]

            # try to detect likely columns dynamically
            name = None
            ctype = None
            count = None
            price = None

            # Find hyperlink text for card name if exists
            name_link = tr.find("a")
            if name_link:
                name = name_link.get_text(strip=True)

            # Try to detect count (first numeric-like small cell)
            for td in tds:
                if "×" in td.get_text():
                    count = td.get_text().replace("×", "").strip()
                    break

            # Try to get Type column if present
            for td in tds:
                txt = td.get_text(strip=True)
                # Common card type indicators
                if any(x in txt for x in ["Creature", "Instant", "Sorcery", "Artifact", "Land", "Enchantment", "Planeswalker"]):
                    ctype = txt
                    break

            # Price = last cell starting with $
            for td in reversed(tds):
                txt = td.get_text(strip=True)
                if txt.startswith("$"):
                    price = txt
                    break

            if name:
                cards.append({
                    "deck_id": deck_id,
                    "deck_source": deck_source,
                    "count": count,
                    "name": name,
                    "type": ctype,
                    "price": price
                })
    return cards


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for i, row in sample_df.iterrows():
        deck_id = row["urlhash"]
        deck_url = row["deckpreview_url"]
        print(f"\n[{i+1}/{len(sample_df)}] Fetching {deck_url}")

        try:
            page.goto(deck_url, timeout=90000)

            # Switch to table view
            try:
                page.wait_for_selector('button.nav-link[aria-controls*="table"]', timeout=15000)
                print("🖱️ Switching to table view...")
                page.click('button.nav-link[aria-controls*="table"]')
                page.wait_for_selector("table", timeout=20000)
                print("✅ Table view loaded.")
            except Exception:
                print("⚠️ Could not switch to table view.")

            # Enable "Type" column
            try:
                print("🎛️ Enabling 'Type' column...")
                page.click("button#dropdown-item-button.dropdown-toggle", timeout=10000)
                page.wait_for_selector("button.dropdown-item", timeout=5000)
                buttons = page.query_selector_all("button.dropdown-item")
                for btn in buttons:
                    label = btn.inner_text().strip()
                    if "Type" in label:
                        btn.click()
                        print("✅ 'Type' column toggled on.")
                        break
                page.wait_for_timeout(1000)
            except Exception:
                print("⚠️ Could not enable Type column.")

            html = page.content()

            # retry once if no tables
            if "<table" not in html:
                print("🔁 Retrying after short wait...")
                page.wait_for_timeout(2000)
                html = page.content()

            # Screenshot for debugging
            page.screenshot(path=os.path.join(DEBUG_DIR, f"{deck_id}.png"), full_page=True)

        except Exception as e:
            print(f"❌ Error loading {deck_url}: {e}")
            continue

        # parse deck source
        soup = BeautifulSoup(html, "html.parser")
        src_el = soup.find("a", href=lambda x: x and any(domain in x for domain in ["moxfield.com", "archidekt.com", "tappedout.net"]))
        deck_source = src_el["href"] if src_el else "Unknown Source"

        cards = parse_table(html, deck_id, deck_source)

        if cards:
            out_path = os.path.join(OUTPUT_DIR, f"{deck_id}.csv")
            pd.DataFrame(cards).to_csv(out_path, index=False)
            print(f"✅ Saved {len(cards)} cards to {out_path}")
        else:
            print("⚠️ No cards parsed.")

    browser.close()

# Merge all decklists
print("\n📦 Merging all decklists into one CSV...")
merged = [pd.read_csv(f) for f in glob.glob(os.path.join(OUTPUT_DIR, "*.csv")) if os.path.getsize(f) > 0]
if merged:
    all_decks = pd.concat(merged, ignore_index=True)
    out_path = f"{COMMANDER_SLUG}_combined_decklists.csv"
    all_decks.to_csv(out_path, index=False)
    print(f"✅ Combined decklists saved as {out_path}")
else:
    print("⚠️ No decks successfully parsed.")
