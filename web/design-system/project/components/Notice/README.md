# Notice

Empty, no-match and error states. Say what happened, then what to do.

`neutral` for empty and no-match, `error` for failures (uses `destructive`), `surface="camera"` on the dark scanner. Every error offers a way forward.

**You provide:** `icon` (a Lucide icon object), `title`, `body`, optional `tone`, `surface`, `actions` (buttons).

- Do: "Couldn't read this tag" with Retake and Type it in.
- Don't: retry on your own, or write "Oops".
