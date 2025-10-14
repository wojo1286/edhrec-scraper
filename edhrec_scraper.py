import requests
import pandas as pd

# URL for optimized decks
url = "https://json.edhrec.com/pages/decks/ojer-axonil-deepest-might/optimized.json"

# Browser-like headers prevent blocking
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Fetch and parse JSON
response = requests.get(url, headers=headers)
response.raise_for_status()
data = response.json()

# Extract decks (list of dictionaries)
decks = data.get("table", [])
print(f"Found {len(decks)} decks")

# Convert to DataFrame and export
df = pd.json_normalize(decks)
df.to_csv("ojer_axonil_optimized_decks.csv", index=False)
print("✅ Saved to ojer_axonil_optimized_decks.csv")
