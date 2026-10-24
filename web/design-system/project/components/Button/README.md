# Button

Pill button with a 44px touch target that presses in on touch.

Use `default` (cobalt) for the one main action on a screen, `secondary` for everything else, `outline` for a quiet alternative, `ghost` in bars, `link` for small text actions and `camera` on the dark camera screens.

**You provide:** children (the label, sentence case, verb first), `variant`, `size` (`sm` 36px, `default` 44px, `lg` 52px and wraps for long labels, `icon`, `icon-sm`), `onClick`. Icons go inside with `data-icon="inline-start"` or `"inline-end"`.

- Do: one cobalt button per screen. "Scan an outfit", "Retake", "Type it in".
- Don't: two cobalt buttons side by side, "Submit", "OK", or "Click here".
- Don't disable buttons to block progress; keep them live and explain on tap.
