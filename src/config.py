import random

# --- SCRAPER SETTINGS ---
MIN_DISCOUNT = 20
OUTPUT_FILE = "data/bras_deals.json"
MAX_WORKERS = 3  # Reduced for better bypass (less aggressive)
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 4

# --- TARGET STORES ---
STORES = {
    "amazon": {
        "url": "https://www.amazon.in/s?k=bras+for+women+discount",
        "name": "Amazon India",
        "selector": 'div[data-component-type="s-search-result"]'
    },
    "flipkart": {
        "url": "https://www.flipkart.com/search?q=bras+for+women+discount",
        "name": "Flipkart",
        "selector": "div._1AtVbE, div._2k03n8, div._4ddW_X"
    },
    "myntra": {
        "url": "https://www.myntra.com/bras?f=Discount_Range%3A20.0",
        "name": "Myntra"
    },
    "ajio": {
        "url": "https://www.ajio.com/api/query/v1/search?text=bras&currentPage=0&pageSize=45",
        "name": "Ajio"
    },
    "zivame": {
        "url": "https://www.zivame.com/lingerie/bras.html",
        "name": "Zivame",
        "selector": ".product-item"
    },
    "clovia": {
        "url": "https://www.clovia.com/bras/s/",
        "name": "Clovia",
        "selector": ".product-list-item"
    },
    "nykaa": {
        "url": "https://www.nykaafashion.com/api/gateway-fashion/v1/search/search-results?q=bras",
        "name": "Nykaa Fashion"
    }
}

# --- BROWSER SETTINGS ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

def get_random_ua():
    return random.choice(USER_AGENTS)
