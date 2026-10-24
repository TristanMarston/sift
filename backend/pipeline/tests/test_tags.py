"""Step 03b: care tags read from listing photos fill in the fabric for listings that state none."""
import io
import json

from PIL import Image

import jsonl
import tags as T
from listing import Listing


def listing(i="1", **over):
    base = dict(id=f"depop:{i}", marketplace="depop", external_id=str(i), url=f"https://www.depop.com/products/{i}/",
                title="Wool sweater", status="active", scraped_at="2026-10-24T01:00:00Z", category="sweaters_knitwear",
                image_urls=[f"https://media-photos.depop.com/b1/1/{i}/P{n}.jpg" for n in range(3)],
                cost=dict(price_cents=4000, total_cents=4000),
                evidence=[dict(field="materials.fibers", status="unknown", source="listing_text", as_of="2026-10-24")])
    base.update(over)
    return Listing(**base).model_dump(mode="json")


def photo():
    buf = io.BytesIO()
    Image.new("RGB", (1200, 900), "white").save(buf, "JPEG")
    return Image.open(io.BytesIO(buf.getvalue()))


def tag_says(text):
    return lambda images: {"tag_found": text is not None, "composition": text}


# --- which listings ---------------------------------------------------------------------

def test_only_listings_without_a_stated_fabric_are_read():
    assert T.needs_tag(listing())
    inferred = listing(materials=dict(fibers=[dict(fiber="cotton")]),
                       evidence=[dict(field="materials.fibers", status="inferred", source="product_line", as_of="2026-10-24")])
    assert T.needs_tag(inferred)                                   # a product-line guess: the tag is better evidence
    stated = listing(materials=dict(fibers=[dict(fiber="wool", pct=100)]),
                     evidence=[dict(field="materials.fibers", status="claimed", source="listing_text", as_of="2026-10-24")])
    assert not T.needs_tag(stated)


# --- applying a tag ---------------------------------------------------------------------

def test_a_read_tag_becomes_verified_tag_image_materials():
    out = T.apply_tag(listing(), "80% Wool 20% Nylon", "2026-10-25")
    assert [(f["fiber"], f["pct"]) for f in out["materials"]["fibers"]] == [("wool", 80), ("nylon", 20)]
    assert out["materials"]["synthetic_share"] == 20
    ev = [e for e in out["evidence"] if e["field"] == "materials.fibers"]
    assert ev == [dict(field="materials.fibers", status="verified", source="tag_image", snippet="80% Wool 20% Nylon",
                       as_of="2026-10-25")]
    Listing.model_validate(out)


def test_a_tag_with_no_fibers_in_it_changes_nothing():
    row = listing()
    assert T.apply_tag(row, "Machine wash cold. Made in China", "2026-10-25") == row


# --- the step ---------------------------------------------------------------------------

def run(tmp_path, rows, ask, **kw):
    (tmp_path / "listings.jsonl").write_text("".join(jsonl.dumps(r) + "\n" for r in rows))
    stats = T.tag_file(tmp_path / "listings.jsonl", tmp_path / "tags.jsonl", ask=ask, fetch=lambda url: photo(), **kw)
    return stats, jsonl.load(tmp_path / "listings.jsonl")


def test_the_step_reads_tags_and_caches_every_answer(tmp_path):
    calls = []

    def ask(images):
        calls.append(len(images))
        return {"tag_found": True, "composition": "100% cotton"}
    rows = [listing("1"), listing("2", materials=dict(fibers=[dict(fiber="wool", pct=100)]),
                                  evidence=[dict(field="materials.fibers", status="claimed", source="listing_text",
                                                 as_of="2026-10-24")])]
    stats, out = run(tmp_path, rows, ask)
    assert stats["read"] == 1 and stats["skipped:stated"] == 1 and calls == [3]   # all 3 photos (fewer than MAX)
    assert out[0]["materials"]["fibers"][0]["fiber"] == "cotton" and out[1] == rows[1]
    stats, out = run(tmp_path, [listing("1")], ask)                # a rerun: answered from the cache, not paid again
    assert calls == [3] and stats["cached"] == 1 and out[0]["materials"]["fibers"][0]["fiber"] == "cotton"


def test_no_tag_and_failures_leave_the_listing_alone(tmp_path):
    def broken(images):
        raise RuntimeError("API down")
    stats, out = run(tmp_path, [listing("1")], tag_says(None))
    assert stats["no_tag"] == 1 and out == [listing("1")]
    stats, out = run(tmp_path, [listing("2")], broken)
    assert stats["error"] == 1 and out == [listing("2")]
    assert json.loads((tmp_path / "tags.jsonl").read_text().splitlines()[0])["composition"] is None


def test_limit_caps_how_many_listings_are_paid_for(tmp_path):
    stats, _ = run(tmp_path, [listing(str(i)) for i in range(5)], tag_says("100% cotton"), limit=2)
    assert stats["read"] == 2 and stats["skipped:limit"] == 3


def test_photos_are_sent_at_a_readable_size_and_at_most_six():
    big = Image.new("RGB", (3000, 2000), "white")
    images = T.prepare([big] * 9)
    assert len(images) == T.MAX_PHOTOS and all(max(Image.open(io.BytesIO(b)).size) == T.SIDE for b in images)


def test_ask_haiku_sends_the_photos_and_reads_the_structured_answer(monkeypatch):
    sent = {}

    class Messages:
        def create(self, **kw):
            sent.update(kw)
            text = json.dumps({"tag_found": True, "composition": "60% cotton 40% polyester"})
            return type("Msg", (), {"stop_reason": "end_turn", "content": [type("B", (), {"type": "text", "text": text})]})

    monkeypatch.setattr(T, "_client", lambda: type("C", (), {"messages": Messages()})())
    assert T.ask_haiku([b"\xff\xd8a", b"\xff\xd8b"])["composition"] == "60% cotton 40% polyester"
    assert sent["model"] == "claude-haiku-5-5" and sent["output_config"]["format"]["type"] == "json_schema"
    content = sent["messages"][0]["content"]
    assert [c["type"] for c in content] == ["image", "image", "text"]


def test_the_last_photos_are_sent_because_sellers_put_the_tag_last():
    urls = [f"u{i}" for i in range(12)]
    assert T.pick(urls) == urls[-T.MAX_PHOTOS:] and T.pick(urls[:3]) == urls[:3]


def test_a_jacket_tag_is_read_for_its_shell_not_its_lining():
    out = T.apply_tag(listing(), "Shell: 100% Cotton; Body Lining: 100% Nylon", "2026-10-25")
    assert [(f["fiber"], f["pct"]) for f in out["materials"]["fibers"]] == [("cotton", 100)]
    assert out["evidence"][-1]["snippet"] == "Shell: 100% Cotton; Body Lining: 100% Nylon"   # the receipt quotes it all


def test_an_answer_with_no_text_is_an_error_to_retry(monkeypatch):
    class Messages:
        def create(self, **kw):
            return type("Msg", (), {"stop_reason": "max_tokens", "content": []})
    monkeypatch.setattr(T, "_client", lambda: type("C", (), {"messages": Messages()})())
    try:
        T.ask_haiku([b"\xff\xd8a"])
        raise AssertionError("expected an error")
    except RuntimeError as e:
        assert "max_tokens" in str(e)
