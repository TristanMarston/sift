"""Step 05: data/listings.jsonl -> data/index/ (embeddings.npy + rows.jsonl + manifest.json)."""
import json

import numpy as np
from PIL import Image

import embed_index as E
from helpers import row

DIM = 4


def fake_fetch(calls):
    def fetch(url):
        calls.append(url)
        if "bad" in url:
            raise OSError("404")
        return Image.new("RGB", (8, 8), (len(url) % 256, 0, 0))
    return fetch


def fake_embed(images):
    v = np.array([[im.getpixel((0, 0))[0] + 1, 1, 0, 0] for im in images], np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def write_listings(path, rows, junk=0):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n" * junk)


def listing(i, **over):
    over.setdefault("image_urls", [f"https://img.example/{i}.jpg"])
    return row(id=f"depop:{i}", marketplace="depop", external_id=str(i), url=f"https://depop.example/{i}", **over)


def build(tmp_path, calls=None, **kw):
    return E.build_index(tmp_path / "listings.jsonl", tmp_path / "index", fake_fetch([] if calls is None else calls),
                         fake_embed, dim=DIM, **kw)


def load(tmp_path):
    d = tmp_path / "index"
    rows = [json.loads(line) for line in (d / "rows.jsonl").read_text().splitlines()]
    return np.load(d / "embeddings.npy"), rows, json.loads((d / "manifest.json").read_text())


def test_rows_and_vectors_are_aligned_and_only_active_rows_are_kept(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [listing(1), listing(2, status="sold"), listing(3)])
    stats = build(tmp_path)
    vecs, rows, _ = load(tmp_path)
    assert [r["id"] for r in rows] == ["depop:1", "depop:3"]
    assert vecs.shape == (2, DIM) and vecs.dtype == np.float32
    np.testing.assert_allclose(vecs, fake_embed([fake_fetch([])(r["image_urls"][0]) for r in rows]))
    assert stats["indexed"] == 2 and stats["skip:sold"] == 1


def test_falls_back_to_the_next_photo_and_drops_rows_with_no_usable_photo(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [
        listing(1, image_urls=["https://img.example/bad1.jpg", "https://img.example/1b.jpg"]),
        listing(2, image_urls=["https://img.example/bad2.jpg", "https://img.example/bad3.jpg"]),
    ])
    stats = build(tmp_path)
    _, rows, _ = load(tmp_path)
    assert [r["id"] for r in rows] == ["depop:1"]
    assert stats["drop:no_image"] == 1


def test_only_the_first_two_photos_are_tried(tmp_path):
    calls = []
    urls = [f"https://img.example/bad{i}.jpg" for i in range(5)]
    write_listings(tmp_path / "listings.jsonl", [listing(1, image_urls=urls)])
    build(tmp_path, calls)
    assert calls == urls[:2]


def test_small_url_asks_each_cdn_for_a_small_variant():
    assert E.small_url("https://media-photos.depop.com/b1/1/2_ab/P0.jpg") == "https://media-photos.depop.com/b1/1/2_ab/P5.jpg"
    assert (E.small_url("https://di2ponv0v5otw.cloudfront.net/posts/2026/10/11/x/l_abc.jpg")
            == "https://di2ponv0v5otw.cloudfront.net/posts/2026/10/11/x/s_abc.jpg")
    assert (E.small_url("https://media-assets.grailed.com/prd/listing/temp/abc")
            == "https://media-assets.grailed.com/prd/listing/temp/abc?w=320")
    for same in ["https://i.ebayimg.com/images/g/x/s-l400.jpg", "https://media-assets.grailed.com/a?w=800",
                 "https://img.example/1.jpg"]:
        assert E.small_url(same) == same


def test_falls_back_to_the_original_when_the_small_variant_fails(tmp_path):
    calls = []
    fetch = fake_fetch(calls)

    def only_original(url):
        if url.endswith("P5.jpg"):
            calls.append(url)
            raise OSError("404")
        return fetch(url)

    write_listings(tmp_path / "listings.jsonl", [listing(1, image_urls=["https://media-photos.depop.com/b1/1/2/P0.jpg"])])
    E.build_index(tmp_path / "listings.jsonl", tmp_path / "index", only_original, fake_embed, dim=DIM)
    _, rows, _ = load(tmp_path)
    assert [r["id"] for r in rows] == ["depop:1"]
    assert calls == ["https://media-photos.depop.com/b1/1/2/P5.jpg", "https://media-photos.depop.com/b1/1/2/P0.jpg"]


def test_invalid_lines_are_counted_not_fatal(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [listing(1), {"id": "nope"}], junk=1)
    stats = build(tmp_path)
    assert stats["indexed"] == 1 and stats["drop:invalid"] == 2


def test_rerun_resumes_without_refetching_and_gives_the_same_index(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [listing(i) for i in range(5)])
    build(tmp_path, chunk=2)
    first = load(tmp_path)
    calls = []
    stats = build(tmp_path, calls, chunk=2)
    again = load(tmp_path)
    assert calls == [] and stats["resumed"] == 5
    np.testing.assert_array_equal(first[0], again[0])
    assert first[1] == again[1]


def test_new_listings_are_added_on_rerun(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [listing(1)])
    build(tmp_path)
    write_listings(tmp_path / "listings.jsonl", [listing(1), listing(2)])
    calls = []
    build(tmp_path, calls)
    _, rows, _ = load(tmp_path)
    assert [r["id"] for r in rows] == ["depop:1", "depop:2"] and calls == ["https://img.example/2.jpg"]


def test_manifest_records_model_dim_and_counts(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [listing(1), listing(2)])
    build(tmp_path, model="fake-model")
    _, _, m = load(tmp_path)
    assert m["model"] == "fake-model" and m["dim"] == DIM and m["count"] == 2
    assert "built_at" in m and m["stats"]["indexed"] == 2


def test_empty_input_writes_an_empty_index(tmp_path):
    write_listings(tmp_path / "listings.jsonl", [])
    build(tmp_path)
    vecs, rows, m = load(tmp_path)
    assert vecs.shape == (0, DIM) and rows == [] and m["count"] == 0
