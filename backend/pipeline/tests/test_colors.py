"""Step 05b: one CIELAB colour per indexed listing (colors.npy, aligned with rows.jsonl), resumable like the embeddings."""
import json

import numpy as np
from PIL import Image

import colors as K


def index_dir(tmp_path, ids):
    (tmp_path / "rows.jsonl").write_text("".join(json.dumps({"id": i, "image_urls": [f"https://img/{i}.jpg"]}) + "\n" for i in ids))
    np.save(tmp_path / "embeddings.npy", np.zeros((len(ids), 3), np.float32))
    return tmp_path


def fetch(url):
    if "bad" in url:
        raise OSError("gone")
    return Image.new("RGB", (40, 40), (20, 90, 40) if "green" in url else (128, 128, 128))


def test_colours_are_aligned_with_rows_and_unknown_where_the_photo_is_gone(tmp_path):
    d = index_dir(tmp_path, ["depop:green", "depop:bad", "depop:grey"])
    stats = K.build_colors(d, fetch, workers=2, chunk=2)
    c = np.load(d / "colors.npy")
    assert c.shape == (3, 3) and stats["colored"] == 2 and stats["no_photo"] == 1
    assert c[0][1] < -20 < 20 < c[0][2] and np.isnan(c[1]).all() and abs(c[2][1]) < 2   # green, unknown, grey


def test_rerun_resumes_without_refetching(tmp_path):
    d = index_dir(tmp_path, ["depop:green", "depop:grey"])
    K.build_colors(d, fetch, workers=1, chunk=1)
    calls = []
    K.build_colors(d, lambda u: calls.append(u) or fetch(u), workers=1, chunk=1)
    assert calls == [] and np.load(d / "colors.npy").shape == (2, 3)


def test_a_new_listing_is_added_on_rerun_in_row_order(tmp_path):
    d = index_dir(tmp_path, ["depop:grey"])
    K.build_colors(d, fetch, workers=1)
    index_dir(tmp_path, ["depop:green", "depop:grey"])
    stats = K.build_colors(d, fetch, workers=1)
    c = np.load(d / "colors.npy")
    assert stats["resumed"] == 1 and c.shape == (2, 3) and c[0][1] < -20 and abs(c[1][1]) < 2
