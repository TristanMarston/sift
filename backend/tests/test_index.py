import json

import numpy as np
import pytest

from backend.index import Index


def unit(*v):
    v = np.array(v, np.float32)
    return v / np.linalg.norm(v)


def r(i, **over):
    base = dict(id=f"depop:{i}", marketplace="depop", category="jackets_outerwear", size="M", condition="good",
                cost=dict(price_cents=1000, total_cents=1000))
    return {**base, **over}


@pytest.fixture
def idx():
    vecs = np.stack([unit(1, 0, 0), unit(1, 1, 0), unit(0, 1, 0), unit(1, 0.2, 0)])
    rows = [
        r(0),
        r(1, marketplace="ebay", size="L", cost=dict(price_cents=5000, total_cents=5500)),
        r(2, category="sneakers", condition=None),
        r(3, size="m", condition="like_new"),
    ]
    return Index(vecs, rows)


def ids(hits):
    return [h[0]["id"] for h in hits]


def test_results_are_sorted_by_cosine_similarity(idx):
    hits = idx.search(unit(1, 0, 0))
    assert ids(hits) == ["depop:0", "depop:3", "depop:1", "depop:2"]
    assert hits[0][1] == pytest.approx(1.0)
    assert all(a[1] >= b[1] for a, b in zip(hits, hits[1:]))


def test_k_limits_the_count(idx):
    assert ids(idx.search(unit(1, 0, 0), k=2)) == ["depop:0", "depop:3"]


def test_min_sim_is_a_hard_cutoff_and_can_empty_the_list(idx):
    assert ids(idx.search(unit(1, 0, 0), min_sim=0.9)) == ["depop:0", "depop:3"]
    assert idx.search(unit(0, 0, 1), min_sim=0.5) == []


def test_category_filter(idx):
    assert ids(idx.search(unit(1, 0, 0), category="sneakers")) == ["depop:2"]


def test_max_price_uses_total_cents(idx):
    assert "depop:1" not in ids(idx.search(unit(1, 0, 0), max_price_cents=5000))
    assert "depop:1" in ids(idx.search(unit(1, 0, 0), max_price_cents=5500))


def test_marketplace_size_and_condition_filters(idx):
    assert ids(idx.search(unit(1, 0, 0), marketplaces=["ebay"])) == ["depop:1"]
    assert ids(idx.search(unit(1, 0, 0), sizes=["M"])) == ["depop:0", "depop:3", "depop:2"]
    assert ids(idx.search(unit(1, 0, 0), conditions=["like_new", "good"])) == ["depop:0", "depop:3", "depop:1"]


def test_filters_combine(idx):
    assert ids(idx.search(unit(1, 0, 0), sizes=["m"], conditions=["good"], category="jackets_outerwear")) == ["depop:0"]


def test_empty_index_returns_nothing():
    assert Index(np.zeros((0, 3), np.float32), []).search(unit(1, 0, 0)) == []


def test_load_reads_the_step_05_output(tmp_path):
    vecs = np.stack([unit(1, 0, 0), unit(0, 1, 0)])
    np.save(tmp_path / "embeddings.npy", vecs)
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(r(i)) + "\n" for i in range(2)))
    (tmp_path / "manifest.json").write_text(json.dumps({"dim": 3, "count": 2}))
    idx = Index.load(tmp_path)
    assert len(idx) == 2 and ids(idx.search(unit(0, 1, 0), k=1)) == ["depop:1"]


def test_load_rejects_misaligned_files(tmp_path):
    np.save(tmp_path / "embeddings.npy", np.stack([unit(1, 0, 0)]))
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(r(i)) + "\n" for i in range(2)))
    with pytest.raises(ValueError):
        Index.load(tmp_path)


# --- duplicates: the same item cross-posted or relisted ------------------------------------

def dup_index():
    same = unit(1, 0.01, 0)                       # photo similarity to unit(1, 0, 0) ~ 0.99995: the same photo
    vecs = np.stack([unit(1, 0, 0), same, unit(1, 0.3, 0), unit(0, 1, 0)])
    rows = [r(0, id="mercari:0", marketplace="mercari", cost=dict(price_cents=5400, total_cents=5400)),
            r(1, id="poshmark:1", marketplace="poshmark", cost=dict(price_cents=4500, total_cents=4500)),
            r(2), r(3)]
    return Index(vecs, rows)


def test_duplicates_collapse_to_the_cheapest_copy():
    assert ids(dup_index().search(unit(1, 0, 0), dedupe=0.97)) == ["poshmark:1", "depop:2", "depop:3"]


def test_look_alikes_below_the_cutoff_are_kept():
    hits = dup_index().search(unit(1, 0, 0), dedupe=0.97)
    assert "depop:2" in ids(hits)                 # ~0.958 to depop:0: a different item that looks similar


def test_duplicates_do_not_use_up_result_slots():
    assert ids(dup_index().search(unit(1, 0, 0), k=2, dedupe=0.97)) == ["poshmark:1", "depop:2"]


def test_without_dedupe_nothing_changes():
    assert len(dup_index().search(unit(1, 0, 0))) == 4


# --- colour re-rank ----------------------------------------------------------------------------

def test_colour_rerank_lifts_the_right_colour_without_changing_similarity():
    """Shortlist by SigLIP, then penalise a colour far from the query's: a green tee at 0.78 beats a grey one at 0.83."""
    from backend import color as C
    rows = [r(0, id="depop:grey"), r(1, id="depop:green"), r(2, id="depop:red")]
    vecs = np.array([[1.0, 0.0, 0.0], [0.94, 0.34, 0.0], [0.9, 0.44, 0.0]], np.float32)   # grey most similar
    grey, green, red = (C.srgb_to_lab(np.array([c], np.float32))[0] for c in [(128, 128, 128), (20, 90, 40), (200, 30, 30)])
    idx = Index(vecs, rows, colors=np.stack([grey, green, red]))
    hits = idx.search(unit(1, 0, 0), color=green)
    assert [row["id"] for row, _ in hits] == ["depop:green", "depop:grey", "depop:red"]
    assert [round(sim, 2) for _, sim in hits] == [0.94, 1.0, 0.9]          # the reported similarity is still SigLIP's
    assert [row["id"] for row, _ in idx.search(unit(1, 0, 0))] == ["depop:grey", "depop:green", "depop:red"]


def test_unknown_colours_are_not_penalised():
    rows = [r(0, id="depop:a"), r(1, id="depop:b")]
    idx = Index(np.eye(2, 3, dtype=np.float32), rows, colors=np.array([[np.nan] * 3, [50, 0, 0]], np.float32))
    assert [row["id"] for row, _ in idx.search(unit(1, 0, 0), color=np.array([50, 0, 0]))] == ["depop:a", "depop:b"]


def test_load_reads_colours_when_present(tmp_path):
    rows = [r(0), r(1)]
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    np.save(tmp_path / "embeddings.npy", np.eye(2, 3, dtype=np.float32))
    assert Index.load(tmp_path).colors is None
    np.save(tmp_path / "colors.npy", np.zeros((2, 3), np.float32))
    assert Index.load(tmp_path).colors.shape == (2, 3)


def test_a_brand_read_off_the_photo_lifts_that_brands_listings():
    """Haiku read "GAP" on the hoodie: GAP hoodies in the shortlist move up, the rest stay in similarity order."""
    rows = [r(0, id="depop:other", brand="Champion"), r(1, id="depop:gap", brand="Gap")]
    idx = Index(np.array([[1.0, 0.0, 0.0], [0.94, 0.34, 0.0]], np.float32), rows)
    assert [row["id"] for row, _ in idx.search(unit(1, 0, 0))] == ["depop:other", "depop:gap"]
    assert [row["id"] for row, _ in idx.search(unit(1, 0, 0), brand=" GAP ")] == ["depop:gap", "depop:other"]
    assert [round(s, 2) for _, s in idx.search(unit(1, 0, 0), brand="GAP")] == [0.94, 1.0]   # similarity unchanged


# --- what the index refuses to serve ------------------------------------------------------------

def test_load_drops_lots_and_bundles_and_mends_titles(tmp_path):
    """Live: "Bulk Denim Jeans Lot 10+ lb Scrap Crafting" was the #1 look match for a pair of Wrangler jeans, and
    titles like "New" or "Title: Uniqlo ..." reached the screen. 198 of 75,841 titles are lots or bundles; 935 are under
    three words. Dropped at load so the fix needs no re-embedding; the vectors and colours stay aligned."""
    rows = [r(0, title="Levi's 501 jeans 32x30"), r(1, title="Bulk Denim Jeans Lot 10+ lb Mens Womens Scrap Crafting"),
            r(2, title="Title: Uniqlo Ultra Light Down Jacket"), r(3, title="New", brand="Uniqlo", color="black, grey"),
            r(4, title="Bundle discounts are on!"), r(5, title="", brand=None, color=None),
            r(6, title="Lots of life left in these Levi's"), r(7, title="Brown sweater", brand="Uniqlo", color="grey"),
            r(8, title="Stay warm without the bulk: Uniqlo Ultra Light Down"), r(9, title="LOT (7) VINTAGE HILO HATTIE shirts"),
            r(10, title="ON HOLD!!", brand="Arc'teryx", color="black"), r(11, title="Nike Dunk Low Off-White Lot 8"),
            r(12, title="Levi 511", brand="Levi's", color="navy")]
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    np.save(tmp_path / "embeddings.npy", np.arange(39, dtype=np.float32).reshape(13, 3))
    np.save(tmp_path / "colors.npy", np.arange(39, dtype=np.float32).reshape(13, 3))
    idx = Index.load(tmp_path)
    assert [x["id"] for x in idx.rows] == ["depop:0", "depop:2", "depop:3", "depop:5", "depop:6", "depop:7", "depop:8",
                                           "depop:10", "depop:11", "depop:12"]
    assert idx.vecs.tolist() == idx.colors.tolist() == [[0, 1, 2], [6, 7, 8], [9, 10, 11], [15, 16, 17], [18, 19, 20],
                                                        [21, 22, 23], [24, 25, 26], [30, 31, 32], [33, 34, 35], [36, 37, 38]]
    assert [x["title"] for x in idx.rows] == ["Levi's 501 jeans 32x30", "Uniqlo Ultra Light Down Jacket",
                                              "Uniqlo black jacket", "Jacket", "Lots of life left in these Levi's",
                                              "Brown sweater", "Stay warm without the bulk: Uniqlo Ultra Light Down",
                                              "Arc'teryx black jacket", "Nike Dunk Low Off-White Lot 8", "Levi 511"]


def test_by_category_counts_what_a_search_in_that_category_sees(idx):
    assert idx.by_category() == {"jackets_outerwear": 3, "sneakers": 1}
    assert Index(np.zeros((0, 3), np.float32), []).by_category() == {}
