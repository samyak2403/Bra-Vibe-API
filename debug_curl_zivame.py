from curl_cffi import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CurlDebug")

def test_zivame():
    url = "https://www.zivame.com/api/v1/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Try different Zivame endpoints
    urls = [
        "https://www.zivame.com/zmapi/search?q=bras&page=1",
        "https://www.zivame.com/pwa/v1/search?q=bras&page=1"
    ]
    
    for u in urls:
        try:
            logger.info(f"Trying ZIVAME {u} with chrome120...")
            r = requests.get(u, headers=headers, impersonate="chrome120", timeout=10)
            logger.info(f"ZIVAME Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                logger.info(f"ZIVAME Success! Data length: {len(str(data))}")
        except Exception as e:
            logger.error(f"Error with Zivame {u}: {e}")

if __name__ == "__main__":
    test_zivame()
