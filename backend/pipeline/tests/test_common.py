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
    ("US", "US"), ("usa", "US"), ("United States", "US"), ("Located in United States", "US"),
    ("Hattiesburg, United States", "US"), ("Austin, TX, United States", "US"),
    ("Located in China", "China"), ("Berlin, Germany", "Germany"), ("Europe", "Europe"), ("MY", "MY"),
    ("", None), (None, None),
])
def test_normalize_region_is_coarse_and_never_a_filter(text, expected):
    assert C.normalize_region(text) == expected


@pytest.mark.parametrize("label, kids", [
    ("Kids > Girls coats & jackets > Girls (4+)", True), ("Boys", True), ("Baby & toddler", True),
    ("Women > Coats & jackets > Fleece jacket", False), ("Clothing > Men > Men's Clothing", False), ("", False), (None, False),
])
def test_is_kids(label, kids):
    assert C.is_kids(label) is kids


@pytest.mark.parametrize("label, expected", [
    ("tops.t_shirts", "tshirts"), ("tops.button_ups", "shirts"), ("tops.sweatshirts_hoodies", "hoodies_sweatshirts"),
    ("tops.long_sleeve_shirts", "shirts"), ("tops.sweaters_knitwear", "sweaters_knitwear"),
    ("bottoms.denim", "jeans_pants"), ("bottoms.sweatpants_joggers", "jeans_pants"), ("bottoms.shorts", None),
    ("footwear.sneakers", "sneakers"), ("outerwear.light_jackets", "jackets_outerwear"),
    ("tailoring.blazers", "jackets_outerwear"), ("flat shirt", "shirts"),
])
def test_category_from_marketplace_slugs(label, expected):
    assert C.category_from_label(label) == expected


@pytest.mark.parametrize("label, expected", [
    ("Clothing, Shoes & Accessories > Men > Men's Clothing > Coats, Jackets & Vests", "jackets_outerwear"),
    ("Clothing, Shoes & Accessories > Men > Men's Clothing > Activewear > Activewear Jackets", "jackets_outerwear"),
    ("Clothing, Shoes & Accessories > Women > Women's Shoes > Athletic Shoes", "sneakers"),
    ("Clothing, Shoes & Accessories > Men > Men's Accessories > Hats", None),
])
def test_ebay_root_category_does_not_make_everything_footwear(label, expected):
    assert C.category_from_label(label) == expected


@pytest.mark.parametrize("label, expected", [
    ("Men > Sweats & hoodies > Track jacket", "jackets_outerwear"),     # Mercari files track jackets under hoodies
    ("Women > Sweats & hoodies > Hoodie", "hoodies_sweatshirts"),
    ("Men > Sweats & hoodies > Other", "hoodies_sweatshirts"),          # unmapped leaf: the parent decides
    ("Women > Coats & jackets > Puffer", "jackets_outerwear"),
    ("Men > Athletic apparel > Jackets", "jackets_outerwear"),
    ("Women > Accessories > Hats", None),
])
def test_the_leaf_of_a_category_path_wins_over_its_parents(label, expected):
    assert C.category_from_label(label) == expected


def test_resolve_category_prefers_the_label_and_never_lets_a_hat_inherit_the_query_category():
    assert C.resolve_category("Jackets & Coats", "tshirts") == "jackets_outerwear"
    assert C.resolve_category("", "tshirts") == "tshirts" and C.resolve_category(None, "sneakers") == "sneakers"
    with pytest.raises(C.Drop, match="unmapped_category"):
        C.resolve_category("accessories.hats", "jackets_outerwear")


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


@pytest.mark.parametrize("text, one_line, expected", [
    ("\u200bWoolrich  Womens\u00a0XL", True, "Woolrich Womens XL"),
    ("100%\u200bcotton\u2060 tee", True, "100%cotton tee"),
    ("soft\u00adware", True, "software"),
    ("line one\n\nline  two\u00a0here  ", False, "line one\n\nline two here"),
    ("  \u200b ", True, None), ("", False, None), (None, False, None),
])
def test_clean_text_removes_invisible_characters_and_odd_spaces(text, one_line, expected):
    assert C.clean_text(text, one_line=one_line) == expected
