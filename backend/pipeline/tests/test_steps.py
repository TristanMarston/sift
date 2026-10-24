"""Steps 02-04 around the mappers: normalize driver, extract driver, report."""
import json
from datetime import datetime

import pytest

import extract as X
import report as R
from helpers import row
from listing import Listing, Normalized
from normalize import run as N
from normalize.common import Drop


# --- 02 normalize driver ------------------------------------------------------------------

def mapper(raw, category, scraped_at):
    if raw["id"] == "boom":
        raise KeyError("price")
    if not raw.get("price"):
        raise Drop("no_price")
    url = "bad" if raw["id"] == "badurl" else f"https://depop.example/{raw['id']}"
    return Normalized(**row(id=f"depop:{raw['id']}", marketplace="depop", external_id=raw["id"], url=url,
                            category=category, scraped_at=scraped_at,
                            cost=dict(price_cents=raw["price"], total_cents=raw["price"])))


def write_run(d, run_id, items, category="tshirts", status="SUCCEEDED", at="2026-10-24T01:00:00+00:00", file=True):
    (d / "raw" / "depop").mkdir(parents=True, exist_ok=True)
    if file:
        (d / "raw" / "depop" / f"{run_id}.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    with (d / "runs.jsonl").open("a") as f:
        f.write(json.dumps(dict(marketplace="depop", category=category, query="q", run_id=run_id, status=status,
                                items=len(items), at=at)) + "\n")


def read_ids(d):
    return [json.loads(line)["id"] for line in (d / "normalized.jsonl").read_text().splitlines()]


def test_normalize_keeps_good_rows_and_counts_every_drop_reason(tmp_path):
    write_run(tmp_path, "r1", [{"id": "a", "price": 100}, {"id": "b"}, {"id": "boom", "price": 1},
                               {"id": "badurl", "price": 1}, {"id": "c", "price": 200}])
    stats = N.normalize_all(tmp_path, {"depop": mapper})
    assert read_ids(tmp_path) == ["depop:a", "depop:c"]
    assert stats["kept"] == 2
    assert stats["drop:depop:no_price"] == 1
    assert stats["drop:depop:error:KeyError"] == 1
    assert stats["drop:depop:invalid"] == 1


def test_mapper_gets_the_queries_category_and_the_run_time(tmp_path):
    write_run(tmp_path, "r1", [{"id": "a", "price": 100}], category="sneakers", at="2026-10-23T05:00:00+00:00")
    N.normalize_all(tmp_path, {"depop": mapper})
    row_ = json.loads((tmp_path / "normalized.jsonl").read_text())
    assert row_["category"] == "sneakers" and row_["scraped_at"].startswith("2026-10-23T05:00:00")


def test_duplicates_keep_the_newest_scrape(tmp_path):
    write_run(tmp_path, "old", [{"id": "a", "price": 100}], at="2026-10-23T01:00:00+00:00")
    write_run(tmp_path, "new", [{"id": "a", "price": 150}], at="2026-10-24T01:00:00+00:00")
    stats = N.normalize_all(tmp_path, {"depop": mapper})
    (only,) = [json.loads(line) for line in (tmp_path / "normalized.jsonl").read_text().splitlines()]
    assert only["cost"]["price_cents"] == 150 and stats["duplicates"] == 1 and stats["kept"] == 1


def test_titles_and_descriptions_are_cleaned_of_invisible_characters(tmp_path):
    def noisy(raw, category, scraped_at):
        n = mapper(raw, category, scraped_at)
        return n.model_copy(update={"title": "\u200bWoolrich  vest", "description": "100%\u200bwool\u00a0blend"})
    write_run(tmp_path, "r1", [{"id": "a", "price": 100}])
    N.normalize_all(tmp_path, {"depop": noisy})
    (only,) = [json.loads(line) for line in (tmp_path / "normalized.jsonl").read_text().splitlines()]
    assert (only["title"], only["description"]) == ("Woolrich vest", "100%wool blend")


def test_failed_runs_and_missing_files_are_skipped(tmp_path):
    write_run(tmp_path, "bad", [{"id": "x", "price": 1}], status="FAILED")
    write_run(tmp_path, "gone", [{"id": "y", "price": 1}], file=False)
    write_run(tmp_path, "ok", [{"id": "a", "price": 100}])
    N.normalize_all(tmp_path, {"depop": mapper})
    assert read_ids(tmp_path) == ["depop:a"]


def test_output_is_sorted_and_reruns_are_identical(tmp_path):
    write_run(tmp_path, "r1", [{"id": "b", "price": 1}, {"id": "a", "price": 1}])
    N.normalize_all(tmp_path, {"depop": mapper})
    first = (tmp_path / "normalized.jsonl").read_text()
    N.normalize_all(tmp_path, {"depop": mapper})
    assert read_ids(tmp_path) == ["depop:a", "depop:b"] and (tmp_path / "normalized.jsonl").read_text() == first


# --- 03 extract driver ----------------------------------------------------------------------

def test_extract_file_writes_listings_and_counts_bad_lines(tmp_path):
    good = Normalized(**row(description="100% cotton", specifics={"Material": "Cotton"}))
    src, dst = tmp_path / "normalized.jsonl", tmp_path / "listings.jsonl"
    src.write_text(good.model_dump_json() + "\n" + json.dumps({"id": "nope"}) + "\n")
    stats = X.extract_file(src, dst)
    (line,) = dst.read_text().splitlines()
    parsed = Listing.model_validate_json(line)
    assert [f.fiber for f in parsed.materials.fibers] == ["cotton"] and "specifics" not in json.loads(line)
    assert (stats["kept"], stats["invalid"]) == (1, 1)


# --- 04 report ------------------------------------------------------------------------------

def L(i, mp="depop", **over):
    base = dict(id=f"{mp}:{i}", marketplace=mp, external_id=str(i), url=f"https://x.example/{mp}/{i}",
                title="Plain tee", description="x" * 50, seller=dict(region="CA"),
                cost=dict(price_cents=1000 + i * 100, total_cents=1000 + i * 100))
    return Listing(**row(**{**base, **over}))


def stated(fibers):
    return dict(materials=dict(fibers=fibers),
                evidence=[dict(field="materials.fibers", status="claimed", source="listing_text", as_of="2026-10-24")])


def test_stats_per_marketplace():
    rows = [L(1, **stated([dict(fiber="cotton", pct=100)])), L(2, **stated([dict(fiber="wool")])),
            L(3, description=None, materials=dict(certifications=["gots"])), L(4, seller=dict()),
            L(5, "ebay", status="sold")]
    s = R.stats(rows)
    d = s["marketplaces"]["depop"]
    assert (d["rows"], d["share"], d["description"], d["any_material"], d["percentages"]) == (4, 80.0, 75.0, 50.0, 25.0)
    assert (d["certification"], d["region"], d["median_price"]) == (25.0, 75.0, 12.5)
    assert (s["total"], s["active"]) == (5, 4) and s["categories"]["jackets_outerwear"] == 5


def test_product_line_inference_does_not_count_as_a_stated_material():
    inferred = L(1, materials=dict(fibers=[dict(fiber="cotton")]),
                 evidence=[dict(field="materials.fibers", status="inferred", source="product_line", as_of="2026-10-24")])
    assert R.stats([inferred])["marketplaces"]["depop"]["any_material"] == 0.0


def test_acceptance_checklist():
    rows = [L(i, "depop" if i % 2 else "ebay", **stated([dict(fiber="cotton", pct=100)])) for i in range(1, 9)]
    ok = {name: passed for name, passed, _ in R.acceptance(R.stats(rows), rows, min_rows=8)}
    assert ok["active rows"] and ok["share per marketplace"] and ok["stated material"] and ok["percentages"]
    assert not ok["marketplaces"]   # only 2 of the 4 needed
    assert not ok["demo props"]
    props = [L(1, title="Carhartt Detroit Jacket", brand="Carhartt"), L(2, title="Patagonia Better Sweater"),
             L(3, title="Nike Dunk Low Panda", brand="Nike")]
    assert {n: p for n, p, _ in R.acceptance(R.stats(props), props, min_rows=3)}["demo props"]


def test_render_has_a_table_row_per_marketplace_and_the_checklist():
    rows = [L(1), L(2, "ebay")]
    md = R.render(R.stats(rows), R.acceptance(R.stats(rows), rows), "2026-10-24")
    assert "| depop | 1 |" in md and "| ebay | 1 |" in md and "- [ ] active rows" in md
