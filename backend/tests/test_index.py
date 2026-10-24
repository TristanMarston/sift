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
