"""Is a run healthy? Outcome first (usable rows), logs second. Logs in tests/fixtures/logs are real Apify run logs:
five healthy ones (two of which contain scary-looking but harmless warnings) and the one run that was blocked."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

import health as H
from normalize import depop
from normalize.common import Drop

LOGS = Path(__file__).parent / "fixtures" / "logs"
NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def log(name):
    return (LOGS / f"{name}.log").read_text()


def rows(good=0, described=None, filtered=None, bad=None, dup=0):
    return H.RowCounts(good=good, duplicates=dup, described=good + dup if described is None else described,
                       filtered=Counter(filtered or {}), bad=Counter(bad or {}))


def assess(**kw):
    base = dict(status="SUCCEEDED", status_message=None, requested=20, rows=rows(good=20), log="")
    return H.assess(**{**base, **kw})


# --- real logs: healthy runs must stay healthy, the blocked run must be caught -----------------------

@pytest.mark.parametrize("name, message", [
    ("depop", None),
    ("poshmark", "Finished! Total 21 requests: 21 succeeded, 0 failed."),   # warns about 'blockedStatusCodes': harmless
    ("grailed", None),
    ("mercari", "20 listing(s), 20 with details, 2 free row(s) (status and coverage), stopped: maxItems."),
    ("ebay", "Finished! Total 21 requests: 21 succeeded, 0 failed."),
])
def test_healthy_real_runs_are_ok(name, message):
    v = assess(log=log(name), status_message=message)
    assert (v.kind, v.bad) == ("ok", False), v


def test_a_healthy_run_that_hit_403s_but_recovered_is_ok_with_a_note():
    v = assess(log=log("mercari"))
    assert v.kind == "ok" and any("403" in n and "recovered" in n for n in v.notes), v.notes


def test_an_early_warning_is_a_note_not_a_failure():
    v = assess(log=log("grailed"))
    assert v.kind == "ok" and any("layout" in n for n in v.notes)


def test_the_real_blocked_run_reported_succeeded_with_zero_failed_requests_but_is_caught_by_its_empty_result():
    v = assess(log=log("getascraper_blocked"), status_message="Finished! Total 1 requests: 1 succeeded, 0 failed.",
               rows=rows())
    assert (v.kind, v.bad, v.hard) == ("empty", True, False)
    assert any("No listings extracted" in r for r in v.reasons)


# --- block evidence ----------------------------------------------------------------------------------

def test_zero_rows_with_http_403_in_the_log_is_a_hard_block():
    v = assess(rows=rows(), log=log("mercari"))
    assert (v.kind, v.hard) == ("blocked", True) and any("403" in r for r in v.reasons)
    assert not any("recovered" in n for n in v.notes)     # nothing came back, so nothing recovered


def test_running_out_of_fresh_addresses_is_a_hard_block_even_if_a_few_rows_came_back():
    text = "WARN  Mercari US refused this run's address (HTTP 403 (Cloudflare), 5903 bytes); the next request leaves through a fresh one (5 of 6).\n" \
           "WARN  Mercari US refused this run's address (HTTP 403 (Cloudflare), 9907 bytes); the next request leaves through a fresh one (6 of 6).\n"
    v = assess(rows=rows(good=5), requested=100, log=text)
    assert (v.kind, v.hard) == ("blocked", True) and any("6 of 6" in r for r in v.reasons)


@pytest.mark.parametrize("log_text, message", [
    ('INFO  Final request statistics: {"requestsFinished":2,"requestsFailed":9,"retryHistogram":[2]}', None),
    ("", "Finished! Total 11 requests: 2 succeeded, 9 failed."),
])
def test_most_requests_failing_is_a_hard_block(log_text, message):
    v = assess(rows=rows(good=3), log=log_text, status_message=message)
    assert (v.kind, v.hard) == ("blocked", True) and any("failed" in r for r in v.reasons)


def test_a_few_failed_requests_are_fine():
    v = assess(status_message="Finished! Total 21 requests: 20 succeeded, 1 failed.")
    assert v.kind == "ok"


def test_an_ebay_auth_token_pool_that_is_empty_is_a_hard_block():
    v = assess(rows=rows(), log="[EBAY_AUTH] Token pool: 0 usable token(s); this run opens on #0.")
    assert v.kind == "blocked"


@pytest.mark.parametrize("status", ["FAILED", "TIMED-OUT", "ABORTED", "ERROR", "NO_RUN"])
def test_runs_that_did_not_succeed_are_failures(status):
    v = assess(status=status, status_message="actor crashed", rows=rows())
    assert (v.kind, v.bad, v.hard) == ("failed", True, False)


def test_zero_rows_without_any_evidence_is_empty_not_blocked():
    v = assess(rows=rows(), log="INFO  Done. Scraped 0 listing(s).")
    assert (v.kind, v.bad, v.hard) == ("empty", True, False)


# --- silent degradation: rows come back, but they are junk or thin ------------------------------------

def test_many_unusable_rows_is_degraded():
    v = assess(rows=rows(good=8, bad={"no_price": 9, "no_image": 3}))
    assert (v.kind, v.hard) == ("degraded", True) and any("12 of 20" in r for r in v.reasons)


def test_rows_without_descriptions_mean_the_actor_is_returning_card_data_only():
    v = assess(rows=rows(good=20, described=2))
    assert v.kind == "degraded" and any("description" in r for r in v.reasons)


def test_the_description_check_can_be_switched_off_for_an_actor_that_has_none():
    assert assess(rows=rows(good=20, described=0), expects_description=False).kind == "ok"


def test_too_few_rows_to_judge_quality_are_not_called_degraded():
    assert assess(rows=rows(good=4, described=0, bad={"no_price": 3})).kind == "ok"


def test_expected_filtering_such_as_kids_is_not_a_problem():
    v = assess(rows=rows(good=6, filtered={"kids": 12, "unmapped_category": 2}))
    assert v.kind == "ok"


def test_far_fewer_rows_than_asked_is_only_a_warning():
    v = assess(requested=200, rows=rows(good=20))
    assert (v.kind, v.bad) == ("short", False)


# --- classifying single rows with the real mappers ----------------------------------------------------

def test_row_classification_good_filtered_bad():
    import json
    raw = json.loads((Path(__file__).parent / "fixtures" / "depop.json").read_text())[0]
    kind, reason, n = H.classify_row(depop.map_item, raw, "tshirts", NOW)
    assert (kind, reason) == ("good", None) and n.id.startswith("depop:")
    assert H.classify_row(depop.map_item, {**raw, "price": {"amount": 5, "currency": "GBP"}}, "tshirts", NOW)[:2] == ("filtered", "non_usd")
    assert H.classify_row(depop.map_item, {**raw, "price": None}, "tshirts", NOW)[:2] == ("bad", "no_price")
    assert H.classify_row(depop.map_item, {**raw, "url": "not a url"}, "tshirts", NOW)[:2] == ("bad", "invalid")
    assert H.classify_row(depop.map_item, {**raw, "id": None}, "tshirts", NOW)[:2] == ("bad", "no_id")


def test_a_mapper_crash_is_a_bad_row_not_a_crash():
    def boom(raw, category, scraped_at):
        raise KeyError("x")
    assert H.classify_row(boom, {}, "tshirts", NOW)[:2] == ("bad", "error:KeyError")


def test_row_counts_add_up():
    c = H.RowCounts()
    c.add("good", None, described=True)
    c.add("good", None, described=False)
    c.add("filtered", "kids")
    c.add("bad", "no_price")
    c.add("duplicate", None, described=True)
    assert (c.good, c.duplicates, c.described, c.saved) == (2, 1, 2, 5) and c.filtered["kids"] == 1 and c.bad["no_price"] == 1
