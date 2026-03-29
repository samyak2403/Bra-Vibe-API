import random

# --- SCRAPER SETTINGS ---
MIN_DISCOUNT = 20
OUTPUT_FILE = "data/bras_deals.json"
PREMIUM_OUTPUT_FILE = "data/premium_bras.json"
ALL_OUTPUT_FILE = "data/all_bras.json"
MAX_WORKERS = 3  # Reduced for better bypass (less aggressive)
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 4
MAX_PAGES = 2  # Number of pages to scrape per store/query

# --- SEARCH QUERIES ---
# Multiple search queries per store for broader results
SEARCH_QUERIES = {
    "amazon": [
        "bras+for+women",
        "t-shirt+bra",
        "push+up+bra",
        "sports+bra+women",
        "bralette+for+women",
        "padded+bra",
        "strapless+bra",
        "bras+discount",
    ],
    "flipkart": [
        "bras+for+women",
        "t-shirt+bra",
        "push+up+bra",
        "sports+bra",
        "bralette",
        "padded+bra",
        "strapless+bra",
        "bras+discount",
    ],
    "myntra": [
        "bras",
        "t-shirt bra",
        "push up bra",
        "sports bra",
        "bralette",
        "padded bra",
        "strapless bra",
    ],
}

# --- BRA CATEGORIES ---
BRA_CATEGORIES = [
    "T-Shirt Bra", "Full Coverage Bra", "Seamless Bra", "Minimizer Bra", 
    "Unlined Bra", "Lined Bra", "Underwire Bra", "Wireless Bra", 
    "Push-Up Bra", "Padded Bra", "Balconette Bra", "Plunge Bra", 
    "Sports Bra", "Maternity Bra", "Nursing Bra", "Post-Surgery Bra", 
    "Sleep Bra", "Strapless Bra", "Backless Bra", "Convertible Bra", 
    "Multiway Bra", "Halter Bra", "Stick-On Bra", "Lace Bra", 
    "Bralette", "Longline Bra", "Cage Bra", "Sheer Bra", 
    "Full Cup Bra", "Demi Cup Bra", "Half Cup Bra", "Quarter Cup Bra", 
    "Front Closure Bra", "Trainer Bra", "Silicone Bra", 
    "Mastectomy Bra", "Cooling Bra", "Posture Corrector Bra"
]

# Category mapping for classification (Keywords)
CATEGORY_KEYWORDS = {
    "T-Shirt Bra": ["t-shirt", "tshirt", "t shirt"],
    "Full Coverage Bra": ["full coverage", "full cup"],
    "Seamless Bra": ["seamless", "no show", "laser cut"],
    "Minimizer Bra": ["minimizer", "minimize"],
    "Unlined Bra": ["unlined", "non-padded", "non padded", "no pad"],
    "Lined Bra": ["lined", "lightly lined"],
    "Underwire Bra": ["underwire", "wired"],
    "Wireless Bra": ["wireless", "non-wired", "wire-free", "wirefree"],
    "Push-Up Bra": ["push-up", "pushup", "push up", "level 1", "level 2", "level 3"],
    "Padded Bra": ["padded", "padding"],
    "Balconette Bra": ["balconette", "balcony"],
    "Plunge Bra": ["plunge"],
    "Sports Bra": ["sports", "active", "workout", "gym", "impact"],
    "Maternity Bra": ["maternity"],
    "Nursing Bra": ["nursing", "feeding"],
    "Post-Surgery Bra": ["post-surgery", "post surgery", "recovery"],
    "Sleep Bra": ["sleep", "night", "leisure"],
    "Strapless Bra": ["strapless"],
    "Backless Bra": ["backless"],
    "Convertible Bra": ["convertible"],
    "Multiway Bra": ["multiway", "multi-way"],
    "Halter Bra": ["halter"],
    "Stick-On Bra": ["stick-on", "stickon", "adhesive", "nubra"],
    "Lace Bra": ["lace", "lacy"],
    "Bralette": ["bralette"],
    "Longline Bra": ["longline", "long line"],
    "Cage Bra": ["cage"],
    "Sheer Bra": ["sheer", "transparent"],
    "Full Cup Bra": ["full cup"],
    "Demi Cup Bra": ["demi cup", "demi"],
    "Half Cup Bra": ["half cup"],
    "Quarter Cup Bra": ["quarter cup"],
    "Front Closure Bra": ["front closure", "front open"],
    "Trainer Bra": ["trainer", "beginner", "starter"],
    "Silicone Bra": ["silicone"],
    "Mastectomy Bra": ["mastectomy"],
    "Cooling Bra": ["cooling", "breathable"],
    "Posture Corrector Bra": ["posture", "corrector"]
}

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
        "url": "https://www.amazon.in/s",
        "name": "Amazon India",
        "selector": 'div[data-component-type="s-search-result"]'
    },
    "flipkart": {
        "url": "https://flipkart.com/api/4/page/fetch",
        "search_url": "https://www.flipkart.com/search",
        "name": "Flipkart",
    },
    "myntra": {
        "url": "https://www.myntra.com/gateway/v2/search/",
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
            "pageSize": "50",
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
            "pageSize": "50",
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
            "PageSize": "50",
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
