"""The team's run log. Each machine's data/runs.jsonl is the union of every run it knows about (any machine, any token),
and an entry is one Apify run, so merging is a union by run id and never conflicts. The same entries are mirrored to a
named dataset on the token's Apify account (push / sync) and can travel as one zip file (export / import), for a token
switch or a backup: Apify deletes a run's data after 7 days on this plan."""
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import jsonl
import scrape as S
from health import BAD

LEDGER = "sift-runs"                                        # the named dataset on the Apify account
SNAPSHOT = ("runs.jsonl", "alerts.jsonl", "raw", "batches",   # everything else in data/ is rebuilt from these,
            "tags.jsonl", "depop_shipping.jsonl")             # except paid lookups: care tags, Depop shipping


def key(entry: dict):
    """One run. A call that never started a run has no run id."""
    return entry.get("run_id") or (entry["marketplace"], entry["query"], entry["at"])


def _alert_key(a: dict):
    return a["at"], a["marketplace"], a["query"], a.get("run_id")


def _ledger(client):
    return client.dataset(client.datasets().get_or_create(name=LEDGER).id)


def push(client, data_dir) -> int:
    """Add to the ledger every local entry whose run is on this account and not in the ledger yet. Returns how many.
    Runs imported from another token are left out: their data cannot be read with this one."""
    book = _ledger(client)
    missing = {r.id for r in client.runs().iterate()} - {e.get("run_id") for e in book.iterate_items()}
    new = [e for e in jsonl.load(Path(data_dir) / "runs.jsonl") if e.get("run_id") in missing]
    for i in range(0, len(new), 500):
        book.push_items(new[i:i + 500])
    return len(new)


def _write_rows(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".tmp").open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(jsonl.dumps(row) + "\n")
    path.with_suffix(".tmp").replace(path)


def sync(client, data_dir, log=S.say) -> Counter:
    """Pull the ledger's runs that are not local yet. A good run's rows are downloaded and written exactly as the runner
    writes them (scrape.clean_rows); a bad run brings only its entry, as its rows are never used. A run whose data
    cannot be read is skipped with a warning, so a later sync retries it."""
    data_dir = Path(data_dir)
    have = {key(e) for e in jsonl.load(data_dir / "runs.jsonl")}
    n = Counter()
    for e in _ledger(client).iterate_items():
        if key(e) in have:
            continue
        if e["status"] == S.OK and e.get("verdict", "ok") not in BAD:
            try:
                rows = client.run(e["run_id"]).dataset().iterate_items()
                _write_rows(data_dir / "raw" / e["marketplace"] / f"{e['run_id']}.jsonl", S.clean_rows(e["marketplace"], rows))
            except Exception as ex:
                log(f"sync: no data for run {e['run_id']} ({e['marketplace']} {e['query']!r}): {type(ex).__name__}: {ex}")
                n["missing_data"] += 1
                continue
            n["downloaded"] += 1
        jsonl.append(data_dir / "runs.jsonl", e)
        have.add(key(e))
        n["runs"] += 1
    return n


def _files(d: Path, part: str) -> list[Path]:
    """The finished files of one snapshot part (a file, or every file below a folder)."""
    found = [d / part] if (d / part).is_file() else sorted((d / part).rglob("*")) if (d / part).is_dir() else []
    return [p for p in found if p.is_file() and p.suffix != ".tmp"]


def export(data_dir, zip_path) -> int:
    """One zip with everything scraped so far: run log, alerts, raw files, batch reports. Returns the file count."""
    data_dir = Path(data_dir)
    paths = [p for part in SNAPSHOT for p in _files(data_dir, part)]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.relative_to(data_dir).as_posix())
    return len(paths)


def _union(dst: Path, src: Path, part: str, key_of) -> int:
    have = {key_of(e) for e in jsonl.load(dst / part)}
    new = [e for e in jsonl.load(src / part) if key_of(e) not in have]
    for e in new:
        jsonl.append(dst / part, e)
        have.add(key_of(e))
    return len(new)


def import_snapshot(data_dir, src) -> Counter:
    """Add a snapshot (an export zip, or another data folder) to data_dir: unknown runs and alerts are appended,
    missing raw files and batch reports copied. Nothing local is overwritten, so importing twice changes nothing."""
    data_dir, src = Path(data_dir), Path(src)
    if src.is_file():
        with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(src) as z:
            z.extractall(tmp, [m for m in z.namelist() if m.split("/")[0] in SNAPSHOT and ".." not in m.split("/")])
            return import_snapshot(data_dir, tmp)
    n = Counter()
    for part in ("raw", "batches"):   # files before entries: a run's entry never arrives without its rows
        for p in _files(src, part):
            target = data_dir / p.relative_to(src)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, target)
                n["files"] += 1
    n["runs"] += _union(data_dir, src, "runs.jsonl", key)
    n["alerts"] += _union(data_dir, src, "alerts.jsonl", _alert_key)
    for part, counter in (("tags.jsonl", "tags"), ("depop_shipping.jsonl", "shipping")):
        answered = {e["id"] for e in jsonl.load(data_dir / part) if not e.get("error")}
        for e in jsonl.load(src / part):   # answers only: a failed call is retried by whoever runs that step next
            if not e.get("error") and e["id"] not in answered:
                jsonl.append(data_dir / part, e)
                answered.add(e["id"])
                n[counter] += 1
    return +n
