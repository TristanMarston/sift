"""Depop (jongoose/depop-scraper) record -> Normalized."""
from listing import Normalized
from normalize.common import (clean_images, make_cost, map_condition, normalize_brand, normalize_region, require,
                              resolve_category)


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    price, original = raw.get("price") or {}, raw.get("originalPrice") or {}
    label = " ".join(str(raw.get(k) or "") for k in ("category", "productType", "group"))
    sizes = raw.get("sizes") or []
    external_id = str(require(raw.get("id"), "no_id"))
    return Normalized(
        id=f"depop:{external_id}", marketplace="depop", external_id=external_id,
        url=require(raw.get("url"), "no_url"), title=require(raw.get("title"), "no_title"),
        description=raw.get("description") or None, status="sold" if raw.get("isSold") else "active",
        scraped_at=scraped_at, brand=normalize_brand(raw.get("brand")), category=resolve_category(label, category),
        subcategory=raw.get("productType"), size=(sizes[0] if sizes else raw.get("size")) or None,
        color=", ".join(raw.get("colours") or []) or None,
        condition=map_condition(raw.get("condition")), condition_raw=raw.get("condition"),
        image_urls=require(clean_images(raw.get("pictureUrls")), "no_image"),
        cost=make_cost(price.get("amount"), price.get("currency"), original=original.get("amount")),
        seller=dict(region=normalize_region(raw.get("country"))))
