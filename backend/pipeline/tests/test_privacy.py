"""No seller identity in fixtures, raw files, or pipeline output (SPEC.md §12)."""
import json
import re
from pathlib import Path

import pytest

import jsonl

from test_mappers import FIX, MAPPERS, NOW, fx

ROOT = Path(__file__).parents[1]
FORBIDDEN = re.compile(r"^(seller_?(user)?name|seller_?url|seller_?id|username|user_?id|avatar_?url|profile_?url|"
                       r"paypal_merchant_id|account_preferences|email|profilelogo)$", re.I)


def forbidden_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if FORBIDDEN.match(k):
                yield f"{path}.{k}"
            yield from forbidden_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from forbidden_keys(v, f"{path}[{i}]")


def test_the_detector_catches_what_it_should():
    assert list(forbidden_keys({"a": [{"sellerUsername": "x"}], "seller": {"avatarUrl": "u", "ratingCount": 3}})) == \
           [".a[0].sellerUsername", ".seller.avatarUrl"]


@pytest.mark.parametrize("mp", MAPPERS)
def test_fixtures_and_mapper_output_have_no_identity_keys(mp):
    assert not list(forbidden_keys(fx(mp)))
    for raw in fx(mp):
        assert not list(forbidden_keys(MAPPERS[mp](raw, "tshirts", NOW).model_dump(mode="json")))


def test_depop_fixture_urls_do_not_carry_a_real_seller_handle():
    assert all("/products/seller-" in r["url"] for r in fx("depop"))


def real_files():
    data = ROOT / "data"
    return sorted([*data.glob("raw/*/*.jsonl"), *data.glob("test/raw/*/*.jsonl"), *data.glob("normalized.jsonl"),
                   *data.glob("listings.jsonl"), *data.glob("test/normalized.jsonl"), *data.glob("test/listings.jsonl")])


def test_real_scraped_output_on_disk_has_no_identity_keys():
    """Scans whatever real data exists locally (data/ is gitignored); passes trivially when there is none."""
    for path in real_files():
        for n, line in enumerate(jsonl.read(path), 1):
            assert not list(forbidden_keys(json.loads(line))), f"{path}:{n}"
