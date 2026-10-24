"""A JSON string may hold U+2028 and friends, which str.splitlines() treats as line breaks (found in real Mercari
descriptions). Lines are read on "\\n" only and written ASCII-escaped, so no consumer can split a record."""
import json
import threading

import jsonl
from helpers import row
from listing import Listing, Normalized

TRICKY = "a b c\x85d\x0be\x0cf\x1cg end"


def test_dumps_is_one_ascii_line_even_with_unicode_line_separators():
    line = jsonl.dumps({"d": TRICKY, "e": "café ✓"})
    assert "\n" not in line and line.isascii() and len(line.splitlines()) == 1
    assert json.loads(line) == {"d": TRICKY, "e": "café ✓"}


def test_read_splits_on_newline_only_and_skips_blank_lines(tmp_path):
    p = tmp_path / "x.jsonl"
    # raw, unescaped separators, as an older file or another tool may have written them
    p.write_text(json.dumps({"d": TRICKY}, ensure_ascii=False) + "\n\n" + json.dumps({"d": "two"}, ensure_ascii=False),
                 encoding="utf-8")
    assert [json.loads(line)["d"] for line in jsonl.read(p)] == [TRICKY, "two"]
    assert jsonl.load(p) == [{"d": TRICKY}, {"d": "two"}]
    assert jsonl.read(tmp_path / "missing.jsonl") == []


def test_a_description_with_line_separators_survives_the_whole_chain(tmp_path):
    import extract as X
    from normalize import run as N
    from test_steps import mapper, write_run
    raw = {"id": "a", "price": 100, "description": TRICKY}
    write_run(tmp_path, "r1", [raw])
    (tmp_path / "raw" / "depop" / "r1.jsonl").write_text(json.dumps(raw, ensure_ascii=False) + "\n", encoding="utf-8")

    def keep_description(r, category, scraped_at):
        n = mapper(r, category, scraped_at)
        return Normalized(**{**n.model_dump(), "description": r["description"]})

    assert N.normalize_all(tmp_path, {"depop": keep_description})["kept"] == 1
    assert X.extract_file(tmp_path / "normalized.jsonl", tmp_path / "listings.jsonl")["kept"] == 1
    (line,) = jsonl.read(tmp_path / "listings.jsonl")
    assert line.isascii() and len(line.splitlines()) == 1
    assert Listing.model_validate_json(line).description == TRICKY


def test_append_writes_whole_lines_even_from_many_threads(tmp_path):
    """Scrape lanes run in threads, and append mode is not atomic across threads on Windows."""
    path = tmp_path / "new" / "log.jsonl"
    def write(i):
        for k in range(50):
            jsonl.append(path, {"i": i, "k": k, "text": TRICKY * 40})
    threads = [threading.Thread(target=write, args=(i,)) for i in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert path.read_text(encoding="utf-8").isascii()
    assert sorted((r["i"], r["k"]) for r in jsonl.load(path)) == [(i, k) for i in range(8) for k in range(50)]
