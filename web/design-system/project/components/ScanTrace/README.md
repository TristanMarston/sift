# ScanTrace

The signature moment: a scan line while the photo is read, then a white line traces each garment, the rest of the photo dims and labels spring out.

Phases: `scanning` (scan line, "Finding garments…"), `tracing` (outlines draw top to bottom, then the lift and labels), `done` (labels and garment shapes are tappable; tapping an empty spot reports a missed garment with a ripple). Without an outline the trace follows the garment's box.

**You provide:** `garments` (each with `bbox` and `outline` as fractions of the photo), `phase`, the photo (`photo` URL or children), optional `selectedId`, `onSelect`, `onTapEmpty`, `onTraced`, `aspect` (default 3:4).

- Do: ask the backend for an outline per garment (40 to 120 points).
- Do: keep the photo between dark bands so nothing covers it.
