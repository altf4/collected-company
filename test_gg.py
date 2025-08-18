from bs4 import BeautifulSoup
import coco

def test_sephiroth():
    # Read file into string
    with open("test/GG - Sephiroth's Intervention [FINAL FANTASY].html", 'r') as file:
        html_content = file.read()
        assert coco.gg.get_quantity_from_html(html_content) == 55
        
if __name__ == "__main__":
    test_sephiroth()