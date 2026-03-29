import random

# --- SCRAPER SETTINGS ---
MIN_DISCOUNT = 20
OUTPUT_FILE = "data/bras_deals.json"
PREMIUM_OUTPUT_FILE = "data/premium_bras.json"
ALL_OUTPUT_FILE = "data/all_bras.json"
MAX_WORKERS = 3  # Reduced for better bypass (less aggressive)
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 4

# --- PREMIUM BRAS CONFIG ---
PREMIUM_MIN_PRICE = 500  # Minimum discounted price for premium classification
PREMIUM_BRANDS = [
    # International Premium
    "wacoal", "triumph", "calvin klein", "ck", "victoria's secret", "victoria",
    "la senza", "marks & spencer", "m&s", "hanes", "bali", "maidenform",
    "playtex", "vanity fair", "wonderbra", "chantelle", "simone perele",
    "freya", "panache", "fantasie", "elomi", "gossard", "passionata",
    
    # Indian Premium
    "amante", "enamor", "lovable", "jockey", "clovia", "zivame",
    "soie", "shyaway", "inner sense", "mod & shy", "prettysecrets",
    "parfait", "susie", "bodycare", "floret", "trylo", "groversons",
    "juliet", "kalyani", "nykd", "nykaa", "macrowoman", "candyskin",
    
    # Sports / Athleisure Premium  
    "nike", "adidas", "puma", "under armour", "reebok", "fila",
    "decathlon", "domyos", "lululemon",
    
    # Designer / Luxury
    "la perla", "agent provocateur", "fleur du mal", "cosabella",
    "hanro", "wolford", "stella mccartney", "dkny", "tommy hilfiger",
    "gap", "h&m", "hunkemoller",
]

# --- TARGET STORES ---
STORES = {
    "amazon": {
        "url": "https://www.amazon.in/s?k=bras+for+women",
        "name": "Amazon India",
        "selector": 'div[data-component-type="s-search-result"]'
    },
    "flipkart": {
        "url": "https://flipkart.com/api/4/page/fetch",
        "search_url": "https://www.flipkart.com/search?q=bras+for+women&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&page=1",
        "name": "Flipkart",
    },
    "myntra": {
        "url": "https://www.myntra.com/gateway/v2/search/bras",
        "browse_url": "https://www.myntra.com/bras",
        "name": "Myntra"
    },
    "ajio": {
        "url": "https://www.ajio.com/api/category/830311004",
        "browse_url": "https://www.ajio.com/s/bras-4621-72911",
        "name": "Ajio",
        "params": {
            "fields": "CUSTOM_CLASSIFICATION",
            "currentPage": "0",
            "pageSize": "45",
            "platform": "site",
            "showAdsOnNextPage": "true",
            "is_498": "false",
            "gridColumns": "3",
            "advfilter": "true"
        }
    },
    "zivame": {
        "url": "https://www.zivame.com/zmapi/v2/search",
        "browse_url": "https://www.zivame.com/lingerie/bras.html",
        "name": "Zivame",
        "params": {
            "searchTerm": "bras",
            "page": "0",
            "pageSize": "40",
            "sort": "popularity"
        }
    },
    "clovia": {
        "url": "https://www.clovia.com/web/api/v1/category-products-desktop",
        "browse_url": "https://www.clovia.com/bras/s/",
        "name": "Clovia",
        "params": {
            "path": "/bras/s/",
            "page": "1",
            "active_target": "-tab2"
        }
    },
    "nykaa": {
        "url": "https://www.nykaafashion.com/rest/appapi/V2/categories/products",
        "browse_url": "https://www.nykaafashion.com/bras/c/595",
        "name": "Nykaa Fashion",
        "categoryId": "595",
        "params": {
            "categoryId": "595",
            "PageSize": "30",
            "currentPage": "1",
            "sort": "popularity",
            "filter_format": "v2"
        }
    }
}

# --- BROWSER SETTINGS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def get_random_ua():
    return random.choice(USER_AGENTS)
