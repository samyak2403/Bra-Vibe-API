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
                # e.g. https://m.media-amazon.com/images/I/61N+QWw6VTL._AC_UL320_.jpg -> https://m.media-amazon.com/images/I/61N+QWw6VTL.jpg
                # handles ._AC_UL320_., ._SY300_., etc.
                return re.sub(r'\._[a-zA-Z0-9_+%-]+_\.', '.', url)
            # Flipkart
            elif 'flixcart' in url:
                # e.g. https://rukminim2.flixcart.com/image/128/128/... -> https://rukminim2.flixcart.com/image/1080/1080/...
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
                return re.sub(r'/\d+x(?:\d*/)?', '/1080x1080/', url)
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
            "image_url": self.enhance_image_quality(str(raw.get('image_url', ''))),
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
        self.pre_flight("amazon", "https://www.amazon.in/")
        
        search_url = f"{conf['url']}&ref=nb_sb_noss"
        html = self.safe_request(search_url, "amazon")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
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
        
        # Strategy 1: Try Flipkart's internal page fetch API
        self.pre_flight("flipkart", "https://www.flipkart.com/")
        
        # Try the search page and parse JSON embedded in HTML
        search_url = conf.get('search_url', 'https://www.flipkart.com/search?q=bras+for+women&page=1')
        html = self.safe_request(search_url, "flipkart")
        if not html:
            logger.warning("[FLIPKART] HTML fetch failed, trying fallback...")
            return []
        
        results = []
        
        # Strategy: Parse the SSR JSON data embedded in Flipkart pages
        # Flipkart embeds product data in script tags as JSON
        try:
            # Look for pageDataV4 or similar embedded JSON
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
                            results.append(self.normalize(raw, conf['name']))
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.debug(f"Flipkart JSON-LD parse error: {e}")
        
        # Strategy 2: Traditional HTML parsing as fallback
        if not results:
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all product cards - Flipkart uses various class patterns
                # Try multiple selector strategies
                product_links = soup.select('a[href*="/p/"]')
                seen_urls = set()
                
                for link in product_links:
                    try:
                        href = link.get('href', '')
                        if href in seen_urls or '/p/' not in href:
                            continue
                        seen_urls.add(href)
                        
                        # Get the parent card container
                        card = link
                        for _ in range(5):
                            parent = card.parent
                            if parent and parent.name == 'div':
                                card = parent
                            else:
                                break
                        
                        # Find product name - it's typically in a div with specific styles
                        name_el = link.select_one('div[class*="col"] a[title]') or link.select_one('a[title]')
                        name = name_el.get('title', '') if name_el else ''
                        if not name:
                            name_el = card.select_one('a[title]')
                            name = name_el.get('title', '') if name_el else ''
                        if not name:
                            # Try text content of first significant div
                            divs = card.select('div')
                            for d in divs:
                                t = d.get_text(strip=True)
                                if len(t) > 10 and len(t) < 200:
                                    name = t
                                    break
                        
                        if not name or 'bra' not in name.lower():
                            continue
                        
                        # Find prices - look for ₹ symbol
                        price_texts = [el.get_text(strip=True) for el in card.select('div') if '₹' in el.get_text()]
                        prices = []
                        for pt in price_texts:
                            cleaned = self.clean_price(pt)
                            if cleaned > 0:
                                prices.append(cleaned)
                        prices = sorted(set(prices))
                        
                        p_disc = prices[0] if prices else 0
                        p_orig = prices[-1] if len(prices) > 1 else p_disc
                        
                        # Find image
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
                            results.append(self.normalize(raw, conf['name']))
                    except Exception as e:
                        logger.debug(f"Flipkart item parse error: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Flipkart HTML parse error: {e}")
        
        return results

    def scrape_myntra(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Myntra...")
        conf = config.STORES['myntra']
        
        # Strategy: Warm up session then use the gateway API
        self.pre_flight("myntra", "https://www.myntra.com/")
        
        # Try the browse page first to get embedded data
        browse_url = conf.get('browse_url', 'https://www.myntra.com/bras')
        html = self.safe_request(browse_url, "myntra")
        if not html:
            logger.warning("[MYNTRA] Failed to fetch browse page")
            return []
        
        results = []
        
        # Strategy 1: Extract from window.__myx embedded data
        try:
            # Multiple patterns to find embedded product data
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
                # Navigate nested data structures
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
                        results.append(self.normalize(raw, conf['name']))
                    except Exception as e:
                        logger.debug(f"Myntra item error: {e}")
        except Exception as e:
            logger.error(f"Myntra parse error: {e}")
        
        # Strategy 2: Try the gateway API directly
        if not results:
            try:
                api_url = conf['url']
                params = {
                    "p": "1",
                    "rows": "50",
                    "o": "0",
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
                            results.append(self.normalize(raw, conf['name']))
                        except Exception as e:
                            logger.debug(f"Myntra API item error: {e}")
            except Exception as e:
                logger.error(f"Myntra API error: {e}")
        
        return results

    def scrape_ajio(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Ajio...")
        conf = config.STORES['ajio']
        
        # Warm up session on the browse page
        self.pre_flight("ajio", conf.get('browse_url', "https://www.ajio.com/s/bras-4621-72911"))
        
        url = conf['url']
        params = conf.get('params', {})
        
        data = self.safe_request_json(url, "ajio", params=params)
        if not data:
            # Fallback: try alternate URL format
            alt_url = "https://www.ajio.com/api/category/830311004?fields=CUSTOM_CLASSIFICATION&currentPage=0&pageSize=45&platform=site"
            data = self.safe_request_json(alt_url, "ajio")
        
        if not data:
            return []
        
        try:
            products = data.get('products', [])
            if not products and 'data' in data:
                products = data['data'].get('products', [])
            if not products and 'results' in data:
                products = data.get('results', [])
            
            results = []
            for p in products:
                try:
                    # Handle different image structures
                    img_url = ''
                    images = p.get('images', [])
                    if images:
                        if isinstance(images[0], dict):
                            img_url = images[0].get('url', '')
                        else:
                            img_url = str(images[0])
                    if not img_url:
                        img_url = p.get('imageUrl', '') or p.get('image', '')
                    
                    # Handle different price structures
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
        except Exception as e:
            logger.error(f"Ajio parse error: {e}")
        return []

    def scrape_zivame(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Zivame...")
        conf = config.STORES['zivame']
        
        self.pre_flight("zivame", conf.get('browse_url', "https://www.zivame.com/"))
        
        results = []
        
        # Strategy 1: Try Zivame's API endpoint
        api_url = conf['url']
        params = conf.get('params', {})
        data = self.safe_request_json(api_url, "zivame", params=params)
        
        if data:
            try:
                products = data.get('products', [])
                if not products and 'data' in data:
                    products = data['data'].get('products', data['data'].get('items', []))
                if not products and 'results' in data:
                    products = data.get('results', [])
                if not products and 'items' in data:
                    products = data.get('items', [])
                
                for p in products:
                    try:
                        raw = {
                            "product_id": str(p.get('id', p.get('sku', random.getrandbits(32)))),
                            "name": p.get('name', p.get('title', '')),
                            "brand": p.get('brand', p.get('brandName', 'Zivame')),
                            "price_original": p.get('mrp', p.get('originalPrice', p.get('price', 0))),
                            "price_discounted": p.get('offerPrice', p.get('finalPrice', p.get('price', 0))),
                            "discount_percentage": p.get('discount', None),
                            "image_url": p.get('imageUrl', p.get('image', '')),
                            "product_url": p.get('url', p.get('productUrl', '')),
                        }
                        if raw['product_url'] and not raw['product_url'].startswith('http'):
                            raw['product_url'] = "https://www.zivame.com" + raw['product_url']
                        results.append(self.normalize(raw, conf['name']))
                    except Exception as e:
                        logger.debug(f"Zivame API item error: {e}")
            except Exception as e:
                logger.error(f"Zivame API parse error: {e}")
        
        # Strategy 2: Fall back to HTML scraping
        if not results:
            browse_url = conf.get('browse_url', 'https://www.zivame.com/lingerie/bras.html')
            html = self.safe_request(browse_url, "zivame")
            if html:
                try:
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Try to extract from embedded JSON/script data
                    scripts = soup.select('script[type="application/ld+json"]')
                    for script in scripts:
                        try:
                            ld_data = json.loads(script.string or '')
                            if isinstance(ld_data, dict) and ld_data.get('@type') == 'ItemList':
                                for item in ld_data.get('itemListElement', []):
                                    p = item.get('item', item)
                                    offers = p.get('offers', {})
                                    raw = {
                                        "product_id": str(random.getrandbits(32)),
                                        "name": p.get('name', ''),
                                        "brand": "Zivame",
                                        "price_original": offers.get('highPrice', offers.get('price', 0)),
                                        "price_discounted": offers.get('lowPrice', offers.get('price', 0)),
                                        "image_url": p.get('image', ''),
                                        "product_url": p.get('url', ''),
                                    }
                                    results.append(self.normalize(raw, conf['name']))
                        except json.JSONDecodeError:
                            continue
                    
                    # HTML fallback
                    if not results:
                        items = soup.select('.product-item, [data-product-id], .product-card')
                        for item in items:
                            try:
                                name_tag = item.select_one('.product-item-link, .product-name, a[title]')
                                if not name_tag: continue
                                
                                price_disc = item.select_one('.price-wrapper .price, .special-price .price, .offer-price')
                                price_orig = item.select_one('.old-price .price, .regular-price .price, .mrp-price')
                                
                                raw = {
                                    "product_id": str(item.get('data-product-id', random.getrandbits(32))),
                                    "name": name_tag.get_text(strip=True),
                                    "brand": "Zivame",
                                    "price_original": price_orig.get_text(strip=True) if price_orig else (price_disc.get_text(strip=True) if price_disc else 0),
                                    "price_discounted": price_disc.get_text(strip=True) if price_disc else 0,
                                    "image_url": item.select_one('img').get('src', '') if item.select_one('img') else "",
                                    "product_url": name_tag.get('href', ''),
                                }
                                results.append(self.normalize(raw, conf['name']))
                            except Exception as e:
                                logger.debug(f"Zivame HTML item error: {e}")
                except Exception as e:
                    logger.debug(f"Zivame HTML parse error: {e}")
        
        return results

    def scrape_clovia(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Clovia...")
        conf = config.STORES['clovia']
        
        self.pre_flight("clovia", conf.get('browse_url', "https://www.clovia.com/bras/s/"))
        
        api_url = conf['url']
        params = conf.get('params', {})
        
        data = self.safe_request_json(api_url, "clovia", params=params)
        if not data:
            # Fallback with full URL
            fallback_url = f"{api_url}?path=/bras/s/&page=1&active_target=-tab2"
            text = self.safe_request(fallback_url, "clovia")
            if text:
                try:
                    data = json.loads(text)
                except:
                    data = {}
        
        if not data:
            return []
        
        try:
            products = data.get('data', {}).get('products', [])
            if not products and 'products' in data:
                products = data['products']
            if not products and 'items' in data:
                products = data.get('items', [])
            
            results = []
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
                    results.append(self.normalize(raw, conf['name']))
                except Exception as e:
                    logger.debug(f"Clovia item error: {e}")
            return results
        except Exception as e:
            logger.error(f"Clovia API parse error: {e}")
            return []

    def scrape_nykaa(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Nykaa Fashion...")
        conf = config.STORES['nykaa']
        
        self.pre_flight("nykaa", conf.get('browse_url', "https://www.nykaafashion.com/bras/c/595"))
        
        url = conf['url']
        params = conf.get('params', {})
        
        data = self.safe_request_json(url, "nykaa", params=params)
        
        if not data:
            # Fallback: try with different params
            alt_params = {
                "categoryId": conf.get('categoryId', '595'),
                "PageSize": "30",
                "currentPage": "1",
                "sort": "popularity",
            }
            data = self.safe_request_json(url, "nykaa", params=alt_params)
        
        if not data:
            # Fallback 2: Try HTML scraping from browse page
            browse_url = conf.get('browse_url', 'https://www.nykaafashion.com/bras/c/595')
            html = self.safe_request(browse_url, "nykaa")
            if html:
                try:
                    # Look for embedded product data
                    match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});\s*</script>', html, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                except:
                    pass
        
        if not data:
            return []
        
        try:
            products = data.get('data', {}).get('products', [])
            if not products and 'products' in data:
                products = data['products']
            if not products and 'response' in data:
                products = data['response'].get('products', [])
            
            results = []
            for p in products:
                try:
                    if not p.get('name') and not p.get('title'):
                        continue
                    raw = {
                        "product_id": str(p.get('id', p.get('productId', ''))),
                        "name": p.get('name', p.get('title', '')),
                        "brand": p.get('brandName', p.get('brand_name', p.get('brand', 'N/A'))),
                        "price_original": p.get('mrp', p.get('originalPrice', 0)),
                        "price_discounted": p.get('price', p.get('offerPrice', 0)),
                        "discount_percentage": p.get('discount', None),
                        "image_url": p.get('imageUrl', p.get('image_url', p.get('image', ''))),
                        "product_url": "https://www.nykaafashion.com" + str(p.get('productUrl', p.get('url', ''))),
                    }
                    results.append(self.normalize(raw, conf['name']))
                except Exception as e:
                    logger.debug(f"Nykaa item error: {e}")
            return results
        except Exception as e:
            logger.error(f"Nykaa parse error: {e}")
        return []

# --- PRODUCTION RUNNER ---

def main():
    start_time = time.time()
    logger.info("Initializing Production Scraper Engine...")
    
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
                logger.info(f"Finished {store_name}: Found {len(data)} items")
            except Exception as e:
                logger.error(f"Thread error in {store_name}: {e}")

    # --- POST-PROCESSING ---
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
    logger.info(f"Premium deals identified: {len(premium_deals)}")

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
        logger.info(f"Report generated: {config.OUTPUT_FILE} ({len(final_deals)} deals)")
        
        with open(config.PREMIUM_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(premium_output, f, indent=2)
        logger.info(f"Premium report generated: {config.PREMIUM_OUTPUT_FILE} ({len(premium_deals)} premium deals)")
        
        with open(config.ALL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_output, f, indent=2)
        logger.info(f"All products report generated: {config.ALL_OUTPUT_FILE} ({len(deduped_all)} items)")
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
    # as they likely come from premium segments
    if price >= 1000 and product.get('discount_percentage', 0) >= 20:
        return True
    
    return False

if __name__ == "__main__":
    main()

