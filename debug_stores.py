import time
import json
import logging
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScraperDebug")

def debug_stores():
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        
        # === ZIVAME ===
        logger.info("\n--- Debugging ZIVAME ---")
        page_z = context.new_page()
        z_captured = []
        def handle_z(response):
            try:
                if response.status == 200 and ('zmapi' in response.url or 'search' in response.url or 'product' in response.url):
                    if 'json' in response.headers.get('content-type', ''):
                        z_captured.append((response.url, response.json()))
                        logger.info(f"Zivame API: {response.url}")
            except: pass
        page_z.on("response", handle_z)
        
        page_z.goto("https://www.zivame.com/lingerie/bras.html", wait_until="networkidle", timeout=60000)
        time.sleep(5)
        
        with open("zivame_debug.html", "w", encoding="utf-8") as f:
            f.write(page_z.content())
        logger.info(f"Zivame APIs captured: {len(z_captured)}")
        page_z.close()
        
        # === NYKAA ===
        logger.info("\n--- Debugging NYKAA ---")
        page_n = context.new_page()
        n_captured = []
        def handle_n(response):
            try:
                if response.status == 200 and ('search' in response.url or 'products' in response.url):
                    if 'json' in response.headers.get('content-type', ''):
                        n_captured.append((response.url, response.json()))
                        logger.info(f"Nykaa API: {response.url}")
            except: pass
        page_n.on("response", handle_n)
        
        page_n.goto("https://www.nykaafashion.com/bras/c/595", wait_until="networkidle", timeout=60000)
        time.sleep(5)
        
        with open("nykaa_debug.html", "w", encoding="utf-8") as f:
            f.write(page_n.content())
        logger.info(f"Nykaa APIs captured: {len(n_captured)}")
        page_n.close()
        
        browser.close()

if __name__ == "__main__":
    debug_stores()
