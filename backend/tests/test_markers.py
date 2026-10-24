from backend import markers as M
from conftest import ev

BRANDS = M.index_brands([
    {"name": "Patagonia", "aliases": ["patagonia inc"],
     "repair_program": {"value": "Worn Wear repairs", "url": "https://patagonia.example/repairs"},
     "guarantee": {"value": "Ironclad Guarantee", "url": "https://patagonia.example/guarantee"},
     "certifications": [{"name": "fair_trade", "url": "https://patagonia.example/ft"}], "as_of": "2026-10-24"},
    {"name": "Levi's", "repair_program": {"value": "Tailor shop repairs", "url": "https://levi.example/tailor"},
     "as_of": "2026-10-24"},
])


def fibers(*pairs, **flags):
    return {"fibers": [{"fiber": f, "pct": p, "organic": flags.get("organic"), "recycled": flags.get("recycled")}
                       for f, p in pairs],
            "synthetic_share": flags.get("synthetic_share"), "certifications": flags.get("certs", []),
            "composition_suspect": False}


def kinds(marker):
    return [f["kind"] for f in marker["facts"]]


# --- quality ---------------------------------------------------------------------------

def test_no_evidence_is_unknown_with_no_score(row):
    q, scored = M.quality(row(brand="No Name"), BRANDS)
    assert q == {"level": "unknown", "score": None, "facts": []} and scored == []


def test_brand_repair_program_is_medium_and_cited(row):
    q, _ = M.quality(row(brand="LEVIS"), BRANDS)  # brand match ignores case and punctuation
    assert q["level"] == "medium"
    f = q["facts"][0]
    assert f["kind"] == "repair_program" and f["source"] == "brand_table" and f["source_url"] == "https://levi.example/tailor"


def test_repair_program_and_guarantee_count_once_but_both_show(row):
    q, _ = M.quality(row(brand="Patagonia Inc"), BRANDS)
    assert kinds(q) == ["repair_program", "guarantee"] and q["level"] == "medium"


def test_brand_plus_product_line_is_high(row):
    r = row(brand="Patagonia", title="Patagonia Better Sweater", category="sweaters_knitwear",
            materials=fibers(("polyester", None), recycled=True),
            evidence=[ev("materials.fibers", "product_line", "inferred", "Better Sweater: recycled polyester fleece")])
    q, _ = M.quality(r, BRANDS)
    assert q["level"] == "high"
    assert "product_line" in kinds(q) and "materials" in kinds(q)


def test_fiber_that_suits_the_category_adds_a_point(row):
    q, _ = M.quality(row(category="sweaters_knitwear", materials=fibers(("wool", 100)),
                         evidence=[ev("materials.fibers", snippet="100% wool")]), {})
    assert q["level"] == "medium" and q["facts"][0]["value"] == "100% wool"


def test_structured_fiber_data_adds_half_a_point_more(row):
    r = row(category="jeans_pants", materials=fibers(("cotton", 100)), evidence=[ev("materials.fibers", "specifics")])
    q, _ = M.quality(r, {})
    assert q["score"] > M.quality(row(category="jeans_pants", materials=fibers(("cotton", 100)),
                                      evidence=[ev("materials.fibers")]), {})[0]["score"]


def test_pilling_prone_knit_is_low(row):
    q, _ = M.quality(row(category="sweaters_knitwear", materials=fibers(("acrylic", 100), synthetic_share=100),
                         evidence=[ev("materials.fibers")]), {})
    assert q["level"] == "low" and q["score"] is not None


def test_a_stated_material_that_moves_nothing_is_shown_but_unknown(row):
    q, _ = M.quality(row(category="tshirts", materials=fibers(("cotton", 60), ("polyester", 40), synthetic_share=40),
                         evidence=[ev("materials.fibers")]), {})
    assert q["level"] == "unknown" and q["score"] is None
    assert q["facts"][0]["value"] == "60% cotton, 40% polyester"


def test_leather_sneakers_and_organic_labels(row):
    q, _ = M.quality(row(category="sneakers", materials=fibers(("leather", None))), {})
    assert q["level"] == "medium" and q["facts"][0]["value"] == "leather"
    q, _ = M.quality(row(category="tshirts", materials=fibers(("cotton", 100), organic=True)), {})
    assert q["facts"][0]["value"] == "100% organic cotton"


# --- eco -------------------------------------------------------------------------------

def test_secondhand_is_always_shown_but_scores_nothing(row):
    e = M.eco(row(), {})
    assert e["level"] == "unknown" and e["score"] is None and kinds(e) == ["secondhand"]


def test_vintage_plus_recycled_is_high(row):
    r = row(flags={"is_vintage": True, "is_deadstock": False, "is_upcycled": False},
            materials=fibers(("polyester", 100), recycled=True, synthetic_share=100))
    e = M.eco(r, {})
    # +1 vintage, +1 recycled, -1 synthetic share > 50%  -> 1 point
    assert e["level"] == "medium" and set(kinds(e)) >= {"vintage", "recycled", "synthetic_share"}


def test_mostly_synthetic_with_nothing_else_is_low(row):
    assert M.eco(row(materials=fibers(("polyester", 80), ("cotton", 20), synthetic_share=80)), {})["level"] == "low"


def test_certifications_count_at_most_twice_including_the_brands(row):
    r = row(brand="Patagonia", materials=fibers(("cotton", 100), organic=True, certs=["gots", "oeko_tex", "bluesign"]))
    e = M.eco(r, BRANDS)
    assert kinds(e).count("certification") == 4          # 3 on the listing + the brand's Fair Trade
    assert e["level"] == "high" and e["score"] == 1.0    # organic + 2 (capped) = 3 -> clamped


def test_animal_materials_are_a_neutral_fact(row):
    e = M.eco(row(materials=fibers(("wool", 100))), {})
    assert "animal_materials" in kinds(e) and e["level"] == "unknown"


# --- confidence ------------------------------------------------------------------------

def test_confidence_reflects_how_much_evidence_moved_the_estimate(row):
    assert M.confidence([]) == "unknown"
    inferred = M.quality(row(evidence=[ev("materials.fibers", "product_line", "inferred")]), {})[1]
    assert M.confidence(inferred) == "low"
    brand_only = M.quality(row(brand="Levi's"), BRANDS)[1]
    assert M.confidence(brand_only) == "medium"
    rich = M.quality(row(brand="Levi's", category="jeans_pants", materials=fibers(("cotton", 100)),
                         evidence=[ev("materials.fibers", "specifics")]), BRANDS)[1]
    assert M.confidence(rich) == "high"


# --- quality from build: construction, survival, weak materials ----------------------------

VINTAGE = {"is_vintage": True, "is_deadstock": False, "is_upcycled": False}


def test_a_durable_construction_named_in_the_listing_adds_a_cited_point(row):
    q, scored = M.quality(row(category="jeans_pants", title="Levi's 501 selvedge jeans 32x32"), {})
    f = next(f for f in q["facts"] if f["kind"] == "construction")
    assert q["level"] == "medium" and f["value"] == "selvedge" and f["snippet"] == "selvedge" and f in scored


def test_several_construction_words_still_count_once(row):
    r = row(title="Carhartt double knee pants", description="Heavy duck canvas, triple stitched. Reinforced knees.")
    q, _ = M.quality(r, {})
    assert [f["value"] for f in q["facts"] if f["kind"] == "construction"] == ["double knee, duck canvas, triple stitched"]
    assert q["score"] == M.quality(row(title="Carhartt double knee pants"), {})[0]["score"]


def test_a_vintage_piece_still_in_good_condition_has_already_lasted(row):
    q, _ = M.quality(row(flags=VINTAGE, condition="good"), {})
    f = next(f for f in q["facts"] if f["kind"] == "survival")
    assert q["level"] == "medium" and f["value"] == "Vintage and still in good condition"
    # deadstock-style vintage with tags was never worn, and a worn-out vintage piece proves nothing
    assert "survival" not in kinds(M.quality(row(flags=VINTAGE, condition="new_with_tags"), {})[0])
    assert "survival" not in kinds(M.quality(row(flags=VINTAGE, condition="fair"), {})[0])


def test_stretch_jeans_lose_the_cotton_point_and_score_low(row):
    stretch = fibers(("cotton", 98), ("elastane", 2), synthetic_share=2)
    q, _ = M.quality(row(category="jeans_pants", materials=stretch, evidence=[ev("materials.fibers")]), {})
    assert q["level"] == "low"
    rigid = M.quality(row(category="jeans_pants", materials=fibers(("cotton", 100)), evidence=[ev("materials.fibers")]), {})
    assert rigid[0]["level"] == "medium"


def test_faux_and_pu_leather_score_low(row):
    for fiber in ("synthetic_leather", "polyurethane"):
        q, _ = M.quality(row(category="jackets_outerwear", materials=fibers((fiber, None)), evidence=[ev("materials.fibers")]), {})
        assert q["level"] == "low", fiber


def test_construction_words_are_matched_as_words(row):
    assert "construction" not in kinds(M.quality(row(title="Waxed-look nylon bomber, not heavyweightish"), {})[0])
