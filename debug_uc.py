import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UC-Debug")

def test_ajio_uc():
    options = uc.ChromeOptions()
    options.headless = False  # Start headed first to ensure bypass
    options.add_argument('--window-size=1920,1080')
    
    logger.info("Launching undetected-chromedriver...")
    driver = uc.Chrome(options=options, version_main=146)
    
    try:
        logger.info("Navigating to Ajio...")
        driver.get("https://www.ajio.com/s/bras-4621-72911")
        time.sleep(5) # Let Akamai evaluate
        
        # Scroll a bit
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(2)
        
        html = driver.page_source
        
        with open("ajio_uc_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        if "Access Denied" in html:
            logger.error("AJIO still blocked us with Access Denied!")
        else:
            logger.info("AJIO loaded successfully! Parsing for products...")
            soup = BeautifulSoup(html, 'html.parser')
            # Find item cards in Ajio
            items = soup.find_all('div', class_='item')
            counts = len(items)
            logger.info(f"Found {counts} product items in HTML.")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_ajio_uc()
