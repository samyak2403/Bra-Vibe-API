from curl_cffi import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CurlDebug")

def test_ajio():
    url = "https://www.ajio.com/api/category/830216011"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
    }
    
    # Try different impersonations
    for impersonate in ["chrome120", "chrome116", "safari15_3", "edge101"]:
        try:
            logger.info(f"Trying AJIO with {impersonate}...")
            r = requests.get(url, headers=headers, impersonate=impersonate, timeout=10)
            logger.info(f"AJIO {impersonate} Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                logger.info(f"AJIO {impersonate} Success! Items: {len(data.get('products', []))}")
                break
        except Exception as e:
            logger.error(f"Error with {impersonate}: {e}")

def test_nykaa():
    url = "https://www.nykaafashion.com/api/catalog/search?q=bras&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for impersonate in ["chrome120", "chrome116", "safari15_3", "edge101"]:
        try:
            logger.info(f"Trying NYKAA with {impersonate}...")
            r = requests.get(url, headers=headers, impersonate=impersonate, timeout=10)
            logger.info(f"NYKAA {impersonate} Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                logger.info(f"NYKAA {impersonate} Success! Data length: {len(str(data))}")
                break
        except Exception as e:
            logger.error(f"Error with {impersonate}: {e}")

if __name__ == "__main__":
    test_ajio()
    test_nykaa()
