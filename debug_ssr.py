import time
import json
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScraperDebug")

def debug_ssr():
    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        )
        
        page = context.new_page()
        logger.info("\n--- Debugging ZIVAME HTML ---")
        page.goto("https://www.zivame.com/lingerie/bras.html", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        with open("zivame_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        logger.info("\n--- Debugging NYKAA HTML ---")
        page.goto("https://www.nykaafashion.com/bras/c/595", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        with open("nykaa_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        logger.info("\n--- Debugging AJIO HTML ---")
        page.goto("https://www.ajio.com/s/bras-4621-72911", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        with open("ajio_debug2.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        browser.close()

if __name__ == "__main__":
    debug_ssr()
