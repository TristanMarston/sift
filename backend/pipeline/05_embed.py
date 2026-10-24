"""Step 05: data/listings.jsonl -> data/index/ (one FashionSigLIP vector per active listing, from its first photo).

  uv run python pipeline/05_embed.py [--test] [--workers 32]

Resumable: rerun after a crash or Ctrl-C and finished chunks are kept. Needs the model weights in the HF cache
(set HF_HUB_DISABLE_XET=1 on slow wifi)."""
import argparse
import io
import urllib.request
from pathlib import Path

from PIL import Image

import embed_index
from backend.embed import DIM, MODEL_ID, embed_images

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


def fetch(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    im.thumbnail((384, 384))  # keeps the aspect ratio; embed handles the rest
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", action="store_true", help="work on data/test/ (the go/no-go run)")
    ap.add_argument("--workers", type=int, default=32, help="parallel photo downloads (default 32)")
    args = ap.parse_args()
    data = HERE / "data" / ("test" if args.test else "")
    stats = embed_index.build_index(data / "listings.jsonl", data / "index", fetch, embed_images,
                                    dim=DIM, workers=args.workers, model=MODEL_ID)
    print(dict(stats))


if __name__ == "__main__":
    main()
