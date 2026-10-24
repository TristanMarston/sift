"""eBay (memo23/ebay-search-scraper-ppe, detail mode) record -> Normalized.
Material and origin live in `itemSpecifics`, which is passed on as `specifics` for 03_extract.py.
The item specific `Type` is the leaf of the category path: eBay files tees under a generic "Women's Clothing > Tops"."""
import html

from listing import Normalized
from normalize.common import (Drop, clean_images, is_kids, make_cost, map_condition, normalize_brand,
                              normalize_region, require, resolve_category)

BIG_SELLER_FEEDBACK = 5000  # a guess until we see more business sellers


def _seller_type(raw: dict) -> str | None:
    kind = raw.get("sellerAccountType")
    if kind == "private":
        return "individual"
    if kind == "business":
        return "large_reseller" if (raw.get("sellerFeedbackScore") or 0) >= BIG_SELLER_FEEDBACK else "small_shop"
    return None


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    path = raw.get("categoryPath") or ""
    if is_kids(path):
        raise Drop("kids")
    spec = {k: str(v) for k, v in (raw.get("itemSpecifics") or {}).items() if isinstance(v, (str, int, float))}
    condition = (spec.get("Condition") or raw.get("condition") or "").split(". ")[0] or None  # drop the seller prose
    positive = raw.get("sellerFeedbackPercentage")
    external_id = str(require(raw.get("itemId"), "no_id"))
    return Normalized(
        id=f"ebay:{external_id}", marketplace="ebay", external_id=external_id,
        url=f"https://www.ebay.com/itm/{external_id}", title=html.unescape(require(raw.get("title"), "no_title")),
        description=html.unescape(raw["description"]) if raw.get("description") else None,
        status="active" if raw.get("listingStatus") == "ACTIVE" else "sold", scraped_at=scraped_at,
        brand=normalize_brand(raw.get("brand") or spec.get("Brand")),
        category=resolve_category(" > ".join(filter(None, [path, spec.get("Type")])), category),
        subcategory=spec.get("Type"), size=spec.get("Size"), color=spec.get("Color"),
        condition=map_condition(condition), condition_raw=condition,
        image_urls=require(clean_images(raw.get("images")), "no_image"),
        cost=make_cost(raw.get("priceValue"), raw.get("currency"), shipping=raw.get("shippingCost"),
                       free_shipping=True if raw.get("shippingType") == "free" else None),
        # 0% positive means no feedback in the last 12 months (eBay's window), not a bad seller
        seller=dict(type=_seller_type(raw), rating=round(positive / 20, 2) if positive else None,
                    region=normalize_region(raw.get("itemLocation"))),
        specifics=spec)
