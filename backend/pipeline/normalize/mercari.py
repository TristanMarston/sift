"""Mercari US (automation_craft/mercari-us-scraper, details on) record -> Normalized.
Buyer total = price + shipping (only when the buyer pays) + Mercari's buyer-protection fee; the fee is not part of
`cost` (it is a marketplace fee, and no other marketplace's fees are modelled). Mercari US sellers ship from US states."""
from listing import Normalized
from normalize.common import (Drop, clean_images, is_kids, make_cost, map_condition, normalize_brand, require,
                              resolve_category, seller_type)


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    if raw.get("type", "listing") != "listing":
        raise Drop("not_listing")
    path = raw.get("categoryPath") or ""
    if is_kids(path):
        raise Drop("kids")
    external_id = str(require(raw.get("listingId"), "no_id"))
    buyer_pays = raw.get("shippingPayer") == "buyer"
    shipping = raw.get("shippingFee") if buyer_pays else (0 if raw.get("shippingPayer") == "seller" else None)
    count = raw.get("sellerListingCount")
    live = raw.get("status", "on_sale") == "on_sale" and not raw.get("sold")
    return Normalized(
        id=f"mercari:{external_id}", marketplace="mercari", external_id=external_id,
        url=require(raw.get("url"), "no_url"), title=require(raw.get("title"), "no_title"),
        description=raw.get("description") or None, status="active" if live else "sold", scraped_at=scraped_at,
        brand=normalize_brand(raw.get("brand")),
        category=resolve_category(" > ".join(filter(None, [path, raw.get("category")])), category),
        subcategory=raw.get("category"), size=raw.get("size") or None, color=raw.get("color") or None,
        condition=map_condition(raw.get("condition")), condition_raw=raw.get("condition"),
        image_urls=require(clean_images(raw.get("photoUrls") or [raw.get("imageUrl")]), "no_image"),
        cost=make_cost(raw.get("price"), raw.get("currency"), shipping=shipping, original=raw.get("originalPrice")),
        # a rating of 0 from 0 reviews means "no rating yet", not a bad one
        seller=dict(type=seller_type(count), rating=raw.get("sellerRating") if raw.get("sellerRatingCount") else None,
                    region="US", listing_count=count))
