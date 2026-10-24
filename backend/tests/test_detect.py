import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from PIL import Image

from backend import detect as D

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "schema" / "api.schema.json").read_text())
UPPER, PANTS, SHOE_L, SHOE_R = 4, 6, 9, 10


def validate(resp):
    errors = list(Draft202012Validator({**SCHEMA, "$ref": "#/$defs/DetectResponse"}).iter_errors(resp))
    assert not errors, [e.message for e in errors[:5]]


def seg(*blocks, size=100, p=0.9):
    """A label map with rectangular blocks (cls, x0, y0, x1, y1) and a flat class probability."""
    labels = np.zeros((size, size), np.int64)
    for c, x0, y0, x1, y1 in blocks:
        labels[y0:y1, x0:x1] = c
    return labels, np.full((size, size), p, np.float32)


def box(r):
    return [round(v, 2) for v in (r["box"]["x"], r["box"]["y"], r["box"]["w"], r["box"]["h"])]


# --- SegFormer regions -----------------------------------------------------------------

def test_one_box_per_garment_class_normalized():
    rs = D.seg_regions(*seg((UPPER, 20, 10, 80, 50), (PANTS, 30, 50, 70, 90)))
    assert [(r["label"], r["category"]) for r in rs] == [("top", None), ("pants", "jeans_pants")]
    assert box(rs[0]) == [0.2, 0.1, 0.6, 0.4] and rs[0]["confidence"] == pytest.approx(0.9)


def test_only_the_largest_blob_counts_so_a_second_person_does_not_stretch_the_box():
    rs = D.seg_regions(*seg((UPPER, 0, 0, 30, 40), (UPPER, 60, 0, 70, 10)))
    assert box(rs[0]) == [0.0, 0.0, 0.3, 0.4]


def test_left_and_right_shoes_make_one_sneakers_box():
    rs = D.seg_regions(*seg((SHOE_L, 10, 80, 20, 90), (SHOE_R, 40, 80, 50, 90)))
    assert [(r["label"], r["category"]) for r in rs] == [("shoes", "sneakers")]
    assert box(rs[0]) == [0.1, 0.8, 0.4, 0.1]


def test_tiny_specks_and_non_catalog_classes_are_ignored():
    hat, bag = 1, 16
    assert D.seg_regions(*seg((UPPER, 0, 0, 3, 3), (hat, 10, 10, 40, 40), (bag, 50, 50, 90, 90))) == []


# --- YOLOS regions ---------------------------------------------------------------------

def yolos_out(*dets, n=5):
    """logits (1, n, 47) and boxes (1, n, 4) with the given (class, prob, cx, cy, w, h); the rest are no-object."""
    logits = np.full((1, n, 47), -10.0, np.float32)
    logits[0, :, 46] = 10.0
    boxes = np.zeros((1, n, 4), np.float32)
    for i, (c, p, *b) in enumerate(dets):
        logits[0, i, 46] = 0.0                   # no-object vs class c: softmax gives class c probability p
        logits[0, i, c] = np.log(p / (1 - p))
        boxes[0, i] = b
    return logits, boxes


def test_yolos_maps_classes_and_converts_center_boxes():
    jacket, pants = 4, 6
    rs = D.yolos_regions(*yolos_out((jacket, 0.95, 0.5, 0.4, 0.4, 0.4), (pants, 0.9, 0.5, 0.8, 0.3, 0.4)))
    assert [(r["label"], r["category"]) for r in rs] == [("jacket", "jackets_outerwear"), ("pants", "jeans_pants")]
    assert box(rs[0]) == [0.3, 0.2, 0.4, 0.4]


def test_yolos_drops_low_scores_parts_and_overlapping_duplicates():
    jacket, coat, sleeve = 4, 9, 31
    rs = D.yolos_regions(*yolos_out((jacket, 0.9, 0.5, 0.5, 0.4, 0.4), (coat, 0.8, 0.5, 0.5, 0.42, 0.4),
                                    (sleeve, 0.99, 0.2, 0.5, 0.1, 0.3), (jacket, 0.2, 0.8, 0.8, 0.2, 0.2)))
    assert [r["label"] for r in rs] == ["jacket"]


def test_yolos_left_and_right_shoes_make_one_sneakers_box():
    shoe = 23
    rs = D.yolos_regions(*yolos_out((shoe, 0.9, 0.15, 0.85, 0.1, 0.1), (shoe, 0.8, 0.45, 0.85, 0.1, 0.1)))
    assert [(r["label"], r["category"]) for r in rs] == [("shoes", "sneakers")]
    assert box(rs[0]) == [0.1, 0.8, 0.4, 0.1]


# --- Haiku relabel ---------------------------------------------------------------------

IMG = Image.new("RGB", (200, 100), "white")
TOP = {"label": "top", "category": None, "box": {"x": 0.25, "y": 0.0, "w": 0.5, "h": 0.5}, "confidence": 0.9}
PANTS_R = {"label": "pants", "category": "jeans_pants", "box": {"x": 0.25, "y": 0.5, "w": 0.5, "h": 0.5},
           "confidence": 0.8}


def test_haiku_names_a_single_garment_and_the_segmentation_box_is_kept():
    fake = lambda crop, hint: [{"label": "denim jacket", "category": "jackets_outerwear",  # noqa: E731
                               "box": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}}]
    [g] = D.relabel(IMG, [TOP], fake)
    assert g["label"] == "denim jacket" and g["category"] == "jackets_outerwear" and g["box"] == TOP["box"]


def test_haiku_splits_a_layered_upper_into_two_boxes_in_image_coordinates():
    fake = lambda crop, hint: [  # noqa: E731
        {"label": "bomber jacket", "category": "jackets_outerwear", "box": {"x": 0, "y": 0, "w": 1, "h": 1}},
        {"label": "t-shirt", "category": "tshirts", "box": {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}},
    ]
    jacket, tee = D.relabel(IMG, [TOP], fake, pad=0)
    assert jacket["box"] == TOP["box"]
    assert tee["box"] == pytest.approx({"x": 0.375, "y": 0.125, "w": 0.25, "h": 0.25})
    assert tee["confidence"] < jacket["confidence"]


def test_without_haiku_or_when_it_fails_the_segmentation_labels_stand():
    def broken(crop, hint):
        raise RuntimeError("no network")
    assert D.relabel(IMG, [TOP, PANTS_R], None) == [TOP, PANTS_R]
    assert D.relabel(IMG, [TOP, PANTS_R], broken) == [TOP, PANTS_R]
    assert D.relabel(IMG, [TOP], lambda c, h: []) == [TOP]


def test_haiku_answers_are_cleaned():
    g = D.clean({"label": " Jacket ", "category": "hats", "box": {"x": -0.1, "y": 0.5, "w": 2, "h": 0.2}})
    assert g == {"label": "jacket", "category": None, "box": {"x": 0.0, "y": 0.5, "w": 1.0, "h": 0.2}}


# --- response --------------------------------------------------------------------------

def test_response_is_sorted_numbered_and_matches_the_schema():
    resp = D.response(IMG, [PANTS_R, TOP])
    validate(resp)
    assert resp["image"] == {"width": 200, "height": 100}
    assert [(g["id"], g["label"]) for g in resp["garments"]] == [("g0", "top"), ("g1", "pants")]


def test_haiku_only_fallback_when_segmentation_finds_nothing(monkeypatch):
    monkeypatch.setattr(D, "segformer", lambda im: [])
    fake = lambda crop, hint: [{"label": "dress", "category": "dresses_skirts",  # noqa: E731
                               "box": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}}]
    resp = D.detect(IMG, llm=fake)
    validate(resp)
    assert [g["label"] for g in resp["garments"]] == ["dress"]


def test_exif_rotation_is_applied_before_boxes_are_measured():
    im = Image.new("RGB", (200, 100))
    exif = im.getexif()
    exif[0x0112] = 6  # rotated 90 degrees: the phone held upright
    im.info["exif"] = exif.tobytes()
    assert D.upright(im).size == (100, 200)


def test_boxes_hanging_off_the_edge_are_clamped_to_the_image():
    pants = 6
    [r] = D.yolos_regions(*yolos_out((pants, 0.9, 0.2, 0.9, 0.5, 0.4)))
    assert box(r) == [0.0, 0.7, 0.45, 0.3]


def test_describe_sends_the_crop_and_reads_the_structured_answer(monkeypatch):
    sent = {}

    class Messages:
        def create(self, **kw):
            sent.update(kw)
            text = json.dumps({"garments": [{"label": "jacket", "category": "jackets_outerwear",
                                             "box": {"x": 0, "y": 0, "w": 1, "h": 1}}]})
            return type("Msg", (), {"stop_reason": "end_turn", "content": [type("B", (), {"type": "text", "text": text})]})

    monkeypatch.setattr(D, "_client", lambda: type("C", (), {"messages": Messages()})())
    assert D.describe(b"\xff\xd8jpeg", "top")[0]["label"] == "jacket"
    assert sent["model"] == "claude-haiku-5-5"
    assert sent["output_config"]["format"]["type"] == "json_schema"
    image, text = sent["messages"][0]["content"]
    assert image["source"]["media_type"] == "image/jpeg" and '"top"' in text["text"]


def test_unsure_segmentation_counts_as_nothing_so_product_shots_go_to_haiku_or_the_whole_image(monkeypatch):
    # On a lone-sneaker product shot SegFormer (trained on worn clothes) guesses top/pants fragments at ~0.4-0.7
    unsure = [{**TOP, "confidence": 0.62}, {**PANTS_R, "confidence": 0.55}]
    monkeypatch.setattr(D, "segformer", lambda im: unsure)
    fake = lambda crop, hint: [{"label": "sneakers", "category": "sneakers",  # noqa: E731
                               "box": {"x": 0.2, "y": 0.3, "w": 0.6, "h": 0.4}}]
    assert [g["label"] for g in D.detect(IMG, llm=fake)["garments"]] == ["sneakers"]
    monkeypatch.setattr(D, "name", fake_name)
    monkeypatch.setattr(D, "segformer", lambda im: [*unsure, {**TOP, "label": "top", "confidence": 0.95}])
    assert [g["confidence"] for g in D.detect(IMG, llm=None)["garments"]] == [0.95]


def test_a_garment_split_by_an_arm_keeps_both_halves():
    # a hand on the knee cuts the jeans into two blobs: the box must cover both legs
    rs = D.seg_regions(*seg((PANTS, 10, 50, 40, 90), (PANTS, 45, 50, 70, 90)))
    assert box(rs[0]) == [0.1, 0.5, 0.6, 0.4]


# --- FashionSigLIP zero-shot category ---------------------------------------------------

def test_zero_shot_picks_the_closest_category_text_among_the_allowed_ones():
    texts = np.eye(len(D.CATEGORIES), 4, dtype=np.float32)  # category i points along axis i (first 4)
    vec = np.array([0.1, 0.2, 0.9, 0.3], np.float32)          # closest to category 2 (tshirts)
    cat, conf = D.zero_shot(vec, texts)
    assert cat == D.CATEGORIES[2] and 0.5 < conf <= 1
    cat, _ = D.zero_shot(vec, texts, allowed=["jackets_outerwear", "hoodies_sweatshirts"])
    assert cat == "hoodies_sweatshirts"  # axis 1 beats axis 0 once tshirts is not allowed


def fake_name(im, allowed):
    return allowed[-1], 0.8


def test_without_haiku_a_segformer_top_gets_its_category_from_fashionsiglip(monkeypatch):
    monkeypatch.setattr(D, "segformer", lambda im: [TOP, PANTS_R])
    monkeypatch.setattr(D, "name", fake_name)
    tops = [g for g in D.detect(IMG, llm=None)["garments"] if g["box"] == TOP["box"]]
    assert [(g["label"], g["category"]) for g in tops] == [("shirt", "shirts")]  # last of UPPERS


def test_a_product_shot_with_nothing_sure_becomes_one_whole_photo_garment(monkeypatch):
    monkeypatch.setattr(D, "segformer", lambda im: [{**TOP, "confidence": 0.5}])
    monkeypatch.setattr(D, "name", lambda im, allowed: ("sneakers", 0.9))
    resp = D.detect(IMG, llm=None)
    validate(resp)
    assert resp["garments"] == [{"id": "g0", "label": "sneakers", "category": "sneakers",
                                 "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}, "confidence": 0.9}]
    assert D.detect(IMG, llm=lambda c, h: [])["garments"][0]["category"] == "sneakers"  # Haiku found nothing
