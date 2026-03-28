import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime
import re
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from curl_cffi import requests as curl_requests
import config

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("BraScraper")

class ScraperBase:
    """Base class providing shared utilities for all scrapers."""
    def __init__(self):
        self.session = curl_requests.Session(impersonate="chrome110")

    def get_headers(self, site="common") -> Dict[str, str]:
        ua = config.get_random_ua()
        # Extract OS/Platform for Sec-CH-UA
        platform = "Windows"
        if "Macintosh" in ua: platform = "macOS"
        elif "Linux" in ua: platform = "Linux"

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="122", "Chromium";v="122"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": f'"{platform}"',
            "Cache-Control": "max-age=0",
        }
        
        # Site-specific overrides
        if "amazon" in site:
            headers.update({
                "Host": "www.amazon.in",
                "Referer": "https://www.google.com/",
                "Sec-Fetch-Site": "cross-site",
                "Upgrade-Insecure-Requests": "1"
            })
        elif "flipkart" in site:
             headers.update({
                 "Referer": "https://www.flipkart.com/",
                 "x-user-agent-platform": "Desktop",
                 "x-user-agent-client": "Web",
                 "Upgrade-Insecure-Requests": "1"
             })
        elif site in ["ajio", "nykaa", "clovia"]:
             headers.update({
                 "Accept": "application/json, text/plain, */*",
                 "Sec-Fetch-Mode": "cors",
                 "Sec-Fetch-Site": "same-origin",
                 "X-Requested-With": "XMLHttpRequest"
             })
             if site == "ajio":
                 headers["X-Ajio-App-Version-Name"] = "1.0.0"
                 headers["Referer"] = "https://www.ajio.com/s/bras-4621-72911"
             elif site == "nykaa":
                 headers["domain"] = "NYKAA_FASHION"
                 headers["Referer"] = "https://www.nykaafashion.com/bras/c/595"
             elif site == "clovia":
                 headers["Referer"] = "https://www.clovia.com/bras/s/"

        return headers

        return headers

    def safe_request(self, url: str, site: str) -> str:
        """Fetch content with professional retry logic and session management."""
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                headers = self.get_headers(site)
                # Randomized delay with jitter
                delay = random.uniform(2, 6) + (attempt * 2)
                time.sleep(delay)
                
                # Use impersonated session for better bypass
                response = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    low_text = response.text.lower()
                    if "captcha" in low_text or "robot check" in low_text:
                        logger.warning(f"[{site.upper()}] CAPTCHA/Bot-Check detected. Attempt {attempt+1}")
                        continue
                    return response.text
                
                if response.status_code in [403, 503, 410]:
                    logger.warning(f"[{site.upper()}] Blocked ({response.status_code}) on attempt {attempt+1}")
                    time.sleep(pow(2, attempt + 2) + random.random())
                else:
                    logger.debug(f"[{site.upper()}] Status {response.status_code}")
            
            except Exception as e:
                logger.error(f"[{site.upper()}] Error: {str(e)[:100]}")
            
        return ""

    def pre_flight(self, site: str, url: str):
        """Standard 'warm-up' request to establish cookies/sessions."""
        try:
            logger.debug(f"[{site.upper()}] Pre-flight session warm-up...")
            self.session.get(url, headers=self.get_headers(site), timeout=10)
        except: pass

    def clean_price(self, val: Any) -> float:
        if not val: return 0.0
        try:
            # Handle list-like or dict-like price inputs
            if isinstance(val, (list, tuple)): val = val[0]
            if isinstance(val, dict): val = val.get('amount', val.get('value', 0))
            return float(re.sub(r'[^\d.]', '', str(val).replace(',', '')))
        except:
            return 0.0

    def calculate_discount(self, original: float, discounted: float) -> int:
        if original > 0 and discounted > 0 and original > discounted:
            return int(((original - discounted) / original) * 100)
        return 0

    def normalize(self, raw: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Maps raw data to the unified production schema."""
        original = self.clean_price(raw.get('price_original'))
        discounted = self.clean_price(raw.get('price_discounted'))
        
        # Calculate discount if not provided
        disc = raw.get('discount_percentage')
        if not disc or not isinstance(disc, (int, float)):
             if original > 0 and discounted > 0 and original > discounted:
                 disc = int(((original - discounted) / original) * 100)
             else:
                 disc = 0
        else:
            disc = int(self.clean_price(disc))

        return {
            "product_id": str(raw.get('product_id', '')),
            "name": str(raw.get('name', 'N/A')).strip(),
            "brand": str(raw.get('brand', 'N/A')).strip(),
            "category": "Bras",
            "price_original": original,
            "price_discounted": discounted,
            "discount_percentage": disc,
            "rating": str(raw.get('rating', 'N/A')),
            "review_count": int(self.clean_price(raw.get('review_count', 0))),
            "sizes_available": raw.get('sizes_available', []),
            "colors_available": raw.get('colors_available', []),
            "image_url": str(raw.get('image_url', '')),
            "product_url": str(raw.get('product_url', '')),
            "website_source": source,
            "stock_status": str(raw.get('stock_status', 'In Stock')),
            "scraped_at": datetime.now().isoformat()
        }

# --- STORE SCRAPERS ---

class StoreScrapers(ScraperBase):
    def scrape_amazon(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Amazon India...")
        conf = config.STORES['amazon']
        # Amazon bypass: Establish session context first
        self.pre_flight("amazon", "https://www.amazon.in/")
        
        # Add realistic search parameters
        search_url = f"{conf['url']}&ref=nb_sb_noss"
        html = self.safe_request(search_url, "amazon")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        # Professional Amazon selectors
        products = soup.select('div[data-component-type="s-search-result"], .s-result-item[data-asin]')
        results = []

        for item in products:
            try:
                asin = item.get('data-asin')
                if not asin: continue

                name_tag = item.select_one('h2 a span, .a-size-base-plus.a-color-base.a-text-normal')
                if not name_tag: continue
                
                low_name = name_tag.text.lower()
                if "bra" not in low_name: continue 
                
                # Prices can be in multiple locations
                p_disc_tag = item.select_one('.a-price .a-offscreen')
                p_disc = self.clean_price(p_disc_tag.text if p_disc_tag else 0)
                
                p_orig_tag = item.select_one('.a-price.a-text-price span.a-offscreen')
                p_orig = self.clean_price(p_orig_tag.text if p_orig_tag else p_disc)
                
                image_tag = item.select_one('img.s-image')
                link_tag = item.select_one('h2 a, a.a-link-normal.s-no-outline')
                
                raw = {
                    "product_id": asin,
                    "name": name_tag.text.strip(),
                    "brand": name_tag.text.split(' ')[0],
                    "price_original": p_orig,
                    "price_discounted": p_disc,
                    "image_url": image_tag.get('src') if image_tag else "",
                    "product_url": "https://www.amazon.in" + link_tag.get('href') if link_tag else "",
                }
                results.append(self.normalize(raw, conf['name']))
            except Exception as e:
                logger.debug(f"Amazon item error: {e}")
        return results

    def scrape_flipkart(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Flipkart...")
        conf = config.STORES['flipkart']
        self.pre_flight("flipkart", "https://www.flipkart.com/")
        
        # Use a more natural search URL
        url = conf['url']
        html = self.safe_request(url, "flipkart")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        # Grid items often use these classes
        items = soup.select('div[data-id], ._1AtVbE, ._4ddW_X')
        results = []

        for item in items:
            try:
                # Common Flipkart selectors for title and brand
                brand_tag = item.select_one('div._2Wk9SZ, ._2Wk9SZ')
                name_tag = item.select_one('a.IRpwTa, a.s1Q9rs, ._2mylT6')
                if not name_tag: continue
                
                prices = item.select('div._30jeq3, ._30jeq3') # Discounted price
                orig_prices = item.select('div._3I9_ca, ._3I9_ca') # MRP
                
                raw = {
                    "product_id": item.get('data-id') or random.getrandbits(32),
                    "name": name_tag.text.strip(),
                    "brand": brand_tag.text.strip() if brand_tag else "N/A",
                    "price_original": orig_prices[0].text if orig_prices else 0,
                    "price_discounted": prices[0].text if prices else 0,
                    "discount_percentage": item.select_one('div._3Ay6Wh, ._3Ay6Wh').text if item.select_one('div._3Ay6Wh, ._3Ay6Wh') else None,
                    "rating": item.select_one('div._3LWZlK, ._3LWZlK').text if item.select_one('div._3LWZlK, ._3LWZlK') else "N/A",
                    "image_url": item.select_one('img').get('src') if item.select_one('img') else "",
                    "product_url": "https://www.flipkart.com" + name_tag.get('href'),
                }
                results.append(self.normalize(raw, conf['name']))
            except Exception as e:
                logger.debug(f"Flipkart item error: {e}")
        return results

    def scrape_myntra(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Myntra...")
        conf = config.STORES['myntra']
        # Fixed URL: Use search query for more items
        url = "https://www.myntra.com/bras?q=bras"
        html = self.safe_request(url, "myntra")
        if not html: return []
        
        # Look for window.__myx or window.__myx_navigationData__
        match = re.search(r'window\[".__myx"\]\s*=\s*({.*?});|window\.__myx\s*=\s*({.*?});', html)
        if not match: 
            match = re.search(r'window\.__myx_navigationData__\s*=\s*({.*?});', html)
        if not match:
             # Check for raw JSON in a script tag fallback
             match = re.search(r'<script id="__myx">.*?({.*?})</script>', html, re.DOTALL)
            
        if not match: return []
        try:
            # Get the group that matched
            data_str = match.group(1) or match.group(2)
            data = json.loads(data_str)
            search_data = data.get('searchData', {}) or data
            products = search_data.get('results', {}).get('products', [])
            if not products and 'products' in data: # Direct list
                products = data['products']
                
            return [self.normalize({
                "product_id": p.get('productId'),
                "name": p.get('productName'),
                "brand": p.get('brand'),
                "price_original": p.get('mrp'),
                "price_discounted": p.get('price'),
                "rating": p.get('rating'),
                "review_count": p.get('ratingCount'),
                "image_url": p.get('searchImage'),
                "product_url": "https://www.myntra.com/" + p.get('landingPageUrl'),
            }, conf['name']) for p in products]
        except Exception as e:
            logger.error(f"Myntra parse error: {e}")
            return []

    def scrape_ajio(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Ajio...")
        conf = config.STORES['ajio']
        try:
            # Ajio Bra Category ID: 830311004
            url = "https://www.ajio.com/api/category/830311004?size=45&start=0"
            self.pre_flight("ajio", "https://www.ajio.com/s/bras-4621-72911")
            
            headers = self.get_headers("ajio")
            headers.update({
                "Referer": "https://www.ajio.com/s/bras-4621-72911",
                "Accept": "application/json, text/plain, */*"
            })
            
            html = self.safe_request(url, "ajio")
            if not html: return []

            try:
                data = json.loads(html)
                products = data.get('products', [])
                if not products and 'data' in data: products = data['data'].get('products', [])
                
                return [self.normalize({
                    "product_id": p.get('code'),
                    "name": p.get('name'),
                    "brand": p.get('brandName'),
                    "price_original": p.get('wasPriceData', {}).get('value'),
                    "price_discounted": p.get('price', {}).get('value'),
                    "image_url": p.get('images', [{}])[0].get('url'),
                    "product_url": "https://www.ajio.com" + p.get('url'),
                }, conf['name']) for p in products]
            except json.JSONDecodeError:
                logger.warning("Ajio API returned non-JSON content.")
                return []
                
        except Exception as e:
            logger.error(f"Ajio API error: {e}")
        return []

    def scrape_zivame(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Zivame...")
        conf = config.STORES['zivame']
        # Zivame bypass: Pre-landing and then scrape
        self.pre_flight("zivame", "https://www.zivame.com/")
        html = self.safe_request(conf['url'], "zivame")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.product-item')
        results = []
        for item in items:
            try:
                name_tag = item.select_one('.product-item-link')
                if not name_tag: continue
                
                price_disc = item.select_one('.price-wrapper .price')
                price_orig = item.select_one('.old-price .price')
                
                results.append(self.normalize({
                    "product_id": item.get('data-product-id') or random.getrandbits(32),
                    "name": name_tag.text.strip(),
                    "brand": "Zivame",
                    "price_original": price_orig.text if price_orig else (price_disc.text if price_disc else 0),
                    "price_discounted": price_disc.text if price_disc else 0,
                    "image_url": item.select_one('img.product-image-photo').get('src') if item.select_one('img.product-image-photo') else "",
                    "product_url": name_tag.get('href'),
                }, conf['name']))
            except Exception as e:
                logger.debug(f"Zivame item error: {e}")
        return results

    def scrape_clovia(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Clovia...")
        conf = config.STORES['clovia']
        # Clovia now uses an internal API
        # Clovia now uses an internal API identified by browser verification
        api_url = f"{conf['url']}?path=/bras/s/&page=1&active_target=-tab2"
        
        headers = self.get_headers("clovia")
        html = self.safe_request(api_url, "clovia")
        if not html: return []
        
        try:
            data = json.loads(html)
            # The API returns data nested under 'data' -> 'products'
            products = data.get('data', {}).get('products', [])
            if not products and 'products' in data: products = data['products']
            
            return [self.normalize({
                "product_id": str(p.get('id') or p.get('sku')),
                "name": p.get('name'),
                "brand": "Clovia",
                "price_original": p.get('mrp'),
                "price_discounted": p.get('offer_price') or p.get('price_actual') or p.get('price'),
                "image_url": p.get('image_url') or p.get('imageUrl'),
                "product_url": "https://www.clovia.com" + p.get('product_url', ''),
            }, conf['name']) for p in products if p.get('name')]
        except Exception as e:
            logger.error(f"Clovia API parse error: {e}")
            return []

    def scrape_nykaa(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Nykaa Fashion...")
        conf = config.STORES['nykaa']
        try:
            # Nykaa V2 Category API requires categoryId
            url = f"{conf['url']}?categoryId={conf['categoryId']}&PageSize=30&currentPage=1&sort=popularity&filter_format=v2"
            
            self.pre_flight("nykaa", "https://www.nykaafashion.com/bras/c/595")
            headers = self.get_headers("nykaa")
            
            resp = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                # Nykaa data structure: data -> products
                products = data.get('data', {}).get('products', [])
                
                return [self.normalize({
                    "product_id": p.get('id'),
                    "name": p.get('name'),
                    "brand": p.get('brandName') or p.get('brand_name'),
                    "price_original": p.get('mrp'),
                    "price_discounted": p.get('price'),
                    "discount_percentage": p.get('discount'),
                    "image_url": p.get('imageUrl') or p.get('image_url'),
                    "product_url": "https://www.nykaafashion.com" + p.get('productUrl', ''),
                }, conf['name']) for p in products if p.get('name')]
            else:
                logger.warning(f"Nykaa API failed with status {resp.status_code}")
        except Exception as e:
            logger.error(f"Nykaa API error: {e}")
        return []

# --- PRODUCTION RUNNER ---

def main():
    start_time = time.time()
    logger.info("Initializing Production Scraper Engine...")
    
    scrapers = StoreScrapers()
    all_data = []
    
    # List of scraping methods
    tasks = [
        scrapers.scrape_amazon,
        scrapers.scrape_flipkart,
        scrapers.scrape_myntra,
        scrapers.scrape_ajio,
        scrapers.scrape_zivame,
        scrapers.scrape_clovia,
        scrapers.scrape_nykaa
    ]

    # Concurrent Execution
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_store = {executor.submit(task): task.__name__ for task in tasks}
        for future in as_completed(future_to_store):
            store_name = future_to_store[future]
            try:
                data = future.result()
                all_data.extend(data)
                logger.info(f"Finished {store_name}: Found {len(data)} items")
            except Exception as e:
                logger.error(f"Thread error in {store_name}: {e}")

    # --- POST-PROCESSING ---
    # 1. Higher-level Filtering
    filtered = [p for p in all_data if p['discount_percentage'] >= config.MIN_DISCOUNT]
    
    # 2. Strict Deduplication
    seen = set()
    deduped = []
    for p in filtered:
        # Generate hashable key
        norm_name = re.sub(r'[^a-zA-Z0-9]', '', p['name'].lower())
        key = f"{p['brand'].lower()}_{norm_name}"
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    # 3. Final Sorting
    final_deals = sorted(deduped, key=lambda x: x['discount_percentage'], reverse=True)

    # --- EXPORT ---
    output = {
        "metadata": {
            "source": "India Multi-Store Consolidated",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_extracted": len(all_data),
                "total_filtered": len(filtered),
                "final_count": len(final_deals),
                "duration_seconds": round(time.time() - start_time, 2)
            }
        },
        "deals": final_deals
    }

    try:
        with open(config.OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        logger.info(f"Report generated: {config.OUTPUT_FILE} ({len(final_deals)} deals)")
    except Exception as e:
        logger.error(f"Failed to save output: {e}")

if __name__ == "__main__":
    main()
