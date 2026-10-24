import pytest

from backend import wear as W

JACKET = {"low": 80, "high": 160}


def test_expected_wears_scale_with_quality_and_condition():
    assert W.expected_wears(JACKET, "unknown", "new_with_tags") == {"low": 80, "high": 160, "mid": 120}
    assert W.expected_wears(JACKET, "high", "good") == {"low": 96, "high": 192, "mid": 144}   # x1.5 x0.8
    assert W.expected_wears(JACKET, "low", "fair") == {"low": 41, "high": 82, "mid": 61}      # x0.85 x0.6


def test_unknown_condition_uses_the_middle_factor():
    assert W.expected_wears(JACKET, "unknown", None)["mid"] == 102  # 120 x 0.85


def test_expected_wears_never_drop_below_one():
    assert W.expected_wears({"low": 1, "high": 1}, "low", "fair") == {"low": 1, "high": 1, "mid": 1}


def test_cpw_rounds_half_up_to_whole_cents():
    assert W.cpw(4800, 144) == 33
    assert W.cpw(150, 100) == 2   # 1.5 -> 2, not banker's 2... and 2.5 -> 3 below
    assert W.cpw(250, 100) == 3


def test_cpw_table():
    assert W.cpw_table(4800, 144) == {"at_30": 160, "at_60": 80, "at_100": 48, "at_mid": 33}


def test_typical_is_the_median_price_and_wears():
    assert W.typical([1000, 3000, 9000], [50, 100, 200]) == {"price_cents": 3000, "expected_wears_mid": 100, "cpw_cents": 30}
    assert W.typical([1000, 3000], [50, 101])["price_cents"] == 2000
    assert W.typical([], []) is None


def test_break_even_only_for_items_pricier_than_typical():
    typ = {"price_cents": 4000, "expected_wears_mid": 60, "cpw_cents": 67}
    assert W.break_even(4800, typ) == 72          # ceil(4800 / 67)
    assert W.break_even(4000, typ) is None        # not pricier: it already wins on price
    assert W.break_even(3000, typ) is None
    assert W.break_even(4800, None) is None


def test_wear_facts_show_the_baseline_and_condition_assumptions():
    base = {"as_of": "2026-10-23", "source": "team assumption", "categories": {"jackets_outerwear": JACKET}}
    facts = W.wear_facts("jackets_outerwear", base, "good", "Good - used")
    assert [f["kind"] for f in facts] == ["baseline", "condition"]
    assert facts[0]["value"] == "80–160 wears for jackets & outerwear (assumption)"
    assert facts[0]["source"] == "baseline" and facts[0]["status"] == "inferred" and facts[0]["as_of"] == "2026-10-23"
    assert facts[1]["value"] == "Good: about 80% of its life left (assumption)"
    assert facts[1]["snippet"] == "Good - used"


def test_wear_facts_cite_the_category_source_and_drop_the_assumption_label():
    base = {"as_of": "2026-10-23", "source": "PEFCR", "source_url": "https://pefcr.pdf",
            "categories": {"jackets_outerwear": JACKET,
                           "sneakers": {"low": 67, "high": 167, "source": "PEFCR, expert judgement"}}}
    jacket = W.wear_facts("jackets_outerwear", base, None, None)[0]
    assert jacket["value"] == "80–160 wears for jackets & outerwear"
    assert jacket["snippet"] == "PEFCR" and jacket["source_url"] == "https://pefcr.pdf"
    assert W.wear_facts("sneakers", base, None, None)[0]["snippet"] == "PEFCR, expert judgement"


def test_unknown_condition_is_said_out_loud():
    base = {"as_of": "2026-10-23", "source": "s", "categories": {"tshirts": {"low": 30, "high": 60}}}
    assert W.wear_facts("tshirts", base, None, None)[1]["value"] == "Condition not stated: assume about 85% of its life left"


@pytest.mark.parametrize("cond,factor", [("new_with_tags", 1.0), ("like_new", 0.95), ("good", 0.8), ("fair", 0.6), (None, 0.85)])
def test_condition_factors(cond, factor):
    assert W.CONDITION[cond] == factor
