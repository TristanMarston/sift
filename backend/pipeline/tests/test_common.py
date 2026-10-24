import pytest

from normalize import common as C


@pytest.mark.parametrize("raw, cents", [
    (48, 4800), (48.0, 4800), ("48", 4800), ("$48.00", 4800), ("1,200.50", 120050), (19.99, 1999), (0.1 + 0.2, 30),
    ("0", 0), (None, None), ("free", None), ("", None), (-5, None), (True, None),
])
def test_to_cents(raw, cents):
    assert C.to_cents(raw) == cents


@pytest.mark.parametrize("raw, expected", [
    ("New with tags", "new_with_tags"), ("NWT", "new_with_tags"), ("Brand new", "new_with_tags"),
    ("New", "new_with_tags"), ("New/Never Worn", "new_with_tags"),
    ("New without tags", "like_new"), ("NWOT", "like_new"), ("Like new", "like_new"),
    ("Used - Excellent", "like_new"), ("Gently Used", "like_new"),
    ("Good", "good"), ("Used - Good", "good"), ("Used", "good"), ("Pre-owned", "good"),
    ("Used - Fair", "fair"), ("Fair", "fair"), ("Poor", "fair"), ("Very Worn", "fair"),
    ("Refurbished", None), ("For parts or not working", None), ("", None), (None, None),
])
def test_map_condition(raw, expected):
    assert C.map_condition(raw) == expected


@pytest.mark.parametrize("count, kind", [
    (None, None), (0, "individual"), (20, "individual"), (21, "small_shop"), (200, "small_shop"),
    (201, "large_reseller"), (977, "large_reseller"),
])
def test_seller_type(count, kind):
    assert C.seller_type(count) == kind


@pytest.mark.parametrize("label, expected", [
    ("Men > Coats & Jackets > Bomber", "jackets_outerwear"), ("Jackets & Coats", "jackets_outerwear"),
    ("Puffer Vest", "jackets_outerwear"), ("Denim Jacket", "jackets_outerwear"), ("Fleece", "jackets_outerwear"),
    ("Hoodies & Sweatshirts", "hoodies_sweatshirts"), ("Sweatshirts", "hoodies_sweatshirts"),
    ("Sweaters", "sweaters_knitwear"), ("Women > Cardigans", "sweaters_knitwear"),
    ("Sweater Vest", "sweaters_knitwear"),
    ("T-Shirts", "tshirts"), ("Graphic Tees", "tshirts"), ("Tops > T-Shirts", "tshirts"),
    ("Shirts", "shirts"), ("Button-Ups", "shirts"), ("Flannel", "shirts"), ("Polos", "shirts"),
    ("Dress Shirts", "shirts"), ("Denim Shirt", "shirts"),
    ("Jeans", "jeans_pants"), ("Pants", "jeans_pants"), ("Sweatpants", "jeans_pants"),
    ("Dress Pants", "jeans_pants"), ("Cargo", "jeans_pants"),
    ("Dresses", "dresses_skirts"), ("Skirts", "dresses_skirts"), ("Denim Skirt", "dresses_skirts"),
    ("Sneakers", "sneakers"), ("Athletic Shoes", "sneakers"), ("Boots", "sneakers"), ("Dress Shoes", "sneakers"),
    ("Shorts", None), ("Hats", None), ("Accessories", None), ("Tops", None), ("", None), (None, None),
])
def test_category_from_label(label, expected):
    assert C.category_from_label(label) == expected


@pytest.mark.parametrize("text, expected", [
    ("US", True), ("usa", True), ("United States", True), ("Austin, TX, United States", True),
    ("Canada", False), ("United Kingdom", False), ("Europe", False), ("GB", False),
    ("", None), (None, None),
])
def test_is_us(text, expected):
    assert C.is_us(text) is expected


@pytest.mark.parametrize("raw, expected", [
    ("Carhartt", "Carhartt"), ("carhartt", "Carhartt"), ("CARHARTT", "Carhartt"),
    ("The North Face", "The North Face"), ("north face", "The North Face"), ("TNF", "The North Face"),
    ("Levis", "Levi's"), ("LEVI'S", "Levi's"), ("Levi Strauss & Co.", "Levi's"),
    ("Arcteryx", "Arc'teryx"), ("arc'teryx", "Arc'teryx"), ("dr martens", "Dr. Martens"), ("Doc Martens", "Dr. Martens"),
    ("new balance", "New Balance"), ("Carhartt WIP", "Carhartt WIP"),
    ("ralph lauren", "Ralph Lauren"), ("RALPH LAUREN", "RALPH LAUREN"), ("J.Crew", "J.Crew"), ("  Zara  ", "Zara"),
    ("", None), (None, None), ("unbranded", None), ("No Brand", None), ("Other", None), ("N/A", None),
    ("Vintage", None), ("handmade", None),
])
def test_normalize_brand(raw, expected):
    assert C.normalize_brand(raw) == expected


# --- building blocks every mapper uses -------------------------------------------------------

def cost(**kw):
    return C.make_cost(**kw)


def test_make_cost_basic_and_with_shipping_and_markdown():
    assert cost(price=48) == dict(price_cents=4800, currency="USD", shipping_cents=None, free_shipping=None,
                                  total_cents=4800, original_price_cents=None, retail_price_cents=None)
    c = cost(price="48.00", shipping="5.99", original=60)
    assert (c["total_cents"], c["shipping_cents"], c["free_shipping"], c["original_price_cents"]) == (5399, 599, False, 6000)


@pytest.mark.parametrize("kw, free", [
    (dict(price=10, shipping=0), True), (dict(price=10, shipping=0, free_shipping=False), False),
    (dict(price=10, free_shipping=True), True), (dict(price=10), None),
])
def test_free_shipping_is_derived_from_zero_shipping_unless_stated(kw, free):
    assert cost(**kw)["free_shipping"] is free


@pytest.mark.parametrize("original", [None, 0, 48, 30, "n/a"])
def test_original_price_only_counts_when_it_is_a_markdown(original):
    assert cost(price=48, original=original)["original_price_cents"] is None


@pytest.mark.parametrize("kw, reason", [
    (dict(price=None), "no_price"), (dict(price=-3), "no_price"), (dict(price="free"), "no_price"),
    (dict(price=48, currency="GBP"), "non_usd"), (dict(price=48, currency="eur"), "non_usd"),
])
def test_make_cost_drops_unusable_prices(kw, reason):
    with pytest.raises(C.Drop, match=reason):
        cost(**kw)


def test_make_cost_accepts_usd_in_any_case_or_unstated():
    assert cost(price=1, currency="usd")["currency"] == "USD" and cost(price=1, currency=None)["currency"] == "USD"


def test_clean_images_keeps_http_urls_once_in_order():
    urls = ["https://a/1.jpg", None, "", "ftp://x", "//cdn/2.jpg", "https://a/1.jpg", "http://b/3.jpg", 5]
    assert C.clean_images(urls) == ["https://a/1.jpg", "http://b/3.jpg"]
    assert C.clean_images(None) == []


def test_require_returns_the_value_or_drops():
    assert C.require("x", "no_title") == "x"
    for empty in (None, "", [], 0):
        with pytest.raises(C.Drop, match="no_title"):
            C.require(empty, "no_title")
