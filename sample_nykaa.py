import sys
import os
import json
# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from bras_scraper import StoreScrapers

def get_sample():
    scraper = StoreScrapers()
    print("Extracting 1 item from Nykaa Fashion to show the new data structure...")
    # Nykaa's search URL
    try:
        results = scraper.scrape_nykaa()
        if results:
            print("\n✅ SUCCESS: Found", len(results), "items.")
            print("\n--- SAMPLE ITEM WITH SIZES & COLORS ---")
            # Find an item that has sizes/colors for better proof
            sample = results[0]
            for r in results:
                if r.get('sizes_available') or r.get('colors_available'):
                    sample = r
                    break
            print(json.dumps(sample, indent=2))
        else:
            print("❌ No results found on Nykaa.")
    except Exception as e:
        print(f"❌ Error during Nykaa scrape: {e}")

if __name__ == "__main__":
    get_sample()
