"""Step 04: per-marketplace coverage stats and the acceptance checklist (SPEC.md §15) for listings.jsonl."""
from collections import Counter
from statistics import median

PROPS = {"Carhartt Detroit jacket": ("carhartt", "detroit"), "Patagonia Better Sweater": ("patagonia", "better", "sweater"),
         "Nike Dunk Low": ("nike", "dunk", "low")}


def pct(count: int, total: int) -> float:
    return round(100 * count / total, 1) if total else 0.0


def _stated_material(l) -> bool:
    """A material the listing itself states (product-line inference does not count)."""
    return any(e.field == "materials.fibers" and e.status == "claimed" for e in l.evidence)


def _metrics(rows, total) -> dict:
    n = len(rows)
    return dict(rows=n, share=pct(n, total),
                description=pct(sum(len(l.description or "") > 40 for l in rows), n),
                any_material=pct(sum(_stated_material(l) for l in rows), n),
                percentages=pct(sum(any(f.pct is not None for f in l.materials.fibers) for l in rows), n),
                certification=pct(sum(bool(l.materials.certifications) for l in rows), n),
                region=pct(sum(l.seller.region is not None for l in rows), n),
                median_price=median(l.cost.price_cents for l in rows) / 100 if rows else 0.0)


def stats(listings) -> dict:
    total = len(listings)
    by_mp = {mp: _metrics([l for l in listings if l.marketplace == mp], total)
             for mp in sorted({l.marketplace for l in listings})}
    return dict(total=total, active=sum(l.status == "active" for l in listings), marketplaces=by_mp,
                categories=Counter(l.category for l in listings), overall=_metrics(listings, total))


def acceptance(s: dict, listings, min_rows: int = 20_000) -> list[tuple[str, bool, str]]:
    """(check, passed, detail) for each acceptance line in SPEC.md §15."""
    biggest = max((m["share"] for m in s["marketplaces"].values()), default=0.0)
    missing = [name for name, words in PROPS.items()
               if not any(all(w in f"{l.brand or ''} {l.title}".lower() for w in words) for l in listings)]
    o = s["overall"]
    return [
        ("active rows", s["active"] >= min_rows, f"{s['active']} of {min_rows}"),
        ("marketplaces", len(s["marketplaces"]) >= 4, f"{len(s['marketplaces'])} of 4 needed"),
        ("share per marketplace", biggest <= 50, f"largest is {biggest}% (max 50)"),
        ("stated material", o["any_material"] >= 25, f"{o['any_material']}% (min 25)"),
        ("percentages", o["percentages"] >= 10, f"{o['percentages']}% (min 10)"),
        ("demo props", not missing, "all present" if not missing else f"missing: {', '.join(missing)}"),
        ("region on every row", o["region"] == 100 if listings else False, f"{o['region']}%"),
    ]


def render(s: dict, checks, date: str) -> str:
    lines = [f"# Scrape report", "", f"Generated {date} from `data/listings.jsonl`: {s['total']} rows ({s['active']} active).",
             "", "## Per marketplace", "",
             "| marketplace | rows | share % | description >40 chars % | stated material % | composition % % | "
             "certification % | region % | median price $ |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for mp, m in s["marketplaces"].items():
        lines.append(f"| {mp} | {m['rows']} | {m['share']} | {m['description']} | {m['any_material']} | {m['percentages']} | "
                     f"{m['certification']} | {m['region']} | {m['median_price']:.2f} |")
    lines += ["", "## Categories", "", "| category | rows |", "| --- | ---: |"]
    lines += [f"| {c} | {n} |" for c, n in sorted(s["categories"].items())]
    lines += ["", "## Acceptance", ""]
    lines += [f"- [{'x' if ok else ' '}] {name}: {detail}" for name, ok, detail in checks]
    return "\n".join(lines) + "\n"
