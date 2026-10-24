# ImpactReceipt

A thermal-receipt comparison: your garment and this pick, line by line.

One receipt with two columns, so it stays readable on a phone. Rows: item, price, materials, CO₂ (made vs saved), water, then one row per value with its status. Estimates carry `EST.` The bottom edge is torn.

**You provide:** `yours` and `pick` (`{title, source, price?, priceNote?, materials, co2, water, badges}`), optional `stamp` ("OCT 25 · 10:42").

- Do: show "Owned" as your garment's price.
- Don't: show dollars saved unless the retail price is known.
