# MatchCard

One resale listing: photo, heart, title, price, meta line, reason chips and an optional receipt summary.

`large` for Exact match (one column), `compact` for the Similar style grid. Cards use `layout`, so they glide to new places when the list re-ranks. After Update, `moved` shows a cobalt ▲ that fades on its own and `isNew` shows a NEW tag. `MatchCardSkeleton` breathes while results load.

**You provide:** `match` (`{listing, score, band, reasons, receipt?}`), `size`, `liked`, `onLike`, optional `moved` and `isNew`.

- Do: wrap lists in a `LayoutGroup` so reorders animate.
- Don't: reload the list without animation.
