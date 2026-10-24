"""Run step 05 (embed) and a quick query on Modal: model weights and listing photos download at datacenter
speed, and only listings.jsonl / a photo / the results cross our own connection.

  uv run modal run modal_app.py::embed --test                 # pipeline/data/test/listings.jsonl -> volume, index back to data/test/index
  uv run modal run modal_app.py::embed                         # full run; the index stays on the volume
  uv run modal run modal_app.py::embed --listings x.jsonl --name sample
  uv run modal run modal_app.py::query --photo jacket.jpg [--name test] [--category jackets_outerwear]
  SIFT_INDEX_NAME=full uv run modal deploy modal_app.py          # the HTTP API (backend.app) at a public URL

Deploy settings come from your shell: SIFT_INDEX_NAME (default full), SIFT_CORS_ORIGINS, SIFT_CORS_ORIGIN_REGEX
(default: the team's Vercel URLs) and SIFT_MIN_CONTAINERS (1 keeps one warm for a demo; it bills while idle).

The index lives on the `sift-index` volume at /vol/<name>/ (name = test | full | ...)."""
import importlib
import json
import os
import sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
REPO, FILE = "Marqo/marqo-fashionSigLIP", "onnx/vision_model.onnx"


def _download_model():
    from huggingface_hub import hf_hub_download
    hf_hub_download(REPO, FILE)


image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("numpy", "pillow", "onnxruntime", "huggingface_hub", "pydantic", "pyyaml")
    .run_function(_download_model)
    .add_local_python_source("backend")
    .add_local_dir(HERE / "pipeline", "/root/pipeline", ignore=["data", "tests", "**/__pycache__"])
)


def _download_api_models():
    from huggingface_hub import hf_hub_download
    hf_hub_download(REPO, FILE)                                          # FashionSigLIP vision tower: /search
    hf_hub_download("mattmdjaga/segformer_b2_clothes", "onnx/model.onnx")  # SegFormer clothes: /detect


api_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("numpy", "pillow", "onnxruntime", "huggingface_hub", "pydantic", "pyyaml", "fastapi",
                 "python-multipart", "anthropic")
    .run_function(_download_api_models)                                  # baked in: cold starts skip 500 MB of downloads
    .env({"SIFT_INDEX": f"/vol/{os.getenv('SIFT_INDEX_NAME', 'full')}/index",
          "SIFT_CORS_ORIGINS": os.getenv("SIFT_CORS_ORIGINS", "http://localhost:3000"),
          "SIFT_CORS_ORIGIN_REGEX": os.getenv("SIFT_CORS_ORIGIN_REGEX", "https://sift(-[a-z0-9-]+)?[.]vercel[.]app")})
    .add_local_python_source("backend", ignore=["**/__pycache__"])     # the default ignore would drop category_text.npy
    .add_local_dir(HERE / "ml", "/ml", ignore=["**/*.py"])               # ranker.ML resolves to /ml in the container
)
app = modal.App("sift", image=image)
vol = modal.Volume.from_name("sift-index", create_if_missing=True)


def _pipeline():
    sys.path.insert(0, "/root/pipeline")
    return importlib.import_module("embed_index"), importlib.import_module("05_embed")


@app.function(volumes={"/vol": vol}, cpu=4, memory=4096, timeout=3 * 3600)
def build(listings: bytes, name: str, workers: int = 64) -> dict:
    from backend.embed import DIM, MODEL_ID, embed_images
    embed_index, step05 = _pipeline()
    d = Path("/vol") / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "listings.jsonl").write_bytes(listings)
    stats = embed_index.build_index(d / "listings.jsonl", d / "index", step05.fetch, embed_images,
                                    dim=DIM, workers=workers, model=MODEL_ID)
    vol.commit()
    return dict(stats)


@app.function(volumes={"/vol": vol})
def index_files(name: str) -> dict:
    d = Path("/vol") / name / "index"
    return {f: (d / f).read_bytes() for f in ["embeddings.npy", "rows.jsonl", "manifest.json"]}


@app.function(volumes={"/vol": vol}, cpu=2, memory=2048)
def search(photo: bytes, name: str, k: int, category: str | None) -> list:
    import io

    from PIL import Image

    from backend.embed import embed_image
    from backend.index import Index
    idx = Index.load(Path("/vol") / name / "index")
    hits = idx.search(embed_image(Image.open(io.BytesIO(photo))), k=k, category=category)
    return [(len(idx), round(sim, 3), r["cost"]["total_cents"], r["marketplace"], r["title"], r["url"]) for r, sim in hits]


@app.local_entrypoint()
def embed(test: bool = False, listings: str = "", name: str = "", download: bool = False):
    data = HERE / "pipeline" / "data" / ("test" if test else "")
    src = Path(listings) if listings else data / "listings.jsonl"
    name = name or ("test" if test else "full")
    print(f"uploading {src} ({src.stat().st_size // 1024} KB) -> volume sift-index:/{name}")
    print(build.remote(src.read_bytes(), name))
    if test or download:
        out = data / "index" if not listings else src.parent / "index"
        out.mkdir(parents=True, exist_ok=True)
        for f, b in index_files.remote(name).items():
            (out / f).write_bytes(b)
        print(f"index copied to {out}")
        print(json.loads((out / "manifest.json").read_text()))


@app.local_entrypoint()
def query(photo: str, name: str = "test", k: int = 10, category: str = ""):
    hits = search.remote(Path(photo).read_bytes(), name, k, category or None)
    print(f"{hits[0][0] if hits else 0} listings indexed; top {len(hits)}:")
    for _, sim, cents, mp, title, url in hits:
        print(f"{sim:.3f}  ${cents / 100:>7.2f}  {mp:<8} {title[:60]}  {url}")


@app.function(image=api_image, volumes={"/vol": vol}, cpu=2, memory=4096, timeout=60, scaledown_window=600,
              min_containers=int(os.getenv("SIFT_MIN_CONTAINERS", "0")))
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def api():
    from backend.app import create_app
    return create_app()
