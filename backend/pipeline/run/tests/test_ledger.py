"""The team's run log: local runs.jsonl <-> the Apify ledger (push, sync) and <-> a zip snapshot (export, import)."""
import json
import zipfile

import jsonl
import scrape as S
from normalize import run as N
from run import ledger as L
from fakes import MAPPERS, FakeApify


def entry(run_id, mp="depop", query="boxy tee", status="SUCCEEDED", verdict="ok", items=2, **over):
    return dict(marketplace=mp, category="tshirts", query=query, max_items=200, run_id=run_id, status=status,
                status_message=None, items=items, est_charge_usd=0.002, at="2026-10-24T10:00:00+00:00", verdict=verdict, **over)


def scrape_into(client, data_dir, queries=("q1", "q2"), mp="depop"):
    plan = [S.Task(mp, "tshirts", q, 3) for q in queries]
    S.run_plan(client, plan, None, data_dir, log=lambda _: None)
    return jsonl.load(data_dir / "runs.jsonl")


# --- push: local -> ledger ---------------------------------------------------------------------

def test_push_adds_local_runs_of_this_account_that_the_ledger_lacks(tmp_path):
    client = FakeApify()
    mine = scrape_into(client, tmp_path)
    jsonl.append(tmp_path / "runs.jsonl", entry("from-another-token"))     # imported: its data is not on this account
    jsonl.append(tmp_path / "runs.jsonl", entry(None, status="ERROR"))     # a call that never started a run
    assert L.push(client, tmp_path) == 2
    assert [e["run_id"] for e in client.ledger()] == [e["run_id"] for e in mine]
    assert L.push(client, tmp_path) == 0          # nothing twice


# --- sync: ledger -> local ---------------------------------------------------------------------

def test_sync_rebuilds_a_teammates_runs_exactly_scrubbed_and_rerunning_changes_nothing(tmp_path):
    client = FakeApify()
    a, b = tmp_path / "a", tmp_path / "b"
    scrape_into(client, a)
    L.push(client, a)
    assert L.sync(client, b, log=lambda _: None) == {"runs": 2, "downloaded": 2}
    assert (b / "runs.jsonl").read_text() == (a / "runs.jsonl").read_text()
    for path in (a / "raw").rglob("*.jsonl"):
        assert (b / path.relative_to(a)).read_text() == path.read_text()
    assert "sellerUsername" not in (b / "raw" / "depop" / "run0.jsonl").read_text()
    N.normalize_all(a, MAPPERS), N.normalize_all(b, MAPPERS)
    assert (b / "normalized.jsonl").read_text() == (a / "normalized.jsonl").read_text()
    assert L.sync(client, b, log=lambda _: None) == {}


def test_sync_takes_the_entry_of_a_bad_run_but_not_its_quarantined_rows(tmp_path):
    client = FakeApify()
    client.dataset(client.datasets().get_or_create(name=L.LEDGER).id).push_items([entry("run9", verdict="blocked")])
    assert L.sync(client, tmp_path, log=lambda _: None) == {"runs": 1}
    assert jsonl.load(tmp_path / "runs.jsonl")[0]["run_id"] == "run9"
    assert not (tmp_path / "raw").exists()


def test_sync_skips_a_run_whose_data_is_gone_so_a_later_sync_can_retry_it(tmp_path):
    client = FakeApify()
    client.dataset(client.datasets().get_or_create(name=L.LEDGER).id).push_items([entry("expired")])
    lines = []
    assert L.sync(client, tmp_path, log=lines.append) == {"missing_data": 1}
    assert not jsonl.load(tmp_path / "runs.jsonl") and "expired" in lines[0]


# --- export / import: one file with everything -------------------------------------------------

def snapshot_dir(tmp_path):
    d = tmp_path / "src"
    scrape_into(FakeApify(), d)
    jsonl.append(d / "alerts.jsonl", dict(at="t", marketplace="depop", query="q1", run_id="run0", verdict="short"))
    (d / "batches" / "b1").mkdir(parents=True)
    (d / "batches" / "b1" / "batch.json").write_text("{}")
    (d / "normalized.jsonl").write_text("derived, not part of a snapshot\n")
    return d


def files(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def test_export_then_import_gives_the_same_runs_raw_files_alerts_and_batches(tmp_path):
    src, dst = snapshot_dir(tmp_path), tmp_path / "dst"
    L.export(src, tmp_path / "snap.zip")
    assert L.import_snapshot(dst, tmp_path / "snap.zip") == {"runs": 2, "files": 3, "alerts": 1}
    expected = {k: v for k, v in files(src).items() if k.split("/")[0] in L.SNAPSHOT}   # not normalized.jsonl, run_report.md
    assert files(dst) == expected
    assert L.import_snapshot(dst, tmp_path / "snap.zip") == {}       # importing twice changes nothing
    assert files(dst) == expected


def test_import_from_a_folder_adds_to_local_data_and_never_overwrites(tmp_path):
    src, dst = snapshot_dir(tmp_path), tmp_path / "dst"
    scrape_into(FakeApify(), dst, queries=("mine",))                  # local run0 is a different run than src's run0
    local_raw = (dst / "raw" / "depop" / "run0.jsonl").read_bytes()
    jsonl.append(dst / "runs.jsonl", entry("elsewhere"))
    counts = L.import_snapshot(dst, src)
    assert counts["files"] == 2 and counts["runs"] == 1               # run1 is new; run0 is already known
    assert (dst / "raw" / "depop" / "run0.jsonl").read_bytes() == local_raw
    assert [e["run_id"] for e in jsonl.load(dst / "runs.jsonl")] == ["run0", "elsewhere", "run1"]


def test_import_ignores_zip_members_outside_the_snapshot(tmp_path):
    with zipfile.ZipFile(tmp_path / "evil.zip", "w") as z:
        z.writestr("../../outside.txt", "x")
        z.writestr("notes.txt", "x")
        z.writestr("runs.jsonl", json.dumps(entry("r1")) + "\n")
    dst = tmp_path / "dst"
    assert L.import_snapshot(dst, tmp_path / "evil.zip") == {"runs": 1}
    assert not (tmp_path / "outside.txt").exists() and not (dst / "notes.txt").exists()


def test_care_tag_answers_travel_with_a_snapshot_so_nobody_pays_for_them_twice(tmp_path):
    src, dst = snapshot_dir(tmp_path), tmp_path / "dst"
    jsonl.append(src / "tags.jsonl", {"id": "depop:1", "as_of": "2026-10-24", "tag_found": True, "composition": "100% wool"})
    jsonl.append(src / "tags.jsonl", {"id": "depop:2", "as_of": "2026-10-24", "tag_found": False, "composition": None,
                                      "error": "TimeoutError: "})       # a failed call is retried, not shared
    L.export(src, tmp_path / "snap.zip")
    assert L.import_snapshot(dst, tmp_path / "snap.zip")["tags"] == 1
    assert [t["id"] for t in jsonl.load(dst / "tags.jsonl")] == ["depop:1"]
    assert "tags" not in L.import_snapshot(dst, tmp_path / "snap.zip")   # importing twice changes nothing
