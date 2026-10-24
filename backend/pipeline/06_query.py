"""Step 06 (a check, not a build step): search the index with a photo and print the top matches.

  uv run python pipeline/06_query.py photo.jpg [--test] [--category jackets_outerwear] [-k 10]
"""
import argparse
from pathlib import Path

from PIL import Image

from backend.embed import embed_image
from backend.index import Index

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=Path)
    ap.add_argument("--test", action="store_true", help="use data/test/index")
    ap.add_argument("--category", help="restrict to one of the 8 categories")
    ap.add_argument("-k", type=int, default=10)
    args = ap.parse_args()
    idx = Index.load(HERE / "data" / ("test" if args.test else "") / "index")
    hits = idx.search(embed_image(Image.open(args.photo)), k=args.k, category=args.category)
    print(f"{len(idx)} listings indexed; top {len(hits)}:")
    for row, sim in hits:
        print(f"{sim:.3f}  ${row['cost']['total_cents'] / 100:>7.2f}  {row['marketplace']:<8} {row['title'][:60]}  {row['url']}")


if __name__ == "__main__":
    main()
