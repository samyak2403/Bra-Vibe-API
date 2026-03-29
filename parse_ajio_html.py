import bs4
import re

html = open("ajio_uc_debug.html", encoding="utf-8").read()
soup = bs4.BeautifulSoup(html, "html.parser")

bras = []
for tag in soup.find_all(string=re.compile("bra", re.IGNORECASE)):
    parent = tag.parent
    if parent and parent.name not in ['script', 'style', 'title'] and len(tag.strip()) < 100:
        card = parent.find_parent('div', class_=True)
        if card:
            bras.append((tag.strip(), tuple(card.get('class', []))))

print(f"Found {len(bras)} 'bra' occurrences.")
print("Sample matches:")
for b in set(bras[:30]):
    print(b)

# Also let's try to find common product containers
for c in ['item', 'product-card', 'product-item', 'product', 'card']:
    elements = soup.find_all('div', class_=re.compile(c, re.IGNORECASE))
    if elements:
        print(f"Found {len(elements)} elements with class related to '{c}'")
