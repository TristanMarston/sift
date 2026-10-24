"""Batches: what the next one scrapes (planning), and the loop that runs, checks and continues them."""
from decimal import Decimal

import pytest

import scrape as S
from run import batch as B


def cfg(quotas=None):
    q = {"tshirts": {"depop": [("t1", 100), ("t2", 100), ("t3", 100)], "ebay": [("e1", 50), ("e2", 50)]},
         "sneakers": {"depop": [("s1", 100), ("s2", 100)], "ebay": [("f1", 50)]}}
    return S.Config(quotas or {"depop": 900, "ebay": 300}, q)


def ran(mp, cat, query, items=100, verdict="ok", status="SUCCEEDED"):
    return dict(marketplace=mp, category=cat, query=query, items=items, verdict=verdict, status=status, est_charge_usd=0.1)


# --- planning ------------------------------------------------------------------------------------

def test_rows_are_split_in_the_quota_ratio_and_queries_stay_breadth_first():
    lanes = B.plan_batch(cfg(), [], 400)
    assert {mp: lane.rows for mp, lane in lanes.items()} == {"depop": 300, "ebay": 100}
    assert [t.query for t in lanes["depop"].tasks] == ["t1", "s1", "t2", "s2", "t3"]
    assert lanes["depop"].quota == 300 and lanes["ebay"].quota == 100


def test_done_queries_are_skipped_bad_ones_retried_and_a_lane_never_passes_its_quota():
    past = [ran("depop", "tshirts", "t1"), ran("depop", "sneakers", "s1", verdict="blocked"),
            *[ran("depop", "tshirts", q, items=300) for q in ("x1", "x2")]]
    lanes = B.plan_batch(cfg(), past, 4000)
    assert [t.query for t in lanes["depop"].tasks] == ["s1", "t2", "s2", "t3"]
    assert lanes["depop"].rows == 900 - 700 and lanes["depop"].quota == 900     # 700 rows so far (the blocked run's don't count)


def test_a_marketplace_with_a_full_quota_or_no_queries_left_is_not_in_the_batch():
    full = [ran("ebay", "tshirts", "x", items=300)]
    assert set(B.plan_batch(cfg(), full, 400)) == {"depop"}
    used_up = [ran("ebay", c, q, items=10) for c, q in (("tshirts", "e1"), ("tshirts", "e2"), ("sneakers", "f1"))]
    assert set(B.plan_batch(cfg(), used_up, 400)) == {"depop"}


def test_filters_choose_marketplaces_and_categories_and_the_rows_go_to_what_is_chosen():
    lanes = B.plan_batch(cfg(), [], 400, only={"ebay"}, categories={"sneakers"})
    assert list(lanes) == ["ebay"] and lanes["ebay"].rows == 300   # capped by its quota
    assert [t.query for t in lanes["ebay"].tasks] == ["f1"]
    assert list(B.plan_batch(cfg(), [], 400, skip={"depop"})) == ["ebay"]


def test_each_lane_carries_its_best_and_worst_case_cost():
    lane = B.plan_batch(cfg(), [], 400)["ebay"]                  # 2 eBay runs of 50 rows
    assert lane.est_usd == 2 * (50 * Decimal("0.005") + Decimal("0.02"))
    assert lane.cap_usd == 2 * S.charge_cap("ebay", 50)


def test_fit_shrinks_the_batch_until_its_worst_case_fits_the_money():
    rows, lanes = B.fit(cfg(), [], 400, Decimal("0.60"))
    assert rows < 400 and 0 < sum(l.cap_usd for l in lanes.values()) <= Decimal("0.60")
    assert B.fit(cfg(), [], 400, Decimal("100")) == (400, B.plan_batch(cfg(), [], 400))
    assert B.fit(cfg(), [], 400, Decimal("0.05")) == (0, {})
