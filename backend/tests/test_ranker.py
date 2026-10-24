import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from backend import ranker as R
from conftest import ev, make_row

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schema" / "api.schema.json").read_text())
CFG = R.Config(
    baselines={"as_of": "2026-10-23", "source": "team assumption",
               "categories": {"jackets_outerwear": {"low": 80, "high": 160}, "tshirts": {"low": 30, "high": 60}}},
    brands=R.markers.index_brands([{"name": "Carhartt", "as_of": "2026-10-24",
                                    "repair_program": {"value": "Repairs", "url": "https://carhartt.example/r"}}]),
)
QUERY = {"category": "jackets_outerwear", "filters": {}}


def validate(resp):
    errors = list(Draft202012Validator({**SCHEMA, "$ref": "#/$defs/SearchResponse"}).iter_errors(resp))
    assert not errors, [e.message for e in errors[:5]]


def price(cents, **kw):
    return dict(cost=dict(price_cents=cents, total_cents=cents), **kw)


@pytest.fixture
def hits():
    """A jacket search: the cheapest match is fair and unbranded; a like-new Carhartt Detroit costs a bit more."""
    return [
        (make_row("cheap", condition="fair", brand=None, **price(1500)), 0.95),
        (make_row("mid", condition="like_new", brand="Carhartt", title="Carhartt Detroit Jacket",
                  evidence=[ev("materials.fibers", "product_line", "inferred", "Detroit: cotton duck")], **price(2500)), 0.90),
        (make_row("nwt", condition="new_with_tags", brand="Carhartt", **price(6500)), 0.85),
        (make_row("plain", condition="like_new", **price(3000)), 0.80),
        (make_row("pricey", condition="good", **price(12000)), 0.78),
    ]


def ids(rows):
    return [r["id"] for r in rows]


def test_response_matches_the_api_schema(hits):
    validate(R.rank(hits, QUERY, CFG))


def test_empty_search_is_valid_and_has_no_typical():
    resp = R.rank([], QUERY, CFG)
    validate(resp)
    assert resp["results"] == [] and resp["typical"] is None
    assert resp["headline"] == {"cheapest_id": None, "cheapest_rank_by_cpw": None}
    assert resp["slider"] == [[]] * 11


def test_results_come_in_cost_per_wear_order(hits):
    resp = R.rank(hits, QUERY, CFG)
    cpw = [r["wear"]["cpw_cents"]["at_mid"] for r in resp["results"]]
    assert cpw == sorted(cpw) and ids(resp["results"]) == resp["orders"]["cpw"]


def test_every_order_is_a_permutation_of_the_results(hits):
    resp = R.rank(hits, QUERY, CFG)
    for order in [*resp["orders"].values(), *resp["slider"]]:
        assert sorted(order) == sorted(ids(resp["results"]))


def test_price_and_match_orders(hits):
    o = R.rank(hits, QUERY, CFG)["orders"]
    assert o["price"] == ["depop:cheap", "depop:mid", "depop:plain", "depop:nwt", "depop:pricey"]
    assert o["match"] == ["depop:cheap", "depop:mid", "depop:nwt", "depop:plain", "depop:pricey"]


def test_eco_order_ranks_built_to_last_cotton_first_and_a_vintage_piece_above_a_worn_one(hits):
    hits[3] = (make_row("plain", condition="like_new", flags={"is_vintage": True, "is_deadstock": False,
                                                                "is_upcycled": False}, **price(3000)), 0.80)
    o = R.rank(hits, QUERY, CFG)["orders"]["eco"]
    assert o[0] == "depop:mid"                                  # cotton duck, known line: lasts longest
    assert o.index("depop:plain") < o.index("depop:cheap")     # vintage, like new, beats fair condition


def test_slider_ends_are_the_value_and_match_orders(hits):
    resp = R.rank(hits, QUERY, CFG)
    assert resp["slider"][0] == resp["orders"]["cpw"]
    assert resp["slider"][10] == resp["orders"]["match"]


def test_demo_guard_a_well_evidenced_item_beats_the_cheapest_per_wear(hits):
    resp = R.rank(hits, QUERY, CFG)
    assert resp["headline"]["cheapest_id"] == "depop:cheap"
    assert resp["headline"]["cheapest_rank_by_cpw"] > 1
    assert resp["orders"]["cpw"] != resp["orders"]["price"]


def test_break_even_only_on_items_pricier_than_typical(hits):
    resp = R.rank(hits, QUERY, CFG)
    typ = resp["typical"]["price_cents"]
    for r in resp["results"]:
        assert (r["wear"]["break_even_wears"] is not None) == (r["cost"]["total_cents"] > typ)


def test_match_band_and_small_thumbnail(hits):
    res = {r["id"]: r for r in R.rank(hits, QUERY, CFG)["results"]}
    assert res["depop:cheap"]["match"] == {"similarity": 0.95, "band": "exact"}
    assert res["depop:pricey"]["match"]["band"] == "similar"
    assert res["depop:cheap"]["thumb_url"].endswith("/P5.jpg")


def test_receipt_numbers_can_be_recomputed_from_the_facts(hits):
    r = {r["id"]: r for r in R.rank(hits, QUERY, CFG)["results"]}["depop:mid"]
    assert r["quality"]["level"] == "high"                     # repair program + product line
    assert r["wear"]["expected_wears"] == {"low": 114, "high": 228, "mid": 171}   # x1.5 high, x0.95 like new
    assert r["wear"]["basis"] == "evidence_adjusted" and r["wear"]["cpw_cents"]["at_mid"] == 15
    assert [f["kind"] for f in r["wear"]["facts"]] == ["baseline", "condition"]
    assert r["confidence"] in {"low", "medium", "high"}


def test_seller_identity_fields_are_not_passed_through(hits):
    r = R.rank(hits, QUERY, CFG)["results"][0]
    assert set(r["seller"]) == {"type", "rating", "region"}
    assert "description" not in r and "evidence" not in r


def test_missing_baseline_category_is_an_error_not_a_guess():
    with pytest.raises(KeyError):
        R.rank([(make_row("x", category="sneakers"), 0.9)], QUERY, CFG)


def test_load_config_reads_the_repo_files():
    cfg = R.load_config()
    assert set(cfg.baselines["categories"]) == {"tshirts", "hoodies_sweatshirts", "shirts", "sweaters_knitwear",
                                                "jeans_pants", "jackets_outerwear", "sneakers", "dresses_skirts"}
    assert isinstance(cfg.brands, dict)


def test_match_order_is_the_order_the_index_gave(hits):
    """The index already ranks by similarity (minus the colour penalty when it has colours), so the match sort keeps
    that order instead of re-sorting by the raw similarity."""
    swapped = [hits[1], hits[0], *hits[2:]]                       # 0.90 before 0.95
    resp = R.rank(swapped, QUERY, CFG)
    assert resp["orders"]["match"][:2] == [swapped[0][0]["id"], swapped[1][0]["id"]]


@pytest.mark.parametrize("sim, band", [(0.95, "exact"), (0.9, "exact"), (0.8986, "close"), (0.8, "close"), (0.72, "similar")])
def test_three_match_bands(sim, band):
    """0.90 and 0.72 both read "similar" before; a 0.80-0.90 match looks like the same garment in another colour or
    cut, so it gets its own band."""
    assert R.band(sim) == band


def test_eco_percentile_places_each_result_among_the_others(hits):
    """"Greener than 72% of these matches": the share of the other results with a lower eco score."""
    res = R.rank(hits, QUERY, CFG)["results"]
    ps = sorted(r["eco"]["percentile"] for r in res)
    assert ps[0] == 0 and ps[-1] == 100 and all(0 <= p <= 100 for p in ps)
    best = max(res, key=lambda r: r["eco"]["score"])
    assert best["eco"]["percentile"] == 100
    assert R.rank(hits[:1], QUERY, CFG)["results"][0]["eco"]["percentile"] == 100


def test_headline_says_how_close_the_best_match_is(hits):
    assert R.rank(hits, QUERY, CFG)["headline"]["match"] == "exact"          # best similarity 0.95
    low = [(row, min(sim, 0.7)) for row, sim in hits]
    assert R.rank(low, QUERY, CFG)["headline"]["match"] == "similar"
    assert R.rank([], QUERY, CFG)["headline"]["match"] is None
