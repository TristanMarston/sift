"""ml/evidence/brands.yaml: every claim on a receipt must be sourced, and every listing brand must match one row."""
from datetime import date
from pathlib import Path

import pytest
import yaml

from backend import markers, ranker

BRANDS = yaml.safe_load((Path(ranker.ML) / "evidence" / "brands.yaml").read_text())["brands"]
CERTS = set(markers.CERT_LABEL)


def ids(b):
    return b["name"]


@pytest.mark.parametrize("b", BRANDS, ids=ids)
def test_every_claim_has_a_value_and_an_https_source(b):
    for key in ("repair_program", "guarantee"):
        if key in b:
            assert b[key]["value"].strip() and b[key]["url"].startswith("https://"), key
    for c in b.get("certifications", []):
        assert c["name"] in CERTS and c["url"].startswith("https://"), c


@pytest.mark.parametrize("b", BRANDS, ids=ids)
def test_every_row_is_dated_and_checked_by_someone(b):
    assert isinstance(b["as_of"], date)
    assert b.get("verified_by"), "a teammate must open each URL before the row ships"


@pytest.mark.parametrize("b", BRANDS, ids=ids)
def test_a_row_says_something(b):
    assert {"repair_program", "guarantee", "certifications"} & set(b), "a brand with no facts adds nothing"


def test_no_two_brands_claim_the_same_listing_name():
    keys = [markers.brand_key(n) for b in BRANDS for n in [b["name"], *b.get("aliases", [])]]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("listing_brand", ["Carhartt", "Patagonia", "Nike", "The North Face", "THE NORTH FACE",
                                           "Levi's", "LEVIS"])
def test_demo_and_top_catalog_brands_are_covered(listing_brand):
    assert markers.brand_key(listing_brand) in ranker.load_config().brands
