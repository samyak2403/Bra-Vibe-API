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
        "url": "https://www.amazon.in/s?k=bras+discount",
        "name": "Amazon India",
        "selector": 'div[data-component-type="s-search-result"]'
    },
    "flipkart": {
        "url": "https://www.flipkart.com/search?q=bras+discount",
        "name": "Flipkart",
        "selector": "div._1AtVbE, div._2k03n8, div._4ddW_X"
    },
    "myntra": {
        "url": "https://www.myntra.com/bras?f=Discount_Range%3A20.0",
        "name": "Myntra"
    },
    "ajio": {
        "url": "https://www.ajio.com/api/category/830311004?size=45&start=0",
        "name": "Ajio"
    },
    "zivame": {
        "url": "https://www.zivame.com/lingerie/bras.html",
        "name": "Zivame",
        "selector": ".product-item"
    },
    "clovia": {
        "url": "https://www.clovia.com/web/api/v1/category-products-desktop/bras/s/",
        "name": "Clovia"
    },
    "nykaa": {
        "url": "https://www.nykaafashion.com/rest/appapi/V2/categories/products",
        "name": "Nykaa Fashion",
        "categoryId": "3947"
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
