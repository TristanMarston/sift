"""Quality and eco markers: a level, a 0-1 score used only for sorting, and the facts that earned it.
Every point comes from a fact on the receipt; no fact, no point.

Quality points: brand repair program or guarantee +2, known durable product line +2, fiber that suits the
category +1 (+0.5 when from structured data or a tag), a durable construction named in the listing +1, vintage and
still in good condition +1 (it has already lasted), pilling-prone knit -1, stretch jeans -1, faux or PU leather -1.
Eco points: vintage/deadstock/upcycled +1 each, recycled +1, organic +1, certifications +1 each (max 2),
synthetic share over 50% -1. "Secondhand" and animal materials are shown but score nothing."""
import re

SYNTHETIC_LIMIT = 50
STRETCH_LIMIT = 2  # % elastane above which jeans bag out and wear faster
WEAK = {"synthetic_leather", "polyurethane"}  # peel and crack
CONSTRUCTION = re.compile(
    r"\b(selvedge|selvage|raw denim|duck canvas|cotton duck|double[- ]knee|triple[- ]stitch(?:ed)?|bar[- ]tack(?:ed)?|"
    r"chain[- ]?stitch(?:ed)?|full[- ]grain(?: leather)?|goodyear[- ]welt(?:ed)?|gore-?tex|ripstop|"
    r"waxed (?:cotton|canvas)|boiled wool|heavyweight)\b", re.I)
ANIMAL = {"wool", "cashmere", "alpaca", "mohair", "silk", "leather", "down"}
NATURAL = ANIMAL | {"cotton", "linen", "hemp"}   # viscose and lyocell are regenerated, not natural
NATURAL_SHARE = 95
CERT_LABEL = {"gots": "GOTS", "oeko_tex": "OEKO-TEX", "bluesign": "bluesign", "fair_trade": "Fair Trade",
              "rws": "Responsible Wool Standard", "rds": "Responsible Down Standard", "b_corp": "B Corp"}
# Fibers that suit each category, and the share needed (0 = any amount, used when pct is unknown).
DURABLE = {
    "sweaters_knitwear": ({"wool", "cashmere", "alpaca", "mohair"}, 80),
    "jeans_pants": ({"cotton"}, 95),
    "jackets_outerwear": ({"cotton", "wool", "leather", "nylon"}, 80),   # nylon: abrasion-resistant technical shells
    "tshirts": ({"cotton", "linen", "hemp"}, 95),
    "hoodies_sweatshirts": ({"cotton"}, 80),
    "shirts": ({"cotton", "linen", "hemp", "wool"}, 95),
    "sneakers": ({"leather"}, 0),
    "dresses_skirts": ({"wool", "linen", "silk"}, 80),   # cotton left out: the default fabric of cheap dresses
}
# Fabrics sellers name in titles without a fiber ("denim jeans", "suede sneakers"): 7,367 listings at 76k. The fabric is a
# claimed fact that implies one fiber (denim is cotton twill, suede is leather, corduroy and chambray are cotton weaves,
# canvas is cotton) and earns the fiber point when that fiber suits the category. The composition stays unstated.
FABRIC = {"denim": "cotton", "corduroy": "cotton", "chambray": "cotton", "canvas": "cotton", "suede": "leather",
          "nubuck": "leather"}
_FABRIC_RE = re.compile(r"\b(denim|corduroy|chambray|canvas|suede|nubuck)\b", re.I)
_SHOE_RE = re.compile(r"\b(denim|canvas|suede|nubuck|leather)\b", re.I)   # a sneaker title's "leather" is its upper
# A sneaker description that says what the upper is ("suede upper", "Upper Material: Leather"): 742 of the 6,589 sneakers
# with no other material evidence. Only an "upper" phrase counts; descriptions also mention other shoes and jackets.
_UPPER_RE = re.compile(r"\b(denim|canvas|suede|nubuck|leather)\b[^.]{0,20}?\buppers?\b|\buppers?\b[^.]{0,25}?\b(denim|canvas|suede|nubuck|leather)\b", re.I)
FLAGS = [("is_vintage", "vintage", "Vintage", "Already had a first life"),
         ("is_deadstock", "deadstock", "Deadstock", "Old unsold stock, never worn"),
         ("is_upcycled", "upcycled", "Upcycled", "Remade from existing garments")]


def brand_key(name: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def index_brands(rows: list[dict]) -> dict:
    return {brand_key(n): b for b in rows for n in [b["name"], *b.get("aliases", [])]}


def _fact(kind, label, value, status="claimed", source="listing_text", as_of="", source_url=None, snippet=None):
    return dict(kind=kind, label=label, value=value, status=status, source=source, source_url=source_url,
                snippet=snippet or None, as_of=str(as_of))


def _evidence(row, field):
    return next((e for e in row.get("evidence", []) if e["field"] == field), None)


def _composition(fibers) -> str:
    def one(f):
        name = " ".join(w for w in ["organic" if f["organic"] else "", "recycled" if f["recycled"] else "", f["fiber"]] if w)
        return f"{f['pct']:g}% {name}" if f["pct"] is not None else name
    return ", ".join(one(f) for f in fibers)


def _level(points, bands):
    if points == 0:
        return "unknown"
    return next(level for floor, level in bands if points >= floor)


def title_fabric(row: dict) -> tuple[str, str, str] | None:
    """(word as written, implied fiber, display value) for a fabric the title names, e.g. ("denim", "cotton",
    "Denim (cotton)"); a sneaker title's plain "leather" is its upper. None when the title names none."""
    shoe = row["category"] == "sneakers"
    m = (_SHOE_RE if shoe else _FABRIC_RE).search(row["title"] or "")
    snippet = m and m[0]
    if not m and shoe and (u := _UPPER_RE.search(row.get("description") or "")):
        m, snippet = _SHOE_RE.search(u[0]), u[0].strip()
    if not m:
        return None
    fabric, fiber = m[0].lower(), FABRIC.get(m[0].lower(), m[0].lower())
    return snippet, fiber, fabric.capitalize() if fabric == fiber else f"{fabric.capitalize()} ({fiber})"


def quality(row: dict, brands: dict) -> tuple[dict, list[dict]]:
    """(marker, scored) where `scored` are the facts that moved the points (for confidence)."""
    facts, scored, points = [], [], 0.0
    b = brands.get(brand_key(row.get("brand")))
    if b:
        promises = [(k, lbl) for k, lbl in [("repair_program", "Repair program"), ("guarantee", "Guarantee")] if b.get(k)]
        for i, (k, lbl) in enumerate(promises):
            f = _fact(k, lbl, b[k]["value"], source="brand_table", as_of=b.get("as_of", ""), source_url=b[k]["url"])
            facts.append(f)
            if i == 0:
                scored.append(f)
                points += 2
    line = next((e for e in row.get("evidence", []) if e["source"] == "product_line"), None)
    if line:
        f = _fact("product_line", "Known product line", line["snippet"] or "Known durable line",
                  status="inferred", source="product_line", as_of=line["as_of"])
        facts.append(f)
        scored.append(f)
        points += 2
    fibers = row["materials"]["fibers"]
    if fibers:
        e = _evidence(row, "materials.fibers") or {}
        f = _fact("materials", "Materials", _composition(fibers), status=e.get("status", "claimed"),
                  source=e.get("source", "listing_text"), as_of=e.get("as_of", ""), snippet=e.get("snippet"))
        facts.append(f)
        good, need = DURABLE.get(row["category"], (set(), 101))
        known = [x for x in fibers if x["pct"] is not None]
        share = sum(x["pct"] for x in known if x["fiber"] in good) if known else (100 if all(x["fiber"] in good for x in fibers) else 0)
        acrylic = sum(x["pct"] or 0 for x in fibers if x["fiber"] == "acrylic")
        stretch = sum(x["pct"] or 0 for x in fibers if x["fiber"] == "elastane")
        main = max(fibers, key=lambda x: x["pct"] or 0)["fiber"]
        if (row["category"] == "jeans_pants" and stretch >= STRETCH_LIMIT) or main in WEAK:
            points -= 1
            scored.append(f)
        elif share >= need and share > 0:
            points += 1.5 if f["source"] in {"specifics", "tag_image"} else 1
            scored.append(f)
        elif row["category"] == "sweaters_knitwear" and (acrylic >= 50 or (row["materials"]["synthetic_share"] or 0) > SYNTHETIC_LIMIT):
            points -= 1
            scored.append(f)
    as_of = row["scraped_at"][:10]
    if not fibers and (fab := title_fabric(row)):
        good, _ = DURABLE.get(row["category"], (set(), 101))
        if fab[1] in good:
            f = _fact("fabric", "Fabric", fab[2], as_of=as_of, snippet=fab[0])
            facts.append(f)
            scored.append(f)
            points += 1
    found = list(dict.fromkeys(m[0] for m in CONSTRUCTION.finditer(f"{row['title']}. {row.get('description') or ''}")))
    if found:
        f = _fact("construction", "Construction", ", ".join(dict.fromkeys(x.lower() for x in found)), as_of=as_of,
                  snippet=", ".join(found))
        facts.append(f)
        scored.append(f)
        points += 1
    if row["flags"]["is_vintage"] and row.get("condition") in {"good", "like_new"}:
        e = _evidence(row, "flags.is_vintage") or {}
        f = _fact("survival", "Already lasted", f"Vintage and still in {row['condition'].replace('_', ' ')} condition",
                  as_of=e.get("as_of", as_of), snippet=e.get("snippet"))
        facts.append(f)
        scored.append(f)
        points += 1
    level = _level(points, [(3, "high"), (1, "medium"), (float("-inf"), "low")])
    score = None if level == "unknown" else min(1.0, max(0.0, (points + 1) / 6))
    return {"level": level, "score": score, "facts": facts}, scored


# Eco score (0-1). Every item here is secondhand, so the new-garment impact is avoided for all of them; what separates
# them is what happens next. Weights are a team judgement (API.md states them).
ECO_WEIGHTS = {"fibers": 0.35, "durability": 0.30, "shipping": 0.15, "circularity": 0.20}
ECO_LABELS = {"fibers": "Fabric", "durability": "How long it lasts", "shipping": "Where it ships from",
              "circularity": "Second life"}   # the item panel's bars; copy rules: short, sentence case, no em dashes
ECO_PART = {"secondhand": None, "vintage": "circularity", "deadstock": "circularity", "upcycled": "circularity",
            "recycled": "circularity", "organic": "circularity", "certification": "circularity",
            "natural_fibers": "fibers", "materials": "fibers", "fabric_unknown": "fibers", "synthetic_share": "fibers",
            "animal_materials": "fibers", "durability": "durability", "shipping": "shipping"}
ECO_HIGH, ECO_LOW = 0.70, 0.40      # 100% cotton alone is medium; cotton + vintage, or cotton + built to last, is high
SHIP_US, SHIP_ABROAD, SHIP_UNKNOWN = 1.0, 0.4, 0.6


def _natural_share(fibers) -> float | None:
    """Share of natural fibers, 0-1; None when nothing is stated. Names without percentages count equally."""
    if not fibers:
        return None
    known = [f for f in fibers if f["pct"] is not None]
    if known:
        return min(1.0, sum(f["pct"] for f in known if f["fiber"] in NATURAL) / (sum(f["pct"] for f in known) or 1))
    return sum(f["fiber"] in NATURAL for f in fibers) / len(fibers)


def eco(row: dict, brands: dict, wears: int | None = None, typical: int | None = None) -> dict:
    """`wears` is the item's expected wears (mid) and `typical` the category's baseline, from the ranker: a garment
    that lasts longer replaces more new clothing."""
    as_of = row["scraped_at"][:10]
    facts = [_fact("secondhand", "Secondhand", "Already in use: no new garment is made", status="verified", as_of=as_of)]
    circularity = 0.0
    for flag, kind, label, value in FLAGS:
        if row["flags"][flag]:
            e = _evidence(row, f"flags.{flag}") or {}
            facts.append(_fact(kind, label, value, as_of=e.get("as_of", as_of), snippet=e.get("snippet")))
            circularity += 1
    m = row["materials"]
    for attr, label in [("recycled", "Recycled"), ("organic", "Organic")]:
        hit = [f["fiber"] for f in m["fibers"] if f[attr]]
        if hit:
            facts.append(_fact(attr, label, f"{label} {', '.join(hit)}", as_of=as_of))
            circularity += 1
    b = brands.get(brand_key(row.get("brand"))) or {}
    certs = [(c, None, as_of) for c in m["certifications"]]
    certs += [(c["name"], c["url"], b.get("as_of", "")) for c in b.get("certifications", [])
              if c["name"] not in m["certifications"]]  # stated by both: one fact, the listing's
    for c, url, when in certs:
        facts.append(_fact("certification", "Certification", CERT_LABEL.get(c, c),
                           source="brand_table" if url else "listing_text", source_url=url, as_of=when))
    circularity += 0.5 * min(2, len(certs))
    fibers = m["fibers"]
    share = _natural_share(fibers)
    if share is not None:  # the fact states the fibers, never "sustainable"
        e = _evidence(row, "materials.fibers") or {}
        kind, label = ("natural_fibers", "Natural fibers") if share * 100 >= NATURAL_SHARE else ("materials", "Materials")
        if share * 100 >= NATURAL_SHARE or (m["synthetic_share"] or 0) <= SYNTHETIC_LIMIT:
            facts.append(_fact(kind, label, _composition(fibers), status=e.get("status", "claimed"),
                               source=e.get("source", "listing_text"), as_of=e.get("as_of", as_of), snippet=e.get("snippet")))
    elif (fab := title_fabric(row)) and fab[1] in NATURAL:   # "denim jeans": the seller named the fabric
        facts.append(_fact("natural_fibers", "Natural fibers", fab[2], as_of=as_of, snippet=fab[0]))
        share = 1.0
    else:
        facts.append(_fact("fabric_unknown", "Fabric", "Not stated", status="unknown", as_of=as_of))
        share = 0.5
    if (m["synthetic_share"] or 0) > SYNTHETIC_LIMIT:
        facts.append(_fact("synthetic_share", "Synthetic fibers", f"{m['synthetic_share']:g}% synthetic", as_of=as_of))
    animal = sorted({f["fiber"] for f in m["fibers"]} & ANIMAL)
    if animal:
        facts.append(_fact("animal_materials", "Animal materials", ", ".join(animal), as_of=as_of))
    durability = 0.5
    if wears and typical:
        durability = min(1.0, max(0.0, wears / typical - 0.5))
        facts.append(_fact("durability", "Lasts", f"Expected {wears} wears, typical {typical}"
                           + (": fewer replacements" if wears > typical else ""), status="inferred", source="baseline",
                           as_of=as_of))
    region = (row.get("seller") or {}).get("region")
    if region is None:
        shipping = SHIP_UNKNOWN
    elif region in {"US", "USA"}:
        shipping = SHIP_US
        facts.append(_fact("shipping", "Shipping", "Ships from the US", status="verified", as_of=as_of))
    else:
        shipping = SHIP_ABROAD
        facts.append(_fact("shipping", "Shipping", f"Ships from {region}: long haul", status="verified", as_of=as_of))
    part_scores = {"fibers": share, "durability": durability, "shipping": shipping, "circularity": min(1.0, circularity / 2)}
    score = sum(ECO_WEIGHTS[k] * v for k, v in part_scores.items())
    level = "high" if score >= ECO_HIGH else "low" if score < ECO_LOW else "medium"
    for f in facts:
        f["part"] = ECO_PART[f["kind"]]
    parts = [{"key": k, "label": ECO_LABELS[k], "weight": ECO_WEIGHTS[k], "score": round(v, 3)} for k, v in part_scores.items()]
    return {"level": level, "score": round(score, 3), "facts": facts, "parts": parts}


def confidence(scored: list[dict]) -> str:
    """How much evidence moved the wear estimate."""
    if not scored:
        return "unknown"
    firm = [f for f in scored if f["status"] != "inferred"]
    if not firm:
        return "low"
    if len(firm) >= 2 and any(f["source"] == "brand_table" for f in firm):
        return "high"
    return "medium"
