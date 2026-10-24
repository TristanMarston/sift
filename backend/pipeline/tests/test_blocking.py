"""What the runner does when a marketplace blocks us, returns junk, or we stop it. See ../BLOCKING.md."""
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import scrape as S
import scrape_report as R
from test_scrape import FakeClient, read_jsonl, t

MERCARI_403_LOG = (Path(__file__).parent / "fixtures" / "logs" / "mercari.log").read_text()  # real: two 403s, recovered


def classify(task, raw):
    """A scripted row judge: 'junk' rows are unusable, 'kids' rows are filtered, the rest are good."""
    if raw.get("junk"):
        return "bad", "no_price", None
    if raw.get("kids"):
        return "filtered", "kids", None
    return "good", None, SimpleNamespace(id=f"{task.marketplace}:{raw['id']}", description="d" * 60)


def rows(*ids, **flags):
    return [{"id": i, **flags} for i in ids]


def run(client, plan, tmp_path, quotas=None, **kw):
    lines = []
    summary = S.run_plan(client, plan, quotas, tmp_path, classify=classify, log=lines.append, **kw)
    return summary, lines


# --- a block: know at once, stop that marketplace, leave the others alone -----------------------------

def test_a_blocked_run_alerts_at_once_and_stops_only_that_marketplace(tmp_path):
    client = FakeClient(rows_by_call={0: []}, logs={0: MERCARI_403_LOG})
    summary, lines = run(client, [t("depop", q=f"d{i}") for i in range(3)] + [t("poshmark", q="p0")], tmp_path)
    assert [a for a, _ in client.calls] == ["jongoose/depop-scraper", "123webdata/poshmark-scraper"]
    (alert,) = [l for l in lines if l.startswith("ALERT")]
    assert alert.startswith("ALERT [depop] BLOCKED") and "STOPPED" in alert and "console.apify.com/actors/runs/run0" in alert
    (saved,) = read_jsonl(tmp_path / "alerts.jsonl")
    assert (saved["marketplace"], saved["verdict"], saved["run_id"], saved["action"]) == ("depop", "blocked", "run0", "stopped")
    assert summary.markets["depop"].stopped.startswith("BLOCKED") and summary.markets["poshmark"].stopped is None
    assert R.exit_code(summary) == 2


def test_stop_all_on_block_halts_every_marketplace(tmp_path):
    client = FakeClient(rows_by_call={0: []}, logs={0: MERCARI_403_LOG})
    summary, _ = run(client, [t("depop", q="d"), t("poshmark", q="p")], tmp_path, stop_all_on_block=True)
    assert len(client.calls) == 1 and summary.halted


def test_one_empty_run_is_an_alert_and_a_second_in_a_row_stops_the_marketplace(tmp_path):
    client = FakeClient(rows_by_call={0: [], 1: []})
    summary, lines = run(client, [t(q=f"d{i}") for i in range(4)], tmp_path)
    alerts = [l for l in lines if l.startswith("ALERT")]
    assert len(client.calls) == 2 and len(alerts) == 2
    assert "EMPTY" in alerts[0] and "1 of 2" in alerts[0] and "STOPPED" in alerts[1]
    assert summary.markets["depop"].stopped.startswith("EMPTY")


def test_an_empty_run_between_good_ones_does_not_stop_anything(tmp_path):
    client = FakeClient(rows_by_call={1: []})
    summary, lines = run(client, [t(q=f"d{i}") for i in range(4)], tmp_path)
    assert len(client.calls) == 4 and summary.markets["depop"].stopped is None
    assert len([l for l in lines if l.startswith("ALERT")]) == 1 and R.exit_code(summary) == 0


# --- junk that is billed: stop at once and keep it out of the catalog ------------------------------------

def test_junk_rows_make_a_degraded_run_that_stops_the_marketplace_and_is_quarantined(tmp_path):
    client = FakeClient(rows_by_call={0: rows(*[f"j{i}" for i in range(12)], junk=True)})
    summary, lines = run(client, [t(q="a"), t(q="b")], tmp_path, quotas={"depop": 5})
    m = summary.markets["depop"]
    assert len(client.calls) == 1 and m.stopped.startswith("DEGRADED")
    assert (m.quarantined, m.rows.saved, m.rows_toward_quota) == (12, 0, 0)
    (entry,) = read_jsonl(tmp_path / "runs.jsonl")
    assert entry["verdict"] == "degraded" and entry["rows_bad"] == 12 and entry["items"] == 12
    assert any("12 of 12" in l for l in lines if l.startswith("ALERT"))


def test_money_spent_on_bad_runs_is_reported_as_wasted(tmp_path):
    client = FakeClient(rows_by_call={0: []}, logs={0: MERCARI_403_LOG})
    summary, _ = run(client, [t("mercari", q="m")], tmp_path)
    assert summary.markets["mercari"].wasted == Decimal("0.006")


# --- resume: bad runs are retried, good ones are not, a query that is really empty is given up on ----------

def test_resume_retries_bad_runs_skips_good_ones_and_gives_up_on_a_twice_empty_query(tmp_path):
    plan = [t(q="good"), t(q="dud")]
    run(FakeClient(rows_by_call={1: []}), plan, tmp_path)                       # dud is empty (1st time)
    again = FakeClient(rows_by_call={0: []})
    run(again, plan, tmp_path)                                                  # dud is retried, empty again
    assert [kw["run_input"]["query"] for _, kw in again.calls] == ["dud"]
    third = FakeClient()
    run(third, plan, tmp_path)                                                  # empty twice = really empty
    assert third.calls == []


def test_rows_of_a_bad_run_do_not_count_toward_the_quota(tmp_path):
    run(FakeClient(rows_by_call={0: rows(*[f"j{i}" for i in range(12)], junk=True)}), [t(q="a")], tmp_path)
    again = FakeClient(items=4)
    run(again, [t(q="b"), t(q="c")], tmp_path, quotas={"depop": 5})
    assert len(again.calls) == 2    # 4 + 4 rows reach the quota of 5 only after the second run


# --- the operator's brake and Ctrl-C ---------------------------------------------------------------------

def test_a_STOP_file_halts_the_run_before_the_next_actor_call(tmp_path):
    (tmp_path / "STOP").write_text("")
    client = FakeClient()
    summary, lines = run(client, [t(q="a")], tmp_path)
    assert client.calls == [] and summary.manual_stop and R.exit_code(summary) == 4
    assert any("STOP" in l for l in lines)


def test_ctrl_c_still_produces_the_report_with_what_was_collected(tmp_path):
    summary, _ = run(FakeClient(statuses={1: "INTERRUPT"}), [t(q="a"), t(q="b"), t(q="c")], tmp_path)
    assert summary.interrupted and R.exit_code(summary) == 130
    assert summary.markets["depop"].rows.good == 3 and (tmp_path / "run_report.md").exists()


# --- the report -------------------------------------------------------------------------------------------

def test_report_counts_good_filtered_bad_duplicate_rows_and_money(tmp_path):
    first = rows("a", "b") + rows("k1", kids=True) + rows("j1", junk=True)
    second = rows("a", "c")                                                     # "a" repeats: a duplicate
    summary, _ = run(FakeClient(rows_by_call={0: first, 1: second}), [t(q="x"), t(q="y")], tmp_path)
    m = summary.markets["depop"]
    assert (m.rows.good, m.rows.duplicates, dict(m.rows.filtered), dict(m.rows.bad), m.rows.saved) == (3, 1, {"kids": 1}, {"no_price": 1}, 6)
    assert m.queries_ok + m.queries_short == 2 and m.queries_bad == 0 and m.est_spend == Decimal("0.006")
    md = (tmp_path / "run_report.md").read_text()
    assert "| depop |" in md and "good rows saved: 3" in md and "kids 1" in md and "no_price 1" in md
    data = json.loads((tmp_path / "run_report.json").read_text())
    assert data["markets"]["depop"]["rows_good"] == 3 and data["exit_code"] == 0


def test_report_tells_the_operator_what_to_do_about_a_stopped_marketplace(tmp_path):
    client = FakeClient(rows_by_call={0: []}, logs={0: MERCARI_403_LOG})
    summary, _ = run(client, [t("depop", q="d")], tmp_path)
    md = R.render(summary)
    assert "STOPPED" in md and "depop" in md and "console.apify.com/actors/runs/run0" in md and "re-run the same command" in md.lower()


@pytest.mark.parametrize("changes, code", [
    ({}, 0), ({"budget_stop": True}, 3), ({"manual_stop": True}, 4), ({"interrupted": True}, 130),
    ({"interrupted": True, "manual_stop": True, "budget_stop": True}, 130),
])
def test_exit_codes(changes, code):
    assert R.exit_code(R.Summary(**changes)) == code


def test_a_stopped_marketplace_exits_2_ahead_of_a_budget_stop():
    s = R.Summary(budget_stop=True)
    s.markets["depop"] = R.MarketStats(stopped="BLOCKED at 'x'")
    assert R.exit_code(s) == 2


def test_the_report_flags_a_marketplace_whose_queries_mostly_come_back_short():
    """A site that serves a few pages and then cuts us off looks like this: nothing fails, everything is a trickle."""
    s = R.Summary()
    s.markets["depop"] = R.MarketStats(queries_ok=1, queries_short=4)
    s.markets["ebay"] = R.MarketStats(queries_ok=9, queries_short=3)
    text = R.render(s)
    assert "watch: depop" in text and "watch: ebay" not in text
