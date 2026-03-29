import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.bras_scraper import StoreScrapers
import json

def preview():
    scraper = StoreScrapers()
    print("Fetching sample payload from Myntra (JSON Extraction)...")
    res = scraper.scrape_myntra()
    if res:
        print("\n--- SAMPLE EXTRACTED JSON RECORD ---")
        print(json.dumps(res[0], indent=2))
    else:
        print("No results returned.")

if __name__ == "__main__":
    preview()
