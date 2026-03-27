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
        self.session = requests.Session()

    def get_headers(self, site="common") -> Dict[str, str]:
        headers = {
            "User-Agent": config.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if "amazon" in site:
            headers.update({
                "Host": "www.amazon.in",
                "Referer": "https://www.google.com/"
            })
        elif "flipkart" in site:
            headers.update({"Referer": "https://www.flipkart.com/"})
        return headers

    def safe_request(self, url: str, site: str) -> str:
        """Fetch HTML content with retries and adaptive delays."""
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                headers = self.get_headers(site)
                # Production sleep: slightly more variance
                time.sleep(random.uniform(3, 7))
                
                response = self.session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    if "captcha" in response.text.lower():
                        logger.warning(f"[{site.upper()}] CAPTCHA detected on attempt {attempt+1}.")
                        continue
                    return response.text
                
                logger.warning(f"[{site.upper()}] Status {response.status_code} on attempt {attempt+1}.")
            except Exception as e:
                logger.error(f"[{site.upper()}] Request error: {e}")
            
            time.sleep(pow(4, attempt)) # Exponential backoff
        return ""

    def clean_price(self, val: Any) -> float:
        if not val: return 0.0
        try:
            return float(re.sub(r'[^\d.]', '', str(val).replace(',', '')))
        except:
            return 0.0

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
        html = self.safe_request(conf['url'], "amazon")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        products = soup.select(conf['selector'])
        results = []

        for item in products:
            try:
                name_tag = item.select_one('h2 a span')
                if not name_tag or "bra" not in name_tag.text.lower(): continue
                
                prices = item.select('.a-price-whole')
                p_disc = self.clean_price(prices[0].text if prices else 0)
                
                orig_tag = item.select_one('.a-text-price span[aria-hidden="true"]')
                p_orig = self.clean_price(orig_tag.text if orig_tag else p_disc)
                
                raw = {
                    "product_id": item.get('data-asin'),
                    "name": name_tag.text,
                    "brand": name_tag.text.split(' ')[0],
                    "price_original": p_orig,
                    "price_discounted": p_disc,
                    "rating": item.select_one('span.a-icon-alt').text.split(' ')[0] if item.select_one('span.a-icon-alt') else "N/A",
                    "review_count": item.select_one('span.a-size-base.s-underline-text').text if item.select_one('span.a-size-base.s-underline-text') else 0,
                    "image_url": item.select_one('img.s-image').get('src') if item.select_one('img.s-image') else "",
                    "product_url": "https://www.amazon.in" + item.select_one('h2 a').get('href'),
                }
                results.append(self.normalize(raw, conf['name']))
            except Exception as e:
                logger.debug(f"Amazon item error: {e}")
        return results

    def scrape_flipkart(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Flipkart...")
        conf = config.STORES['flipkart']
        html = self.safe_request(conf['url'], "flipkart")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(conf['selector'])
        results = []

        for item in items:
            try:
                name_tag = item.select_one('a.IRpwTa, a.s1Q9rs')
                if not name_tag or "bra" not in name_tag.text.lower(): continue
                
                raw = {
                    "product_id": item.get('data-id', str(random.getrandbits(32))),
                    "name": name_tag.text,
                    "brand": item.select_one('div._2Wk9SZ').text if item.select_one('div._2Wk9SZ') else "N/A",
                    "price_original": item.select_one('div._3I9_ca').text if item.select_one('div._3I9_ca') else 0,
                    "price_discounted": item.select_one('div._30jeq3').text if item.select_one('div._30jeq3') else 0,
                    "discount_percentage": item.select_one('div._3Ay6Wh').text if item.select_one('div._3Ay6Wh') else None,
                    "rating": item.select_one('div._3LWZlK').text if item.select_one('div._3LWZlK') else "N/A",
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
        html = self.safe_request(conf['url'], "myntra")
        if not html: return []
        
        match = re.search(r'window\.__myx\s*=\s*({.*?});', html)
        if not match: return []
        try:
            data = json.loads(match.group(1))
            products = data.get('searchData', {}).get('results', {}).get('products', [])
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
            resp = self.session.get(conf['url'], headers=self.get_headers("ajio"), timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                products = resp.json().get('products', [])
                return [self.normalize({
                    "product_id": p.get('code'),
                    "name": p.get('name'),
                    "brand": p.get('brandName'),
                    "price_original": p.get('wasPriceData', {}).get('value'),
                    "price_discounted": p.get('price', {}).get('value'),
                    "image_url": p.get('images', [{}])[0].get('url'),
                    "product_url": "https://www.ajio.com" + p.get('url'),
                }, conf['name']) for p in products]
        except Exception as e:
            logger.error(f"Ajio API error: {e}")
        return []

    def scrape_zivame(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Zivame...")
        conf = config.STORES['zivame']
        html = self.safe_request(conf['url'], "zivame")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(conf['selector'])
        results = []
        for item in items:
            try:
                name_tag = item.select_one('.product-item-link')
                if not name_tag: continue
                results.append(self.normalize({
                    "product_id": item.get('data-product-id', random.getrandbits(32)),
                    "name": name_tag.text.strip(),
                    "brand": "Zivame",
                    "price_original": item.select_one('.old-price .price').text if item.select_one('.old-price .price') else 0,
                    "price_discounted": item.select_one('.price-wrapper .price').text,
                    "image_url": item.select_one('img.product-image-photo').get('src'),
                    "product_url": name_tag.get('href'),
                }, conf['name']))
            except Exception as e:
                logger.debug(f"Zivame item error: {e}")
        return results

    def scrape_clovia(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Clovia...")
        conf = config.STORES['clovia']
        html = self.safe_request(conf['url'], "clovia")
        if not html: return []
        
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(conf['selector'])
        results = []
        for item in items:
            try:
                name_tag = item.select_one('.prod-name')
                if not name_tag: continue
                results.append(self.normalize({
                    "product_id": item.get('id', random.getrandbits(32)),
                    "name": name_tag.text.strip(),
                    "brand": "Clovia",
                    "price_original": item.select_one('.mrp').text if item.select_one('.mrp') else 0,
                    "price_discounted": item.select_one('.offer-price').text,
                    "image_url": item.select_one('img').get('src'),
                    "product_url": "https://www.clovia.com" + item.select_one('a').get('href'),
                }, conf['name']))
            except Exception as e:
                logger.debug(f"Clovia item error: {e}")
        return results

    def scrape_nykaa(self) -> List[Dict[str, Any]]:
        logger.info("Scraping Nykaa Fashion...")
        conf = config.STORES['nykaa']
        try:
            resp = self.session.get(conf['url'], headers=self.get_headers("nykaa"), timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get('products', []) or data.get('data', {}).get('products', [])
                return [self.normalize({
                    "product_id": p.get('id'),
                    "name": p.get('name'),
                    "brand": p.get('brand_name'),
                    "price_original": p.get('mrp'),
                    "price_discounted": p.get('price'),
                    "discount_percentage": p.get('discount'),
                    "image_url": p.get('image_url'),
                    "product_url": "https://www.nykaafashion.com" + p.get('product_url'),
                }, conf['name']) for p in products]
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
