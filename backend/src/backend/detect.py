"""POST /detect: find each garment in a shopper's photo. Returns schema/api.schema.json#DetectResponse.

Default: SegFormer-B2 clothes (ONNX) gives one box per garment class, then Claude Haiku looks at each crop to name
it, pick our category, and split layered uppers (a jacket over a t-shirt). Haiku also covers photos SegFormer finds
nothing in. Without an API key, or when Haiku fails, the SegFormer labels stand. `backend="yolos"` swaps in
YOLOS-Fashionpedia (ONNX), which names categories itself, for comparison."""
import base64
import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from PIL import Image, ImageOps

SEGFORMER = ("mattmdjaga/segformer_b2_clothes", "onnx/model.onnx")
YOLOS = ("onnx-community/yolos-fashionpedia-ONNX", "onnx/model.onnx")
HAIKU = "claude-haiku-5-5"
CATEGORIES = ["jackets_outerwear", "hoodies_sweatshirts", "tshirts", "sneakers", "jeans_pants", "sweaters_knitwear",
              "shirts", "dresses_skirts"]
UPPERS = ["jackets_outerwear", "hoodies_sweatshirts", "tshirts", "sweaters_knitwear", "shirts"]
LABEL = {"jackets_outerwear": "jacket", "hoodies_sweatshirts": "hoodie", "tshirts": "t-shirt", "sneakers": "sneakers",
         "jeans_pants": "pants", "sweaters_knitwear": "sweater", "shirts": "shirt", "dresses_skirts": "dress or skirt"}
CATEGORY_TEXT = Path(__file__).with_name("category_text.npy")  # FashionSigLIP text vectors, CATEGORIES order
SCALE = 100.0      # cosine -> logits for the zero-shot softmax
MEAN, STD = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
MIN_AREA = 0.005   # share of the image a garment must cover
MIN_SCORE = 0.5    # YOLOS class probability
SAME = 0.5         # IoU above which two YOLOS boxes of one category are the same garment
PART = 0.25        # a SegFormer blob this share of a garment's largest blob belongs to the same garment
SURE = 0.7         # SegFormer mean confidence: real garments score 0.84-0.99, fragments on product shots 0.4-0.7

SEG_CLASSES = {4: ("top", None), 5: ("skirt", "dresses_skirts"), 6: ("pants", "jeans_pants"),
               7: ("dress", "dresses_skirts")}  # uppers get their category from Haiku
SEG_SHOES = (9, 10)  # left shoe, right shoe
YOLOS_CLASSES = {
    0: ("shirt", "shirts"), 1: ("top", "tshirts"), 2: ("sweater", "sweaters_knitwear"),
    3: ("cardigan", "sweaters_knitwear"), 4: ("jacket", "jackets_outerwear"), 5: ("vest", "jackets_outerwear"),
    6: ("pants", "jeans_pants"), 7: ("shorts", "jeans_pants"), 8: ("skirt", "dresses_skirts"),
    9: ("coat", "jackets_outerwear"), 10: ("dress", "dresses_skirts"), 11: ("jumpsuit", None),
    12: ("cape", "jackets_outerwear"), 23: ("shoes", "sneakers"),
}


@cache
def _session(repo: str, file: str) -> ort.InferenceSession:
    return ort.InferenceSession(hf_hub_download(repo, file), providers=["CPUExecutionProvider"])


def upright(image: Image.Image) -> Image.Image:
    """Apply the phone's EXIF rotation, so boxes match what the browser draws."""
    return ImageOps.exif_transpose(image).convert("RGB")


def _pixels(im: Image.Image, size: tuple[int, int]) -> np.ndarray:
    x = (np.asarray(im.resize(size, Image.BILINEAR), np.float32) / 255 - MEAN) / STD
    return x.transpose(2, 0, 1)[None].astype(np.float32)


def _clamp(x, y, w, h) -> dict:
    """(x, y, w, h) trimmed to the image: everything in 0-1."""
    x0, y0 = min(1.0, max(0.0, float(x))), min(1.0, max(0.0, float(y)))
    x1, y1 = min(1.0, max(x0, float(x + w))), min(1.0, max(y0, float(y + h)))
    return {"x": round(x0, 4), "y": round(y0, 4), "w": round(x1 - x0, 4), "h": round(y1 - y0, 4)}


def _region(label, category, box, confidence) -> dict:
    return {"label": label, "category": category, "box": _clamp(*box), "confidence": round(float(confidence), 4)}


# --- SegFormer -------------------------------------------------------------------------

def _blobs(mask: np.ndarray) -> list[np.ndarray]:
    """4-connected components of a boolean mask, largest first, as flat pixel indices."""
    h, w = mask.shape
    seen, flat, out = np.zeros(mask.size, bool), mask.ravel(), []
    for start in np.flatnonzero(flat):
        if seen[start]:
            continue
        seen[start], stack, blob = True, [start], []
        while stack:
            i = stack.pop()
            blob.append(i)
            r, c = divmod(i, w)
            for j, ok in ((i - w, r > 0), (i + w, r < h - 1), (i - 1, c > 0), (i + 1, c < w - 1)):
                if ok and flat[j] and not seen[j]:
                    seen[j] = True
                    stack.append(j)
        out.append(np.array(blob))
    return sorted(out, key=len, reverse=True)


def _seg_box(idx: np.ndarray, probs: np.ndarray):
    h, w = probs.shape
    ys, xs = np.divmod(idx, w)
    box = (xs.min() / w, ys.min() / h, (xs.max() + 1 - xs.min()) / w, (ys.max() + 1 - ys.min()) / h)
    return box, probs.ravel()[idx].mean()


def seg_regions(labels: np.ndarray, probs: np.ndarray) -> list[dict]:
    """One region per garment class: its largest blob plus any blob at least PART of its size (a garment cut in
    two by an arm), so small patches elsewhere (another person, the background) do not stretch the box."""
    min_px, out = MIN_AREA * labels.size, []
    for cls, (label, category) in SEG_CLASSES.items():
        blobs = _blobs(labels == cls)
        if blobs and len(blobs[0]) >= min_px:
            keep = [b for b in blobs if len(b) >= PART * len(blobs[0])]
            out.append(_region(label, category, *_seg_box(np.concatenate(keep), probs)))
    shoes = [b for b in _blobs(np.isin(labels, SEG_SHOES))[:2] if len(b) >= min_px / 4]
    if shoes:
        out.append(_region("shoes", "sneakers", *_seg_box(np.concatenate(shoes), probs)))
    return out


def segformer(im: Image.Image) -> list[dict]:
    logits = _session(*SEGFORMER).run(None, {"pixel_values": _pixels(im, (512, 512))})[0][0]
    p = np.exp(logits - logits.max(0))
    p /= p.sum(0)
    return seg_regions(p.argmax(0), p.max(0))


# --- YOLOS -----------------------------------------------------------------------------

def _iou(a, b) -> float:
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def yolos_regions(logits: np.ndarray, boxes: np.ndarray) -> list[dict]:
    p = np.exp(logits[0] - logits[0].max(-1, keepdims=True))
    p = (p / p.sum(-1, keepdims=True))[:, :-1]  # drop no-object
    kept = []  # (score, label, category, (x, y, w, h))
    for i in np.argsort(-p.max(-1)):
        cls, score = int(p[i].argmax()), float(p[i].max())
        if score < MIN_SCORE or cls not in YOLOS_CLASSES:
            continue
        cx, cy, w, h = boxes[0, i]
        box = (cx - w / 2, cy - h / 2, w, h)
        label, category = YOLOS_CLASSES[cls]
        if any(k[2] == category and _iou(k[3], box) > SAME for k in kept):
            continue
        kept.append((score, label, category, box))
    shoes = [k for k in kept if k[2] == "sneakers"]
    if len(shoes) > 1:  # left and right shoe: one garment
        x0, y0 = min(k[3][0] for k in shoes), min(k[3][1] for k in shoes)
        x1, y1 = max(k[3][0] + k[3][2] for k in shoes), max(k[3][1] + k[3][3] for k in shoes)
        kept = [k for k in kept if k[2] != "sneakers"] + [(shoes[0][0], "shoes", "sneakers", (x0, y0, x1 - x0, y1 - y0))]
    return [_region(label, category, box, score) for score, label, category, box in kept]


def yolos(im: Image.Image) -> list[dict]:
    k = min(512 / min(im.size), 864 / max(im.size))
    logits, boxes = _session(*YOLOS).run(None, {"pixel_values": _pixels(im, (round(im.width * k), round(im.height * k)))})
    return yolos_regions(logits, boxes)


# --- Haiku -----------------------------------------------------------------------------

PROMPT = """This is a crop from a shopper's photo. A segmentation model calls it "{hint}".
List each separate clothing item clearly visible that someone could buy secondhand. A jacket worn open over a \
t-shirt is two items. Ignore accessories, skin and background. Outermost or largest item first.
For each item give: label (2-3 plain words, e.g. "denim jacket"), category (one of the allowed values, or null if \
none fits), and box (x, y, w, h as fractions of this crop, origin top-left)."""

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["garments"],
    "properties": {"garments": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["label", "category", "box"],
        "properties": {
            "label": {"type": "string"},
            "category": {"type": ["string", "null"], "enum": [*CATEGORIES, None]},
            "box": {"type": "object", "additionalProperties": False, "required": ["x", "y", "w", "h"],
                    "properties": {k: {"type": "number"} for k in "xywh"}},
        }}}},
}


@cache
def _client():
    import anthropic
    return anthropic.Anthropic(timeout=20, max_retries=1)


def describe(jpeg: bytes, hint: str) -> list[dict]:
    """Ask Haiku what garments are in one crop. Raises on API errors; the caller falls back."""
    msg = _client().messages.create(
        model=HAIKU, max_tokens=1024, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(jpeg).decode()}},
            {"type": "text", "text": PROMPT.format(hint=hint)},
        ]}],
    )
    if msg.stop_reason == "refusal":
        return []
    return json.loads(next(b.text for b in msg.content if b.type == "text"))["garments"]


def clean(g: dict) -> dict:
    return {"label": g["label"].strip().lower(), "category": g["category"] if g["category"] in CATEGORIES else None,
            "box": _clamp(*(g["box"][k] for k in "xywh"))}


def _jpeg(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def _crop(im: Image.Image, box: dict, pad: float) -> tuple[Image.Image, tuple]:
    """The region plus `pad` of its size on each side; also the crop's own box in image fractions."""
    x0, y0 = max(0.0, box["x"] - pad * box["w"]), max(0.0, box["y"] - pad * box["h"])
    x1, y1 = min(1.0, box["x"] + (1 + pad) * box["w"]), min(1.0, box["y"] + (1 + pad) * box["h"])
    W, H = im.size
    return im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H))), (x0, y0, x1 - x0, y1 - y0)


def _haiku(im: Image.Image, region: dict, llm, pad: float) -> list[dict]:
    try:
        crop, (cx, cy, cw, ch) = _crop(im, region["box"], pad)
        found = [clean(g) for g in llm(_jpeg(crop), region["label"])]
    except Exception:  # noqa: BLE001  any Haiku failure: keep what SegFormer saw
        return [region]
    if len(found) <= 1:
        return [{**region, "label": g["label"], "category": g["category"] or region["category"]} for g in found] or [region]
    return [_region(g["label"], g["category"], (cx + g["box"]["x"] * cw, cy + g["box"]["y"] * ch, g["box"]["w"] * cw,
                                                g["box"]["h"] * ch), region["confidence"] * (1 - 0.1 * i))
            for i, g in enumerate(found)]


def relabel(im: Image.Image, regions: list[dict], llm, pad: float = 0.1) -> list[dict]:
    """Haiku names (and splits) each region, all crops in parallel."""
    if llm is None or not regions:
        return regions
    with ThreadPoolExecutor(len(regions)) as pool:
        return [g for gs in pool.map(lambda r: _haiku(im, r, llm, pad), regions) for g in gs]


def _haiku_only(im: Image.Image, llm) -> list[dict]:
    if llm is None:
        return []
    try:
        found = [clean(g) for g in llm(_jpeg(im), "the whole photo")]
    except Exception:  # noqa: BLE001
        return []
    return [_region(g["label"], g["category"], [g["box"][k] for k in "xywh"], 0.5) for g in found]


# --- FashionSigLIP zero-shot category -----------------------------------------------------

def zero_shot(vec: np.ndarray, texts: np.ndarray, allowed: list[str] = CATEGORIES) -> tuple[str, float]:
    """The allowed category whose text vector is closest to the image vector, with its softmax share."""
    idx = [CATEGORIES.index(c) for c in allowed]
    logits = SCALE * (texts[idx] @ vec)
    p = np.exp(logits - logits.max())
    p /= p.sum()
    return allowed[int(p.argmax())], float(p.max())


@cache
def _texts() -> np.ndarray:
    return np.load(CATEGORY_TEXT)


def name(im: Image.Image, allowed: list[str] = CATEGORIES) -> tuple[str, float]:
    """Our category for a garment photo: the same FashionSigLIP model /search embeds with, no API call."""
    from backend.embed import embed_image
    return zero_shot(embed_image(im), _texts(), allowed)


def _name_top(im: Image.Image, r: dict) -> dict:
    """SegFormer only knows "upper clothes": pick which upper when Haiku did not."""
    if r["category"] is not None or r["label"] != "top":
        return r
    try:
        cat, _ = name(_crop(im, r["box"], 0.1)[0], UPPERS)
    except Exception:  # noqa: BLE001  no model: the region stays an unnamed top
        return r
    return {**r, "label": LABEL[cat], "category": cat}


def _whole(im: Image.Image) -> list[dict]:
    """A product shot (one item, nothing worn): the whole photo is the garment."""
    try:
        cat, conf = name(im, CATEGORIES)
    except Exception:  # noqa: BLE001  no model: an empty list tells the app to search the whole photo
        return []
    return [_region(LABEL[cat], cat, (0, 0, 1, 1), conf)]


# --- response --------------------------------------------------------------------------

def response(im: Image.Image, regions: list[dict]) -> dict:
    ranked = sorted(regions, key=lambda r: -r["confidence"])
    return {"image": {"width": im.width, "height": im.height},
            "garments": [{"id": f"g{i}", **r} for i, r in enumerate(ranked)]}


DEFAULT_LLM = describe if os.getenv("ANTHROPIC_API_KEY") else None


def detect(image: Image.Image, backend: str = "segformer", llm=DEFAULT_LLM) -> dict:
    im = upright(image)
    if backend == "yolos":
        return response(im, yolos(im))
    regions = [r for r in segformer(im) if r["confidence"] >= SURE]
    if regions:
        return response(im, [_name_top(im, r) for r in relabel(im, regions, llm)])
    return response(im, _haiku_only(im, llm) or _whole(im))
