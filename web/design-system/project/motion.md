# Motion

Every moment below is built into the components. Timings live in `lib/motion.ts` (`spring`, `ease`, `trace`), so changing a value there changes it everywhere.

## 1. Scan and trace (the signature moment)

`ScanTrace` runs in three phases. It is the moment judges remember, so it gets the most care.

1. **Shutter** (0ms). The `Shutter` disc presses in on pointer down (`spring.snappy`) and the frame freezes.
2. **Scan line** (while `/scan` runs, usually 1 to 3s). The photo dims and breathes gently. A soft light band (`scan-glow`) sweeps top to bottom every 1.8s with a short pause. "Finding garments…" sits under the photo.
3. **Trace** (when garments arrive). A 2px `trace-line` with a 5px `trace-halo` underneath draws around each garment's outline in 0.7s (`ease.trace`). Garments go top to bottom, 0.15s apart. The halo keeps the line visible on white clothes.
4. **Lift.** As the last outline closes, everything outside the garments dims (`camera-scrim`, 0.4s), so the clothes stand forward like Visual Look Up.
5. **Labels.** 0.1s after its outline closes, each garment's dot pops in and a white pill springs out of it (`spring.label`, a small bounce). Pills grow toward the side with more room and shorten with an ellipsis instead of clipping.
6. **Tap.** Labels and garment shapes are tappable. Tapping an empty spot shows a ring rippling out from the finger and reports the point, for a garment the scan missed.

Without an outline from the backend, the trace falls back to the garment's box.

## 2. Live search counter

`SearchCounter` rises from the bottom band (`spring.sheet`) right after the labels land. The count rolls up to the real index size in 1.1s, marketplace names light up one by one every 0.22s, and the timer shows real elapsed time until the search returns, then freezes ("Searched · 1.2s").

## 3. Camera to results

Built with the flow (not a standalone component). The selected garment's cut-out lifts (`shadow-lift`) and flies into its `GarmentTabs` slot while the screen cross-fades from `camera` to `background` (0.4s). Cards rise in 40ms apart. The camera screen and results are one continuous screen so shared elements can move between them.

## 4. Like, Update, reshuffle

- **Heart:** pops from 50% to full size with `spring.pop` and fills cobalt.
- **Update button:** slides into the dock on the first like (`spring.sheet`). Its count rolls (old number slides up, new one slides in).
- **Reshuffle:** on Update, cards glide to their new places (`layout`, `spring.ui`). Cards that moved up show a cobalt `▲ 2` that appears, holds and fades on its own in about 2.8s. New cards fade in with a `NEW` tag; dropped cards shrink slightly and fade.
- **Learned line:** "Learned: you like boxy fits and earth tones." The words arrive one at a time (60ms apart), each un-blurring as it fades in.

## 5. Voice to values

1. Holding the mic scales it up slightly and sends soft rings outward every 1.6s. The `VoiceSheet` rises from the dock with a waveform and "Listening…".
2. On release, the transcript appears word by word in `type-quote`. Phrases the parser understood get a `primary-tint` highlight.
3. Each highlight then flies down and becomes a `ValueChip` (shared `layoutId`), with a small mic mark showing it came from speech. The phrase stays underlined in the transcript.
4. The sheet sinks back into the dock and the list re-ranks (moment 4).

A quick tap (under 250ms) shows "Hold to talk" instead.

## 6. Tag reveal

The tag photo shrinks into a thumbnail at the top of the result sheet. The fiber bar fills one segment at a time (0.7s each, 0.35s apart). The footprint numbers count up over 1.2s. The plain-language line and the "Want this look with better materials?" button fade in last.

## 7. Theme toggle

The new theme grows out of the toggle button as a circle (View Transitions, 0.5s). The sun and moon icons swap with a quarter turn. With Reduce Motion on, the theme changes instantly.

## 8. Small things

- Buttons scale to 0.97 on press (100ms). Chips and the heart use `whileTap` springs.
- Sheets rise from the control that opened them and leave the same way.
- Nothing slides in from a direction it can't go back to.

## 9. Loading

- Waiting for a photo read: the scan line.
- Waiting for a search: the live counter.
- Waiting for a re-rank: the current cards stay put and breathe (`animate-pulse`: opacity 1 to 0.5 and back over 2s), then glide to their new places.
- Waiting for results to first appear: `MatchCardSkeleton` blocks breathing the same way.
- After 8 seconds: "Taking longer than usual" with a Retry button.
- No spinners anywhere.

## Reduce Motion

| Moment | With Reduce Motion |
| --- | --- |
| Trace | Outlines still draw (no movement involved); labels fade in without scaling |
| Reshuffle | Cards swap places without gliding; new ones fade in |
| Chips from voice | Chips fade in place |
| Counter | Shows the final number |
| Breathing | Stops at 70% opacity |
| Theme toggle | Instant |
