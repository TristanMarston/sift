# Backend requests from the web app (Oct 24, evening)

For Anthony and his coding agent, from Tristan (web). The item panel ("Why it's $0.55 a wear") now explains where
the eco score and the expected wears come from. It already works without these fields. With them it shows exact
numbers instead of an approximation. Both are **additive and optional**: the web types already accept them
(`web/lib/search.ts`), and `web/lib/explain.ts` switches to them as soon as they appear. No web change needed.

## 1. `eco.parts` and `fact.part` (most needed)

The panel shows the four parts of the eco score with a bar each. Today it hard-codes the weights from `schema/API.md`
and guesses which facts belong to which part from `fact.kind`. That copy will drift the next time the formula changes.

```json
"eco": {
  "level": "medium", "score": 0.62, "percentile": 61,
  "parts": [
    {"key": "fibers",      "label": "Fabric",              "weight": 0.35, "score": 0.5},
    {"key": "durability",  "label": "How long it lasts",   "weight": 0.30, "score": 0.5},
    {"key": "shipping",    "label": "Where it ships from", "weight": 0.15, "score": 1.0},
    {"key": "circularity", "label": "Second life",         "weight": 0.20, "score": 0.0}
  ],
  "facts": [
    {"kind": "secondhand",     "part": null,     "...": "..."},
    {"kind": "fabric_unknown", "part": "fibers", "...": "..."}
  ]
}
```

Rules:
- `key` is one of `fibers`, `durability`, `shipping`, `circularity`, in that order (the order the panel shows).
- `weight` is the weight from `ECO_WEIGHTS`. `score` is the 0–1 value that goes into the formula in `markers.eco()`:
  natural share, durability, shipping, and `min(1, circularity / 2)`.
- `sum(weight × score)` equals `eco.score` (within rounding).
- Every eco fact gets `part`: the key of the part it feeds, or `null` for facts that feed none (`secondhand`).
- `label` is short and in sentence case. Copy rules apply: no em dashes, no exclamation marks, no virtue words.

Suggested tests (red/green): the weights sum to 1; `sum(weight × score)` matches `score`; every eco fact has a `part`
key; `secondhand` has `part: null`.

## 2. `wear.steps` (nice to have)

Under the arithmetic, the panel says how the expected wears were reached. Today it can only show the baseline text,
which way quality moves it, and the condition text, without the multipliers.

```json
"wear": {
  "expected_wears": {"low": 80, "mid": 120, "high": 200},
  "steps": [
    {"label": "Typical for jackets & outerwear", "value": "100 wears"},
    {"label": "High quality", "value": "× 1.5"},
    {"label": "Good condition", "value": "× 0.8"}
  ]
}
```

Rules:
- In order: the category's typical wears (`baseline.mid`, or the middle of low and high), then `QUALITY_MULT[level]`,
  then `CONDITION[condition]` (a missing condition says "Condition not stated").
- The product rounds to `expected_wears.mid`.
- Short strings. The web app shows `label` and `value` as written.

## 3. Already done, thanks

- `eco.percentile` is live. The web app shows "Greener than N% of these matches" only when it's a number. The saved
  samples and the landing wall don't have it, which is fine.

## 4. One copy fix made on the web side

`results-screen.tsx` said "Nothing close — 50 similar jackets". It now says "No close match: 50 similar jackets"
(no em dashes). Please follow the copy rules for any text the server writes too.

## When it ships

Add both fields to `schema/api.schema.json` and `schema/API.md`, redeploy, and tell Tristan. To check: open any item;
each eco part gets a bar, and "How we got N wears" shows the multipliers.
