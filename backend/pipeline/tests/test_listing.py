import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

import listing as L
from helpers import row
from listing import Listing

DEFS = json.loads((Path(__file__).parents[3] / "schema" / "api.schema.json").read_text())["$defs"]
RESULT = DEFS["Result"]["properties"]


@pytest.mark.parametrize("enum, expected", [
    (L.Marketplace, DEFS["Marketplace"]["enum"]),
    (L.Category, DEFS["Category"]["enum"]),
    (L.Condition, DEFS["Condition"]["enum"]),
    (L.Certification, RESULT["materials"]["properties"]["certifications"]["items"]["enum"]),
    (L.SellerType, [t for t in RESULT["seller"]["properties"]["type"]["enum"] if t]),
    (L.EvidenceStatus, DEFS["Fact"]["properties"]["status"]["enum"]),
    (L.EvidenceSource, DEFS["Fact"]["properties"]["source"]["enum"]),
])
def test_enums_match_schema(enum, expected):
    assert set(get_args(enum)) == set(expected)


def test_nested_fields_match_schema():
    models = Listing.model_fields
    for name in ("flags", "cost", "materials"):
        nested = models[name].annotation.model_fields
        assert set(nested) == set(RESULT[name]["properties"]), name
    fiber = RESULT["materials"]["properties"]["fibers"]["items"]["properties"]
    assert set(L.Fiber.model_fields) == set(fiber)
    assert set(RESULT["seller"]["properties"]) <= set(L.Seller.model_fields)


def test_top_level_fields_split_between_listing_and_ranker():
    ranker_only = {"match", "quality", "eco", "wear", "confidence", "thumb_url"}
    listing_only = {"external_id", "description", "status", "scraped_at", "country_of_manufacture", "evidence"}
    assert set(Listing.model_fields) == (set(RESULT) - ranker_only) | listing_only


def test_minimal_row_validates_and_round_trips():
    parsed = Listing(**row())
    assert parsed.cost.currency == "USD"
    assert parsed.flags.is_vintage is False
    assert parsed.materials.fibers == [] and parsed.materials.synthetic_share is None
    assert Listing.model_validate_json(parsed.model_dump_json()) == parsed


@pytest.mark.parametrize("bad", [
    dict(seller={"username": "bob"}),
    dict(seller={"type": "individual", "profile_url": "https://x.example/bob"}),
    dict(seller_username="bob"),
    dict(avatar_url="https://x.example/a.jpg"),
])
def test_rejects_seller_identity(bad):
    with pytest.raises(ValidationError):
        Listing(**row(**bad))


@pytest.mark.parametrize("bad", [
    dict(id="poshmark:other"),
    dict(id="etsy:64f1a2", marketplace="etsy"),
    dict(image_urls=[]),
    dict(category="hats"),
    dict(condition="mint"),
    dict(url="not a url"),
    dict(cost=dict(price_cents=4800, total_cents=4800, currency="EUR")),
    dict(cost=dict(price_cents=-1, total_cents=-1)),
    dict(cost=dict(price_cents=4800, shipping_cents=500, total_cents=4800)),
])
def test_rejects_invalid_rows(bad):
    with pytest.raises(ValidationError):
        Listing(**row(**bad))


def test_normalized_carries_specifics_but_listing_does_not():
    assert L.Normalized(**row(specifics={"Material": "Cotton"})).specifics == {"Material": "Cotton"}
    with pytest.raises(ValidationError):
        Listing(**row(specifics={"Material": "Cotton"}))


def test_total_is_price_plus_known_shipping():
    ok = Listing(**row(cost=dict(price_cents=4800, shipping_cents=500, total_cents=5300)))
    assert ok.cost.total_cents == 5300
