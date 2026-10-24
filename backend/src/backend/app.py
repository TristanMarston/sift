"""The HTTP API (schema/API.md §1): GET /health, POST /detect, POST /search. Every error is {"error": {code, message}}.

  uv run uvicorn backend.app:app --port 8000

SIFT_INDEX: the step-05 index folder (default pipeline/data/index). SIFT_CORS_ORIGINS: comma-separated web origins
(default http://localhost:3000). Models and the index load on first use, so the server starts at once."""
import io
import json
import os
from functools import cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend import ranker

MAX_BYTES = 10 * 1024 * 1024
FORMATS = {"JPEG", "PNG", "WEBP"}
K = 50
DUPLICATE = 0.97  # photo similarity at which two listings are one item; checked by eye on the first real batch
MIN_SIM = 0.3  # cosine below this looks nothing alike: dropped, so a search may come back empty (API.md: Result set)
INDEX = Path(os.getenv("SIFT_INDEX", Path(__file__).resolve().parents[2] / "pipeline" / "data" / "index"))

Category = Literal["jackets_outerwear", "hoodies_sweatshirts", "tshirts", "sneakers", "jeans_pants",
                   "sweaters_knitwear", "shirts", "dresses_skirts"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Filters(_Strict):
    max_price_cents: int | None = Field(None, ge=0)
    marketplaces: list[Literal["depop", "poshmark", "grailed", "mercari", "ebay"]] | None = None
    sizes: list[str] | None = None
    conditions: list[Literal["new_with_tags", "like_new", "good", "fair"]] | None = None


class SearchParams(_Strict):
    category: Category | None = None
    filters: Filters | None = None


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _error(status, code, message):
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _photo(upload: UploadFile | None) -> Image.Image:
    if upload is None:
        raise ApiError(400, "invalid_image", "no image file in the request (field `image`)")
    data = upload.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError(413, "image_too_large", "the image is over 10 MB")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError):
        raise ApiError(400, "invalid_image", "the file is not a readable image") from None
    if im.format not in FORMATS:
        raise ApiError(400, "invalid_image", f"unsupported image type {im.format}; use JPEG, PNG or WebP")
    from backend.detect import upright  # same EXIF handling as /detect, so crops line up
    return upright(im)


def _params(raw: str | None) -> SearchParams:
    try:
        return SearchParams(**json.loads(raw)) if raw else SearchParams()
    except (json.JSONDecodeError, TypeError, ValidationError) as e:
        raise ApiError(400, "invalid_params", f"`params` must be JSON matching SearchParams: {e}") from None


def create_app(index=None, cfg=None, embed=None, detect=None, categorize=None, origins=None) -> FastAPI:
    """Pass the index, ranking config and models to test; otherwise each loads on first use."""
    @cache
    def deps():
        from backend.index import Index
        return (index if index is not None else Index.load(INDEX), cfg or ranker.load_config())

    def embed_fn(im):
        if embed is not None:
            return embed(im)
        from backend.embed import embed_image
        return embed_image(im)

    def category_of(vec) -> str:
        """Similarity alone cannot keep other categories out (median 0.54 vs 0.61 for the same category on the test
        scrape), so a search without a category uses the one FashionSigLIP reads from the same vector."""
        if categorize is not None:
            return categorize(vec)
        from backend.detect import _texts, zero_shot
        return zero_shot(vec, _texts())[0]

    def detect_fn(im):
        if detect is not None:
            return detect(im)
        from backend.detect import detect as run
        return run(im)

    app = FastAPI(title="Sift API")
    app.add_middleware(CORSMiddleware, allow_methods=["GET", "POST"], allow_headers=["*"],
                       allow_origins=origins or os.getenv("SIFT_CORS_ORIGINS", "http://localhost:3000").split(","))

    @app.exception_handler(ApiError)
    def api_error(request: Request, e: ApiError):
        return _error(e.status, e.code, e.message)

    @app.exception_handler(Exception)
    def internal(request: Request, e: Exception):
        return _error(500, "internal", "something went wrong on our side")

    @app.get("/health")
    def health():
        return {"status": "ok", "index_size": len(deps()[0])}

    @app.post("/detect")
    def detect_route(image: UploadFile | None = File(None)):
        return detect_fn(_photo(image))

    @app.post("/search")
    def search(image: UploadFile | None = File(None), params: str | None = Form(None)):
        q = _params(params)
        idx, conf = deps()
        vec = embed_fn(_photo(image))
        category = q.category or category_of(vec)
        f = q.filters or Filters()
        hits = idx.search(vec, k=K, min_sim=MIN_SIM, category=category, max_price_cents=f.max_price_cents,
                          marketplaces=f.marketplaces, sizes=f.sizes, conditions=f.conditions, dedupe=DUPLICATE)
        return ranker.rank(hits, {**q.model_dump(exclude_unset=True), "category": category}, conf)

    return app


app = create_app()
