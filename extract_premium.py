import json

def extract_premium():
    with open('data/bras_deals.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    premium_deals = data.get('premium_deals', [])
    if not premium_deals:
        print("No premium deals field found yet.")
        return

    premium_output = {
        "metadata": {
            "source": "India Multi-Store Consolidated - Premium",
            "timestamp": data['metadata']['timestamp'],
            "stats": {
                "total_extracted": data['metadata']['stats']['total_extracted'],
                "premium_count": len(premium_deals),
                "duration_seconds": data['metadata']['stats']['duration_seconds']
            }
        },
        "deals": premium_deals
    }
    
    # Remove premium_deals from original
    del data['premium_deals']
    
    with open('data/premium_bras.json', 'w', encoding='utf-8') as f:
        json.dump(premium_output, f, indent=2)
        
    with open('data/bras_deals.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    extract_premium()
    print("Successfully separated premium_bras.json")
