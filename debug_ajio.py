import time
import json
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScraperDebug")

def debug_ajio_chromium():
    logger.info("Debugging AJIO with Chromium + advanced args...")
    with Stealth().use_sync(sync_playwright()) as pw:
        # Use advanced args for Chromium
        browser = pw.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-IN"
        )
        page = context.new_page()
        
        captured = []
        def handle_response(response):
            try:
                if response.status == 200 and ('/api/' in response.url or '/search/' in response.url):
                    if 'json' in response.headers.get('content-type', ''):
                        data = response.json()
                        captured.append((response.url, data))
                        logger.info(f"Ajio Intercepted: {response.url}")
            except:
                pass
        
        page.on("response", handle_response)
        page.goto("https://www.ajio.com/s/bras-4621-72911", wait_until="networkidle", timeout=60000)
        
        # Human-like scrolling
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 1000)")
            page.mouse.move(100, 100)
            page.mouse.move(200, 200)
            time.sleep(2)
        
        with open("ajio_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
            
        with open("ajio_api.json", "w", encoding="utf-8") as f:
            json.dump(captured, f, indent=2)
            
        logger.info(f"Ajio captured API responses: {len(captured)}")
        browser.close()

if __name__ == "__main__":
    debug_ajio_chromium()
