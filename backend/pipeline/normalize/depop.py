"""Depop (jongoose/depop-scraper) record -> Normalized."""
import re

from listing import Normalized
from normalize.common import (Drop, clean_images, depop_fee, make_cost, map_condition, normalize_brand,
                              normalize_region, require, resolve_category, to_cents)


def _title(raw: dict) -> str | None:
    """Depop's own title is the first few words of the description, cut mid-phrase ("The North Face White Fuzzy").
    The seller's real title is the first line of the description without its hashtags (at most 120 characters)."""
    for line in (raw.get("description") or "").split("\n"):
        line = " ".join(re.sub(r"#\S*", " ", line).split())
        if re.search(r"[^\W_]", line):   # a letter or digit: a line of only emoji ("✨✨✨") is not a title
            return line if len(line) <= 120 else line[:121].rsplit(" ", 1)[0][:120]
    return raw.get("title")


def map_item(raw: dict, category: str, scraped_at) -> Normalized:
    price, original = raw.get("price") or {}, raw.get("originalPrice") or {}
    label = " ".join(str(raw.get(k) or "") for k in ("category", "productType", "group"))
    if raw.get("group") == "tops":   # Depop is British: a vest under tops is a tank top ("vests-tanks-camis")
        label = re.sub(r"\bvests?\b", "tank", label)
    sizes = raw.get("sizes") or []
    size = (sizes[0] if sizes else raw.get("size")) or None
    # Depop has no kids label, but its kids department uses only broad categories ("Kids > Shoes", where adults get
    # "Men > Footwear > Sneakers"), and kids sizes say "6 years" or "12-18 months"
    if raw.get("category") in ("Clothing", "Shoes") or re.search(r"\b(?:months?|years?)\b", size or "", re.I):
        raise Drop("kids")
    external_id = str(require(raw.get("id"), "no_id"))
    return Normalized(
        id=f"depop:{external_id}", marketplace="depop", external_id=external_id,
        url=require(raw.get("url"), "no_url"), title=require(_title(raw), "no_title"),
        description=raw.get("description") or None, status="sold" if raw.get("isSold") else "active",
        scraped_at=scraped_at, brand=normalize_brand(raw.get("brand")), category=resolve_category(label, category),
        subcategory=raw.get("productType"), size=size,
        color=", ".join(raw.get("colours") or []) or None,
        condition=map_condition(raw.get("condition")), condition_raw=raw.get("condition"),
        image_urls=require(clean_images(raw.get("pictureUrls")), "no_image"),
        cost=make_cost(price.get("amount"), price.get("currency"), original=original.get("amount"),
                       fee_cents=depop_fee(to_cents(price.get("amount")))),
        seller=dict(region=normalize_region(raw.get("country"))))
