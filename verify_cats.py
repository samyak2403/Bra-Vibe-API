import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

import config

def classify(name):
    name_lower = name.lower()
    found = []
    for cat, keywords in config.CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                found.append(cat)
                break
    return found

def main():
    try:
        with open('data/all_bras.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('deals', [])
        print(f"Total items to categorize: {len(items)}")
        
        stats = {}
        categorized_count = 0
        
        for item in items:
            cats = classify(item.get('name', ''))
            if cats:
                categorized_count += 1
                cat = cats[0]
                stats[cat] = stats.get(cat, 0) + 1
                item['category'] = cat
                item['category_all'] = cats
            else:
                stats['Uncategorized'] = stats.get('Uncategorized', 0) + 1
        
        print("\n--- CATEGORY SUMMARY ---")
        sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_stats:
            print(f"  {cat:25}: {count}")
            
        print(f"\nTotal Categorized: {categorized_count} / {len(items)} ({round(categorized_count/len(items)*100, 2)}%)")
        
        # Save updated data
        with open('data/all_bras.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print("\nUpdated data/all_bras.json with new categories.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
