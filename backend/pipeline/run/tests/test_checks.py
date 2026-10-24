"""Batch checks: each one's pass / warn / fail, which marketplaces stop, and the gathering from a real data folder."""
from collections import Counter
from datetime import datetime, timezone

import pytest

import extract as X
import jsonl
import scrape as S
from run import checks as C
from fakes import MAPPERS, FakeApify, mapper_for

NOW = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
MATERIAL = "100% cotton, barely worn, " + "d" * 40


def entry(run_id, mp="depop", cat="tshirts", items=10, verdict="ok", est=0.01):
    return dict(marketplace=mp, category=cat, query=f"q-{run_id}", run_id=run_id, status="SUCCEEDED", items=items,
                verdict=verdict, est_charge_usd=est, at="2026-10-24T10:00:00+00:00")


def listing(i, mp="depop", cat="tshirts", description=MATERIAL):
    return X.extract(mapper_for(mp)({"itemId": str(i), "description": description, "category": cat}, cat, NOW))


def judge(entries=None, listings=None, **kw):
    args = dict(entries=entries or [entry("r1")], listings=[listing(i) for i in range(10)] if listings is None else listings,
                invalid=Counter(), stats=Counter(), prior_ids=set(), real_usd={}, stopped={}, leaks=[])
    return C.assess(**{**args, **kw})


def level(checks, name, mp="depop"):
    (c,) = [c for c in checks if c.name == name and c.marketplace == mp]
    return c.level


def test_a_healthy_batch_passes_every_check():
    checks = judge()
    assert {c.level for c in checks} == {"ok"} and C.failed(checks) == {} and not C.stop_all(checks)


def test_a_lane_the_run_judge_stopped_fails_that_marketplace_only():
    checks = judge(entries=[entry("r1"), entry("r2", mp="ebay")],
                   listings=[listing(i) for i in range(10)] + [listing(i, mp="ebay") for i in range(10)],
                   stopped={"depop": "BLOCKED at 'q-r1': ran out of fresh addresses"})
    assert list(C.failed(checks)) == ["depop"] and level(checks, "run health", "ebay") == "ok"


@pytest.mark.parametrize("drops, expected", [({"no_price": 1}, ("fail", "ok")), ({"kids": 1}, ("ok", "ok")),
                                             ({"kids": 4}, ("ok", "warn"))])
def test_unusable_rows_fail_and_many_filtered_rows_warn(drops, expected):
    checks = judge(stats=Counter({f"drop:depop:{r}": n for r, n in drops.items()}),
                   listings=[listing(i) for i in range(10 - sum(drops.values()))])
    assert (level(checks, "unusable rows"), level(checks, "filtered rows")) == expected


@pytest.mark.parametrize("described, expected", [(10, "ok"), (8, "warn"), (6, "fail")])
def test_descriptions(described, expected):
    rows = [listing(i, description=MATERIAL if i < described else "short") for i in range(10)]
    assert level(judge(listings=rows), "descriptions") == expected


@pytest.mark.parametrize("known, expected", [(0, "ok"), (6, "warn"), (9, "fail")])
def test_new_listings_measure_what_the_rows_we_paid_for_added(known, expected):
    assert level(judge(prior_ids={f"depop:{i}" for i in range(known)}), "new listings") == expected


def test_listings_that_fail_validation_fail_the_marketplace():
    assert level(judge(invalid=Counter({"depop": 1})), "valid listings") == "fail"


@pytest.mark.parametrize("real, expected", [(None, "ok"), (0.02, "ok"), (0.20, "fail")])
def test_a_real_bill_well_above_our_estimate_means_the_actor_price_changed(real, expected):
    assert level(judge(real_usd={"r1": real}), "real cost") == expected


def test_few_stated_materials_and_empty_categories_only_warn():
    checks = judge(entries=[entry("r1"), entry("r2", cat="sneakers")],
                   listings=[listing(i, description="d" * 60) for i in range(20)])
    assert level(checks, "stated material") == "warn" and level(checks, "categories") == "warn"
    assert C.failed(checks) == {}


def test_a_marketplace_with_no_usable_rows_gets_a_warning_not_a_crash():
    checks = judge(entries=[entry("r1", items=0, verdict="empty")], listings=[])
    assert level(checks, "rows") == "warn" and C.failed(checks) == {}


def test_seller_identity_anywhere_stops_everything():
    checks = judge(leaks=["raw/depop/r1.jsonl:3 .sellerUsername"])
    assert C.stop_all(checks) and level(checks, "privacy", "all") == "fail"


# --- gathering from a data folder (same code as steps 02-03) -------------------------------------

def test_judge_reads_the_batch_from_disk_and_compares_it_with_the_runs_before_it(tmp_path):
    repeat = lambda mp, q, n: [{"type": "listing", "itemId": f"same-{k}", "description": MATERIAL} for k in range(n)]
    client = FakeApify(rows=repeat)
    S.run_plan(client, [S.Task("depop", "tshirts", "q1", 10)], None, tmp_path, log=lambda _: None)
    S.run_plan(client, [S.Task("depop", "tshirts", "q2", 10)], None, tmp_path, log=lambda _: None)
    first, second = jsonl.load(tmp_path / "runs.jsonl")
    assert C.failed(C.judge(client, tmp_path, [first], mappers=MAPPERS)) == {}
    checks = C.judge(client, tmp_path, [second], mappers=MAPPERS)
    assert level(checks, "new listings") == "fail"          # q2 returned the same 10 listings as q1


def test_judge_finds_identity_keys_in_the_batchs_raw_files_and_asks_apify_for_the_real_bill(tmp_path):
    client = FakeApify(cost=lambda mp, items: 5.0)
    S.run_plan(client, [S.Task("depop", "tshirts", "q1", 10)], None, tmp_path, log=lambda _: None)
    (e,) = jsonl.load(tmp_path / "runs.jsonl")
    jsonl.append(tmp_path / "raw" / "depop" / f"{e['run_id']}.jsonl", {"itemId": "x", "seller": {"username": "bob"}})
    checks = C.judge(client, tmp_path, [e], mappers=MAPPERS)
    assert C.stop_all(checks) and level(checks, "real cost") == "fail"


def test_the_report_has_a_line_per_check_and_says_what_stopped():
    checks = judge(stopped={"depop": "BLOCKED"})
    md = C.render("20261024-100000-laptop", checks, {"est_usd": 0.01, "real_usd": 0.01})
    assert "# Batch 20261024-100000-laptop" in md and "STOPPED: depop" in md
    assert md.count("\n| depop |") == len([c for c in checks if c.marketplace == "depop"])
