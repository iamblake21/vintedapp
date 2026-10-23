from vinted_alerts.client import parse_amount, parse_card_title, parse_catalog_html, params_from_search_url

# Trimmed copy of a real card from www.vinted.it/catalog (October 2026).
CARD = (
    '<div class="NoC3Da_new-item-box__container" data-testid="product-item-id-10492284945">'
    '<img src="https://images1.vinted.net/t/02_x/310x430/77ea5188.webp?s=d7b6&amp;x=1" '
    'alt="Nike Dunk bébé 21, Brand: Nike, Condizioni: Ottime, Taglia: 21, 20.00 €, 21.70 €" '
    'class="web_ui__Image__content" data-testid="product-item-id-10492284945--image--img"/>'
    '<a href="/items/10492284945-nike-dunk-bebe-21?referrer=catalog" class="overlay" '
    'data-testid="product-item-id-10492284945--overlay-link" '
    'title="Nike Dunk bébé 21, Brand: Nike, Condizioni: Ottime, Taglia: 21, 20.00 €, 21.70 €" '
    'target="_self"><div></div></a></div>'
)


def test_parse_catalog_html():
    [item] = parse_catalog_html(CARD + CARD, "https://www.vinted.it")
    assert item.id == 10492284945
    assert item.title == "Nike Dunk bébé 21"
    assert (item.price, item.total_price, item.currency) == (20.0, 21.7, "EUR")
    assert (item.brand, item.condition, item.size) == ("Nike", "Ottime", "21")
    assert item.url == "https://www.vinted.it/items/10492284945-nike-dunk-bebe-21"
    assert item.photo_url.endswith("s=d7b6&x=1")


def test_parse_card_title_edge_cases():
    t = parse_card_title("Nike Dunk Neu, Brand: Nike, Condizioni: Nuovo senza cartellino, "
                         "Taglia: 44,5, 70.00 €, 74.20 €")
    assert (t["size"], t["price"], t["total_price"]) == ("44,5", 70.0, 74.2)
    t = parse_card_title("Lotto, 3 paia, Condizioni: Buone, 1.234,50 €, 1.300,00 €")
    assert (t["title"], t["price"], t["total_price"]) == ("Lotto, 3 paia", 1234.5, 1300.0)
    t = parse_card_title("Jumper &quot;blue&quot;, Brand: Zara, £12.00, £13.30")
    assert (t["title"], t["currency"], t["price"]) == ('Jumper "blue"', "GBP", 12.0)
    assert parse_card_title("Cosa, 5,00 €")["total_price"] == 5.0


def test_parse_amount():
    assert parse_amount("1.234,50") == 1234.5
    assert parse_amount("1,234.50") == 1234.5
    assert parse_amount("12,5") == 12.5


def test_params_from_search_url():
    url = ("https://www.vinted.it/catalog?search_text=nike&catalog[]=1231&brand_ids[]=53"
           "&brand_ids[]=14&order=relevance&page=3&time=123&price_to=50")
    assert params_from_search_url(url) == [
        ("search_text", "nike"), ("catalog[]", "1231"), ("brand_ids[]", "53"),
        ("brand_ids[]", "14"), ("price_to", "50")]
