import json
from bs4 import BeautifulSoup

def extract_zivame_html():
    with open("zivame_debug.html", "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    
    # Try finding product cards by common class names or looking for 'a' tags with specific product structure
    products = []
    
    # Let's inspect all links to see if they look like product pages
    for a in soup.find_all("a", href=True):
        href = a['href']
        if '/bras/' in href or '.html' in href:
            title = a.get('title') or a.text.strip()
            if title and len(title) > 10 and 'bra' in title.lower():
                products.append({'url': href, 'title': title})
                
    print(f"Found {len(products)} potential product links")
    
    # Or inspect generic elements that contain price
    prices = soup.find_all(text=lambda text: text and '₹' in text or 'Rs.' in text or 'Rs ' in text)
    print(f"Found {len(prices)} price elements")
    
    # print a few details to debug
    if products:
        for p in products[:5]:
            print(p)

if __name__ == "__main__":
    extract_zivame_html()
