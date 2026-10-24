"""Normalized row -> Listing: materials, certifications, flags, retail price, origin, plus evidence.
Order for materials (SCRAPING.md §4): structured specifics > listing text > product line.
Never invent: no evidence means null and an 'unknown' evidence record."""
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

import jsonl
from listing import Category, Evidence, Fiber, Listing, Materials, Normalized
from normalize.common import slug

_LAMBSWOOL = "lamb(?:['’]?s|s['’])?\\s?wool"   # lambswool, lambs wool, lamb's wool
_FIBER = ("cotton|polyester|poly|nylon|polyamide|wool|merino|" + _LAMBSWOOL + "|linen|hemp|ramie|silk|viscose|rayon|modal|"
          "lyocell|tencel|acetate|acrylic|modacrylic|elastane|spandex|lycra|polyurethane|cashmere|alpaca|mohair|camel hair|"
          "leather|down")
# Bare words skip "down" (button-down), "leather" (leather patch), "poly" (poly mailer), "camel" (a colour) and the traps below.
_BARE = ("cotton(?!\\s+on\\b)|polyester|nylon|wool|merino|" + _LAMBSWOOL + "|linen|hemp|silk(?!\\s*-?\\s*screen)|viscose|"
         "rayon|modal|lyocell|tencel|acrylic|elastane|spandex|lycra|cashmere|alpaca|mohair")
# Keys are letters only, so every spelling of lambswool and "camel hair" find their entry.
_CANON = {"poly": "polyester", "polyamide": "nylon", "spandex": "elastane", "lycra": "elastane", "rayon": "viscose",
          "tencel": "lyocell", "merino": "wool", "lambswool": "wool", "lambwool": "wool", "camelhair": "camel",
          "suede": "leather"}
# Words sellers put between the percentage and the fiber: "100% pure new wool", "100% Italian boiled wool".
_ADJ = r"(?:(?:pure|virgin|new|fine|extra[\s-]?fine|super[\s-]?fine|italian|scottish|worsted|boiled|premium|genuine|" \
       r"shetland|baby|\d[\s-]?ply)[\s/]+)*"
# Lining and insulation are not what the garment is made of (MATERIAL_KEYS skips eBay's fields for them for the same
# reason). Resellers paste those fields into descriptions ("Lining Material: Nylon"), and tags say "Lining: 100% poly".
_PCTS = r"\d{1,3}(?:\.\d+)?\s*%\s*[a-z]+(?:\s*[,/&]?\s*(?:and\s+)?\d{1,3}(?:\.\d+)?\s*%\s*[a-z]+)*"
_WORDS = r"[a-z]+(?:\s*/\s*[a-z]+)*"   # "Acrylic/Polyester"
_INNER = re.compile(rf"\b(?:lining|insulation)(?:\s+material)?\s*[:\-]\s*(?:{_PCTS}|{_WORDS})|\blined\s+with\s+(?:{_PCTS}|{_WORDS})"
                    rf"|(?:\d{{1,3}}(?:\.\d+)?\s*%\s*)?\b[a-z]+\s+lining\b(?!\s*(?:material|[:\-]))", re.I)
_PCT = re.compile(rf"(?<![\d.])(\d{{1,3}}(?:\.\d+)?)\s*%\s*{_ADJ}(organic\s+|recycled\s+)?({_FIBER})\b", re.I)
_BARE_RE = re.compile(rf"\b(organic\s+|recycled\s+)?({_BARE})\b", re.I)
# A dedicated material field is unambiguous, so there "leather", "down" and "poly" are fibers too, and suede is leather.
_BARE_FIELD_RE = re.compile(rf"\b(organic\s+|recycled\s+)?({_BARE}|leather|suede|down|poly)\b", re.I)
_DOWN = re.compile(r"(?<!button )(?<!button-)\b(?:down\s+(?:jacket|coat|vest|parka|puffer|hooded|hoodie|sweater|fill(?:ed)?|"
                   r"insulat\w+)|(?:goose|duck|feather)\s+down|down-filled)\b", re.I)
_FAUX_LEATHER = re.compile(r"\b(?:vegan|faux|synthetic)\s+leather\b", re.I)
_REAL_LEATHER = re.compile(r"\b(?:genuine|real|full[- ]grain|top[- ]grain)\s+leather\b", re.I)
_SYNTHETIC = {"polyester", "nylon", "acrylic", "modacrylic", "elastane", "polyurethane"}
# Structured specifics we trust for composition. Lining and insulation are left out: they would add up past 100%.
FLAG_KEYS = ("styles", "style", "era")
MATERIAL_KEYS = ("material", "outer shell material", "upper material", "fabric type", "fabric", "composition")

_CERTS = {
    "gots": r"\bgots\b|global organic textile standard",
    "oeko_tex": r"oeko[\s_-]?tex",
    "bluesign": r"\bbluesign",
    "fair_trade": r"fair[\s-]?trade",
    "rws": r"\brws\b|responsible wool standard",
    "rds": r"\brds\b|responsible down standard",
    "b_corp": r"\bb[\s-]?corp(?:oration)?\b",
}
_FLAGS = {
    "is_vintage": r"\b(?:vintage|vtg)\b(?![\s-]*(?:wash|style|inspired|fit|look|fade|effect))",
    "is_deadstock": r"\bdead[\s-]?stock\b|\bnew old stock\b|\b(?-i:NOS)\b",        # NOS: capitals only ("Nos Amis")
    "is_upcycled": r"\bup[\s-]?cycl(?:ed|e)\b|(?<!not )\breworked\b",           # reworked: remade from a garment
}
_RETAIL = re.compile(r"\b(?:retail(?:s|ed)?(?:\s+(?:price|value))?(?:\s+(?:for|at))?|msrp)\s*[:\-]?\s*"
                     r"\$\s*(\d[\d,]*(?:\.\d{1,2})?)", re.I)
# Countries clothes are made in, by every name sellers and eBay use. A known list, so "made in a smoke free home" and
# "made in limited quantities" are not countries and "Made in Hong Kong" is not "Hong".
_COUNTRIES = {name: name.title() for name in (
    "china", "taiwan", "macau", "japan", "india", "pakistan", "bangladesh", "vietnam", "cambodia", "indonesia", "thailand",
    "malaysia", "philippines", "myanmar", "laos", "nepal", "mongolia", "turkey", "jordan", "egypt", "israel", "morocco",
    "tunisia", "madagascar", "mauritius", "kenya", "ethiopia", "lesotho", "mexico", "guatemala", "honduras", "nicaragua",
    "haiti", "colombia", "peru", "ecuador", "bolivia", "brazil", "argentina", "chile", "canada", "italy", "portugal",
    "spain", "france", "germany", "austria", "switzerland", "belgium", "netherlands", "denmark", "sweden", "norway",
    "finland", "iceland", "poland", "romania", "bulgaria", "hungary", "lithuania", "latvia", "estonia", "ukraine",
    "greece", "albania", "serbia", "croatia", "slovakia", "slovenia", "moldova", "england", "scotland", "wales",
    "ireland", "australia", "hong kong", "sri lanka", "el salvador", "dominican republic", "south korea", "new zealand",
    "south africa", "costa rica", "czech republic", "north macedonia")} | {
    "usa": "USA", "u.s.a.": "USA", "u.s.a": "USA", "u.s.": "USA", "us": "USA", "united states": "USA",
    "united states of america": "USA", "america": "USA", "uk": "UK", "u.k.": "UK", "united kingdom": "UK",
    "great britain": "UK", "republic of ireland": "Ireland", "korea": "South Korea", "republic of korea": "South Korea", "korea, republic of": "South Korea",
    "viet nam": "Vietnam", "macao": "Macau", "burma": "Myanmar", "holland": "Netherlands", "czechia": "Czech Republic",
    "macedonia": "North Macedonia"}
_NO_COUNTRY = {"unknown", "n/a", "na", "none", "other", "not specified"}
_MADE_IN = re.compile(r"\bmade\s+in\s*:?\s*(?:the\s+)?("
                      + "|".join(re.escape(c) for c in sorted(_COUNTRIES, key=len, reverse=True)) + r")(?![a-z])", re.I)


class ProductLine(BaseModel):
    brand: str
    title_has: list[str]
    categories: list[Category]   # the garments the line covers: a name can also be a shoe ("Nuptse Traction Booties")
    note: str
    fibers: list[Fiber]
    durable: bool = False  # True: a known long-lived line (quality +2); False: the line only tells us its fabric


PRODUCT_LINES = [ProductLine(**p) for p in yaml.safe_load(Path(__file__).with_name("product_lines.yaml").read_text(encoding="utf-8"))]


def parse_fibers(text: str, field: bool = False) -> tuple[list[Fiber], str]:
    """Fibers named in `text` and the matched snippets. Percent matches first, then bare words.
    `field=True` when `text` comes from a structured material field rather than free text."""
    out, snips = [], []

    def add(name, pct, modifier, snippet):
        """A fiber with no percentage is added only if that fiber is not listed yet."""
        name, modifier = re.sub(r"[^a-z_]", "", name.lower()), modifier.strip().lower()
        fiber = Fiber(fiber=_CANON.get(name, name), pct=pct, organic=True if modifier == "organic" else None,
                      recycled=True if modifier == "recycled" else None)
        if fiber not in out and (pct is not None or fiber.fiber not in {f.fiber for f in out}):
            out.append(fiber)
            snips.append(snippet)

    text = _INNER.sub(" ", re.sub(r"#\w+", " ", text))   # hashtags are tags, not claims: resellers tag the lining too
    for m in _FAUX_LEATHER.finditer(text):
        add("synthetic_leather", None, "", m[0])
    text = _FAUX_LEATHER.sub(" ", text)
    for m in _PCT.finditer(text):
        if float(m[1]) <= 100:
            add(m[3], float(m[1]), m[2] or "", m[0])
    text = _PCT.sub(" ", text)
    for m in _REAL_LEATHER.finditer(text):
        add("leather", None, "", m[0])
    for m in _DOWN.finditer(text):
        add("down", None, "", m[0])
    for m in (_BARE_FIELD_RE if field else _BARE_RE).finditer(text):
        add(m[2], None, m[1] or "", m[0])
    return out, "; ".join(snips)


def to_materials(fibers: list[Fiber], certifications: list[str]) -> Materials:
    """Percentages summing to 90-110 are scaled to 100; otherwise kept and flagged suspect."""
    pcts = [f.pct for f in fibers if f.pct is not None]
    total = sum(pcts)
    suspect = bool(pcts) and not 90 <= total <= 110
    scale = 100 / total if pcts and not suspect else 1
    fibers = [f.model_copy(update={"pct": None if f.pct is None else round(f.pct * scale, 1)}) for f in fibers]
    complete = bool(fibers) and not suspect and len(pcts) == len(fibers)
    share = round(sum(f.pct for f in fibers if f.fiber in _SYNTHETIC), 1) if complete else None
    return Materials(fibers=fibers, synthetic_share=share, certifications=certifications, composition_suspect=suspect)


def match_product_line(brand: str | None, title: str, category: str, lines: list[ProductLine]) -> ProductLine | None:
    for p in lines:
        brand_ok = slug(p.brand) == slug(brand) if brand else slug(p.brand) in slug(title)
        if brand_ok and category in p.categories and all(re.search(rf"\b{re.escape(w)}\b", title, re.I) for w in p.title_has):
            return p


def _hits(patterns: dict[str, str], text: str) -> dict[str, str]:
    return {k: m[0] for k, p in patterns.items() if (m := re.search(p, text, re.I))}


def extract(n: Normalized, lines: list[ProductLine] = PRODUCT_LINES) -> Listing:
    day = n.scraped_at.date()
    text = f"{n.title}. {n.description or ''}"
    spec = {k.strip().lower(): v.strip() for k, v in n.specifics.items() if v and v.strip()}
    evidence = list(n.evidence)

    def note(field, status, source, snippet=None):
        evidence.append(Evidence(field=field, status=status, source=source, snippet=snippet, as_of=day))

    fibers, snippet = parse_fibers(" ".join(spec.get(k, "") for k in MATERIAL_KEYS), field=True)
    source = "specifics"
    in_text, text_snippet = parse_fibers(text)
    # The field wins, unless it is empty or the text names the same fibers with the percentages the field lacks
    if not fibers or (all(f.pct is None for f in fibers) and any(f.pct is not None for f in in_text)
                      and {f.fiber for f in fibers} <= {f.fiber for f in in_text}):
        fibers, snippet, source = in_text, text_snippet, "listing_text"
    line = match_product_line(n.brand, f"{n.title} {spec.get('product line', '')} {spec.get('model', '')}", n.category, lines)
    if fibers:
        note("materials.fibers", "claimed", source, snippet)
    elif line:
        fibers = line.fibers
        note("materials.fibers", "inferred", "product_line", line.note)
    else:
        note("materials.fibers", "unknown", "listing_text")
    if line and line.durable:  # a known durable line is its own evidence (quality credits it), whatever the seller stated
        note("product_line", "inferred", "product_line", line.note)

    certs = {}
    for source, where in (("specifics", " ".join(spec.values())), ("listing_text", text)):
        for cert, snippet in _hits(_CERTS, where).items():
            if cert not in certs:
                certs[cert] = snippet
                note("materials.certifications", "claimed", source, snippet)

    # Flags come from the title and structured style fields only: descriptions carry shop-wide boilerplate
    # ("especially for pre-owned or vintage goods") that says nothing about this item.
    flags = {}
    for source, where in (("listing_text", n.title), ("specifics", " ".join(spec.get(k, "") for k in FLAG_KEYS))):
        for flag, snippet in _hits(_FLAGS, where).items():
            if flag not in flags:
                flags[flag] = snippet
                note(f"flags.{flag}", "claimed", source, snippet)
    if spec.get("vintage", "").lower() in {"yes", "true"} and "is_vintage" not in flags:
        flags["is_vintage"] = "Vintage: Yes"
        note("flags.is_vintage", "claimed", "specifics", "Vintage: Yes")

    cost = n.cost.model_dump()
    if cost["retail_price_cents"] is not None:   # an actor field (Poshmark's "Original Price")
        note("cost.retail_price_cents", "claimed", "specifics", f"${cost['retail_price_cents'] / 100:.2f}")
    elif m := _RETAIL.search(text):
        cost["retail_price_cents"] = int(Decimal(m[1].replace(",", "")) * 100)
        note("cost.retail_price_cents", "claimed", "listing_text", m[0])

    country = next((v for k, v in spec.items() if k.startswith("country") and ("manufactur" in k or "origin" in k)
                    and v.lower() not in _NO_COUNTRY), None)
    if country:
        note("country_of_manufacture", "claimed", "specifics", country)
        country = _COUNTRIES.get(country.lower(), country)
    elif m := _MADE_IN.search(text):
        country = _COUNTRIES[m[1].lower()]
        note("country_of_manufacture", "claimed", "listing_text", m[0])

    data = n.model_dump(exclude={"specifics"})
    data.update(cost=cost, materials=to_materials(fibers, list(certs)), country_of_manufacture=country,
                flags=n.flags.model_copy(update={k: True for k in flags}), evidence=evidence)
    return Listing(**data)


def extract_file(src, dst) -> Counter:
    """Step 03 driver: normalized.jsonl -> listings.jsonl. Lines that do not validate are counted and skipped."""
    stats, out = Counter(), []
    for line in jsonl.read(src):
        try:
            out.append(jsonl.dumps(extract(Normalized.model_validate_json(line)).model_dump(mode="json")) + "\n")
        except ValidationError:
            stats["invalid"] += 1
    Path(dst).with_suffix(".tmp").write_text("".join(out), encoding="utf-8", newline="\n")
    Path(dst).with_suffix(".tmp").replace(dst)
    stats["kept"] = len(out)
    return stats
