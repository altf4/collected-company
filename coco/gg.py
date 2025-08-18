from bs4 import BeautifulSoup

def get_quantity_from_html(html_content: str) -> int:
    soup = BeautifulSoup(html_content, 'html.parser')
    results = soup.find(id="variant-stock")
    return int(results.text.strip()) if results else 0
