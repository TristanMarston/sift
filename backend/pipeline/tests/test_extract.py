from datetime import date

import pytest

import extract as X
from listing import Fiber, Listing, Normalized


def norm(**over):
    base = dict(
        id="ebay:1", marketplace="ebay", external_id="1", url="https://ebay.com/itm/1",
        title="Plain tee", status="active", scraped_at="2026-10-24T01:00:00Z", category="tshirts",
        image_urls=["https://img.example/1.jpg"], cost=dict(price_cents=2000, total_cents=2000),
    )
    return Normalized(**{**base, **over})


def ex(text, **over):
    return X.extract(norm(description=text, **over))


def fibers(text):
    return [(f.fiber, f.pct, f.organic, f.recycled) for f in X.parse_fibers(text)[0]]


# --- composition ---------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("100% cotton", [("cotton", 100, None, None)]),
    ("100 % Cotton", [("cotton", 100, None, None)]),
    ("99.5% cotton 0.5% elastane", [("cotton", 99.5, None, None), ("elastane", 0.5, None, None)]),
    ("60% Cotton / 40% Polyester", [("cotton", 60, None, None), ("polyester", 40, None, None)]),
    ("95% cotton 5% spandex", [("cotton", 95, None, None), ("elastane", 5, None, None)]),
    ("80% poly", [("polyester", 80, None, None)]),
    ("100% polyamide", [("nylon", 100, None, None)]),
    ("100% rayon", [("viscose", 100, None, None)]),
    ("100% tencel", [("lyocell", 100, None, None)]),
    ("100% merino wool", [("wool", 100, None, None)]),
    ("100% organic cotton", [("cotton", 100, True, None)]),
    ("100% recycled polyester", [("polyester", 100, None, True)]),
    ("100% cotton ... 100% cotton", [("cotton", 100, None, None)]),
    ("2100% cotton", [("cotton", None, None, None)]),
    ("150% cotton", []),
])
def test_percent_compositions(text, expected):
    assert fibers(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("cotton tee", [("cotton", None, None, None)]),
    ("organic cotton hoodie", [("cotton", None, True, None)]),
    ("recycled polyester fleece", [("polyester", None, None, True)]),
    ("wool blend sweater", [("wool", None, None, None)]),
    ("Woolrich jacket", []),
    ("Cotton On tee", []),
    ("silk screen graphic tee", []),
    ("button down shirt", []),
    ("vegan leather jacket", [("synthetic_leather", None, None, None)]),
    ("faux leather pants", [("synthetic_leather", None, None, None)]),
    ("genuine leather jacket", [("leather", None, None, None)]),
    ("leather patch on the sleeve", []),
    ("", []),
])
def test_bare_words_and_traps(text, expected):
    assert fibers(text) == expected


def test_percent_wins_over_bare_word_for_the_same_fiber():
    assert fibers("100% cotton, soft cotton feel") == [("cotton", 100, None, None)]


def test_snippet_quotes_the_matched_text():
    assert X.parse_fibers("Shell 60% cotton, 40% polyester. Great shape")[1] == "60% cotton; 40% polyester"


def F(fiber, pct=None):
    return Fiber(fiber=fiber, pct=pct)


@pytest.mark.parametrize("fs, pcts, share, suspect", [
    ([F("cotton", 100)], [100], 0, False),
    ([F("cotton", 60), F("polyester", 40)], [60, 40], 40, False),
    ([F("cotton", 55), F("polyester", 40)], [57.9, 42.1], 42.1, False),
    ([F("cotton", 100), F("polyester", 100)], [100, 100], None, True),
    ([F("cotton", 60)], [60], None, True),
    ([F("cotton")], [None], None, False),
    ([], [], None, False),
])
def test_materials_normalize_and_flag(fs, pcts, share, suspect):
    m = X.to_materials(fs, [])
    assert [f.pct for f in m.fibers] == pcts
    assert m.synthetic_share == share
    assert m.composition_suspect is suspect


# --- certifications, flags, text facts ------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("GOTS certified organic cotton", ["gots"]),
    ("OEKO-TEX Standard 100", ["oeko_tex"]),
    ("oeko tex certified", ["oeko_tex"]),
    ("bluesign approved fabric", ["bluesign"]),
    ("Fair Trade Certified sewn", ["fair_trade"]),
    ("fairtrade cotton", ["fair_trade"]),
    ("Responsible Wool Standard (RWS)", ["rws"]),
    ("RDS down", ["rds"]),
    ("B-Corp brand", ["b_corp"]),
    ("gots + bluesign", ["gots", "bluesign"]),
    ("forgots", []),
    ("nothing here", []),
])
def test_certifications(text, expected):
    assert ex(text).materials.certifications == expected


@pytest.mark.parametrize("text, vintage, deadstock, upcycled", [
    ("Vintage 90s Levi's", True, False, False),
    ("vintage wash denim", False, False, False),
    ("Vintage Fit 501", False, False, False),
    ("Deadstock NWT", False, True, False),
    ("dead stock from the 80s", False, True, False),
    ("new old stock", False, True, False),
    ("upcycled flannel", False, False, True),
    ("Up-cycled patchwork", False, False, True),
    ("plain tee", False, False, False),
])
def test_flags(text, vintage, deadstock, upcycled):
    f = ex(text).flags
    assert (f.is_vintage, f.is_deadstock, f.is_upcycled) == (vintage, deadstock, upcycled)


@pytest.mark.parametrize("text, cents", [
    ("Retails for $120", 12000),
    ("retail: $98.50", 9850),
    ("Original retail price $60", 6000),
    ("MSRP $75", 7500),
    ("retails for $1,200", 120000),
    ("retail tags attached", None),
    ("retail 100% cotton", None),
])
def test_retail_price(text, cents):
    assert ex(text).cost.retail_price_cents == cents


@pytest.mark.parametrize("text, country", [
    ("Made in USA", "USA"), ("made in the USA", "USA"), ("Made in China", "China"),
    ("Handmade in Peru", None), ("made in 1995", None), ("no origin", None),
])
def test_made_in(text, country):
    assert ex(text).country_of_manufacture == country


# --- product lines --------------------------------------------------------------------------

def test_product_lines_file_covers_the_demo_props():
    lines = {(p.brand, tuple(p.title_has)) for p in X.PRODUCT_LINES}
    assert ("Carhartt", ("detroit",)) in lines
    assert ("Patagonia", ("better", "sweater")) in lines


def test_product_line_matches_on_brand_and_title():
    hit = X.match_product_line("Carhartt", "Carhartt DETROIT Jacket Brown", X.PRODUCT_LINES)
    assert hit.note == "Carhartt Detroit → cotton duck"
    assert X.match_product_line(None, "Patagonia Better Sweater fleece", X.PRODUCT_LINES)
    assert X.match_product_line(" PATAGONIA ", "better sweater", X.PRODUCT_LINES)
    assert X.match_product_line("Carhartt", "Carhartt beanie", X.PRODUCT_LINES) is None
    assert X.match_product_line("Carhartt WIP", "Carhartt WIP detroit jacket", X.PRODUCT_LINES) is None
    assert X.match_product_line("Nike", "Nike detroit jacket", X.PRODUCT_LINES) is None


# --- extract() ------------------------------------------------------------------------------

def test_extract_from_description_records_claimed_evidence():
    out = X.extract(norm(title="Nike tee", description="Soft. 100% cotton. Vintage. Retails for $40. Made in Mexico"))
    assert isinstance(out, Listing)
    assert [(f.fiber, f.pct) for f in out.materials.fibers] == [("cotton", 100)]
    assert out.materials.synthetic_share == 0
    assert out.flags.is_vintage and out.cost.retail_price_cents == 4000
    assert out.country_of_manufacture == "Mexico"
    by_field = {e.field: e for e in out.evidence}
    assert (by_field["materials.fibers"].status, by_field["materials.fibers"].source) == ("claimed", "listing_text")
    assert by_field["materials.fibers"].snippet == "100% cotton"
    assert by_field["flags.is_vintage"].as_of == date(2026, 10, 24)


def test_structured_specifics_win_over_text():
    out = X.extract(norm(description="100% polyester", specifics={"Material": "Cotton Blend"}))
    assert [f.fiber for f in out.materials.fibers] == ["cotton"]
    assert out.evidence[0].source == "specifics"


@pytest.mark.parametrize("material, expected", [
    ("Leather", ["leather"]), ("Down", ["down"]), ("Poly", ["polyester"]), ("Faux Leather", ["synthetic_leather"]),
    ("Wool, Leather", ["wool", "leather"]), ("Denim", []),
])
def test_a_material_field_is_unambiguous_so_leather_and_down_count(material, expected):
    out = X.extract(norm(specifics={"Material": material}))
    assert [f.fiber for f in out.materials.fibers] == expected


def test_specifics_without_a_material_fall_back_to_text():
    out = X.extract(norm(description="100% nylon", specifics={"Color": "Blue", "Material": ""}))
    assert [f.fiber for f in out.materials.fibers] == ["nylon"] and out.evidence[0].source == "listing_text"


def test_specifics_country_beats_text():
    out = X.extract(norm(description="made in china", specifics={"Country/Region of Manufacture": "Vietnam"}))
    assert out.country_of_manufacture == "Vietnam"


def test_product_line_fills_in_only_when_nothing_is_stated():
    out = X.extract(norm(brand="Patagonia", title="Patagonia Better Sweater Jacket", category="jackets_outerwear"))
    assert [(f.fiber, f.recycled) for f in out.materials.fibers] == [("polyester", True)]
    ev = out.evidence[0]
    assert (ev.field, ev.status, ev.source) == ("materials.fibers", "inferred", "product_line")
    stated = X.extract(norm(brand="Patagonia", title="Patagonia Better Sweater", description="100% wool"))
    assert [f.fiber for f in stated.materials.fibers] == ["wool"]


def test_missing_material_is_null_with_unknown_evidence():
    out = X.extract(norm(title="Black tee", description=None))
    assert out.materials.fibers == [] and out.materials.synthetic_share is None
    assert [(e.field, e.status) for e in out.evidence] == [("materials.fibers", "unknown")]


def test_actor_retail_price_beats_text():
    out = X.extract(norm(description="retail $99", cost=dict(price_cents=2000, total_cents=2000, retail_price_cents=8000)))
    assert out.cost.retail_price_cents == 8000


def test_certification_evidence_and_other_fields_untouched():
    n = norm(title="GOTS organic tee", brand="Pact", size="M", description="Oeko-Tex too")
    out = X.extract(n)
    assert out.materials.certifications == ["gots", "oeko_tex"]
    assert (out.brand, out.size, out.url, out.id) == ("Pact", "M", n.url, n.id)
    assert "materials.certifications" in {e.field for e in out.evidence}
