"""Side-by-side of the two /detect backends on your own photos, to pick one.

  uv run python ml/compare_detect.py PHOTOS_DIR [OUT_DIR]

Writes OUT_DIR/<photo>.jpg: SegFormer (+ Haiku when ANTHROPIC_API_KEY is set) on the left, YOLOS on the right,
and prints each garment with its confidence. An empty result means the app searches the whole photo."""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from backend.detect import DEFAULT_LLM, detect, upright

COLORS = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#46f0f0"]


def draw(im: Image.Image, resp: dict, title: str) -> Image.Image:
    im = im.copy()
    d, (W, H) = ImageDraw.Draw(im), im.size
    for g, c in zip(resp["garments"], COLORS * 3):
        b = g["box"]
        x0, y0 = b["x"] * W, b["y"] * H
        d.rectangle((x0, y0, x0 + b["w"] * W, y0 + b["h"] * H), outline=c, width=max(2, W // 200))
        d.text((x0 + 4, y0 + 4), f"{g['label']} {g['confidence']:.2f}", fill=c)
    d.text((8, 8), title if resp["garments"] else f"{title}: nothing, search whole photo", fill="black")
    return im


def main(src: str, out: str = "detect_compare"):
    Path(out).mkdir(exist_ok=True)
    seg_name = "segformer+haiku" if DEFAULT_LLM else "segformer"
    for p in sorted(Path(src).iterdir()):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        im = upright(Image.open(p))
        im.thumbnail((1024, 1024))  # what the frontend uploads
        panels = []
        for backend, name in [("segformer", seg_name), ("yolos", "yolos")]:
            t = time.time()
            resp = detect(im, backend=backend)
            print(f"{p.name:30} {name:16} {time.time() - t:4.1f}s  "
                  + (", ".join(f"{g['label']} ({g['category']}) {g['confidence']:.2f}" for g in resp["garments"]) or "-"))
            panels.append(draw(im, resp, name))
        sheet = Image.new("RGB", (im.width * 2, im.height), "white")
        sheet.paste(panels[0], (0, 0))
        sheet.paste(panels[1], (im.width, 0))
        sheet.save(Path(out) / f"{p.stem}.jpg", quality=85)
    print(f"\nside-by-sides in {out}/")


if __name__ == "__main__":
    main(*sys.argv[1:])
