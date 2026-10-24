"""Grailed (piotrv1001/grailed-listings-scraper, details mode) record -> Normalized.
Shipping is the seller's US rate. The original price is the highest earlier price in `priceDrops`.
Sellers tag vintage items with a "Vintage" designer ("The North Face × Vintage"): it is a flag, not part of the brand."""
from listing import Normalized
from normalize.common import (clean_images, make_cost, map_condition, normalize_brand, normalize_region, require,
                              resolve_category, seller_type)


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    seller, profile = raw.get("seller") or {}, raw.get("sellerProfile") or {}
    names = [d.get("name") or "" for d in raw.get("designers") or []] or [raw.get("designer") or ""]
    specifics = {"Styles": ", ".join(raw["styles"])} if raw.get("styles") else {}
    if any(n.strip().lower() == "vintage" for n in names):
        specifics["Vintage"] = "Yes"
    us = (raw.get("shipping") or {}).get("us") or {}
    drops = [d for d in raw.get("priceDrops") or [] if isinstance(d, (int, float))]
    path = raw.get("categoryPath") or ""
    count = profile.get("listings_for_sale_count")
    rating = seller.get("ratingAverage")
    external_id = str(require(raw.get("id"), "no_id"))
    return Normalized(
        id=f"grailed:{external_id}", marketplace="grailed", external_id=external_id,
        url=require(raw.get("url"), "no_url"), title=require(raw.get("title"), "no_title"),
        description=raw.get("description") or None, status="sold" if raw.get("sold") else "active",
        scraped_at=scraped_at, brand=" × ".join(b for b in map(normalize_brand, names) if b) or None,
        category=resolve_category(f"{raw.get('category') or ''} {path}", category),
        subcategory=path.split(".")[-1].replace("_", " ") if "." in path else None,
        size=raw.get("size") or None, color=raw.get("color") or None,
        condition=map_condition(raw.get("condition")), condition_raw=raw.get("condition"),
        image_urls=require(clean_images(raw.get("photos") or [raw.get("coverPhoto")]), "no_image"),
        cost=make_cost(raw.get("price"), shipping=us.get("amount") if us.get("enabled") else None,
                       original=max(drops, default=None)),
        seller=dict(type=seller_type(count), rating=round(rating, 2) if rating is not None else None,
                    region=normalize_region(profile.get("country_code") or raw.get("location")), listing_count=count),
        specifics=specifics)
