import requests
from bs4 import BeautifulSoup
import csv, time

BASE = "https://edhrec.com"
OPTIMIZED_URL = "https://edhrec.com/decks/ojer-axonil-deepest-might/optimized"
HEADERS = {"User-Agent": "MyEDHScraper/0.1 (contact@example.com)"}

def get_deck_links():
    resp = requests.get(OPTIMIZED_URL, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    deck_links = []
    for a in soup.select("a.deck-preview, a.deck-name, .deck-link"):
        href = a.get("href")
        if href and "/deck/" in href:
            deck_links.append(href if href.startswith("http") else BASE + href)
    return list(dict.fromkeys(deck_links))  # dedupe

def get_cards(deck_url):
    resp = requests.get(deck_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    cards = []
    for row in soup.select(".card-row"):
        name = row.select_one(".card-name")
        count = row.select_one(".card-count")
        if name:
            cards.append((count.text.strip() if count else "1", name.text.strip()))
    return cards

def main():
    links = get_deck_links()
    print(f"Found {len(links)} deck links.")
    for link in links[:4]:  # first 4 decks only
        print(f"Scraping {link}")
        cards = get_cards(link)
        filename = link.split("/")[-1] + ".csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Count", "Card"])
            writer.writerows(cards)
        time.sleep(2)

if __name__ == "__main__":
    main()

