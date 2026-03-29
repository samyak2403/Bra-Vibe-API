import undetected_chromedriver as uc
import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API-Injector")

def fetch_api_in_browser():
    options = uc.ChromeOptions()
    options.headless = False
    options.add_argument('--window-size=1920,1080')
    driver = uc.Chrome(options=options, version_main=146)
    
    try:
        # --- AJIO ---
        logger.info("Testing AJIO...")
        driver.get("https://www.ajio.com/s/bras-4621-72911")
        time.sleep(3)
        
        ajio_js = """
        var callback = arguments[arguments.length - 1];
        fetch('/api/search?text=bras&urlURI=/s/bras-4621-72911')
            .then(r => r.json())
            .then(data => callback(JSON.stringify(data)))
            .catch(e => callback("ERROR: " + e.toString()));
        """
        ajio_json_raw = driver.execute_async_script(ajio_js)
        logger.info(f"Ajio API response length: {len(str(ajio_json_raw))}")
        logger.info(f"AJIO RAW: {str(ajio_json_raw)[:200]}")
        if "ERROR" not in ajio_json_raw:
            try:
                data = json.loads(ajio_json_raw)
                products = data.get('products', [])
                logger.info(f"AJIO SUCCESS: Found {len(products)} products in JSON!")
            except:
                logger.error("AJIO Parsing error.")

        # --- ZIVAME ---
        logger.info("Testing ZIVAME...")
        driver.get("https://www.zivame.com/bras")
        time.sleep(3)
        zivame_js = """
        var callback = arguments[arguments.length - 1];
        fetch('/api/v1/search?q=bras&page=1')
            .then(r => r.json())
            .then(data => callback(JSON.stringify(data)))
            .catch(e => callback("ERROR: " + e.toString()));
        """
        ziv_json_raw = driver.execute_async_script(zivame_js)
        logger.info(f"Zivame API response length: {len(str(ziv_json_raw))}")
        logger.info(f"ZIVAME RAW: {str(ziv_json_raw)[:200]}")
        if "ERROR" not in ziv_json_raw:
            logger.info("ZIVAME SUCCESS!")

        # --- NYKAA ---
        logger.info("Testing NYKAA...")
        driver.get("https://www.nykaafashion.com/bras")
        time.sleep(3)
        nykaa_js = """
        var callback = arguments[arguments.length - 1];
        fetch('https://www.nykaafashion.com/api/catalog/search?q=bras')
            .then(r => r.json())
            .then(data => callback(JSON.stringify(data)))
            .catch(e => callback("ERROR: " + e.toString()));
        """
        nyk_json_raw = driver.execute_async_script(nykaa_js)
        logger.info(f"Nykaa API response length: {len(str(nyk_json_raw))}")
        logger.info(f"NYKAA RAW: {str(nyk_json_raw)[:200]}")
        if "ERROR" not in nyk_json_raw:
            logger.info("NYKAA SUCCESS!")

    finally:
        driver.quit()

if __name__ == "__main__":
    fetch_api_in_browser()
