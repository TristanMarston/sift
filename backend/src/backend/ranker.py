"""Search hits -> SearchResponse: markers, wears and cost per wear for each result, plus every sort order."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from backend import markers
from backend import wear as W
from backend.images import small_url

ML = Path(__file__).resolve().parents[2] / "ml"
EXACT = 0.9  # similarity at or above this is shown as an exact match
PASS_THROUGH = ["id", "marketplace", "url", "title", "brand", "category", "subcategory", "size", "color", "condition",
                "condition_raw", "image_urls", "flags", "cost", "materials"]


@dataclass
class Config:
    baselines: dict
    brands: dict


def load_config(ml: Path = ML) -> Config:
    baselines = yaml.safe_load((ml / "wear_baselines.yaml").read_text())
    brands = yaml.safe_load((ml / "evidence" / "brands.yaml").read_text())["brands"]
    return Config(baselines, markers.index_brands(brands))


def _result(row: dict, sim: float, cfg: Config) -> dict:
    q, scored = markers.quality(row, cfg.brands)
    wears = W.expected_wears(cfg.baselines["categories"][row["category"]], q["level"], row["condition"])
    sim = round(min(1.0, max(0.0, sim)), 4)
    return {
        **{k: row[k] for k in PASS_THROUGH},
        "thumb_url": small_url(row["image_urls"][0]),
        "match": {"similarity": sim, "band": "exact" if sim >= EXACT else "similar"},
        "quality": q,
        "eco": markers.eco(row, cfg.brands),
        "wear": {
            "expected_wears": wears,
            "basis": "category_baseline" if q["level"] == "unknown" else "evidence_adjusted",
            "cpw_cents": W.cpw_table(row["cost"]["total_cents"], wears["mid"]),
            "break_even_wears": None,
            "facts": W.wear_facts(row["category"], cfg.baselines, row["condition"], row["condition_raw"]),
        },
        "confidence": markers.confidence(scored),
        "seller": {k: row["seller"][k] for k in ("type", "rating", "region")},
    }


def _order(results, key) -> list[str]:
    return [r["id"] for r in sorted(results, key=lambda r: (key(r), r["id"]))]


def _slider(cpw: list[str], match: list[str]) -> list[list[str]]:
    """slider[i]: sort by i/10 x match rank + (1 - i/10) x value rank. Integer weights keep ties exact."""
    n = len(cpw)
    pc, pm = {x: n - p for p, x in enumerate(cpw)}, {x: n - p for p, x in enumerate(match)}
    return [sorted(cpw, key=lambda x: (-(i * pm[x] + (10 - i) * pc[x]), x)) for i in range(11)]


def rank(hits: list[tuple[dict, float]], query: dict, cfg: Config) -> dict:
    """`hits` come in the index's order: similarity, minus the colour penalty when the index has colours."""
    results = [_result(row, sim, cfg) for row, sim in hits]
    given = {r["id"]: i for i, r in enumerate(results)}
    typ = W.typical([r["cost"]["total_cents"] for r in results], [r["wear"]["expected_wears"]["mid"] for r in results])
    for r in results:
        r["wear"]["break_even_wears"] = W.break_even(r["cost"]["total_cents"], typ)
    orders = {
        "cpw": _order(results, lambda r: r["wear"]["cpw_cents"]["at_mid"]),
        "price": _order(results, lambda r: r["cost"]["total_cents"]),
        "match": _order(results, lambda r: given[r["id"]]),
        "eco": _order(results, lambda r: (r["eco"]["score"] is None, -(r["eco"]["score"] or 0))),
    }
    by_id = {r["id"]: r for r in results}
    cheapest = orders["price"][0] if results else None
    return {
        "query": query,
        "typical": typ,
        "results": [by_id[i] for i in orders["cpw"]],
        "orders": orders,
        "slider": _slider(orders["cpw"], orders["match"]),
        "headline": {"cheapest_id": cheapest,
                     "cheapest_rank_by_cpw": orders["cpw"].index(cheapest) + 1 if cheapest else None},
    }
