"""Expected wears and cost per wear. All money is integer cents; every factor is shown on the receipt.

expected wears = category baseline x quality multiplier x condition factor
cost per wear  = total price / expected wears"""
from math import ceil
from statistics import median

QUALITY_MULT = {"high": 1.5, "medium": 1.15, "low": 0.85, "unknown": 1.0}
CONDITION = {"new_with_tags": 1.0, "like_new": 0.95, "good": 0.8, "fair": 0.6, None: 0.85}  # share of life left
CONDITION_LABEL = {"new_with_tags": "New with tags", "like_new": "Like new", "good": "Good", "fair": "Fair"}
CATEGORY_LABEL = {
    "jackets_outerwear": "jackets & outerwear", "hoodies_sweatshirts": "hoodies & sweatshirts", "tshirts": "t-shirts",
    "sneakers": "sneakers", "jeans_pants": "jeans & pants", "sweaters_knitwear": "sweaters & knitwear",
    "shirts": "shirts", "dresses_skirts": "dresses & skirts",
}


def _round(x: float) -> int:
    return int(x + 0.5)  # half up, never banker's rounding


def expected_wears(baseline: dict, level: str, condition: str | None) -> dict:
    f = QUALITY_MULT[level] * CONDITION[condition]
    w = lambda n: max(1, _round(n * f))  # noqa: E731
    mid = baseline.get("mid", (baseline["low"] + baseline["high"]) / 2)  # a published typical figure beats the middle
    return {"low": w(baseline["low"]), "high": w(baseline["high"]), "mid": w(mid)}


def steps(baseline: dict, level: str, condition: str | None, category: str) -> list[dict]:
    """How expected_wears.mid was reached, for the item panel: typical wears, then the quality multiplier, then the
    condition multiplier (web/BACKEND-REQUESTS.md). Short strings, no em dashes."""
    mid = baseline.get("mid", (baseline["low"] + baseline["high"]) / 2)
    quality = "Quality unknown" if level == "unknown" else f"{level.capitalize()} quality"
    cond = f"{CONDITION_LABEL[condition]} condition" if condition else "Condition not stated"
    return [{"label": f"Typical for {CATEGORY_LABEL[category]}", "value": f"{_round(mid)} wears"},
            {"label": quality, "value": f"× {QUALITY_MULT[level]:g}"},
            {"label": cond, "value": f"× {CONDITION[condition]:g}"}]


def cpw(total_cents: int, wears: int) -> int:
    return _round(total_cents / max(1, wears))


def cpw_table(total_cents: int, mid: int) -> dict:
    return {"at_30": cpw(total_cents, 30), "at_60": cpw(total_cents, 60), "at_100": cpw(total_cents, 100),
            "at_mid": cpw(total_cents, mid)}


def typical(totals: list[int], mids: list[int]) -> dict | None:
    """The median match: the "vs. typical match" line and the break-even reference."""
    if not totals:
        return None
    price, wears = _round(median(totals)), max(1, _round(median(mids)))
    return {"price_cents": price, "expected_wears_mid": wears, "cpw_cents": cpw(price, wears)}


def break_even(total_cents: int, typ: dict | None) -> int | None:
    """Wears needed for a pricier item to beat the typical match per wear. None when it is not pricier."""
    if typ is None or total_cents <= typ["price_cents"]:
        return None
    return ceil(total_cents / max(1, typ["cpw_cents"]))


def wear_facts(category: str, baselines: dict, condition: str | None, condition_raw: str | None) -> list[dict]:
    b = baselines["categories"][category]
    src, url = b.get("source", baselines["source"]), b.get("source_url", baselines.get("source_url"))
    fact = lambda kind, label, value, snippet=None, url=None: dict(  # noqa: E731
        kind=kind, label=label, value=value, status="inferred", source="baseline", source_url=url,
        snippet=snippet, as_of=str(baselines["as_of"]))
    life = f"about {round(CONDITION[condition] * 100)}% of its life left"
    tag = " (assumption)" if "assumption" in src.lower() else ""  # only uncited baselines say so
    return [
        fact("baseline", "Typical lifespan", f"{b['low']}–{b['high']} wears for {CATEGORY_LABEL[category]}"
             + (f", typically {b['mid']}" if "mid" in b else "") + tag, src, url),
        fact("condition", "Condition", f"{CONDITION_LABEL[condition]}: {life} (assumption)" if condition
             else f"Condition not stated: assume {life}", condition_raw),
    ]
