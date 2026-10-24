"""Poshmark (123webdata/poshmark-scraper, detail mode) record -> Normalized. Poshmark is US-only and the actor
returns no condition or location: condition comes from the seller's own words ("NWT", "good used condition") when they
state one, else stays unknown, and the region is "US". Poshmark's "Original Price"
(`regular_price`) is what the seller says the item cost new, so it is the retail price, not a markdown."""
from listing import Normalized
from normalize.common import (Drop, clean_images, condition_from_text, is_kids, make_cost, normalize_brand, require,
                               resolve_category)


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    crumbs = raw.get("breadcrumbs") or []
    if is_kids(" ".join(crumbs)):
        raise Drop("kids")
    external_id = str(require(raw.get("product_id"), "no_id"))
    live = raw.get("listing_status", "published") == "published" and raw.get("in_stock") is not False
    title = require(raw.get("name"), "no_title")
    condition, condition_raw = condition_from_text(title, raw.get("description"))
    return Normalized(
        id=f"poshmark:{external_id}", marketplace="poshmark", external_id=external_id,
        url=require(raw.get("url"), "no_url"), title=title, condition=condition, condition_raw=condition_raw,
        description=raw.get("description") or None, status="active" if live else "sold", scraped_at=scraped_at,
        brand=normalize_brand(raw.get("brand")),
        category=resolve_category(" > ".join([*crumbs, raw.get("category") or ""]), category),
        subcategory=raw.get("category"), size=raw.get("size") or None, color=raw.get("color") or None,
        image_urls=require(clean_images(raw.get("images")), "no_image"),
        cost=make_cost(raw.get("price"), raw.get("currency"), retail=raw.get("regular_price")),
        seller=dict(region="US"))
