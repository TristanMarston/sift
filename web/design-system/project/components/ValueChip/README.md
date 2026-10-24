# ValueChip

A value or filter the user switches on and off.

Selected chips use `primary-tint` with a check. Chips that came from speech show a small mic mark and can fly in from the transcript (`layoutId`).

**You provide:** `label`, `selected`, `onToggle`, optional `fromVoice` and `layoutId`.

- Do: use the five values: Natural fibers, Low carbon, Low toxins, Small seller, a max price.
- Don't: invent values the parser can't produce, or use leaf icons.
