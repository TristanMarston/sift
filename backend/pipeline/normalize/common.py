"""Helpers shared by the per-marketplace mappers."""
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class Drop(Exception):
    """A mapper raises this with the reason a raw record is not usable. 02_normalize.py counts the reasons."""


def slug(text: str) -> str:
    """Lowercase letters and digits only: "Levi's" and "LEVIS" compare equal."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")  # zero-width characters, word joiner, BOM, soft hyphen


def clean_text(text: str | None, one_line: bool = False) -> str | None:
    """Drop invisible characters (a zero-width space inside "100%cotton" defeats the composition regex), turn
    non-breaking spaces into plain ones and trim. A one-line field also collapses runs of whitespace. None if empty."""
    if text is None:
        return None
    text = _INVISIBLE.sub("", text).translate({0xA0: " ", 0x2007: " ", 0x202F: " "})
    text = re.sub(r"\s+", " ", text) if one_line else re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(line.strip(" \t") for line in text.split("\n")).strip() or None


def to_cents(value) -> int | None:
    """48, "48.00", "$1,200.50" -> cents. None for anything that is not a non-negative amount."""
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        return None
    return int((d * 100).quantize(Decimal(1), ROUND_HALF_UP)) if d.is_finite() and d >= 0 else None


# First match wins, so order matters.
_CONDITION_RULES = [
    ("like_new", r"new without tags|nwot|like new|excellent|gently used|open box|\bmint\b"),
    ("new_with_tags", r"new with tags|nwt|\bnew\b|never worn|unworn"),
    ("fair", r"fair|acceptable|poor|worn|damaged|flaws?|heavily"),
    ("good", r"good|pre-?owned|used|\bfine\b"),
]


def map_condition(raw: str | None) -> str | None:
    """Marketplace condition text -> new_with_tags / like_new / good / fair; None when it cannot be mapped.
    Ordinal: the lowest label on a marketplace (poor, very worn) maps to the lowest bucket."""
    text = (raw or "").lower()
    return next((cond for cond, pattern in _CONDITION_RULES if re.search(pattern, text)), None)


def seller_type(listing_count: int | None) -> str | None:
    """Thresholds are guesses until the test run shows real listing counts (SPEC.md §16)."""
    if listing_count is None:
        return None
    return "individual" if listing_count <= 20 else "small_shop" if listing_count <= 200 else "large_reseller"


# First match wins, so order matters. Footwear of any kind is "sneakers": it is the only shoe category.
_CATEGORY_RULES = [
    ("dresses_skirts", r"\bdress(?:es)?\b(?!\s+(?:shirt|pant|shoe|boot|sock|slack))|\bskirts?\b|\bgowns?\b"),
    ("sneakers", r"sneaker|trainer|athletic shoe|\bshoes?\b|\bboots?\b|footwear|\bclogs?\b|\bloafers?\b"),
    ("hoodies_sweatshirts", r"hoodie|hooded|sweatshirt"),
    ("sweaters_knitwear", r"sweater|cardigan|knitwear|jumper|\bknits?\b|turtleneck"),
    ("jackets_outerwear", r"jacket|coat|parka|puffer|\bvests?\b|windbreaker|anorak|blazer|outerwear|\bfleece\b|poncho"),
    ("tshirts", r"\bt[- ]?shirts?|\btees?\b"),
    ("shirts", r"shirt|flannel|button[- ]?(?:up|down)|blouse|\bpolos?\b|overshirt"),
    ("jeans_pants", r"jeans?|\bpants?\b|trouser|chino|jogger|sweatpants?|slacks|leggings?|cargo|denim"),
]


def category_from_label(label: str | None) -> str | None:
    """A marketplace category label or path ("Men > Coats & Jackets") -> one of the 8 categories, else None.
    The leaf of a path is the most specific part, so it is tried first ("Sweats & hoodies > Track jacket" is a jacket)."""
    text = re.sub(r"clothing, shoes (?:&|and) accessories", "", (label or "").lower())  # eBay's root category
    for part in reversed(text.split(">")):
        part = re.sub(r"[._]", " ", part)
        for category, pattern in _CATEGORY_RULES:
            if re.search(pattern, part):
                return category
    return None


def resolve_category(label: str | None, fallback: str) -> str:
    """The marketplace's own label wins. No label at all: the query's category (`fallback`). A label that maps to
    none of our 8 categories (hats, bags, shorts) drops the record, so a beanie never inherits "jackets"."""
    if not (label or "").strip():
        return fallback
    category = category_from_label(label)
    if category is None:
        raise Drop("unmapped_category")
    return category


def is_kids(label: str | None) -> bool:
    """True for a kids' category label ("Kids > Girls coats"). Children's clothes are outgrown, not worn out,
    so they would skew wear estimates, and an adult's photo should not match them."""
    return bool(re.search(r"\b(?:kids?|boys?|girls?|baby|toddlers?|infants?|youth)\b", (label or "").lower()))


def normalize_region(text: str | None) -> str | None:
    """Country only ("Berlin, Germany" -> "Germany", any US place -> "US"), never a city or street.
    Recorded on every row so a US-only view is a one-line filter; the pipeline itself does not filter on it."""
    t = re.sub(r"^located in\s+", "", " ".join((text or "").split()), flags=re.I)
    if not t:
        return None
    if t.lower() in {"us", "usa", "u.s.", "u.s.a."} or "united states" in t.lower():
        return "US"
    return t.split(",")[-1].strip()


_BRANDS = ["The North Face", "Carhartt", "Carhartt WIP", "Patagonia", "Nike", "Jordan", "New Balance", "Levi's",
           "Uniqlo", "Arc'teryx", "Columbia", "Champion", "Adidas", "Dr. Martens", "Converse", "Vans", "Dickies",
           "Wrangler", "Reebok", "Puma", "Asics", "Hoka", "Salomon", "Allbirds", "Veja"]
_BRAND_BY_SLUG = {slug(b): b for b in _BRANDS} | {
    "northface": "The North Face", "tnf": "The North Face", "levistrauss": "Levi's", "levistraussco": "Levi's",
    "docmartens": "Dr. Martens", "airjordan": "Jordan"}
_NO_BRAND = {"", "unbranded", "nobrand", "none", "na", "other", "vintage", "handmade", "generic", "unknown",
             "custom", "unmarked"}


def normalize_brand(raw: str | None) -> str | None:
    """Canonical spelling for known brands (the join key for brand facts); junk values become None.
    Unknown brands are trimmed, and title-cased only when typed all lowercase."""
    key = slug(raw or "")
    if key in _NO_BRAND:
        return None
    if key in _BRAND_BY_SLUG:
        return _BRAND_BY_SLUG[key]
    name = " ".join(raw.split())
    return name.title() if name.islower() else name


def make_cost(price, currency=None, shipping=None, free_shipping=None, original=None, retail=None) -> dict:
    """The `cost` block. Raises Drop for a missing price or a non-USD currency (no FX conversion).
    An unstated currency is taken as USD. `original` only counts when it is above the price (a markdown)."""
    if currency and str(currency).upper() != "USD":
        raise Drop("non_usd")
    cents = to_cents(price)
    if cents is None:
        raise Drop("no_price")
    ship, orig = to_cents(shipping), to_cents(original)
    if free_shipping is None and ship is not None:
        free_shipping = ship == 0
    return dict(price_cents=cents, currency="USD", shipping_cents=ship, free_shipping=free_shipping,
                total_cents=cents + (ship or 0), original_price_cents=orig if orig and orig > cents else None,
                retail_price_cents=to_cents(retail))


def clean_images(urls) -> list[str]:
    """http(s) image URLs, in order, once each."""
    out = []
    for u in urls or []:
        if isinstance(u, str) and re.match(r"https?://\S+$", u) and u not in out:
            out.append(u)
    return out


def require(value, reason: str):
    """`value` if it is truthy, else drop the record with `reason`."""
    if not value:
        raise Drop(reason)
    return value
