import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import scrape as S
from scrape import Task


class FakeClient:
    """Stands in for ApifyClient. `statuses` maps call index -> SUCCEEDED/FAILED/NONE/RAISE."""

    def __init__(self, items=3, statuses=None):
        self.calls, self.items, self.statuses = [], items, statuses or {}

    def actor(self, actor_id):
        client = self

        class Actor:
            def call(self, **kw):
                n = len(client.calls)
                client.calls.append((actor_id, kw))
                status = client.statuses.get(n, "SUCCEEDED")
                if status == "RAISE":
                    raise RuntimeError("network down")
                if status == "NONE":
                    return None
                return SimpleNamespace(id=f"run{n}", status=status, default_dataset_id=f"ds{n}", usage_total_usd=0.01,
                                       status_message=None if status == "SUCCEEDED" else "actor crashed")
        return Actor()

    def dataset(self, dataset_id):
        rows = [{"id": f"{dataset_id}-{k}", "title": "tee", "sellerUsername": "bob",
                 "seller": {"username": "bob", "id": 7, "ratingAverage": 4.9}} for k in range(self.items)]
        return SimpleNamespace(iterate_items=lambda: iter(rows))


def t(mp="depop", cat="tshirts", q="boxy tee", n=100):
    return Task(mp, cat, q, n)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


# --- plan ----------------------------------------------------------------------------------

QUERIES = {
    "tshirts": {"depop": [("a1", 10), ("a2", 10)], "ebay": [("b1", 10), ("b2", 10)]},
    "sneakers": {"depop": [("c1", 10), ("c2", 10)], "ebay": [("d1", 10)]},
}


def test_plan_is_breadth_first_over_queries_categories_and_marketplaces():
    order = [(x.query) for x in S.build_plan(QUERIES)]
    assert order == ["a1", "b1", "c1", "d1", "a2", "b2", "c2"]


def test_plan_can_be_limited_to_some_marketplaces():
    assert {x.marketplace for x in S.build_plan(QUERIES, only=["ebay"])} == {"ebay"}


def test_smoke_plan_is_one_20_item_query_per_marketplace():
    assert S.smoke_plan(QUERIES) == [Task("depop", "tshirts", "a1", 20), Task("ebay", "tshirts", "b1", 20)]


def test_estimate_simulates_the_quota_stop_and_sums_best_case_cost_and_worst_case_caps():
    plan = [t(q=f"d{i}", n=100) for i in range(5)] + [t("ebay", q="e0", n=10)]
    est = S.estimate(plan, {"depop": 250, "ebay": 1000})
    assert est["depop"] == dict(runs=3, rows=300, est_usd=Decimal("0.300"), cap_usd=Decimal("0.39"))
    assert est["ebay"] == dict(runs=1, rows=10, est_usd=Decimal("0.070"), cap_usd=Decimal("0.09"))


# --- actor inputs and the charge cap -------------------------------------------------------

@pytest.mark.parametrize("mp, expected", [
    ("depop", {"query": "carhartt jacket", "maxItems": 50}),
    ("grailed", {"searchQuery": "carhartt jacket", "maxItems": 50, "scrapeDetails": True}),
    ("poshmark", {"categoryUrls": ["https://poshmark.com/search?query=carhartt+jacket&type=listings&src=dir"],
                  "maxResultsPerScrape": 50, "usePagination": True, "scrapeProductDetails": True}),
    ("mercari", {"keyword": "carhartt jacket", "limit": 50, "status": ["on_sale"],
                 "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"],
                                        "apifyProxyCountry": "US"}}),
    ("ebay", {"searchQueries": ["carhartt jacket"], "maxItems": 50, "marketplace": "ebay.com", "mode": "active",
              "condition": "used", "detailedItems": True, "includeDescription": True, "includeSummary": False}),
])
def test_run_input_per_actor(mp, expected):
    assert S.ACTORS[mp].build_input("carhartt jacket", 50) == expected


def test_charge_cap_is_the_expected_cost_plus_25_percent_rounded_up_to_the_cent():
    assert S.charge_cap("depop", 100) == Decimal("0.13")
    assert S.charge_cap("grailed", 20) == Decimal("0.31")
    assert S.charge_cap("depop", 10) == Decimal("0.05")  # floor


def test_cap_is_a_call_option_never_part_of_run_input(tmp_path):
    client = FakeClient()
    S.run_plan(client, [t(n=100)], None, tmp_path)
    actor_id, kw = client.calls[0]
    assert actor_id == "jongoose/depop-scraper"
    assert kw["run_timeout"] == timedelta(minutes=30)  # a hung actor ends as TIMED-OUT instead of stalling the run
    assert kw["max_total_charge_usd"] == Decimal("0.13")
    assert kw["run_input"] == {"query": "boxy tee", "maxItems": 100}
    assert "max_total_charge_usd" not in kw["run_input"]


# --- privacy -------------------------------------------------------------------------------

def test_scrub_removes_identity_at_any_depth_and_keeps_the_rest():
    item = {"id": 1, "sellerUsername": "bob", "SELLER_URL": "u", "seller_name": "Bob", "avatarUrl": "a",
            "seller": {"id": 7, "username": "bob", "name": "Bob", "ratingAverage": 4.9, "totalBoughtAndSold": 977},
            "nested": [{"sellerUrl": "x", "price": 5}], "price": {"amount": 5}}
    assert S.scrub(item) == {"id": 1, "seller": {"ratingAverage": 4.9, "totalBoughtAndSold": 977},
                             "nested": [{"price": 5}], "price": {"amount": 5}}


def test_scrub_does_not_touch_item_ids_outside_seller_blocks():
    assert S.scrub({"id": 9, "name": "Detroit jacket"}) == {"id": 9, "name": "Detroit jacket"}


# --- running -------------------------------------------------------------------------------

def test_successful_run_writes_scrubbed_raw_file_and_logs_it(tmp_path):
    S.run_plan(FakeClient(items=3), [t()], None, tmp_path)
    rows = read_jsonl(tmp_path / "raw" / "depop" / "run0.jsonl")
    assert len(rows) == 3
    assert all("sellerUsername" not in r and "username" not in r["seller"] and "id" not in r["seller"] for r in rows)
    assert rows[0]["seller"]["ratingAverage"] == 4.9
    (log,) = read_jsonl(tmp_path / "runs.jsonl")
    assert (log["marketplace"], log["category"], log["query"], log["status"], log["items"], log["run_id"]) == \
           ("depop", "tshirts", "boxy tee", "SUCCEEDED", 3, "run0")
    assert log["est_charge_usd"] == pytest.approx(0.003)


def test_an_empty_dataset_is_a_finished_run_with_zero_items(tmp_path):
    S.run_plan(FakeClient(items=0), [t()], None, tmp_path)
    (log,) = read_jsonl(tmp_path / "runs.jsonl")
    assert (log["status"], log["items"]) == ("SUCCEEDED", 0)


@pytest.mark.parametrize("status, expected", [("FAILED", "FAILED"), ("TIMED-OUT", "TIMED-OUT"),
                                              ("ABORTED", "ABORTED"), ("NONE", "NO_RUN"), ("RAISE", "ERROR")])
def test_bad_runs_are_logged_not_saved_and_do_not_stop_the_others(tmp_path, status, expected):
    client = FakeClient(statuses={0: status})
    S.run_plan(client, [t(q="one"), t(q="two")], None, tmp_path)
    first, second = read_jsonl(tmp_path / "runs.jsonl")
    assert (first["status"], first["items"]) == (expected, 0)
    assert first["status_message"] and second["status"] == "SUCCEEDED"
    assert not (tmp_path / "raw" / "depop" / "run0.jsonl").exists()
    assert len(client.calls) == 2


def test_rerun_skips_successful_queries_and_retries_failed_ones(tmp_path):
    plan = [t(q="one"), t(q="two")]
    S.run_plan(FakeClient(statuses={1: "FAILED"}), plan, None, tmp_path)
    again = FakeClient()
    S.run_plan(again, plan, None, tmp_path)
    assert [kw["run_input"]["query"] for _, kw in again.calls] == ["two"]


def test_a_marketplace_stops_at_its_quota_and_others_continue(tmp_path):
    plan = [t("depop", q=f"d{i}") for i in range(5)] + [t("ebay", q=f"e{i}") for i in range(2)]
    client = FakeClient(items=3)
    S.run_plan(client, plan, {"depop": 5, "ebay": 100}, tmp_path)
    ran = [kw["run_input"].get("query") or kw["run_input"]["searchQueries"][0] for _, kw in client.calls]
    assert ran == ["d0", "d1", "e0", "e1"]  # 3 + 3 rows >= 5 stops depop


def test_quota_counts_rows_from_earlier_runs(tmp_path):
    S.run_plan(FakeClient(items=3), [t(q="one")], None, tmp_path)
    again = FakeClient(items=3)
    S.run_plan(again, [t(q="two"), t(q="three")], {"depop": 5}, tmp_path)
    assert len(again.calls) == 1  # 3 earlier + 3 now >= 5


def test_three_failures_in_a_row_give_up_on_that_marketplace_only(tmp_path):
    plan = [t("depop", q=f"d{i}") for i in range(5)] + [t("ebay", q="e0")]
    client = FakeClient(statuses={0: "FAILED", 1: "FAILED", 2: "FAILED"})
    S.run_plan(client, plan, None, tmp_path)
    assert [a for a, _ in client.calls] == ["jongoose/depop-scraper"] * 3 + ["memo23/ebay-search-scraper-ppe"]


def test_a_success_resets_the_failure_streak(tmp_path):
    plan = [t(q=f"d{i}") for i in range(6)]
    client = FakeClient(statuses={0: "FAILED", 1: "FAILED", 3: "FAILED", 4: "FAILED"})
    S.run_plan(client, plan, None, tmp_path)
    assert len(client.calls) == 6


def test_max_spend_stops_before_the_worst_case_would_exceed_it(tmp_path):
    client = FakeClient(items=100)  # each run really costs 100 * 0.001 = 0.10, and may cost up to the 0.13 cap
    S.run_plan(client, [t(q=f"d{i}", n=100) for i in range(5)], None, tmp_path, max_spend=Decimal("0.30"))
    assert len(client.calls) == 2  # after two runs 0.20 is spent; a third could reach 0.33


# --- the real queries.yaml -----------------------------------------------------------------

@pytest.fixture(scope="module")
def cfg():
    return S.load_config(Path(__file__).parents[1] / "queries.yaml")


def test_queries_cover_exactly_the_api_categories_and_marketplaces(cfg):
    from typing import get_args
    import listing
    assert set(cfg.queries) == set(get_args(listing.Category))
    assert set(cfg.quotas) == set(get_args(listing.Marketplace)) == set(S.ACTORS)
    for by_mp in cfg.queries.values():
        assert set(by_mp) == set(S.ACTORS)


def test_every_query_is_capped_at_500_and_unique_per_marketplace(cfg):
    for by_mp in cfg.queries.values():
        for qs in by_mp.values():
            assert all(1 <= n <= 500 for _, n in qs)
    for mp in S.ACTORS:
        flat = [q for by_mp in cfg.queries.values() for q, _ in by_mp[mp]]
        assert len(flat) == len(set(flat)), mp


def test_pool_can_reach_the_50k_stage(cfg):
    for mp, quota in cfg.quotas.items():
        capacity = sum(n for by_mp in cfg.queries.values() for _, n in by_mp[mp])
        assert capacity >= 3 * quota, (mp, capacity, quota)


def test_demo_props_and_conference_tees_are_queried(cfg):
    def has(cat, mp, text):
        return any(text in q for q, _ in cfg.queries[cat][mp])
    for mp in ("depop", "poshmark", "grailed", "mercari", "ebay"):
        assert has("jackets_outerwear", mp, "carhartt detroit"), mp
        assert has("jackets_outerwear", mp, "better sweater"), mp
        assert has("sneakers", mp, "dunk low"), mp
    assert has("tshirts", "depop", "conference tee") and has("tshirts", "depop", "hackathon shirt")


def test_first_queries_are_broad_so_the_test_run_is_representative(cfg):
    plan = S.smoke_plan(cfg.queries)
    assert {x.marketplace for x in plan} == set(S.ACTORS) and all(x.max_items == 20 for x in plan)
