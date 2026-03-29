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
import threading
from urllib.parse import quote

from curl_cffi import requests as curl_requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# Global lock for undetected-chromedriver initialization to avoid patching conflicts
uc_lock = threading.Lock()

class ScraperBase:
    """Base class providing shared utilities for all scrapers."""
    def __init__(self):
        self.session = curl_requests.Session(impersonate="chrome110")

    def get_headers(self, site="common") -> Dict[str, str]:
        ua = config.get_random_ua()
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
                 "Upgrade-Insecure-Requests": "1"
             })
        elif site in ["ajio", "nykaa", "clovia", "zivame", "myntra"]:
             headers.update({
                 "Accept": "application/json, text/plain, */*",
                 "Sec-Fetch-Mode": "cors",
                 "Sec-Fetch-Dest": "empty",
                 "Sec-Fetch-Site": "same-origin",
                 "X-Requested-With": "XMLHttpRequest"
             })
             if site == "ajio":
                 headers["Referer"] = "https://www.ajio.com/s/bras-4621-72911"
                 headers["Origin"] = "https://www.ajio.com"
             elif site == "nykaa":
                 headers["domain"] = "NYKAA_FASHION"
                 headers["Referer"] = "https://www.nykaafashion.com/bras/c/595"
                 headers["Origin"] = "https://www.nykaafashion.com"
             elif site == "clovia":
                 headers["Referer"] = "https://www.clovia.com/bras/s/"
                 headers["Origin"] = "https://www.clovia.com"
             elif site == "zivame":
                 headers["Referer"] = "https://www.zivame.com/lingerie/bras.html"
                 headers["Origin"] = "https://www.zivame.com"
             elif site == "myntra":
                 headers["Referer"] = "https://www.myntra.com/bras"
                 headers["Origin"] = "https://www.myntra.com"
                 headers["x-myntraweb"] = "Yes"
                 headers["x-meta-app"] = "channel=web"

        return headers

    def safe_request(self, url: str, site: str, params: dict = None) -> str:
        """Fetch content with professional retry logic and session management."""
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                headers = self.get_headers(site)
                delay = random.uniform(2, 6) + (attempt * 2)
                time.sleep(delay)
                
                response = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT, params=params)
                
                if response.status_code == 200:
                    low_text = response.text[:2000].lower()
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

    def safe_request_json(self, url: str, site: str, params: dict = None) -> dict:
        """Fetch JSON directly from an API endpoint with retry logic."""
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                headers = self.get_headers(site)
                delay = random.uniform(1.5, 4) + (attempt * 1.5)
                time.sleep(delay)
                
                response = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT, params=params)
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        logger.warning(f"[{site.upper()}] Non-JSON response on attempt {attempt+1}")
                        continue
                
                if response.status_code in [403, 503, 429]:
                    logger.warning(f"[{site.upper()}] Blocked ({response.status_code}) on attempt {attempt+1}")
                    time.sleep(pow(2, attempt + 2) + random.random())
                else:
                    logger.debug(f"[{site.upper()}] Status {response.status_code}")
            
            except Exception as e:
                logger.error(f"[{site.upper()}] JSON request error: {str(e)[:100]}")
        
        return {}

    def pre_flight(self, site: str, url: str):
        """Standard 'warm-up' request to establish cookies/sessions."""
        try:
            logger.debug(f"[{site.upper()}] Pre-flight session warm-up...")
            self.session.get(url, headers=self.get_headers(site), timeout=10)
            time.sleep(random.uniform(1, 2))
        except: pass

    def clean_price(self, val: Any) -> float:
        if not val: return 0.0
        try:
            if isinstance(val, (list, tuple)): val = val[0]
            if isinstance(val, dict): val = val.get('amount', val.get('value', 0))
            return float(re.sub(r'[^\d.]', '', str(val).replace(',', '')))
        except:
            return 0.0

    def calculate_discount(self, original: float, discounted: float) -> int:
        if original > 0 and discounted > 0 and original > discounted:
            return int(((original - discounted) / original) * 100)
        return 0

    def enhance_image_quality(self, url: str) -> str:
        """Transforms thumbnail image URLs into high-quality image URLs."""
        if not url: return ""
        try:
            # Amazon
            if 'amazon' in url or 'media-amazon' in url:
                return re.sub(r'\._[a-zA-Z0-9_+%-]+_\.', '.', url)
            # Flipkart
            elif 'flixcart' in url:
                return re.sub(r'/image/\d+/\d+/', '/image/1080/1080/', url)
            # Myntra
            elif 'myntassets' in url or 'myntra' in url:
                url = re.sub(r'h_\d+', 'h_1080', url)
                url = re.sub(r'w_\d+', 'w_1080', url)
                url = re.sub(r'q_\d+', 'q_100', url)
                return url
            # Ajio
            elif 'ajio' in url:
                url = re.sub(r'w_\d+', 'w_1080', url)
                url = re.sub(r'h_\d+', 'h_1080', url)
                url = re.sub(r'/\d+W?x\d+H?/', '/1080x1080/', url)
                return url
            # Nykaa
            elif 'nykaa' in url:
                url = re.sub(r'tr=w-\d+', 'tr=w-1080', url)
                url = re.sub(r'tr=h-\d+', 'tr=h-1080', url)
                url = re.sub(r'tr=q-\d+', 'tr=q-100', url)
                return url
            # Clovia
            elif 'clovia' in url:
                return re.sub(r'/\d+x\d*/', '/1080x1080/', url)
            # Zivame
            elif 'zivame' in url:
                return re.sub(r'/\d+x(?:\d*/?)', '/1080x1080/', url)
        except Exception as e:
            logger.debug(f"Image enhancement error: {e}")
        return url

    def normalize(self, raw: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Maps raw data to the unified production schema."""
        original = self.clean_price(raw.get('price_original'))
        discounted = self.clean_price(raw.get('price_discounted'))
        
        disc = raw.get('discount_percentage')
        if not disc or not isinstance(disc, (int, float)):
             if original > 0 and discounted > 0 and original > discounted:
                 disc = int(((original - discounted) / original) * 100)
             else:
                 disc = 0
        else:
            disc = int(self.clean_price(disc))

        # --- CATEGORIZATION LOGIC ---
        name_lower = str(raw.get('name', '')).lower()
        category = "Bras" # Default
        
        # Try to find a more specific category from config.CATEGORY_KEYWORDS
        found_cats = []
        for cat, keywords in config.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in name_lower:
                    found_cats.append(cat)
                    break
        
        if found_cats:
            # Join multiple categories if found, or just take the first
            category = found_cats[0] 

        return {
            "product_id": str(raw.get('product_id', '')),
            "name": str(raw.get('name', 'N/A')).strip(),
            "brand": str(raw.get('brand', 'N/A')).strip(),
            "category": category,
            "category_all": found_cats, # Store all matches for better filtering
            "price_original": original,
            "price_discounted": discounted,
            "discount_percentage": disc,
            "rating": str(raw.get('rating', 'N/A')),
            "review_count": int(self.clean_price(raw.get('review_count', 0))),
            "sizes_available": raw.get('sizes_available', []),
            "colors_available": raw.get('colors_available', []),
            "image_url": self.enhance_image_quality(str(raw.get('image_url', ''))),
            "product_url": str(raw.get('product_url', '')),
            "website_source": source,
            "stock_status": raw.get('stock_status', 'In Stock'),
            "scraped_at": datetime.now().isoformat()
        }

# --- STORE SCRAPERS ---

class StoreScrapers(ScraperBase):
    
    def _dedup_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicates within a single store's results."""
        seen = set()
        unique = []
        for p in results:
            key = p.get('product_id', '') + '_' + p.get('name', '')[:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    def scrape_amazon(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Amazon India (multi-page, multi-query)...")
        conf = config.STORES['amazon']
        self.pre_flight("amazon", "https://www.amazon.in/")
        
        all_results = []
        queries = config.SEARCH_QUERIES.get('amazon', ['bras+for+women'])
        
        for query in queries:
            for page in range(1, config.MAX_PAGES + 1):
                search_url = f"{conf['url']}?k={query}&page={page}&ref=sr_pg_{page}"
                logger.info(f"  [AMAZON] Query='{query}' Page={page}")
                html = self.safe_request(search_url, "amazon")
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                products = soup.select('div[data-component-type="s-search-result"], .s-result-item[data-asin]')
                
                page_count = 0
                for item in products:
                    try:
                        asin = item.get('data-asin')
                        if not asin: continue

                        name_tag = item.select_one('h2 a span, .a-size-base-plus.a-color-base.a-text-normal')
                        if not name_tag: continue
                        
                        low_name = name_tag.text.lower()
                        if "bra" not in low_name: continue 
                        
                        p_disc_tag = item.select_one('.a-price .a-offscreen')
                        p_disc = self.clean_price(p_disc_tag.text if p_disc_tag else 0)
                        
                        p_orig_tag = item.select_one('.a-price.a-text-price span.a-offscreen')
                        p_orig = self.clean_price(p_orig_tag.text if p_orig_tag else p_disc)
                        
                        image_tag = item.select_one('img.s-image')
                        link_tag = item.select_one('h2 a, a.a-link-normal.s-no-outline')
                        
                        # Rating extraction
                        rating_tag = item.select_one('.a-icon-star-small .a-icon-alt, .a-icon-star .a-icon-alt')
                        rating = 'N/A'
                        if rating_tag:
                            rating_match = re.search(r'([\d.]+)', rating_tag.text)
                            if rating_match:
                                rating = rating_match.group(1)
                        
                        review_tag = item.select_one('.a-size-base.s-underline-text, a[href*="customerReviews"] span')
                        review_count = 0
                        if review_tag:
                            review_count = self.clean_price(review_tag.text)
                        
                        raw = {
                            "product_id": asin,
                            "name": name_tag.text.strip(),
                            "brand": name_tag.text.split(' ')[0],
                            "price_original": p_orig,
                            "price_discounted": p_disc,
                            "image_url": image_tag.get('src') if image_tag else "",
                            "product_url": "https://www.amazon.in" + link_tag.get('href') if link_tag else "",
                            "rating": rating,
                            "review_count": review_count,
                        }
                        all_results.append(self.normalize(raw, conf['name']))
                        page_count += 1
                    except Exception as e:
                        logger.debug(f"Amazon item error: {e}")
                
                logger.info(f"  [AMAZON] Page {page} query '{query}': {page_count} items")
                time.sleep(random.uniform(2, 4))  # Inter-page delay
        
        results = self._dedup_results(all_results)
        logger.info(f"[AMAZON] Total unique items: {len(results)}")
        return results

    def scrape_flipkart(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Flipkart (multi-page, multi-query)...")
        conf = config.STORES['flipkart']
        self.pre_flight("flipkart", "https://www.flipkart.com/")
        
        all_results = []
        queries = config.SEARCH_QUERIES.get('flipkart', ['bras+for+women'])
        
        for query in queries:
            for page in range(1, config.MAX_PAGES + 1):
                search_url = f"{conf.get('search_url', 'https://www.flipkart.com/search')}?q={query}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&page={page}"
                logger.info(f"  [FLIPKART] Query='{query}' Page={page}")
                html = self.safe_request(search_url, "flipkart")
                if not html:
                    continue
                
                page_results = []
                
                # Strategy 1: Parse JSON-LD embedded data
                try:
                    json_matches = re.findall(r'<script\s+id="jsonLD"\s+type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
                    for match in json_matches:
                        try:
                            ld_data = json.loads(match)
                            if isinstance(ld_data, dict) and ld_data.get('@type') == 'ItemList':
                                for item in ld_data.get('itemListElement', []):
                                    p = item.get('item', {})
                                    if not p.get('name'): continue
                                    offers = p.get('offers', {})
                                    raw = {
                                        "product_id": str(random.getrandbits(32)),
                                        "name": p.get('name', ''),
                                        "brand": p.get('brand', {}).get('name', 'N/A') if isinstance(p.get('brand'), dict) else str(p.get('brand', 'N/A')),
                                        "price_original": offers.get('highPrice', offers.get('price', 0)),
                                        "price_discounted": offers.get('lowPrice', offers.get('price', 0)),
                                        "image_url": p.get('image', [''])[0] if isinstance(p.get('image'), list) else str(p.get('image', '')),
                                        "product_url": p.get('url', ''),
                                    }
                                    page_results.append(self.normalize(raw, conf['name']))
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.debug(f"Flipkart JSON-LD parse error: {e}")
                
                # Strategy 2: Traditional HTML parsing
                if not page_results:
                    try:
                        soup = BeautifulSoup(html, 'html.parser')
                        product_links = soup.select('a[href*="/p/"]')
                        seen_urls = set()
                        
                        for link in product_links:
                            try:
                                href = link.get('href', '')
                                if href in seen_urls or '/p/' not in href:
                                    continue
                                seen_urls.add(href)
                                
                                card = link
                                for _ in range(5):
                                    parent = card.parent
                                    if parent and parent.name == 'div':
                                        card = parent
                                    else:
                                        break
                                
                                name_el = link.select_one('div[class*="col"] a[title]') or link.select_one('a[title]')
                                name = name_el.get('title', '') if name_el else ''
                                if not name:
                                    name_el = card.select_one('a[title]')
                                    name = name_el.get('title', '') if name_el else ''
                                if not name:
                                    divs = card.select('div')
                                    for d in divs:
                                        t = d.get_text(strip=True)
                                        if len(t) > 10 and len(t) < 200:
                                            name = t
                                            break
                                
                                if not name or 'bra' not in name.lower():
                                    continue
                                
                                price_texts = [el.get_text(strip=True) for el in card.select('div') if '₹' in el.get_text()]
                                prices = []
                                for pt in price_texts:
                                    cleaned = self.clean_price(pt)
                                    if cleaned > 0:
                                        prices.append(cleaned)
                                prices = sorted(set(prices))
                                
                                p_disc = prices[0] if prices else 0
                                p_orig = prices[-1] if len(prices) > 1 else p_disc
                                
                                img = card.select_one('img[src*="rukminim"], img[src*="flixcart"]')
                                img_url = img.get('src', '') if img else ''
                                
                                if name and (p_disc > 0 or p_orig > 0):
                                    raw = {
                                        "product_id": str(random.getrandbits(32)),
                                        "name": name,
                                        "brand": name.split(' ')[0] if name else "N/A",
                                        "price_original": p_orig,
                                        "price_discounted": p_disc,
                                        "image_url": img_url,
                                        "product_url": "https://www.flipkart.com" + href if not href.startswith('http') else href,
                                    }
                                    page_results.append(self.normalize(raw, conf['name']))
                            except Exception as e:
                                logger.debug(f"Flipkart item parse error: {e}")
                                continue
                    except Exception as e:
                        logger.debug(f"Flipkart HTML parse error: {e}")
                
                all_results.extend(page_results)
                logger.info(f"  [FLIPKART] Page {page} query '{query}': {len(page_results)} items")
                time.sleep(random.uniform(2, 4))
        
        results = self._dedup_results(all_results)
        logger.info(f"[FLIPKART] Total unique items: {len(results)}")
        return results

    def scrape_myntra(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Myntra (multi-page, multi-query)...")
        conf = config.STORES['myntra']
        self.pre_flight("myntra", "https://www.myntra.com/")
        
        all_results = []
        for query in config.SEARCH_QUERIES.get('myntra', ['bras']):
            encoded_query = quote(query)
            for page in range(1, config.MAX_PAGES + 1):
                # Strategy 1: Try the browse page with built-in pagination
                if query == "bras":
                    browse_url = f"https://www.myntra.com/bras?p={page}&rows=50"
                else:
                    search_term = quote(query.replace(' ', '-'))
                    browse_url = f"https://www.myntra.com/{search_term}?p={page}&rows=50"
                
                logger.info(f"  [MYNTRA] Query='{query}' Page={page}")
                html = self.safe_request(browse_url, "myntra")
                if not html:
                    continue
                
                page_results = []
                
                # Extract from window.__myx embedded data
                try:
                    patterns = [
                        r'window\.__myx\s*=\s*({.*?});\s*</script>',
                        r'window\["__myx"\]\s*=\s*({.*?});\s*</script>',
                        r'"searchData"\s*:\s*(\{.*?"products"\s*:\s*\[.*?\]\s*\})',
                    ]
                    
                    data = None
                    for pattern in patterns:
                        match = re.search(pattern, html, re.DOTALL)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                break
                            except json.JSONDecodeError:
                                continue
                    
                    if data:
                        products = []
                        if 'searchData' in data:
                            search_data = data['searchData']
                            if 'results' in search_data:
                                products = search_data['results'].get('products', [])
                            elif 'products' in search_data:
                                products = search_data['products']
                        elif 'products' in data:
                            products = data['products']
                        
                        for p in products:
                            try:
                                raw = {
                                    "product_id": str(p.get('productId', '')),
                                    "name": p.get('productName', ''),
                                    "brand": p.get('brand', 'N/A'),
                                    "price_original": p.get('mrp', 0),
                                    "price_discounted": p.get('price', 0),
                                    "discount_percentage": p.get('discountDisplayLabel', '').replace('% OFF', '').strip() if p.get('discountDisplayLabel') else None,
                                    "rating": p.get('rating', 'N/A'),
                                    "review_count": p.get('ratingCount', 0),
                                    "image_url": p.get('searchImage', ''),
                                    "product_url": "https://www.myntra.com/" + str(p.get('landingPageUrl', '')),
                                }
                                page_results.append(self.normalize(raw, conf['name']))
                            except Exception as e:
                                logger.debug(f"Myntra item error: {e}")
                except Exception as e:
                    logger.error(f"Myntra parse error: {e}")
                
                # Strategy 2: Try the gateway API directly
                if not page_results:
                    try:
                        api_url = conf['url'] + query.replace(' ', '%20')
                        params = {
                            "p": str(page),
                            "rows": "50",
                            "o": str((page - 1) * 50),
                            "plaession": "false",
                            "platform": "desktop",
                            "f": "",
                        }
                        data = self.safe_request_json(api_url, "myntra", params=params)
                        if data:
                            products = data.get('results', {}).get('products', [])
                            if not products:
                                products = data.get('products', [])
                            
                            for p in products:
                                try:
                                    raw = {
                                        "product_id": str(p.get('productId', '')),
                                        "name": p.get('productName', ''),
                                        "brand": p.get('brand', 'N/A'),
                                        "price_original": p.get('mrp', 0),
                                        "price_discounted": p.get('price', 0),
                                        "rating": p.get('rating', 'N/A'),
                                        "review_count": p.get('ratingCount', 0),
                                        "image_url": p.get('searchImage', ''),
                                        "product_url": "https://www.myntra.com/" + str(p.get('landingPageUrl', '')),
                                    }
                                    page_results.append(self.normalize(raw, conf['name']))
                                except Exception as e:
                                    logger.debug(f"Myntra API item error: {e}")
                    except Exception as e:
                        logger.error(f"Myntra API error: {e}")
                
                all_results.extend(page_results)
                logger.info(f"  [MYNTRA] Page {page} query '{query}': {len(page_results)} items")
                time.sleep(random.uniform(2, 4))
        
        results = self._dedup_results(all_results)
        logger.info(f"[MYNTRA] Total unique items: {len(results)}")
        return results

    def _parse_ajio_products(self, data: dict, conf: dict) -> List[Dict]:
        """Parse Ajio product data from API response."""
        results = []
        products = data.get('products', [])
        if not products and 'data' in data:
            products = data['data'].get('products', [])
        if not products and 'results' in data:
            products = data.get('results', [])
        
        for p in products:
            try:
                img_url = ''
                images = p.get('images', [])
                if images:
                    if isinstance(images[0], dict):
                        img_url = images[0].get('url', '')
                    else:
                        img_url = str(images[0])
                if not img_url:
                    img_url = p.get('imageUrl', '') or p.get('image', '')
                
                was_price = p.get('wasPriceData', {})
                if isinstance(was_price, dict):
                    orig_price = was_price.get('value', 0)
                else:
                    orig_price = was_price or 0
                
                curr_price = p.get('price', {})
                if isinstance(curr_price, dict):
                    disc_price = curr_price.get('value', 0)
                else:
                    disc_price = curr_price or 0
                
                raw = {
                    "product_id": str(p.get('code', '')),
                    "name": p.get('name', ''),
                    "brand": p.get('brandName', p.get('brand', 'N/A')),
                    "price_original": orig_price or p.get('mrp', 0),
                    "price_discounted": disc_price,
                    "discount_percentage": p.get('discount', None),
                    "image_url": img_url,
                    "product_url": "https://www.ajio.com" + str(p.get('url', '')),
                }
                results.append(self.normalize(raw, conf['name']))
            except Exception as e:
                logger.debug(f"Ajio item error: {e}")
        return results

    def scrape_ajio(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Ajio (Undetected-Chromedriver)...")
        conf = config.STORES['ajio']
        all_results = []
        
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            with uc_lock:
                driver = uc.Chrome(options=options, version_main=146)
            driver.get("https://www.ajio.com/s/bras-4621-72911")
            
            # Simple wait and scroll for Ajio
            time.sleep(5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Method 1: Extraction from window.__PRELOADED_STATE__
            preloaded_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if preloaded_match:
                try:
                    data = json.loads(preloaded_match.group(1))
                    
                    def find_products(d):
                        if isinstance(d, dict):
                            if 'items' in d and isinstance(d['items'], list) and len(d['items']) > 0 and 'productId' in str(d['items'][0]):
                                return d['items']
                            for v in d.values():
                                res = find_products(v)
                                if res: return res
                        elif isinstance(d, list):
                            for i in d:
                                res = find_products(i)
                                if res: return res
                        return None
                    
                    products = find_products(data)
                    if products:
                        for p in products:
                            try:
                                all_results.append(self.normalize({
                                    "name": p.get('name', ''),
                                    "brand": p.get('brandName', 'AJIO'),
                                    "price_discounted": float(p.get('price', {}).get('value', 0)),
                                    "price_original": float(p.get('wasPriceData', {}).get('value', 0)) or float(p.get('price', {}).get('value', 0)) * 1.5,
                                    "image_url": p.get('images', [{}])[0].get('url', ''),
                                    "product_url": "https://www.ajio.com" + p.get('url', '')
                                }, "Ajio"))
                            except: pass
                except: pass

            if not all_results:
                # Method 2: DOM Parsing fallback with broader selectors
                items = soup.select('div[class*="item"], .rilrtl-products-list__item, .product-item')
                logger.info(f"  [AJIO] Found {len(items)} DOM elements")
                for item in items:
                    try:
                        name_tag = item.select_one('.name, [class*="name"]')
                        brand_tag = item.select_one('.brand, [class*="brand"]')
                        price_tag = item.select_one('.price, [class*="price"]')
                        link_tag = item.find('a')
                        img_tag = item.find('img')
                        
                        if name_tag and price_tag:
                            price = float(re.sub(r'[^0-9.]', '', price_tag.get_text()))
                            all_results.append(self.normalize({
                                "name": name_tag.get_text(strip=True),
                                "brand": brand_tag.get_text(strip=True) if brand_tag else "AJIO",
                                "price_discounted": price,
                                "price_original": price * 1.5,
                                "image_url": img_tag.get('src') or img_tag.get('data-src') if img_tag else "",
                                "product_url": "https://www.ajio.com" + link_tag.get('href') if link_tag else ""
                            }, "Ajio"))
                    except: pass
            
            driver.quit()
        except Exception as e:
            logger.error(f"[AJIO] UC Error: {e}")
            
        results = self._dedup_results(all_results)
        logger.info(f"[AJIO] Total unique items items: {len(results)}")
        return results

    def scrape_zivame(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Zivame (Undetected-Chromedriver)...")
        results = []
        
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        
        try:
            with uc_lock:
                driver = uc.Chrome(options=options, version_main=146)
            
            for page in range(1, config.MAX_PAGES + 1):
                # User's suggested search link
                # https://www.zivame.com/search/result?trksrc=search&trkid=formsubmit&q=bras
                url = f"https://www.zivame.com/search/result?trksrc=search&trkid=formsubmit&q=bras&page={page}"
                logger.info(f"  [ZIVAME] Fetching Page {page}...")
                driver.get(url)
                time.sleep(7)
                
                # Scroll to trigger any lazy loadings
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(3)
                
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraction logic: Recursive search for productList
                def find_zivame_prods(d):
                    if isinstance(d, dict):
                        if 'productList' in d and isinstance(d['productList'], list) and len(d['productList']) > 0:
                            return d['productList']
                        for v in d.values():
                            res = find_zivame_prods(v)
                            if res: return res
                    elif isinstance(d, list):
                        for i in d:
                            res = find_zivame_prods(i)
                            if res: return res
                    return None

                # Try to find JSON in scripts
                found_page_items = 0
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'productList' in script.string:
                        try:
                            # Find the first JSON-like structure that contains productList
                            match = re.search(r'(\{.*?"productList".*?\})', script.string, re.DOTALL)
                            if match:
                                data = json.loads(match.group(1))
                                prods = find_zivame_prods(data)
                                if prods:
                                    for item in prods:
                                        try:
                                            results.append(self.normalize({
                                                "name": item.get('product_name', 'Zivame Bra'),
                                                "price_discounted": float(item.get('price', 0)),
                                                "price_original": float(item.get('mrp', 0)),
                                                "image_url": item.get('image_url', ''),
                                                "product_url": "https://www.zivame.com" + item.get('product_url', ''),
                                                "brand": item.get('brand_name', 'Zivame'),
                                            }, "Zivame"))
                                            found_page_items += 1
                                        except: pass
                        except: pass
                
                logger.info(f"  [ZIVAME] Page {page}: Found {found_page_items} items in JSON")
                
                if found_page_items == 0:
                    # Generic DOM fallback
                    items = soup.select('.product-item, [class*="product"]')
                    if items:
                         logger.info(f"  [ZIVAME] Page {page}: Falling back to DOM for {len(items)} items")
                         for item in items:
                             try:
                                 name = item.select_one('[class*="name"]')
                                 price = item.select_one('[class*="price"]')
                                 if name and price:
                                     results.append(self.normalize({
                                         "name": name.get_text(strip=True),
                                         "price_discounted": float(re.sub(r'[^0-9.]', '', price.get_text()))
                                     }, "Zivame"))
                             except: pass

            driver.quit()
        except Exception as e:
            logger.error(f"[ZIVAME] UC Error: {e}")
            
        return self._dedup_results(results)

    def scrape_clovia(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Clovia (multi-page)...")
        conf = config.STORES['clovia']
        self.pre_flight("clovia", conf.get('browse_url', "https://www.clovia.com/bras/s/"))
        
        api_url = conf['url']
        base_params = conf.get('params', {})
        all_results = []
        
        for page in range(1, config.MAX_PAGES + 1):
            params = dict(base_params)
            params['page'] = str(page)
            
            logger.info(f"  [CLOVIA] Page={page}")
            data = self.safe_request_json(api_url, "clovia", params=params)
            
            if not data:
                # Fallback with full URL
                fallback_url = f"{api_url}?path=/bras/s/&page={page}&active_target=-tab2"
                text = self.safe_request(fallback_url, "clovia")
                if text:
                    try:
                        data = json.loads(text)
                    except:
                        data = {}
            
            if not data:
                continue
            
            try:
                products = data.get('data', {}).get('products', [])
                if not products and 'products' in data:
                    products = data['products']
                if not products and 'items' in data:
                    products = data.get('items', [])
                
                page_count = 0
                for p in products:
                    try:
                        if not p.get('name'):
                            continue
                        raw = {
                            "product_id": str(p.get('id', p.get('sku', ''))),
                            "name": p.get('name', ''),
                            "brand": p.get('brand', 'Clovia'),
                            "price_original": p.get('mrp', p.get('original_price', 0)),
                            "price_discounted": p.get('offer_price', p.get('price_actual', p.get('price', 0))),
                            "discount_percentage": p.get('discount', None),
                            "image_url": p.get('image_url', p.get('imageUrl', p.get('image', ''))),
                            "product_url": "https://www.clovia.com" + str(p.get('product_url', p.get('url', ''))),
                        }
                        all_results.append(self.normalize(raw, conf['name']))
                        page_count += 1
                    except Exception as e:
                        logger.debug(f"Clovia item error: {e}")
                
                logger.info(f"  [CLOVIA] Page {page}: {page_count} items")
                
                if not products:
                    break
            except Exception as e:
                logger.error(f"Clovia API parse error: {e}")
            
            time.sleep(random.uniform(2, 4))
        
        results = self._dedup_results(all_results)
        logger.info(f"[CLOVIA] Total unique items: {len(results)}")
        return results

    def scrape_nykaa(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Nykaa (Undetected-Chromedriver)...")
        results = []
        
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        options.add_argument('--window-size=1920,1080')
        
        try:
            with uc_lock:
                driver = uc.Chrome(options=options, version_main=146)
            
            for page in range(1, config.MAX_PAGES + 1):
                # User's suggested type of URL for better results
                # https://www.nykaafashion.com/women/lingerie/bra/c/3947?q=bra&searchType=ManualSearch&internalSearchTerm=bra&typedSearchTerm=bra&p=2
                url = f"https://www.nykaafashion.com/women/lingerie/bra/c/3947?q=bra&searchType=ManualSearch&internalSearchTerm=bra&typedSearchTerm=bra&p={page}"
                logger.info(f"  [NYKAA] Fetching Page {page}...")
                driver.get(url)
                time.sleep(7)
                
                # Simple scroll to trigger loading
                driver.execute_script("window.scrollTo(0, 1500);")
                time.sleep(3)
                
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Strategy 1: Extract from __NEXT_DATA__ JSON
                next_data = soup.find('script', id='__NEXT_DATA__')
                if next_data:
                    try:
                        data = json.loads(next_data.string)
                        
                        def find_nykaa_prods(d):
                            if isinstance(d, dict):
                                if 'products' in d and isinstance(d['products'], list) and len(d['products']) > 0 and 'name' in d['products'][0]:
                                    return d['products']
                                for v in d.values():
                                    res = find_nykaa_prods(v)
                                    if res: return res
                            elif isinstance(d, list):
                                for i in d:
                                    res = find_nykaa_prods(i)
                                    if res: return res
                            return None
                            
                        prods = find_nykaa_prods(data)
                        if prods:
                            logger.info(f"  [NYKAA] Found {len(prods)} products in JSON")
                            for p in prods:
                                try:
                                    results.append(self.normalize({
                                        "name": p.get('name', ''),
                                        "price_discounted": float(p.get('price', {}).get('discounted', 0)),
                                        "price_original": float(p.get('price', {}).get('regular', 0)),
                                        "image_url": p.get('imageUrl', ''),
                                        "product_url": "https://www.nykaafashion.com" + p.get('url', ''),
                                        "brand": p.get('brandName', ''),
                                    }, "Nykaa"))
                                except: pass
                        else:
                            # Fallback to DOM parsing if JSON didn't work
                            items = soup.select('[class*="product-card"], .product-item')
                            if items:
                                logger.info(f"  [NYKAA] Found {len(items)} items via DOM")
                                for item in items:
                                    try:
                                        # Generic extraction for Nykaa cards
                                        name = item.select_one('[class*="name"]')
                                        price = item.select_one('[class*="price"]')
                                        if name and price:
                                            results.append(self.normalize({
                                                "name": name.get_text(strip=True),
                                                "price_discounted": float(re.sub(r'[^0-9.]', '', price.get_text()))
                                            }, "Nykaa"))
                                    except: pass
                    except: pass
            
            driver.quit()
        except Exception as e:
            logger.error(f"[NYKAA] UC Error: {e}")
            
        return self._dedup_results(results)

# --- PRODUCTION RUNNER ---

def main():
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Initializing Production Scraper Engine v2.0...")
    logger.info(f"  MAX_PAGES per store: {config.MAX_PAGES}")
    logger.info(f"  MIN_DISCOUNT: {config.MIN_DISCOUNT}%")
    logger.info(f"  MAX_WORKERS: {config.MAX_WORKERS}")
    logger.info("=" * 60)
    
    scrapers = StoreScrapers()
    all_data = []
    
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
                logger.info(f"✅ Finished {store_name}: Found {len(data)} items")
            except Exception as e:
                logger.error(f"❌ Thread error in {store_name}: {e}")

    # --- POST-PROCESSING ---
    logger.info("=" * 60)
    logger.info("Post-processing results...")
    
    # 1. Deduplicate ALL items
    seen_all = set()
    deduped_all = []
    for p in all_data:
        norm_name = re.sub(r'[^a-zA-Z0-9]', '', p['name'].lower())
        key = f"{p['brand'].lower()}_{norm_name}"
        if key not in seen_all:
            seen_all.add(key)
            deduped_all.append(p)
            
    # 2. Filter for regular deals (>= MIN_DISCOUNT)
    filtered = [p for p in deduped_all if p['discount_percentage'] >= config.MIN_DISCOUNT]
    
    # 3. Final Sorting for deals
    final_deals = sorted(filtered, key=lambda x: x['discount_percentage'], reverse=True)

    # 4. Premium Bras Filtering
    premium_deals = []
    for deal in final_deals:
        if is_premium_product(deal):
            deal_copy = dict(deal)
            deal_copy["premium"] = True
            premium_deals.append(deal_copy)
    
    premium_deals = sorted(premium_deals, key=lambda x: x['discount_percentage'], reverse=True)

    # --- STATS ---
    logger.info("=" * 60)
    logger.info("SCRAPE RESULTS SUMMARY")
    logger.info(f"  Total raw items extracted: {len(all_data)}")
    logger.info(f"  After deduplication:       {len(deduped_all)}")
    logger.info(f"  With {config.MIN_DISCOUNT}%+ discount:      {len(filtered)}")
    logger.info(f"  Final deals:               {len(final_deals)}")
    logger.info(f"  Premium deals:             {len(premium_deals)}")
    logger.info(f"  Duration:                  {round(time.time() - start_time, 2)}s")
    logger.info("=" * 60)

    # --- EXPORT ---
    output = {
        "metadata": {
            "source": "India Multi-Store Consolidated",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_extracted": len(all_data),
                "total_filtered": len(filtered),
                "final_count": len(final_deals),
                "premium_count": len(premium_deals),
                "duration_seconds": round(time.time() - start_time, 2)
            }
        },
        "deals": final_deals
    }

    premium_output = {
        "metadata": {
            "source": "India Multi-Store Consolidated - Premium",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_extracted": len(all_data),
                "premium_count": len(premium_deals),
                "duration_seconds": round(time.time() - start_time, 2)
            }
        },
        "deals": premium_deals
    }
    
    all_output = {
        "metadata": {
            "source": "India Multi-Store Consolidated - All Products",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_extracted": len(deduped_all),
                "duration_seconds": round(time.time() - start_time, 2)
            }
        },
        "deals": deduped_all
    }

    try:
        with open(config.OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        logger.info(f"📄 Report generated: {config.OUTPUT_FILE} ({len(final_deals)} deals)")
        
        with open(config.PREMIUM_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(premium_output, f, indent=2)
        logger.info(f"📄 Premium report generated: {config.PREMIUM_OUTPUT_FILE} ({len(premium_deals)} premium deals)")
        
        with open(config.ALL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_output, f, indent=2)
        logger.info(f"📄 All products report generated: {config.ALL_OUTPUT_FILE} ({len(deduped_all)} items)")
    except Exception as e:
        logger.error(f"Failed to save output: {e}")

def is_premium_product(product: Dict[str, Any]) -> bool:
    """Check if a product qualifies as premium based on brand and price."""
    brand = product.get('brand', '').lower().strip()
    name = product.get('name', '').lower().strip()
    price = product.get('price_discounted', 0)
    
    # Check brand match
    brand_match = False
    for premium_brand in config.PREMIUM_BRANDS:
        pb = premium_brand.lower()
        if pb in brand or pb in name or brand.startswith(pb):
            brand_match = True
            break
    
    # Premium = recognized premium brand + reasonable price
    if brand_match and price >= config.PREMIUM_MIN_PRICE:
        return True
    
    # Also include high-price items (₹1000+) even if brand not in list
    if price >= 1000 and product.get('discount_percentage', 0) >= 20:
        return True
    
    return False

if __name__ == "__main__":
    main()
