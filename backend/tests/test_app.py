"""The HTTP API (schema/API.md §1): every response, including errors, must match schema/api.schema.json."""
import io
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from PIL import Image

from backend import app as A
from backend import ranker as R
from backend.index import Index
from conftest import make_row

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schema" / "api.schema.json").read_text())
CFG = R.Config(baselines={"as_of": "2026-10-23", "source": "team assumption",
                          "categories": {c: {"low": 50, "high": 100} for c in
                                         ["jackets_outerwear", "sneakers"]}}, brands={})


def valid(defn, body):
    errors = list(Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{defn}"}).iter_errors(body))
    assert not errors, [e.message for e in errors[:5]]
    return body


def price(cents):
    return dict(cost=dict(price_cents=cents, total_cents=cents))


# The query photo embeds to e0, so a row's similarity is its first coordinate.
ROWS = [
    (make_row("close", **price(6000)), [1.0, 0.0, 0.0]),
    (make_row("near", marketplace="ebay", url="https://www.ebay.com/itm/near", **price(3000)), [0.8, 0.6, 0.0]),
    (make_row("far", **price(1000)), [0.0, 1.0, 0.0]),                   # below the similarity cutoff
    (make_row("shoe", category="sneakers", **price(2000)), [0.9, 0.1, 0.0]),
]


@pytest.fixture
def client():
    index = Index(np.array([v for _, v in ROWS], np.float32), [r for r, _ in ROWS])
    detect = lambda im: {"image": {"width": im.width, "height": im.height}, "garments": []}  # noqa: E731
    return TestClient(A.create_app(index=index, cfg=CFG, embed=lambda im: np.array([1.0, 0.0, 0.0], np.float32),
                                   detect=detect, categorize=lambda vec: "jackets_outerwear",
                                   origins=["https://sift.example"]))


def jpeg(size=(64, 64), fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", size, "navy").save(buf, fmt)
    return buf.getvalue()


def search(client, params=None, image=None):
    data = {} if params is None else {"params": params if isinstance(params, str) else json.dumps(params)}
    return client.post("/search", files={"image": ("crop.jpg", jpeg() if image is None else image, "image/jpeg")},
                       data=data)


def error_code(resp, status):
    assert resp.status_code == status, resp.text
    return valid("Error", resp.json())["error"]["code"]


# --- GET /health -----------------------------------------------------------------------

def test_health_reports_the_index_size(client):
    assert client.get("/health").json() == {"status": "ok", "index_size": 4}


# --- POST /search ----------------------------------------------------------------------

def test_search_ranks_look_alikes_and_drops_the_ones_that_look_nothing_alike(client):
    body = valid("SearchResponse", search(client, {"category": "jackets_outerwear", "filters": {}}).json())
    assert [r["id"] for r in body["results"]] == body["orders"]["cpw"]
    assert set(body["orders"]["cpw"]) == {"depop:close", "ebay:near"}
    assert body["query"] == {"category": "jackets_outerwear", "filters": {}}


def test_every_param_is_optional_and_a_missing_category_is_read_from_the_photo(client):
    # similarity alone cannot keep sneakers out of a jacket search (other categories score 0.54 on median, same 0.61),
    # so with no category the photo's own FashionSigLIP vector names one, and the response says which
    body = valid("SearchResponse", search(client).json())
    assert {r["id"] for r in body["results"]} == {"depop:close", "ebay:near"}
    assert body["query"] == {"category": "jackets_outerwear"}
    body = valid("SearchResponse", search(client, {"filters": {"max_price_cents": 3000}}).json())
    assert body["query"] == {"category": "jackets_outerwear", "filters": {"max_price_cents": 3000}}


def test_an_explicit_category_is_kept(client):
    body = search(client, {"category": "sneakers"}).json()
    assert [r["id"] for r in body["results"]] == ["depop:shoe"] and body["query"] == {"category": "sneakers"}


@pytest.mark.parametrize("filters, ids", [
    ({"max_price_cents": 3000}, {"ebay:near"}),
    ({"marketplaces": ["ebay"]}, {"ebay:near"}),
    ({"conditions": ["fair"]}, set()),
])
def test_filters_narrow_the_results(client, filters, ids):
    body = search(client, {"category": "jackets_outerwear", "filters": filters}).json()
    assert {r["id"] for r in valid("SearchResponse", body)["results"]} == ids


@pytest.mark.parametrize("params", [
    "{not json",
    {"category": "hats"},
    {"filters": {"max_price_cents": -5}},
    {"filters": {"colour": "red"}},
    {"surprise": 1},
])
def test_bad_params_are_invalid_params(client, params):
    assert error_code(search(client, params), 400) == "invalid_params"


def heic(size=(64, 48)):
    """An iPhone photo as the browser hands it over (Pillow needs pillow-heif to read it)."""
    import pillow_heif
    pillow_heif.register_heif_opener()
    return jpeg(size, "HEIF")


def test_heic_photos_are_accepted_like_jpeg(client):
    """iPhones shoot HEIC. The file is decoded at the door; everything after (upright, embed, detect) sees a PIL
    image as before, so the embedding pipeline is unchanged."""
    body = valid("SearchResponse", search(client, image=heic()).json())
    assert [r["id"] for r in body["results"]] == [r["id"] for r in search(client).json()["results"]]
    d = client.post("/detect", files={"image": ("p.heic", heic(), "image/heic")})
    assert d.status_code == 200 and d.json()["image"] == {"width": 64, "height": 48}


def test_jpeg_converts_a_photo_the_browser_cannot_decode(client):
    """Chrome cannot draw a HEIC file, so the web app asks for a JPEG (upright, long edge at most 1024 px) and carries on
    with its usual crop-and-search."""
    r = client.post("/jpeg", files={"image": ("p.heic", heic((2048, 1024)), "image/heic")})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    im = Image.open(io.BytesIO(r.content))
    assert (im.format, im.size) == ("JPEG", (1024, 512))
    assert error_code(client.post("/jpeg", files={"image": ("p.txt", b"hello", "text/plain")}), 400) == "invalid_image"


def test_a_file_that_is_not_a_photo_is_invalid_image(client):
    assert error_code(search(client, image=b"%PDF-1.4 not a photo"), 400) == "invalid_image"
    assert error_code(client.post("/search", data={"params": "{}"}), 400) == "invalid_image"  # no file at all


def test_photos_over_10_mb_are_refused(client):
    assert error_code(search(client, image=b"\xff" * (10 * 1024 * 1024 + 1)), 413) == "image_too_large"


@pytest.mark.parametrize("fmt", ["PNG", "WEBP"])
def test_png_and_webp_are_accepted(client, fmt):
    assert search(client, image=jpeg(fmt=fmt)).status_code == 200


def test_an_unexpected_failure_is_a_500_in_the_error_shape():
    def broken(im):
        raise RuntimeError("model fell over")
    app = A.create_app(index=Index(np.zeros((0, 3), np.float32), []), cfg=CFG, embed=broken, detect=None)
    assert error_code(TestClient(app, raise_server_exceptions=False).post(
        "/search", files={"image": ("c.jpg", jpeg(), "image/jpeg")}), 500) == "internal"


# --- POST /detect ----------------------------------------------------------------------

def test_detect_returns_the_garments(client):
    body = valid("DetectResponse", client.post("/detect", files={"image": ("p.jpg", jpeg((80, 60)), "image/jpeg")}).json())
    assert body == {"image": {"width": 80, "height": 60}, "garments": []}


def test_detect_refuses_non_photos(client):
    assert error_code(client.post("/detect", files={"image": ("p.txt", b"hello", "text/plain")}), 400) == "invalid_image"


# --- CORS ------------------------------------------------------------------------------

def test_the_web_app_origin_may_call_the_api(client):
    resp = client.get("/health", headers={"Origin": "https://sift.example"})
    assert resp.headers["access-control-allow-origin"] == "https://sift.example"
    assert "access-control-allow-origin" not in client.get("/health", headers={"Origin": "https://evil.example"}).headers


def test_search_shows_a_cross_posted_item_once_at_its_lowest_price():
    same = [1.0, 0.0, 0.0]
    rows = [(make_row("a", marketplace="mercari", url="https://www.mercari.com/us/item/a", **price(5400)), same),
            (make_row("b", marketplace="poshmark", url="https://poshmark.com/listing/b", **price(4500)), same)]
    index = Index(np.array([v for _, v in rows], np.float32), [r for r, _ in rows])
    c = TestClient(A.create_app(index=index, cfg=CFG, embed=lambda im: np.array(same, np.float32),
                                categorize=lambda v: "jackets_outerwear"))
    body = valid("SearchResponse", search(c, {"category": "jackets_outerwear"}).json())
    assert [r["id"] for r in body["results"]] == ["poshmark:b"]


def test_vercel_preview_urls_can_be_allowed_by_pattern():
    index = Index(np.zeros((0, 3), np.float32), [])
    c = TestClient(A.create_app(index=index, cfg=CFG, origin_regex=r"https://sift(-[a-z0-9-]+)?\.vercel\.app"))
    ok = c.get("/health", headers={"Origin": "https://sift-git-main-tristan.vercel.app"})
    assert ok.headers["access-control-allow-origin"] == "https://sift-git-main-tristan.vercel.app"
    assert "access-control-allow-origin" not in c.get("/health", headers={"Origin": "https://evil.vercel.app"}).headers
