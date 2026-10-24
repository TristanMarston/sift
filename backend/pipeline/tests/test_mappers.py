"""Per-marketplace mappers, tested on sanitized real samples in tests/fixtures/."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from listing import Normalized
from normalize import depop, ebay, grailed, mercari, poshmark
from normalize.common import Drop

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)
MAPPERS = {"depop": depop.map_item, "poshmark": poshmark.map_item, "grailed": grailed.map_item, "mercari": mercari.map_item,
           "ebay": ebay.map_item}


def fx(mp):
    return json.loads((FIX / f"{mp}.json").read_text(encoding="utf-8"))


def mapped(mp, i=0, query_category="tshirts", **override):
    raw = copy.deepcopy(fx(mp)[i])
    raw.update(override)
    return MAPPERS[mp](raw, query_category, NOW)


@pytest.mark.parametrize("mp", MAPPERS)
def test_every_real_sample_maps_to_a_valid_row_and_the_label_beats_the_query_category(mp):
    for raw in fx(mp):
        n = MAPPERS[mp](copy.deepcopy(raw), "tshirts", NOW)
        assert isinstance(n, Normalized) and n.id.startswith(mp + ":") and n.id.endswith(n.external_id)
        assert n.category == "jackets_outerwear" and n.image_urls and n.seller.region and n.scraped_at == NOW
        assert n.status == "active" and n.cost.currency == "USD" and n.title and n.description


@pytest.mark.parametrize("mp", MAPPERS)
def test_a_missing_label_falls_back_to_the_query_category(mp):
    labels = {"depop": dict(category=None, productType=None, group=None), "poshmark": dict(category=None, breadcrumbs=[]),
              "grailed": dict(category=None, categoryPath=None), "mercari": dict(category=None, categoryPath=None),
              "ebay": dict(categoryPath=None, itemSpecifics={})}[mp]   # eBay's Type specific is part of its label
    assert mapped(mp, query_category="sneakers", **labels).category == "sneakers"


@pytest.mark.parametrize("mp, label", [
    ("depop", dict(category="Accessories", productType="hats", group="hats")),
    ("poshmark", dict(category="Hats", breadcrumbs=["Women", "Accessories", "Hats"])),
    ("grailed", dict(category="accessories", categoryPath="accessories.hats")),
    ("mercari", dict(category="Hats", categoryPath="Women > Accessories > Hats")),
    ("ebay", dict(categoryPath="Clothing, Shoes & Accessories > Men > Men's Accessories > Hats",
                  itemSpecifics={"Type": "Baseball Cap"})),
])
def test_a_hat_is_dropped_not_filed_under_the_query_category(mp, label):
    with pytest.raises(Drop, match="unmapped_category"):
        mapped(mp, query_category="jackets_outerwear", **label)


@pytest.mark.parametrize("mp, override, reason", [
    ("depop", dict(price={"amount": None, "currency": "USD"}), "no_price"),
    ("depop", dict(price={"amount": 20, "currency": "GBP"}), "non_usd"),
    ("depop", dict(pictureUrls=[]), "no_image"),
    ("depop", dict(url=None), "no_url"),
    ("depop", dict(sizes=["6 years"], size="6 years"), "kids"),      # Depop has no kids label; its kids sizes say so
    ("depop", dict(sizes=["12-18 months"], size="12-18 months"), "kids"),
    ("poshmark", dict(price=None), "no_price"),
    ("poshmark", dict(currency="CAD"), "non_usd"),
    ("poshmark", dict(images=[], main_image=None), "no_image"),
    ("poshmark", dict(breadcrumbs=["Kids", "Boys", "Jackets & Coats"]), "kids"),
    ("mercari", dict(price=None), "no_price"),
    ("mercari", dict(currency="CAD"), "non_usd"),
    ("mercari", dict(photoUrls=[], imageUrl=None), "no_image"),
    ("mercari", dict(categoryPath="Kids > Boys coats & jackets > Boys (4+)"), "kids"),
    ("mercari", dict(type="search"), "not_listing"),
    ("grailed", dict(price=None), "no_price"),
    ("grailed", dict(photos=[], coverPhoto=None), "no_image"),
    ("ebay", dict(priceValue=None), "no_price"),
    ("ebay", dict(currency="GBP"), "non_usd"),
    ("ebay", dict(images=[]), "no_image"),
    ("ebay", dict(buyingFormat="auction"), "auction"),    # its price is the current bid, not what the item will cost
    ("ebay", dict(categoryPath="Clothing, Shoes & Accessories > Kids > Boys > Coats, Jackets & Vests"), "kids"),
])
def test_unusable_records_are_dropped_with_a_reason(mp, override, reason):
    with pytest.raises(Drop, match=reason):
        mapped(mp, **override)


# --- Depop ----------------------------------------------------------------------------------

def test_depop_fields():
    n = mapped("depop", 0)
    assert (n.id, n.external_id, n.brand, n.subcategory, n.size, n.color) == \
           ("depop:965376720", "965376720", "The North Face", "jackets", "L", "white")
    assert (n.condition, n.condition_raw) == ("like_new", "Used - like new")
    assert n.url == "https://www.depop.com/products/seller-the-north-face-white-fuzzy-f24d/"
    assert (n.cost.price_cents, n.cost.original_price_cents, n.cost.shipping_cents, n.cost.total_cents) == (2850, 3000, None, 2850)
    assert (n.seller.region, n.seller.type, n.seller.rating) == ("US", None, None) and n.specifics == {}


def test_depop_first_size_no_colour_and_no_markdown():
    n = mapped("depop", 2)
    assert n.size == "XL" and n.condition == "like_new" and n.cost.original_price_cents is None
    assert mapped("depop", 1).color is None


def test_depop_title_is_the_first_line_of_the_description_because_its_own_title_is_five_words_of_it():
    assert mapped("depop", 0).title == "The North Face white fuzzy jacket"            # was "The North Face White Fuzzy"
    assert mapped("depop", 2).title == "women’s The North Face TNF Apex softshell jacket, size XL"
    assert mapped("depop", 0, description="\n\nCarhartt Detroit Jacket in brown #workwear#detroit\nSize L").title == \
           "Carhartt Detroit Jacket in brown"


def test_depop_title_skips_a_first_line_of_only_emoji():
    assert mapped("depop", 0, description="✨✨✨\nCarhartt Detroit Jacket #workwear").title == "Carhartt Detroit Jacket"


@pytest.mark.parametrize("description", [None, "", "#vintage #y2k #carhartt", "✨ 🔥"])
def test_depop_title_falls_back_to_the_actors_title(description):
    assert mapped("depop", 0, description=description).title == "The North Face White Fuzzy"


def test_depop_title_from_a_long_first_line_is_cut_at_a_word():
    title = mapped("depop", 0, description="Carhartt " * 30).title
    assert len(title) <= 120 and title.endswith("Carhartt")


@pytest.mark.parametrize("category", ["Clothing", "Shoes"])
def test_depop_kids_items_have_only_a_broad_category(category):
    """Depop's kids department has broad categories ("Kids > Shoes"); adult items have specific ones ("Men > Footwear >
    Sneakers"). Checked on the listing pages. A kids item whose size is "Other" is caught this way."""
    with pytest.raises(Drop, match="kids"):
        mapped("depop", 0, category=category, sizes=["Other"], size="Other")


def test_depop_vests_under_tops_are_tank_tops_not_jackets():
    """Depop is British: a "vest" under tops is a tank top (its product type is "vests-tanks-camis")."""
    with pytest.raises(Drop, match="unmapped_category"):
        mapped("depop", 0, category="Tops", group="tops", productType="vests-tanks-camis")
    assert mapped("depop", 0, category="Outerwear", group="coats-jackets", productType="vests").category == "jackets_outerwear"


def test_depop_sold_and_non_us_seller_with_a_usd_price_is_kept_with_its_region():
    n = mapped("depop", 0, isSold=True, country="GB")
    assert n.status == "sold" and n.seller.region == "GB"


# --- Poshmark -------------------------------------------------------------------------------

def test_poshmark_fields():
    n = mapped("poshmark", 0)
    assert (n.id, n.brand, n.size, n.color, n.subcategory) == ("poshmark:6acbf84b28951ffc17205cc0", "The North Face", "M", "Blue", "Jackets & Coats")
    assert (n.cost.price_cents, n.cost.total_cents) == (9000, 9000)
    assert (n.condition, n.condition_raw, n.seller.region) == (None, None, "US")
    assert n.title == fx("poshmark")[0]["name"] and len(n.image_urls) == 3


def test_poshmark_condition_comes_from_the_sellers_words_when_stated():
    n = mapped("poshmark", 0, description="Excellent used condition, no flaws. Measurements in photos")
    assert (n.condition, n.condition_raw) == ("like_new", "Excellent used condition")
    assert mapped("poshmark", 0, name="NWT The North Face jacket").condition == "new_with_tags"
    assert mapped("poshmark", 0, description="Not brand new, worn twice").condition is None


def test_poshmark_original_price_is_the_retail_price_not_a_markdown():
    """Poshmark's "Original Price" is what the item cost new (API.md: retail_price_cents), not an earlier listing price."""
    n = mapped("poshmark", 0)
    assert (n.cost.retail_price_cents, n.cost.original_price_cents) == (22500, None)
    assert mapped("poshmark", 0, regular_price=0).cost.retail_price_cents is None
    assert mapped("poshmark", 2).cost.retail_price_cents is None


def test_poshmark_status():
    assert mapped("poshmark", 0, listing_status="sold_out").status == "sold"
    assert mapped("poshmark", 0, in_stock=False).status == "sold"


# --- Grailed --------------------------------------------------------------------------------

def test_grailed_fields_and_us_shipping():
    n = mapped("grailed", 0)
    assert (n.id, n.brand, n.size, n.condition, n.subcategory) == ("grailed:109434912", "The North Face", "l", "new_with_tags", "vests")
    assert (n.cost.price_cents, n.cost.original_price_cents, n.cost.shipping_cents, n.cost.total_cents) == (8500, 13000, 1499, 9999)
    assert (n.seller.region, n.seller.type, n.seller.listing_count, n.seller.rating) == ("US", "individual", 2, None)


def test_grailed_seller_country_not_listing_region_and_big_sellers():
    n = mapped("grailed", 1)     # item listed in Europe by a US seller with 70k listings
    assert (n.seller.region, n.seller.type, n.condition) == ("US", "large_reseller", "good")
    assert n.seller.rating == pytest.approx(4.81, abs=0.01)


def test_grailed_free_shipping_no_markdown_and_foreign_seller_kept():
    n = mapped("grailed", 3)
    assert (n.cost.free_shipping, n.cost.original_price_cents, n.cost.total_cents) == (True, None, 71400)
    assert (n.seller.region, n.condition) == ("CN", "like_new")


def test_grailed_style_tags_are_passed_on_for_the_vintage_flag():
    assert mapped("grailed", 0, styles=["vintage", "gorpcore"]).specifics == {"Styles": "vintage, gorpcore"}
    assert mapped("grailed", 0, styles=[]).specifics == {}


def test_grailed_brand_comes_from_the_designer_list_without_the_vintage_tag():
    tnf, vintage, supreme = {"id": 1106, "name": "The North Face"}, {"id": 160, "name": "Vintage"}, {"id": 6, "name": "Supreme"}
    tagged = mapped("grailed", 0, designer="The North Face × Vintage", designers=[tnf, vintage], styles=[])
    assert tagged.brand == "The North Face" and tagged.specifics == {"Vintage": "Yes"}
    assert mapped("grailed", 0, designer="Supreme × The North Face", designers=[supreme, tnf]).brand == "Supreme × The North Face"
    assert mapped("grailed", 0, designers=None).brand == "The North Face"   # falls back to `designer`
    assert mapped("grailed", 0, designers=[vintage]).brand is None


def test_grailed_without_us_shipping_has_unknown_shipping():
    n = mapped("grailed", 0, shipping={"us": {"amount": 20, "enabled": False}})
    assert n.cost.shipping_cents is None and n.cost.total_cents == 8500


# --- eBay -----------------------------------------------------------------------------------

def test_ebay_fields():
    n = mapped("ebay", 0)
    assert (n.id, n.brand, n.size, n.color, n.subcategory) == ("ebay:860021552093", "The North Face", "L", "TNF Black / TNF White Logo", "Jacket")
    assert n.url == "https://www.ebay.com/itm/860021552093"
    assert (n.condition, n.condition_raw, n.status, n.seller.region) == ("like_new", "Pre-owned - Excellent", "active", "US")
    assert (n.cost.price_cents, n.cost.shipping_cents, n.cost.free_shipping, n.cost.total_cents) == (15500, 0, True, 15500)
    assert n.specifics["Outer Shell Material"] == "Nylon" and n.specifics["Product Line"] == "The North Face Nuptse"


def test_ebay_shoes_have_their_size_under_us_shoe_size():
    spec = {k: v for k, v in fx("ebay")[0]["itemSpecifics"].items() if k != "Size"}
    assert mapped("ebay", 0, itemSpecifics={**spec, "US Shoe Size": "10.5", "UK Shoe Size": "9.5"}).size == "10.5"


def test_ebay_paid_shipping_adds_up_to_the_total_ebay_shows():
    n = mapped("ebay", 1)
    assert (n.cost.price_cents, n.cost.shipping_cents, n.cost.free_shipping, n.cost.total_cents) == (2599, 666, False, 3265)


def test_ebay_seller_type_and_rating_scale():
    private = mapped("ebay", 2).seller
    big = mapped("ebay", 3).seller
    assert (private.type, private.rating) == ("individual", 5.0)
    assert (big.type, big.rating) == ("large_reseller", pytest.approx(4.99, abs=0.02))
    assert mapped("ebay", 3, sellerFeedbackScore=40).seller.type == "small_shop"


@pytest.mark.parametrize("score, percentage", [(0, 0), (37, 0)])
def test_ebay_zero_percent_positive_means_no_recent_feedback_not_a_bad_seller(score, percentage):
    assert mapped("ebay", 2, sellerFeedbackScore=score, sellerFeedbackPercentage=percentage).seller.rating is None


def test_ebay_condition_uses_only_the_label_before_the_seller_prose_and_html_entities_are_decoded():
    assert mapped("ebay", 3).condition == "good"
    assert "&#039;" not in mapped("ebay", 1).description and "men's" in mapped("ebay", 1).description


@pytest.mark.parametrize("type_, category", [("T-Shirt", "tshirts"), ("Blouse", "shirts"), ("Tank Top", None), (None, None)])
def test_ebay_type_says_what_a_generic_tops_category_is(type_, category):
    """eBay files women's tees under "Women's Clothing > Tops", which is none of our 8 categories."""
    spec = {k: v for k, v in fx("ebay")[0]["itemSpecifics"].items() if k != "Type"} | ({"Type": type_} if type_ else {})
    tops = dict(categoryPath="Clothing, Shoes & Accessories > Women > Women's Clothing > Tops", itemSpecifics=spec)
    if category is None:
        with pytest.raises(Drop, match="unmapped_category"):
            mapped("ebay", 0, **tops)
    else:
        assert mapped("ebay", 0, **tops).category == category


def test_ebay_foreign_item_location_is_kept_with_its_country_and_ended_listings_are_sold():
    n = mapped("ebay", 0, itemLocation="Located in China", listingStatus="ENDED")
    assert n.seller.region == "China" and n.status == "sold"


# --- Mercari (automation_craft/mercari-us-scraper, details on) -------------------------------

def test_mercari_fields():
    n = mapped("mercari", 0)
    assert (n.id, n.external_id, n.brand, n.size, n.color, n.subcategory) == \
           ("mercari:m48783721469", "m48783721469", "The North Face", "XS (0-2)", None, "Puffer Coats & Jackets")
    assert (n.condition, n.condition_raw, n.status, n.url) == ("like_new", "Like new", "active", "https://www.mercari.com/us/item/m48783721469/")
    assert n.seller.region == "US" and len(n.image_urls) == 3 and n.description


def test_mercari_buyer_pays_shipping_and_a_brand_new_seller_has_no_rating():
    n = mapped("mercari", 0)
    assert (n.cost.price_cents, n.cost.shipping_cents, n.cost.free_shipping, n.cost.total_cents) == (3100, 849, False, 3949)
    assert (n.seller.rating, n.seller.listing_count, n.seller.type) == (None, 26, "small_shop")   # rating 0 from 0 reviews = unknown


def test_mercari_seller_pays_shipping_so_it_is_free_for_the_buyer_whatever_fee_the_actor_lists():
    n = mapped("mercari", 1)
    assert (n.cost.shipping_cents, n.cost.free_shipping, n.cost.total_cents) == (0, True, 26000)
    assert (n.brand, n.seller.rating, n.seller.listing_count, n.seller.type) == (None, 5.0, 13, "individual")


def test_mercari_zero_fee_and_a_big_seller():
    n = mapped("mercari", 2)
    assert (n.cost.shipping_cents, n.cost.free_shipping, n.cost.total_cents) == (0, True, 8500)
    assert (n.seller.type, n.condition, n.subcategory) == ("large_reseller", "good", 'Active Jackets for Men')


def test_mercari_markdowns_are_real_prices_in_cents():
    cut = mapped("mercari", 3)     # Mercari shows 23.94, was 27.94: both actors we tried agree
    assert (cut.cost.price_cents, cut.cost.original_price_cents, cut.cost.total_cents) == (2394, 2794, 3243)
    assert mapped("mercari", 4).cost.original_price_cents == 9000


def test_mercari_status_and_the_track_jacket_category():
    assert mapped("mercari", 0, status="sold_out").status == "sold" and mapped("mercari", 0, sold=True).status == "sold"
    assert mapped("mercari", 1).category == "jackets_outerwear"   # "Men > Coats & jackets > Fleece jacket"
    track = mapped("mercari", 0, categoryPath="Men > Sweats & hoodies > Track jacket", category="Track Jackets")
    assert track.category == "jackets_outerwear"
