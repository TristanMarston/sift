"""Quality and eco markers: a level, a 0-1 score used only for sorting, and the facts that earned it.
Every point comes from a fact on the receipt; no fact, no point.

Quality points: brand repair program or guarantee +2, known durable product line +2, fiber that suits the
category +1 (+0.5 when from structured data or a tag), pilling-prone knit -1.
Eco points: vintage/deadstock/upcycled +1 each, recycled +1, organic +1, certifications +1 each (max 2),
synthetic share over 50% -1. "Secondhand" and animal materials are shown but score nothing."""
import re

SYNTHETIC_LIMIT = 50
ANIMAL = {"wool", "cashmere", "alpaca", "mohair", "silk", "leather", "down"}
CERT_LABEL = {"gots": "GOTS", "oeko_tex": "OEKO-TEX", "bluesign": "bluesign", "fair_trade": "Fair Trade",
              "rws": "Responsible Wool Standard", "rds": "Responsible Down Standard", "b_corp": "B Corp"}
# Fibers that suit each category, and the share needed (0 = any amount, used when pct is unknown).
DURABLE = {
    "sweaters_knitwear": ({"wool", "cashmere", "alpaca", "mohair"}, 80),
    "jeans_pants": ({"cotton"}, 95),
    "jackets_outerwear": ({"cotton", "wool", "leather"}, 80),
    "tshirts": ({"cotton", "linen", "hemp"}, 95),
    "hoodies_sweatshirts": ({"cotton"}, 80),
    "shirts": ({"cotton", "linen", "hemp", "wool"}, 95),
    "sneakers": ({"leather"}, 0),
}
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
        if share >= need and share > 0:
            points += 1.5 if f["source"] in {"specifics", "tag_image"} else 1
            scored.append(f)
        elif row["category"] == "sweaters_knitwear" and (acrylic >= 50 or (row["materials"]["synthetic_share"] or 0) > SYNTHETIC_LIMIT):
            points -= 1
            scored.append(f)
    level = _level(points, [(3, "high"), (1, "medium"), (float("-inf"), "low")])
    score = None if level == "unknown" else min(1.0, max(0.0, (points + 1) / 6))
    return {"level": level, "score": score, "facts": facts}, scored


def eco(row: dict, brands: dict) -> dict:
    as_of = row["scraped_at"][:10]
    facts = [_fact("secondhand", "Secondhand", "Already in use: no new garment is made", status="verified", as_of=as_of)]
    points = 0
    for flag, kind, label, value in FLAGS:
        if row["flags"][flag]:
            e = _evidence(row, f"flags.{flag}") or {}
            facts.append(_fact(kind, label, value, as_of=e.get("as_of", as_of), snippet=e.get("snippet")))
            points += 1
    m = row["materials"]
    for attr, label in [("recycled", "Recycled"), ("organic", "Organic")]:
        hit = [f["fiber"] for f in m["fibers"] if f[attr]]
        if hit:
            facts.append(_fact(attr, label, f"{label} {', '.join(hit)}", as_of=as_of))
            points += 1
    b = brands.get(brand_key(row.get("brand"))) or {}
    certs = [(c, None, as_of) for c in m["certifications"]] + \
            [(c["name"], c["url"], b.get("as_of", "")) for c in b.get("certifications", [])]
    for c, url, when in certs:
        facts.append(_fact("certification", "Certification", CERT_LABEL.get(c, c),
                           source="brand_table" if url else "listing_text", source_url=url, as_of=when))
    points += min(2, len(certs))
    if (m["synthetic_share"] or 0) > SYNTHETIC_LIMIT:
        facts.append(_fact("synthetic_share", "Synthetic fibers", f"{m['synthetic_share']:g}% synthetic", as_of=as_of))
        points -= 1
    animal = sorted({f["fiber"] for f in m["fibers"]} & ANIMAL)
    if animal:
        facts.append(_fact("animal_materials", "Animal materials", ", ".join(animal), as_of=as_of))
    level = _level(points, [(2, "high"), (1, "medium"), (float("-inf"), "low")])
    score = None if level == "unknown" else min(1.0, max(0.0, (points + 1) / 4))
    return {"level": level, "score": score, "facts": facts}


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
