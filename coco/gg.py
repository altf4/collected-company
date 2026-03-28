from bs4 import BeautifulSoup

def get_quantity_from_html(html_content: str) -> int:
    """
    Extracts the quantity value from the HTML content by searching for an element with the id "variant-stock".

    Args:
        html_content (str): The HTML content as a string.

    Returns:
        int: The quantity value found in the element with id "variant-stock". Returns 0 if the element is not found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = soup.find(id="variant-stock")
    return int(results.text.strip()) if results else 0
