# MicButton

Push-to-talk button: hold to speak, release to send.

It responds on press, scales up while listening and sends soft rings outward. Space or Enter works the same way. A press under about 250ms is a tap: show "Hold to talk".

**You provide:** `state` (`idle`, `listening`, `processing`), `onPressStart`, `onPressEnd(heldMs)`.

- Do: keep it centered in the `BottomDock`.
- Don't: start recording on tap or toggle it on and off; the hall is noisy.
