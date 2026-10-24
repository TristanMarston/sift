# BottomDock

The floating bar on results: Scan tag, the hold-to-talk mic, and Update after the first like.

Frosted (`bg-card/85`, blur) because content scrolls under it. Leave `space-12` under the last card so it never covers content.

**You provide:** `likedCount`, `micState`, `onScanTag`, `onMicStart`, `onMicEnd(heldMs)`, `onUpdate`.
