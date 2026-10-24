# Sift - Project Description

*Working title. The repo may still be called `thrift-lens`. Rename freely.*

> **Purpose of this file:** the single source of truth for what we are building, why, and how the pieces fit together. It describes intent, goals, and concepts. It does not pick a tech stack. Read it before writing any code.

---

## 1. One-line pitch

**Take a photo of clothing you like. We find the best matches across new and secondhand markets, and rank them by cost per wear instead of price. Every result comes with a "Wear Receipt" that shows the evidence.**

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

**Our difference:** we search by photo, across new and secondhand, and rank using *evidence from real-world outcomes* (what owners say, what the resale market shows). We then show the evidence in a receipt, with sources and sample sizes.

---

## 4. The experience

1. **Open the website.** No sign-up, no typing. The camera is the front page.
2. **Take a photo** of a piece of clothing or a whole outfit. (Upload also works.)
3. **We find the garments** in the photo. For an outfit, each garment gets its own tab. The user can tap to pick one if detection struggles.
4. **We show look-alikes**, ranked by value for wear, from a large pre-collected catalog of new and secondhand items.
5. **Each result has a Wear Receipt**: what you get, what it costs per wear, and why we think so.
6. **The user can explore.** Switch between *Sort by price* and *Sort by cost per wear*. Slide between *closer match* and *better value*. Open any receipt to see sources.

**Signature moment:** the user flips the sort from price to cost per wear. The cards visibly reshuffle. The headline reads something like *"The cheapest match drops to #14."*

---

## 5. Key concepts (plain definitions)

- **Look match.** How visually close an item is to the user's photo. We only rank items that are close enough to be a real alternative.
- **Evidence.** Facts gathered from the real world about how an item or brand holds up. Each piece of evidence has a source and a sample size.
- **Quality score.** A summary of how strong the evidence is that an item will last, compared with similar items. It is a *summary of evidence*, not a lab test.
- **Confidence.** How much evidence sits behind a score. Low evidence gives low confidence, and we say so.
- **Expected wears.** A *range*, not a promise. Better evidence moves the range up. The team sets a baseline per garment type from public benchmarks and labels it as an assumption.
- **Cost per wear.** Price ÷ expected wears. Shown at a few wear counts (for example 30, 60, 100), so the user can pick the one that fits them.
- **Break-even wears.** How many times you must wear the pricier item for it to beat a cheaper one. This is the honest "buy less" message: *if you will not wear it that often, buy the cheaper or used one.*
- **Resale outlook.** What the item is likely to be worth after use. This lowers the *net* cost.
- **Wear Receipt.** The card that shows all of the above for one item.
- **Value rank.** The final ordering of results.

---

## 6. How the ranking works

Your plan has three indexes: **quality, price, resale**. We keep that, with these rules.

| Index | Question it answers | Evidence it uses | Priority |
|---|---|---|---|
| **Quality** | How long will this likely last? | Owner reviews, community discussion, maker guarantees, declared materials | **Core. Must work.** |
| **Price** | What does it cost me now? | Listed price (plus shipping if available) | **Core.** |
| **Resale** | What can I get back later? | Sold prices vs. original prices, speed of sale | **Last. Build only if time allows.** |

**How they combine, in words:**
1. Start with the look matches (the top set of close look-alikes).
2. Use the quality evidence to set an expected-wears range for each item.
3. Divide price by expected wears to get cost per wear. If resale is available, subtract the expected resale value from the price first.
4. Sort by cost per wear. The user's slider can shift weight toward closeness of match or toward price.

**Rules for the ranking:**
- It must be explainable. Anyone can open a receipt and see why an item ranked where it did.
- Never hide a component inside one opaque number.
- If we lack evidence, the item stays in the list but gets no boost. It is labeled *"Not enough evidence yet."* We do not guess.
- Two caveats on resale numbers. Cheap items look better when you measure "% of original price kept", so compare items **within a price band**. And resale price reflects looks and trends as much as durability, so it is a supporting clue, not the main score.

---

## 7. The Wear Receipt

One card per result. Example (illustrative numbers):

```
┌──────────────────────────────────────────────┐
│ Carhartt chore jacket · Poshmark · Size M    │
│ Look match: 91%                              │
├──────────────────────────────────────────────┤
│ PRICE                                $48.00  │
│                                              │
│ EVIDENCE                                     │
│  Owner reviews   4.6★ · 1,240 reviews        │
│                  3% mention wear-out issues  │
│                  (typical for category: 9%)  │
│  Community       38 mentions as long-lasting │
│  Maker support   Repair program offered      │
│  Materials       100% cotton, as declared    │
│                                              │
│ EXPECTED WEARS            120–200 (high conf)│
│ COST PER WEAR  @30 $1.60 · @60 $0.80 · @100 $0.48 │
│                                              │
│ VS. TYPICAL MATCH                            │
│  Typical match costs $0.95/wear at 40 wears  │
│  Break-even: wear this 51+ times to win      │
│                                              │
│ RESALE OUTLOOK (if built)    ~55% of price   │
│                                              │
│ CONFIDENCE  High · Sources ▸ · Date ▸        │
└──────────────────────────────────────────────┘
```

Every line is clickable for its source and sample size. Anything we could not verify is shown as *"unknown"*, not hidden.

---

## 8. Data

### 8.1 Two kinds of data

1. **The Catalog.** Many items from many markets. Each item has: photo, title, brand, garment type, size, condition (new or used), price, link, market name, and materials when the listing gives them.
2. **The Evidence Tables.** A much smaller set of facts, collected **per brand and garment type** (for example, "Carhartt jackets"). Each listing in the Catalog inherits the evidence for its brand and garment type.

**Why this split matters:** quality evidence is about *makers*, not individual listings. We only need evidence for about 100–200 brands across about 5 garment types. That keeps collection small, cheap, and doable in a day. The Catalog can be large, but the Evidence Tables are what make us different.

### 8.2 Where evidence comes from

| Source | What we learn | Main limits |
|---|---|---|
| **Customer reviews on retail sites** | Rating, review count, and how many reviews praise or complain about lasting power (fading, pilling, shrinking, seams failing, holes). An AI reads review text and counts these. | New items only. Coverage differs by retailer. Reviews are mostly written early, so slow wear-out is under-reported. |
| **Community discussion** (for example "buy it for life" forums) | Which brands people say last for years, and which disappoint | Popular brands only. Opinions are noisy. |
| **Resale markets** *(last priority)* | How much value items keep, and how fast they sell | Only items that survived are listed. Price reflects looks and trends too. |
| **Maker promises** | Lifetime guarantees, repair programs | A guarantee often excludes normal wear. Treat as a modest signal. |
| **Declared materials** (fiber, and fabric weight when published) | Facts to display | Research shows a weak link to lasting power. Labels are also wrong often (an EU test found 37% mislabeled). Show it, give it little weight. |

**What we do not use as a quality signal:** price alone. Research shows it does not predict durability.

### 8.3 Scale
- **Catalog:** tens of thousands of items is plenty (about 20,000–50,000). Variety across garment types matters more than raw size. More items add cost and blocking risk without improving the demo.
- **Evidence Tables:** about 100–200 brands × about 5 garment types.
- **Budget:** typical collection tools cost about $1.50–$9 per 1,000 records. Expect roughly $100–$400 total. We will ask the sponsor for event credits.

### 8.4 Timing
- **Friday evening:** small test collection from every planned source. Go or no-go on which sources are reliable.
- **Friday night to Saturday morning:** full collection. This leaves Saturday to build evidence tables, tune, and fix gaps.
- **Saturday evening:** optional refresh. Keep a **backup snapshot** in case a source is blocked later.
- **Demo day:** **never collect live.** All searches use the pre-built data.

### 8.5 Data rules
- Public data only. No seller or reviewer personal information is stored.
- Record the source and the collection date for every fact.
- Some markets restrict automated access in their terms. We note this in our trust section and use only public listing data.
- Include the demo props (specific clothes we will scan) in the catalog so the first scan is guaranteed to hit.

---

## 9. System overview (conceptual)

```
 COLLECT              CLEAN & ORGANIZE          BUILD EVIDENCE
 ───────              ───────────────           ──────────────
 Market listings  ─┐   Standardize brand,        Read reviews → count
 Retail reviews   ─┼─▶ garment type, price,  ─▶  durability praise/complaints
 Community posts  ─┤   size, condition.          Summarize community opinion
 Resale sales     ─┘   Remove duplicates.        Compute resale stats (last)
                                │                       │
                                ▼                       ▼
                        ┌──────────────┐        ┌────────────────┐
                        │   CATALOG    │        │ EVIDENCE TABLES│
                        │ (items, photos)      │ (brand × type) │
                        └──────┬───────┘        └────────┬───────┘
                               │                         │
   USER PHOTO ─▶ FIND GARMENTS ─▶ LOOK MATCHER ─▶ VALUE RANKER ◀┘
                                   (close look-alikes)  (cost per wear, receipt data)
                                                 │
                                                 ▼
                                      WEBSITE: results + Wear Receipts
```

### The parts

1. **Collectors.** Gather listings, reviews, community posts, and sale records on a schedule we control. This is where Apify is the core of the product.
2. **Cleaner.** Makes data from different markets comparable: same brand names, garment types, currencies, and size formats. Removes junk and duplicates. Brand names are messy, and this step decides how much of the catalog can use evidence.
3. **Evidence Builder.** Turns raw reviews and posts into the Evidence Tables. It counts and summarizes. It does not invent.
4. **Catalog.** The searchable collection of items. It must answer: "what looks like this photo?" with optional filters (size, max price, market).
5. **Garment Finder.** Finds each garment in the user's photo and crops it.
6. **Look Matcher.** Returns the closest look-alike items from the Catalog.
7. **Value Ranker.** Looks up evidence for each match, estimates expected wears and cost per wear, and produces the ordered list plus all the fields needed for each receipt.
8. **Website.** Camera, results, sort and slider controls, receipts, the reshuffle animation.

### One agreement the whole team keeps
The Value Ranker returns **the same shape of data for every item**: item facts, scores, receipt lines (each with a source, sample size, and date), and a confidence level. The website is built first against **sample data in that shape**, so it never waits on the backend. Changing that shape requires a quick team huddle.

---

## 10. Trust and honesty rules

These are product features, not extras. They support the trust criteria of our sponsor tracks.

1. **No fake precision.** We never present a score as a lab measurement. We say "evidence suggests."
2. **Show the work.** Every receipt line has a source, a sample size, and a date.
3. **"Not enough evidence" is a valid answer.** We show it clearly.
4. **Ranges, not promises.** Expected wears are ranges. Cost per wear is shown at several wear counts.
5. **Break-even honesty.** If a cheaper option wins for the user's likely use, we say so.
6. **No eco-grade.** We do not claim an item is "sustainable". We make one claim: how long it is likely to stay in use.
7. **Privacy.** No personal data about sellers or reviewers. No accounts. Photos are used for the search.

---

## 11. Scope

### Must work (the golden path)
- Photo in → garments found → look-alikes from several markets → ranked by cost per wear → Wear Receipt on each.
- Evidence from reviews and community sources for the demo brands and garment types.
- Sort toggle (price ↔ cost per wear) with the reshuffle animation.
- "Not enough evidence" state.
- Break-even line.

### Should work if time allows
- Resale outlook (price-band-adjusted).
- "Closer match ↔ better value" slider.
- Optional "what you have" input (brand and price) to compare the item in the photo with the alternatives.

### Later or stretch
- Watch a look and alert when a better cost-per-wear item appears.
- A photo of the clothing tag to confirm brand and materials.
- Spending limits for a buying agent and real checkout.
- "What is my own item worth?" selling flow.
- A wear log for real user retention data.

### Not doing
- Lab claims or testing.
- A predicted wear count for an individual person.
- A sustainability or eco score.
- Collecting data during the demo.

---

## 12. Demo plan (about 2 minutes)

| Time | Beat |
|---|---|
| 0:00–0:15 | **Hook.** "Every shopping agent sorts by price. Watch what happens when you sort by cost per wear." |
| 0:15–0:45 | **Teammate scan.** A prop jacket. Results appear in seconds. Open one Wear Receipt and show the evidence lines. |
| 0:45–1:10 | **The flip.** Toggle price → cost per wear. Cards reshuffle. "The cheapest drops to #14." Show the break-even line. |
| 1:10–1:40 | **"Now you."** Scan a judge's clothing. Show a receipt for a look-alike of their piece. If we have thin evidence, show *"Not enough evidence yet"* and explain why that is a feature. |
| 1:40–2:00 | **How it is built and why it matters.** Large multi-market catalog collected with Apify, evidence from real owners, a transparent receipt. Cost-per-wear framing and longer garment life as the impact. |

**Demo preparation:**
- 2–3 props with strong evidence, already in the catalog.
- Clip light and white board for the table (lighting will be bad).
- Phone hotspot (venue wifi will be slow).
- Cached results for the props, an upload fallback if the camera fails, and a backup demo video.

---

## 13. What "done" looks like

- A scan returns ranked results in about 5 seconds on pre-built data.
- Every result has a complete receipt with real sources, or an honest "unknown" label.
- Sanity checks pass: within the same garment type, makers widely seen as durable generally rank above makers widely seen as disposable.
- Evidence exists for every brand in the demo.
- The sort flip works smoothly on a phone and a laptop.
- Nothing in the product claims more than the evidence supports.

---

## 14. Risks and fallbacks

| Risk | Fallback |
|---|---|
| A market blocks collection | Use a second tool for that market. Collect early and keep a backup snapshot. |
| Review sources are thin for some brands | Show "Not enough evidence". Focus evidence work on demo brands and garment types first. |
| Brand names are messy in listings | Invest early in the Cleaner. Group by brand and garment type, not exact titles. |
| Quality evidence feels subjective | Show raw counts and sources. Use only evidence we can trace. |
| Quality-first only surfaces expensive items | Show break-even wears. Keep the match-closeness gate. Compare against the "typical match", not against an ideal. |
| Venue wifi is slow | Small cached index, cached prop results, phone hotspot. |
| Camera fails | Upload fallback. |
| Resale numbers look too good for cheap items | Compare within price bands. If unsure, leave resale out. |

---

## 15. Event context and tracks

- **Event:** Cal Hacks 13.0 · Fri Oct 23 – Sun Oct 25, 2026 · Palace of Fine Arts, San Francisco.
- **Key times:** Hacking starts about 6 PM Friday. **Submission is due 9 AM Sunday.** Judging is 10:30 AM–12:30 PM Sunday, and the whole team must be at the table. All work must start during the event.
- **Primary track, Reimagining Shopping (Visa):** shopping that optimizes value over time instead of the lowest price. The Wear Receipt gives users transparency and trust. If the sponsor offers access, a controlled-spending agent can be added as a stretch.
- **Data track (Apify):** Apify is the data layer. We could also publish a reusable Actor (for example, brand durability evidence from reviews).
- **Planet track:** the goal is longer garment life. We make it visible and comparable, without claims we cannot back up.
- **Questions to ask sponsors on Friday:** How many tracks can one project enter? Can we get Apify credits for about 50,000 records? Are there marketplace tools they recommend or warn against? Is there any sandbox access for a spending-limits stretch?

---

## 16. Workstreams (suggested)

| Workstream | Owns | Suggested owner |
|---|---|---|
| **Data collection and cleaning** | Collectors, cleaning, the Catalog | Andy |
| **Evidence and ranking** | Evidence Builder, expected wears, cost per wear, Value Ranker | Anthony |
| **Matching** | Garment Finder, Look Matcher | Anthony (with Andy) |
| **Web experience** | Camera, results, receipts, sort flip, animation | Tristan |
| **Story and demo** | Pitch, props, video, submission write-up, sanity-check examples | Haram |

Work in separate areas. Agree on the data shape first (section 9). Build the website against sample data from the start.

---

## 17. Open decisions

- [ ] Product name.
- [ ] Which 5 garment types to cover, and which 100–200 brands.
- [ ] Which markets and sources pass the Friday test.
- [ ] Baseline expected wears per garment type, and the assumptions we label.
- [ ] Whether resale makes it into the first version.
- [ ] Whether we include the optional "what you have" comparison.
- [ ] Whether a spending-limits agent is in scope for the Visa track.

---

## 18. Sources behind the key claims

- Steph Ango, *Buy wisely* — https://stephango.com/buy-wisely
- WRAP and University of Leeds t-shirt durability study (price is not a reliable guide) — https://ahc.leeds.ac.uk/media/news/article/2952/new-research-shows-price-is-not-a-reliable-guide-to-t-shirt-durability
- WRAP: nine extra months of use cuts footprints by about 20–30% — https://sustainablebrands.com/read/behavior-change/trending-while-wrap-scottish-designers-tout-merits-of-durable-fashion-mango-has-a-different-idea
- Yale study on secondhand and overconsumption — https://news.yale.edu/2025/12/08/second-thoughts-secondhand-why-resale-market-expanding-fashions-carbon-footprint
- EU test of fiber labels (37% inaccurate) — https://www.eureporter.co/business/consumers-2/2026/06/22/inaccurate-clothing-labels-a-systemic-issue-eu-testing-finds/
- Lower-priced goods retain more of their price in resale (why we compare within price bands) — https://proceedings.emac-online.org/pdfs/A2025-125270.pdf
- Resale price falls faster than measured jacket performance (price tracks looks) — https://xreiss.efri.uniri.hr/article.php?id=23529
- Review-based quality and durability analysis for fashion goods — https://www.climatechange.ai/blog/2024-01-27-absa-article
