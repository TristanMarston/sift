"""One scraped listing = the static fields of schema/api.schema.json#Result, plus description,
status and evidence. Ranker-computed fields (match, quality, eco, wear, confidence, thumb_url)
are not emitted. Every model forbids extra keys, so seller identity cannot slip into a row."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Marketplace = Literal["depop", "poshmark", "grailed", "mercari", "ebay"]
Category = Literal["jackets_outerwear", "hoodies_sweatshirts", "tshirts", "sneakers",
                   "jeans_pants", "sweaters_knitwear", "shirts", "dresses_skirts"]
Condition = Literal["new_with_tags", "like_new", "good", "fair"]
Certification = Literal["gots", "oeko_tex", "bluesign", "fair_trade", "rws", "rds", "b_corp"]
SellerType = Literal["individual", "small_shop", "large_reseller"]
EvidenceStatus = Literal["verified", "claimed", "inferred", "unknown"]
EvidenceSource = Literal["specifics", "listing_text", "product_line", "tag_image", "model",
                         "brand_table", "baseline"]

Cents = Annotated[int, Field(ge=0)]
Url = Annotated[str, StringConstraints(pattern=r"^https?://\S+$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Flags(_Strict):
    is_vintage: bool = False
    is_deadstock: bool = False
    is_upcycled: bool = False


class Cost(_Strict):
    price_cents: Cents
    currency: Literal["USD"] = "USD"
    shipping_cents: Cents | None = None
    free_shipping: bool | None = None
    total_cents: Cents
    original_price_cents: Cents | None = None
    retail_price_cents: Cents | None = None

    @model_validator(mode="after")
    def _total_is_price_plus_known_shipping(self):
        if self.total_cents != self.price_cents + (self.shipping_cents or 0):
            raise ValueError("total_cents must equal price_cents + shipping_cents (when known)")
        return self


class Fiber(_Strict):
    fiber: str
    pct: Annotated[float, Field(ge=0, le=100)] | None = None
    organic: bool | None = None
    recycled: bool | None = None


class Materials(_Strict):
    fibers: list[Fiber] = []
    synthetic_share: Annotated[float, Field(ge=0, le=100)] | None = None
    certifications: list[Certification] = []
    composition_suspect: bool = False


class Seller(_Strict):
    type: SellerType | None = None
    rating: float | None = None
    region: str | None = None
    listing_count: Cents | None = None


class Evidence(_Strict):
    field: str
    status: EvidenceStatus
    source: EvidenceSource
    snippet: str | None = None
    as_of: date


class Listing(_Strict):
    id: Annotated[str, StringConstraints(pattern=r"^(depop|poshmark|grailed|mercari|ebay):.+$")]
    marketplace: Marketplace
    external_id: str
    url: Url
    title: str
    description: str | None = None
    status: Literal["active", "sold"]
    scraped_at: datetime
    brand: str | None = None
    category: Category
    subcategory: str | None = None
    size: str | None = None
    color: str | None = None
    condition: Condition | None = None
    condition_raw: str | None = None
    image_urls: Annotated[list[Url], Field(min_length=1)]
    flags: Flags = Flags()
    cost: Cost
    materials: Materials = Materials()
    country_of_manufacture: str | None = None
    seller: Seller = Seller()
    evidence: list[Evidence] = []

    @model_validator(mode="after")
    def _id_matches_parts(self):
        if self.id != f"{self.marketplace}:{self.external_id}":
            raise ValueError("id must be '<marketplace>:<external_id>'")
        return self


class Normalized(Listing):
    """A Listing before extraction. `specifics` = the actor's structured fields (e.g. eBay Material)."""
    specifics: dict[str, str] = {}
