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


def test_done_queries_are_skipped_bad_ones_retried_and_rows_so_far_never_cap_a_batch():
    past = [ran("depop", "tshirts", "t1"), ran("depop", "sneakers", "s1", verdict="blocked"),
            *[ran("depop", "tshirts", q, items=600) for q in ("x1", "x2")]]       # 1,300 rows: past depop's quota of 900
    lanes = B.plan_batch(cfg(), past, 4000)
    assert [t.query for t in lanes["depop"].tasks] == ["s1", "t2", "s2", "t3"]
    assert lanes["depop"].rows == 3000 and lanes["depop"].quota == 1300 + 3000  # the blocked run's rows don't count


def test_a_marketplace_with_no_queries_left_gives_its_share_to_the_others():
    full = [ran("ebay", "tshirts", "x", items=300)]
    assert {mp: l.rows for mp, l in B.plan_batch(cfg(), full, 400).items()} == {"depop": 300, "ebay": 100}
    used_up = [ran("ebay", c, q, items=10) for c, q in (("tshirts", "e1"), ("tshirts", "e2"), ("sneakers", "f1"))]
    assert {mp: l.rows for mp, l in B.plan_batch(cfg(), used_up, 400).items()} == {"depop": 400}


def test_a_cheap_marketplaces_share_never_buys_expensive_rows():
    """Depop ($0.001 a row) runs out first. Its share must not turn into eBay ($0.005) or Grailed ($0.012) rows: a
    5,000-row batch would cost 45% more, and Grailed's cut of the money would climb from 31% to 55% as the cheap
    marketplaces ran dry. Freed rows go only to marketplaces no dearer per row; otherwise they stay unspent."""
    depop_done = [ran("depop", c, q, items=10) for c, q in (("tshirts", "t1"), ("tshirts", "t2"), ("tshirts", "t3"),
                                                            ("sneakers", "s1"), ("sneakers", "s2"))]
    assert {mp: l.rows for mp, l in B.plan_batch(cfg(), depop_done, 400).items()} == {"ebay": 100}


def test_a_dear_marketplaces_share_goes_to_the_cheaper_ones_only():
    q = {"tshirts": {"depop": [("t1", 100)], "ebay": [("e1", 50)], "grailed": [("g1", 50)]}}
    three = S.Config({"depop": 600, "ebay": 300, "grailed": 300}, q)
    ebay_done = [ran("ebay", "tshirts", "e1", items=10)]
    assert {mp: l.rows for mp, l in B.plan_batch(three, ebay_done, 1200).items()} == {"depop": 900, "grailed": 300}
    assert {mp: l.rows for mp, l in B.plan_batch(three, [], 1200).items()} == {"depop": 600, "ebay": 300, "grailed": 300}


def test_a_zero_quota_keeps_a_marketplace_out_of_batches():
    assert list(B.plan_batch(cfg({"depop": 900, "ebay": 0}), [], 400)) == ["depop"]
    assert B.plan_batch(cfg({"depop": 0, "ebay": 0}), [], 400) == {}


def test_filters_choose_marketplaces_and_categories_and_the_rows_go_to_what_is_chosen():
    lanes = B.plan_batch(cfg(), [], 400, only={"ebay"}, categories={"sneakers"})
    assert list(lanes) == ["ebay"] and lanes["ebay"].rows == 400
    assert [t.query for t in lanes["ebay"].tasks] == ["f1"]
    assert list(B.plan_batch(cfg(), [], 400, skip={"depop"})) == ["ebay"]


def test_each_lane_carries_its_best_and_worst_case_cost():
    lane = B.plan_batch(cfg(), [], 400)["ebay"]                  # 2 eBay runs of 50 rows
    assert lane.runs == 2
    assert lane.est_usd == 2 * (50 * Decimal("0.005") + Decimal("0.02"))
    assert lane.cap_usd == 2 * S.charge_cap("ebay", 50)


def test_fit_shrinks_the_batch_until_its_worst_case_fits_the_money():
    rows, lanes = B.fit(cfg(), [], 400, Decimal("0.60"))
    assert rows < 400 and 0 < sum(l.cap_usd for l in lanes.values()) <= Decimal("0.60")
    assert B.fit(cfg(), [], 400, Decimal("100")) == (400, B.plan_batch(cfg(), [], 400))
    assert B.fit(cfg(), [], 400, Decimal("0.05")) == (0, {})


# --- the loop ------------------------------------------------------------------------------------

import os
import signal
import json
import threading
import time

import jsonl
from run import checks as C
from fakes import MAPPERS, FakeApify, full_rows

SMALL = S.Config({"depop": 300, "ebay": 100},
                 {"tshirts": {"depop": [("t1", 100), ("t2", 100)], "ebay": [("e1", 50)]},
                  "sneakers": {"depop": [("s1", 100), ("s2", 100)], "ebay": [("f1", 50)]}})


def go(client, d, **kw):
    lines = []
    kw = {"rows": 200, "who": "laptop", "mappers": MAPPERS, "log": lines.append, **kw}
    return B.run_batches(client, SMALL, d, **kw), lines


def batch_dirs(d):
    return sorted(p for p in (d / "batches").iterdir()) if (d / "batches").exists() else []


def test_one_batch_scrapes_every_lane_checks_it_shares_it_and_rebuilds_the_catalog(tmp_path):
    client = FakeApify()
    code, lines = go(client, tmp_path)
    assert code == 0
    assert sorted(client.calls) == [("depop", "s1"), ("depop", "t1"), ("ebay", "e1")]   # 150 + 50 rows
    (b,) = batch_dirs(tmp_path)
    record = json.loads((b / "batch.json").read_text())
    assert record["stopped"] == {} and len(record["run_ids"]) == 3 and record["real_usd"] == pytest.approx(record["est_usd"])
    assert (b / "CHECKS.md").exists() and (b / "run_report.md").exists()
    assert [e["run_id"] for e in client.ledger()] == [e["run_id"] for e in jsonl.load(tmp_path / "runs.jsonl")]
    assert len(jsonl.read(tmp_path / "listings.jsonl")) == 250


def test_lanes_run_side_by_side_and_every_entry_lands_whole(tmp_path):
    both = threading.Barrier(2)

    def together(mp, q, n):
        if q in ("t1", "e1"):        # each lane's first run waits until the other lane's is running too
            both.wait(timeout=5)     # one lane at a time would break the barrier: that run then fails
        return full_rows(mp, q, n)
    go(FakeApify(rows=together), tmp_path)
    entries = jsonl.load(tmp_path / "runs.jsonl")
    assert len(entries) == 3 and all(e["status"] == "SUCCEEDED" for e in entries)


def test_batches_all_keeps_going_until_nothing_is_left(tmp_path):
    client = FakeApify()
    code, lines = go(client, tmp_path, batches=None)
    assert code == 0 and len(batch_dirs(tmp_path)) == 2 and len(client.calls) == 6      # every query, past the quotas
    assert any("nothing left to scrape" in l for l in lines)


def test_a_marketplace_that_fails_its_checks_sits_out_the_rest_of_the_command(tmp_path):
    junk = lambda mp, q, n: [{**r, "junk": mp == "depop"} for r in full_rows(mp, q, n)]   # eBay's keep list would drop "junk"
    client = FakeApify(rows=junk)
    code, lines = go(client, tmp_path, batches=None)
    assert code == 2
    assert [q for mp, q in client.calls if mp == "depop"] == ["t1"]      # judged junk once, never retried in this command
    assert [q for mp, q in client.calls if mp == "ebay"] == ["e1", "f1"]  # the other lane carried on
    first = json.loads((batch_dirs(tmp_path)[0] / "batch.json").read_text())
    assert list(first["stopped"]) == ["depop"] and any("depop" in l and "STOPPED" in l for l in lines)


def test_seller_identity_in_a_batch_stops_everything(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "judge", lambda *a, **k: [C.Check("all", "privacy", "fail", "raw/depop/x.jsonl:1 .username")])
    client = FakeApify()
    assert go(client, tmp_path, batches=None)[0] == 2 and len(batch_dirs(tmp_path)) == 1


def test_no_batch_starts_unless_its_worst_case_fits_the_account_balance_and_max_spend(tmp_path):
    poor = FakeApify(max_usage=205.0, usage=203.0)        # $2 left: all of it is the safety margin
    code, lines = go(poor, tmp_path / "a")
    assert code == 3 and poor.calls == [] and any("money" in l for l in lines)
    client = FakeApify()
    code, _ = go(client, tmp_path / "b", batches=None, max_spend=Decimal("0.70"))
    assert code == 3 and len(client.calls) == 3


def test_a_busy_token_is_refused_unless_forced(tmp_path):
    busy = FakeApify(active=1)
    code, lines = go(busy, tmp_path)
    assert code == B.EXIT_BUSY and busy.calls == [] and any("another runner" in l for l in lines)
    assert go(busy, tmp_path, force=True)[0] == 0 and busy.calls


def test_a_stop_file_halts_before_the_next_batch(tmp_path):
    (tmp_path / "STOP").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "STOP").touch()
    client = FakeApify()
    assert go(client, tmp_path)[0] == 4 and client.calls == []


def test_ctrl_c_lets_the_lanes_finish_their_current_run_then_stops(tmp_path):
    def interrupt(mp, q, n):
        os.kill(os.getpid(), signal.SIGINT)              # a real Ctrl-C, delivered to the main thread
        deadline = time.monotonic() + 10                 # this run stays "on Apify" until the main thread has handled it
        while not (tmp_path / "STOP").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        return full_rows(mp, q, n)
    client = FakeApify(rows=interrupt)
    old = signal.signal(signal.SIGINT, signal.default_int_handler)   # `pytest &` starts with Ctrl-C ignored
    try:
        code, lines = go(client, tmp_path, only={"depop"})
    finally:
        signal.signal(signal.SIGINT, old)
    assert code == 130 and len(client.calls) == 1 and not (tmp_path / "STOP").exists()
    assert len(jsonl.load(tmp_path / "runs.jsonl")) == 1 and len(batch_dirs(tmp_path)) == 1


def test_recheck_judges_an_old_batch_again(tmp_path):
    client = FakeApify()
    go(client, tmp_path)
    (b,) = batch_dirs(tmp_path)
    (b / "CHECKS.md").unlink()
    checks = B.recheck(client, tmp_path, b.name, mappers=MAPPERS)
    assert C.failed(checks) == {} and (b / "CHECKS.md").exists()
