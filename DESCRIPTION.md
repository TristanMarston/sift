# Sift - Project Description

*Working title. Rename freely.*

> **Purpose of this file:** what we are building, why, and how the pieces fit together. It describes intent, goals, and concepts. Specifics live in other docs, and they win on conflict: the API contract is `schema/api.schema.json` + `schema/API.md`, and the data is `backend/pipeline/SCRAPING.md`. See `README.md` for the doc map. Read this before writing any code.

---

## 1. One-line pitch

**Take a photo of clothing you like. We find the best look-alikes across secondhand marketplaces, and rank them by cost per wear instead of price. Every result comes with a "Wear Receipt" that shows the evidence: cost, quality, and eco facts.**

Tagline candidates:
- *Every shopping agent sorts by price. We sort by cost per wear.*
- *Buy it once.*

---

## 2. Why we are building this

### The problem
Almost every shopping tool answers one question: **"What is the cheapest?"** That pushes people toward cheap items that wear out fast. They buy again, and again. Easier and cheaper shopping often means *more* shopping.

### The idea we are borrowing
Steph Ango's essay *Buy Wisely* gives a simple rule: **cost per use = price ÷ the number of times you will use it.**
- A $5 item you use 10 times costs $0.50 per use. A $20 item you use 200 times costs $0.10 per use.
- Durable things cost less over time, even when they cost more up front.
- Durable things are also great secondhand, because they last and are not tied to a trend.
- Resale value is a clue: if other people want it used, it is probably well made.
- Sometimes the best choice is not to buy at all.

### Why this matters for clothes
- Price does not tell you quality. A university and WRAP test of 47 t-shirts found no link between price and durability. The most expensive shirt (£395) ranked 28th of 47. A £4 one ranked 15th.
- Wearing clothes longer is one of the biggest levers we have. WRAP estimates that nine more months of use cuts a garment's carbon, waste, and water footprint by about 20–30%.
- Secondhand is not a free pass. A Yale study of 1,009 US shoppers found that people who buy more secondhand also tend to buy more new clothes. Making things easier to find does not reduce buying by itself. **How long things stay in use is what counts.**

### Our job
Make **"how long will this last?"** as easy to see as **"how much does it cost?"**

---

## 3. What already exists (and how we differ)

| Kind of product | Examples | What they optimize | What is missing |
|---|---|---|---|
| General shopping agents | Meta Muse, OpenAI Dots, Grok Bot | Finding a deal and completing the purchase | No sense of quality or longevity |
| Secondhand search | Beni, Gem, Copped, Phia | Finding the same item cheaper, or checking price fairness | Cheap ≠ lasting |
| Fabric-based "quality scores" | Wovyyn, Worth, Fabricly, Fabric Lens | A score from fiber content on a product page | Fiber is a weak signal. The scores are not tied to real-world outcomes |
| Curated "buy it for life" shops | BuyMeOnce | Hand-picked durable items | A small catalog, not a search over everything |
| Wardrobe apps | Whering, Indyx | Tracking cost per wear of things you already own | Nothing at the moment of buying |

**Our difference:** we search by photo across four secondhand marketplaces and rank by *cost per wear*, not price. Every number traces to evidence we can show: declared materials (with how sure we are of them), known product lines, and sourced brand facts such as repair programs and certifications. We show that evidence in a receipt, and we say "unknown" when we do not have it. Owner reviews and community evidence are the next layer (stretch).

---

## 4. The experience

1. **Open the website.** No sign-up, no typing. The camera is the front page.
2. **Take a photo** of a piece of clothing or a whole outfit. (Upload also works.)
3. **We find the garments** in the photo. For an outfit, each garment gets its own tab. The user can draw a box if detection struggles.
4. **We show look-alikes**, ranked by cost per wear, from a pre-collected catalog of secondhand listings (Depop, Poshmark, Grailed, eBay).
5. **Each result has a Wear Receipt**: what it costs, how it rates on quality and eco, its cost per wear, and why we think so.
6. **The user can explore.** Sort by *cost per wear*, *price*, *look match*, or *eco*. Slide between *closer match* and *better value*. Open any receipt to see sources.

**Signature moment:** the user flips the sort from price to cost per wear. The cards visibly reshuffle. The headline reads something like *"The cheapest match drops to #14."*

---

## 5. Key concepts (plain definitions)

- **Look match.** How visually close an item is to the user's photo. Items below a similarity cutoff are dropped, so we only rank real alternatives.
- **Evidence.** Facts about an item or its brand. Each fact has a source, a status (*verified*, *claimed*, *inferred*, *unknown*), and a date.
- **The three markers.** Each one is a *level* (high / medium / low / unknown) plus the facts behind it. A hidden 0–1 score exists only for sorting, and the UI never shows it.
  - **Cost:** price, shipping, markdown, and "vs retail" when known.
  - **Quality:** how strong the evidence is that the item will last: materials, known product line, maker support. It is a *summary of evidence*, not a lab test.
  - **Eco:** stated facts only: secondhand, vintage/deadstock/upcycled, recycled or organic fibers, certifications, synthetic share. It is not a sustainability grade.
- **Confidence.** How much evidence sits behind an item's expected wears. Low evidence gives low confidence, and we say so.
- **Expected wears.** A *range*, not a promise. Each garment type has a baseline from public benchmarks, labeled as an assumption. Quality evidence moves the range.
- **Cost per wear.** Price ÷ expected wears. Shown at a few wear counts (30, 60, 100), so the user can pick the one that fits them.
- **Break-even wears.** How many times you must wear a pricier item for it to beat the typical match. This is the honest "buy less" message: *if you will not wear it that often, buy the cheaper one.*
- **Resale outlook** *(later, not in v1).* What the item is likely to be worth after use.
- **Wear Receipt.** The card that shows all of the above for one item.

---

## 6. How the ranking works

| Index | Question it answers | Evidence it uses (v1) | Priority |
|---|---|---|---|
| **Quality** | How long will this likely last? | Declared materials, known product lines, brand facts (repair program, published supplier list, certifications) | **Core. Must work.** Owner reviews and community evidence are stretch. |
| **Price** | What does it cost me now? | Listed price (plus shipping if available) | **Core.** |
| **Eco** | What do we know about its footprint? | Stated facts (§5). Shown and sortable, **not** part of cost per wear | **Core.** |
| **Resale** | What can I get back later? | Sold prices vs. original prices | **Later, not in v1.** |

**How they combine, in words:**
1. Start with the look matches (up to 50 close look-alikes).
2. Use the quality evidence to set an expected-wears range for each item.
3. Divide price by expected wears to get cost per wear.
4. Sort by cost per wear by default. The backend computes every number. The website does all the sorting and slider weighting locally, so the reshuffle is instant (see `schema/API.md` §3).

**Rules for the ranking:**
- It must be explainable. Anyone can open a receipt and see why an item ranked where it did.
- Never hide a component inside one opaque number.
- If we lack evidence, the item stays in the list but gets no boost. It is labeled *"Not enough evidence yet."* We do not guess.
- Declared materials are weak evidence (labels are often wrong, and fiber only loosely predicts durability). Show them, and give them modest weight.

---

## 7. The Wear Receipt

One card per result. Example (illustrative numbers). The exact fields are `Result` in `schema/API.md` §2.

```
┌──────────────────────────────────────────────┐
│ Carhartt Detroit jacket · Poshmark · Size M  │
│ Look match: 91% · Good condition             │
├──────────────────────────────────────────────┤
│ COST                                 $48.00  │
│  Seller marked down from $60                 │
│                                              │
│ QUALITY                               High   │
│  Materials      Cotton duck (likely:         │
│                 known product line)          │
│  Maker support  Repair program (brand site)  │
│                                              │
│ ECO                                 Medium   │
│  Secondhand     Already in use (vintage)     │
│  Synthetic      0% (as declared)             │
│                                              │
│ EXPECTED WEARS            120–200 (high conf)│
│ COST PER WEAR  @30 $1.60 · @60 $0.80 · @100 $0.48 │
│                                              │
│ VS. TYPICAL MATCH                            │
│  Typical match: $40, $0.67/wear              │
│  Break-even: wear this 72+ times to win      │
│                                              │
│ CONFIDENCE  High · Sources ▸ · Date ▸        │
└──────────────────────────────────────────────┘
```

Every line is clickable for its source, status, and date. Anything we could not verify is shown as *"unknown"*, not hidden.

---

## 8. Data

### 8.1 Two kinds of data

1. **The Catalog.** 20,000 listings at first, growing to ~50,000, from four secondhand marketplaces (Depop, Poshmark, Grailed, eBay), counting any listing priced in USD across 8 categories: jackets and outerwear, hoodies and sweatshirts, t-shirts, sneakers, jeans and pants, sweaters and knitwear, shirts, dresses and skirts. Each listing has: photos, title, brand, category, size, condition, price, link, marketplace, the full description, and materials when the listing states them. Details are in `backend/pipeline/SCRAPING.md`.
2. **The Evidence Tables.** Small and hand-curated:
   - a `brands` table of ~40 brands (repair program, published supplier list, material commitments, certifications), where every claim has a source URL;
   - `product_lines.yaml` (for example Carhartt Detroit → cotton duck);
   - `backend/ml/wear_baselines.yaml`: the expected-wear range per category, labeled as an assumption.

**Why this split matters:** much of the quality evidence is about *makers*, not individual listings. Each listing inherits the facts for its brand. That keeps the evidence work small and doable in a day.

### 8.2 Where evidence comes from

| Source | What we learn | Main limits | Status |
|---|---|---|---|
| **Declared materials** (listing text, eBay item specifics) | Fiber, %, organic/recycled, certifications | A weak link to lasting power. Labels are often wrong (an EU test found 37% mislabeled). Show it, give it little weight. | **v1** |
| **Known product lines** | The material of well-known models | A small hand-made table. Marked *inferred* | **v1** |
| **Maker promises** (brand table) | Repair programs, guarantees, supplier lists | A guarantee often excludes normal wear. A modest signal | **v1** |
| **Care-tag photos** | The real fiber content from tag images | OCR coverage varies | **P1, after the golden path** |
| **Customer reviews on retail sites** | Rating, count, durability complaints | New items only. Wear-out is under-reported | **Stretch** |
| **Community discussion** ("buy it for life") | Which brands people say last | Popular brands only. Noisy | **Stretch** |
| **Resale markets** | Value kept, speed of sale | Survivorship. Price tracks looks | **Later** |

**What we do not use as a quality signal:** price alone. Research shows it does not predict durability.

### 8.3 Scale
- **Catalog:** 20,000 → ~50,000 listings. Variety across categories matters more than raw size.
- **Evidence:** ~40 brands × 8 categories, plus the product-line table.
- **Budget:** ~$97 of Apify credits for 20k listings (26k raw rows with over-scrape), ~$240 for 50k (`backend/pipeline/SPEC.md` §6).

### 8.4 Timing
- **Friday evening:** a 20-item test run per marketplace. Go or no-go on each source.
- **Friday night to Saturday morning:** full collection. This leaves Saturday to build the evidence tables, tune, and fix gaps.
- **Demo day:** **never collect live.** All searches use the pre-built data. Keep a backup snapshot.

### 8.5 Data rules
- Public data only. No seller or reviewer personal information is stored (no usernames, no profile URLs).
- Record the source and the collection date for every fact.
- Some markets restrict automated access in their terms. We note this in our trust section and use only public listing data.
- Include the demo props in the catalog so the first scan is guaranteed to hit.

---

## 9. System overview (conceptual)

```
 COLLECT              CLEAN & ORGANIZE          BUILD EVIDENCE
 ───────              ───────────────           ──────────────
 Secondhand       ─┐   Normalize brand,          Extract materials,
 listings (4 mkts) ├─▶ category, price,      ─▶  certifications, flags
 Brand facts      ─┘   condition. Dedupe.        Brand table, product lines
 (hand-curated)        Thumbs + embeddings.      Wear baselines
                                │                       │
                                ▼                       ▼
                        ┌──────────────┐        ┌────────────────┐
                        │   CATALOG    │        │ EVIDENCE TABLES│
                        │ (listings +  │        │ (brands, lines,│
                        │  embeddings) │        │  baselines)    │
                        └──────┬───────┘        └────────┬───────┘
                               │                         │
   USER PHOTO ─▶ /detect ─▶ crop ─▶ /search: LOOK MATCHER ─▶ VALUE RANKER ◀┘
                                         (top 50 look-alikes)  (markers, CPW, receipt)
                                                 │
                                                 ▼
                                  WEBSITE: sorts, slider, Wear Receipts
```

### The parts

1. **Collectors.** Apify actors gather listings once, during the build. Apify is the core of the data layer.
2. **Cleaner.** Makes data from different markets comparable: the same brand names, categories, currencies, and conditions. Removes junk and duplicates. Brand names are messy, and this step decides how much of the catalog can use evidence.
3. **Evidence Builder.** Extracts materials and flags from listing text, and joins brand facts and product lines. It counts and summarizes. It does not invent.
4. **Catalog.** The searchable collection of listings with image embeddings. It answers "what looks like this photo?" with optional filters (max price, marketplace, size, condition).
5. **Garment Finder** (`/detect`). Finds each garment in the user's photo.
6. **Look Matcher** (`/search`). Returns the closest look-alikes from the Catalog.
7. **Value Ranker** (inside `/search`). Builds the three markers, expected wears, cost per wear, break-even, and every receipt line.
8. **Website.** Camera, tabs, results, sorts and slider (computed locally), receipts, the reshuffle animation.

### One agreement the whole team keeps
The API contract is **`schema/api.schema.json`** (the source of truth) and **`schema/API.md`** (its explanation). Every result has the same shape: item facts, three markers, wear numbers, and receipt facts (each with a source, status, and date). The website is built against sample data in that shape, so it never waits on the backend. Changing the schema requires a quick team huddle.

---

## 10. Trust and honesty rules

These are product features, not extras. They support the trust criteria of our sponsor tracks.

1. **No fake precision.** We never present a score as a lab measurement. Markers show a level and their facts, never a number. We say "evidence suggests."
2. **Show the work.** Every receipt line has a source, a status, and a date.
3. **"Not enough evidence" is a valid answer.** We show it clearly.
4. **Ranges, not promises.** Expected wears are ranges. Cost per wear is shown at several wear counts.
5. **Break-even honesty.** If a cheaper option wins for the user's likely use, we say so.
6. **Eco means facts, not a grade.** The eco marker summarizes stated facts (secondhand, recycled, deadstock, certifications, synthetic share). We never call an item "sustainable." Our one outcome claim is how long it is likely to stay in use.
7. **Privacy.** No personal data about sellers or reviewers. No accounts. Photos are used only for the search.

---

## 11. Scope

### Must work (the golden path)
- Photo in → garments found → look-alikes from several marketplaces → ranked by cost per wear → Wear Receipt on each.
- Quality evidence from materials, product lines, and brand facts for the demo brands.
- The three markers (cost, quality, eco) on every receipt.
- Four sorts (cost per wear, price, look match, eco) with the reshuffle animation.
- The "Not enough evidence" state.
- The break-even line.

### Should work if time allows
- The "Closer match ↔ better value" slider.
- Care-tag OCR to verify materials (SCRAPING.md §4, P1).

### Later or stretch
- Owner-review and community evidence (these slot in as new receipt facts, with no schema change).
- Resale outlook (price-band-adjusted).
- Optional "what you have" input (brand and price) to compare against the alternatives.
- New-retail listings alongside secondhand.
- Watch a look and alert when a better cost-per-wear item appears.
- Spending limits for a buying agent and real checkout.
- "What is my own item worth?" selling flow.
- A wear log for real user retention data.

### Not doing
- Lab claims or testing.
- A predicted wear count for an individual person.
- A sustainability grade or claim.
- Collecting data during the demo.

---

## 12. Demo plan (about 2 minutes)

| Time | Beat |
|---|---|
| 0:00–0:15 | **Hook.** "Every shopping agent sorts by price. Watch what happens when you sort by cost per wear." |
| 0:15–0:45 | **Teammate scan.** A prop jacket. Results appear in seconds. Open one Wear Receipt and show the quality and eco facts with their sources. |
| 0:45–1:10 | **The flip.** Toggle price → cost per wear. Cards reshuffle. "The cheapest drops to #14." Show the break-even line. |
| 1:10–1:40 | **"Now you."** Scan a judge's clothing. Show a receipt for a look-alike of their piece. If we have thin evidence, show *"Not enough evidence yet"* and explain why that is a feature. |
| 1:40–2:00 | **How it is built and why it matters.** A multi-market secondhand catalog collected with Apify, sourced evidence, a transparent receipt. Cost-per-wear framing and longer garment life as the impact. |

**Demo preparation:**
- 2–3 props with strong evidence (Carhartt Detroit jacket, Patagonia Better Sweater, Nike Dunk Low), already in the catalog.
- Clip light and white board for the table (lighting will be bad).
- Phone hotspot (venue wifi will be slow).
- Cached results for the props, an upload fallback if the camera fails, and a backup demo video.

---

## 13. What "done" looks like

- A scan returns ranked results in about 5 seconds on pre-built data.
- Every result has a complete receipt with real sources, or an honest "unknown" label.
- Sanity checks pass: within the same category, makers widely seen as durable generally rank above makers widely seen as disposable.
- Every demo brand has a row in the brands table.
- The demo props return themselves in the top 3.
- The sort flip works smoothly on a phone and a laptop.
- Nothing in the product claims more than the evidence supports.

---

## 14. Risks and fallbacks

| Risk | Fallback |
|---|---|
| A market blocks collection | Use the fallback actor for that market (SCRAPING.md §1). Collect early and keep a backup snapshot. |
| Few listings state materials | Add material-rich queries. Lean on product lines and brand facts. Show "Not enough evidence". |
| Brand names are messy in listings | Invest early in the Cleaner. Group by brand and category, not exact titles. |
| Quality evidence feels subjective | Show the facts, with their status and sources. Use only evidence we can trace. |
| Quality-first only surfaces expensive items | Show break-even wears. Keep the similarity cutoff. Compare against the "typical match", not against an ideal. |
| Venue wifi is slow | Sorting is local. Small cached index, cached prop results, phone hotspot. |
| Camera fails | Upload fallback. |

---

## 15. Event context and tracks

- **Event:** Cal Hacks 13.0 · Fri Oct 23 – Sun Oct 25, 2026 · Palace of Fine Arts, San Francisco.
- **Key times:** Hacking starts about 6 PM Friday. **Submission is due 9 AM Sunday.** Judging is 10:30 AM–12:30 PM Sunday, and the whole team must be at the table. All work must start during the event.
- **Primary track, Reimagining Shopping (Visa):** shopping that optimizes value over time instead of the lowest price. The Wear Receipt gives users transparency and trust. If the sponsor offers access, a controlled-spending agent can be added as a stretch.
- **Data track (Apify):** Apify is the data layer. We could also publish a reusable Actor (for example, material and brand-fact extraction from listings).
- **Planet track:** the goal is longer garment life. We make it visible and comparable, without claims we cannot back up.
- **Questions to ask sponsors on Friday:** How many tracks can one project enter? Can we get Apify credits for about 50,000 records? Are there marketplace tools they recommend or warn against? Is there any sandbox access for a spending-limits stretch?

---

## 16. Workstreams

| Workstream | Owns | Owner |
|---|---|---|
| **Data collection and cleaning** | Collectors, cleaning, extraction, the Catalog (`backend/pipeline`, `backend/database`) | Andy |
| **Evidence and ranking** | Brand table, product lines, wear baselines, markers, cost per wear, Value Ranker | Anthony |
| **Matching** | Garment Finder, Look Matcher (`backend/ml`) | Anthony (with Andy) |
| **API contract** | `schema/`: any change needs a huddle | Anthony + Tristan |
| **Web experience** | Camera, results, sorts, slider, receipts, animation (`web/`) | Tristan |
| **Story and demo** | Pitch, props, video, submission write-up, sanity-check examples | Haram |

Work in separate areas. Build the website against sample data in the schema's shape from the start.

---

## 17. Decisions

### Made
- [x] Markets: Depop, Poshmark, Grailed, eBay. Any listing priced in USD counts, wherever it ships from (Mercari was tried and dropped: no description, one photo).
- [x] 8 categories and ~40 curated brands.
- [x] Three markers (cost, quality, eco) + cost per wear. Eco is facts, not a grade.
- [x] v1 evidence = materials, product lines, brand facts. Reviews and community are stretch.
- [x] Resale is not in v1.
- [x] "What you have" comparison is stretch.
- [x] Secondhand only in v1.
- [x] API contract: `schema/api.schema.json` (FastAPI backend, Python 3.12).

### Open
- [ ] Product name.
- [ ] Expected-wear baselines per category and their labeled assumptions: Anthony, in `backend/ml/wear_baselines.yaml`.
- [ ] Mocks strategy and receipt image gallery: Tristan (`schema/API.md` §5).
- [ ] Whether a spending-limits agent is in scope for the Visa track.

---

## 18. Sources behind the key claims

- Steph Ango, *Buy wisely* — https://stephango.com/buy-wisely
- WRAP and University of Leeds t-shirt durability study (price is not a reliable guide) — https://ahc.leeds.ac.uk/media/news/article/2952/new-research-shows-price-is-not-a-reliable-guide-to-t-shirt-durability
- WRAP: nine extra months of use cuts footprints by about 20–30% — https://sustainablebrands.com/read/behavior-change/trending-while-wrap-scottish-designers-tout-merits-of-durable-fashion-mango-has-a-different-idea
- Yale study on secondhand and overconsumption — https://news.yale.edu/2025/12/08/second-thoughts-secondhand-why-resale-market-expanding-fashions-carbon-footprint
- EU test of fiber labels (37% inaccurate) — https://www.eureporter.co/business/consumers-2/2026/06/22/inaccurate-clothing-labels-a-systemic-issue-eu-testing-finds/
- Lower-priced goods retain more of their price in resale (why resale must compare within price bands) — https://proceedings.emac-online.org/pdfs/A2025-125270.pdf
- Resale price falls faster than measured jacket performance (price tracks looks) — https://xreiss.efri.uniri.hr/article.php?id=23529
- Review-based quality and durability analysis for fashion goods — https://www.climatechange.ai/blog/2024-01-27-absa-article
