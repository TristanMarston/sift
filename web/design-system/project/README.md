Sift finds look-alikes for the clothes you photograph, new and secondhand, and ranks them by cost per wear instead of price: the price divided by how many times you'll likely wear it. Every number comes with the evidence behind it. Secondhand is one of the best ways to lower cost per wear, so used listings sit right alongside new ones. The interface feels warm, soft and honest, with the calm of Apple Camera and Visual Look Up. Motion carries the experience: every reveal, reorder and number change animates. The garment tracing and the sort flip (price to cost per wear, cards reshuffling) are the moments people remember.

The demo runs on an iPhone in Safari and is often mirrored to a laptop, so everything is sized to read at arm's length. It works on desktop too.

## Content fundamentals

Write plain, warm and short. The product speaks; the user's things are "your" things ("Your shirt", "Your picks").

- **Sentence case everywhere**: buttons, headings, chips, tabs. "Scan an outfit", never "Scan An Outfit".
- **No em dashes.** Use a period, a comma or a middle dot (`·`). "Chore coat · navy".
- **No "It's not X, it's Y" lines** and no slogans built on contrast. Say what it does.
- **No exclamation marks**, no "please", "simply" or "just".
- **Sell the idea, then the product.** Lead with cost per wear ("Buy it once."), not with Sift. The product shows up in the actions.
- **Never claim virtue.** Banned: "eco-friendly", "sustainable", "green", "guilt-free", "planet-positive". Longer wear is why cost per wear matters, so the environmental side is welcome, but only as a specific, sourced fact ("Wearing clothes 9 months longer cuts their carbon, water and waste footprint by about 20–30%. WRAP") or a count ("Tees bought · 6 vs 1"). Never the headline, never leaves or green.
- **Cost per wear is always an estimate.** Show it with an `EstTag` and the wear count it assumes ("÷ 150 wears", "150 wears · est."). Expected wears are ranges; when there's room, show the range.
- **Label durability by evidence, never by price.** Price alone doesn't predict how long clothes last. Say "Pills after ~25 wears", not "Cheap tee".
- **Every claim shows where it came from**, with a `StatusBadge`: **Verified** (read from the tag or a certification), **Claimed** (the seller's text), **Unknown**. Unknown is shown, never hidden.
- **Every estimate carries an `EstTag`.** Footprints use kg of CO₂ and liters of water. No "that's like X days of drinking water" comparisons unless a source backs them.
- **Errors say what happened, then what to do**, and always offer a button: "Couldn't read this tag. Get closer and fill the frame." [Retake] [Type it in]. Never retake or retry automatically.
- **Ellipsis only for work in progress**: "Finding garments…", "Listening…".

| Do | Don't |
| --- | --- |
| An expensive shirt you wear every day is worth more than a cheap one you wear twice. | It's not just shopping, it's a movement! |
| $0.27 a wear EST. · 150 wears | Only 27¢ per wear! |
| The cheapest match drops to #4 | Cheap clothes are a scam |
| 100% organic cotton · Verified | Eco-friendly fabric |
| 4.1 kg CO₂ saved EST. | Saves the planet |
| No exact match. This one might be one of a kind. | Oops! Nothing found. |
| Chore coat · navy | Chore Coat — Navy |

Numbers: prices in whole dollars (`$48`, cents only when present: `$48.50`); cost per wear in dollars and cents, never a ¢ sign (`$0.27`, "a wear" in prose, `/wear` in data); counts with commas (`18,432`); estimates rounded to two meaningful digits (`4.1`, `2.0`, `2,700`); times to one decimal (`1.2s`). Numbers sit in `type-data` or `type-numeral` with tabular figures.

The full copy library is in the Wording section.

## Color

- **Light is the default.** Dark mode is a manual toggle (`ThemeToggle`) that sets `.dark` or `data-theme="dark"` on `<html>`. The phone's system setting is ignored, so a teammate's phone can't flip the demo.
- **The landing sits on the cobalt `stage`** in both themes, with `stage-foreground` text (secondary text at 85% or more so it stays above 4.5:1) and a white `stage` button for Scan. It's the one place cobalt fills a screen. The theme toggle is hidden there.
- **Camera screens are always dark** in both themes. They use only `camera`, `camera-foreground`, `camera-muted`, `camera-control`, `camera-scrim`, `trace-line` and `trace-halo`.
- **Neutrals carry the page.** `background` is the canvas, `card` holds content, `foreground` is text, `muted-foreground` is supporting text. The greys are cool so listing photos keep their true color.
- **Cobalt (`primary`) means "confirmed" or "do this next".** Use it for the one filled main action on a screen, `primary-tint` with `primary-tint-foreground` for selected chips and New tags, the `verified` dot, the moved-up marker and the focus `ring`. Never decorate with it.
- **No green.** Color shows how strong the evidence is, never how virtuous something is. No leaf icons, kraft textures or earthy "eco" palettes.
- **Fiber bars** use `fiber-plant` (wheat), `fiber-animal` (clay), `fiber-regenerated` (lilac) and `fiber-synthetic` (slate). Synthetic is slate, never red: the plain-language line carries the fact. Every segment is labeled, so color is never the only signal. Unaccounted share uses the `hatch` pattern.
- **`destructive` is for errors only**: a blocked camera, an unreadable tag. A garment difference is a grey ✗ chip, not red.
- **Receipts** sit on `receipt-paper` with `receipt-ink`, a hair warmer than `card` so they read as paper.

Contrast is checked in both themes. Text pairs are 4.5:1 or better (`foreground` 12.8:1+, `muted-foreground` 5.5:1+ light and 5.9:1+ dark, `primary-foreground` on `primary` 6.1:1+, `primary-tint-foreground` on `primary-tint` 8.2:1+). Marks and borders that carry meaning are 3:1 or better (`input`, `unknown`, every fiber color on `card`). The focus ring is a solid 2px `ring` with a 2px offset, 4.3:1 or better on every surface.

## Typography

Three families, each with one job.

- **Fraunces** (serif, `--font-serif`): big moments only. The intro headline, garment names, section headings, the one big number on a screen. Optical sizing is on, so large sizes get finer detail.
- **Figtree** (sans, `--font-sans`): all interface text. Body copy is 17px, like iOS.
- **DM Mono** (`--font-mono`): data. Meta lines, timers, counts, receipts. Always tabular figures (`tabular`).

| Style | Family | Size / leading | Use |
| --- | --- | --- | --- |
| `type-display` | Fraunces | 44 / 46, -0.02em | Intro headline. One per screen. |
| `type-title-1` | Fraunces | 34 / 38, -0.015em | Garment name, tag result header. |
| `type-title-2` | Fraunces | 26 / 30, -0.01em | Section headings, empty-state headlines. |
| `type-numeral` | Fraunces | 64 / 60, -0.03em | The one big number: "50%", "2.1". |
| `type-quote` | Fraunces italic | 19 / 26 | The Learned line and the spoken transcript. |
| `type-wordmark` | Fraunces 500 | 28 / 28 | "Sift" in the top bar. Plain type, no logo yet. |
| `type-headline` | Figtree 600 | 17 / 22 | Card and sheet titles. |
| `type-body` | Figtree | 17 / 24 | Body copy. |
| `type-button` | Figtree 600 | 16 / 20 | Button labels. |
| `type-callout` | Figtree 500 | 15 / 20 | Chips, tabs, secondary lines. |
| `type-footnote` | Figtree | 13 / 18 | Captions, badge words, helper text. |
| `type-data` | DM Mono | 13 / 18 | `DEPOP · SIZE M · GOOD`, timers. |
| `type-receipt` | DM Mono | 13 / 20 | Receipt lines. |
| `type-label` | DM Mono 500 | 11 / 14, +0.08em | Uppercase micro labels: `EST.`, `NEW`. The only text under 13px. |
| `type-counter` | DM Mono 500 | 28 / 32 | The live search count. |

Tracking tightens as size grows and opens slightly below 14px. Uppercase is for mono meta lines and receipt labels only. Sizes are in rem in the app so they scale with the user's text size.

## Spacing and layout

- A 4px grid (`space-1` to `space-12`). Phone side gutter is `space-4` (16px); sections are `space-6` apart.
- **Mobile first.** Camera, tag and receipt screens are one centered column (max 448px). Results widen to a 2 or 3 column grid on desktop; nothing else changes.
- **Camera layout copies a phone camera**: a 3:4 photo between dark bands, with controls and the search counter in the bands, so nothing covers the photo.
- Touch targets are 44px or larger. Respect `env(safe-area-inset-*)` at the top and bottom.
- Leave `space-12` under the last card so the floating `BottomDock` never covers content.

## Shape

Apple-style rounding. `radius-image` (14px) for listing photos and garment cut-outs, `radius-card` (20px) for cards, the dock and the counter panel, `radius-sheet` (28px) for the top corners of sheets, `radius-pill` for buttons, chips, tabs and badges, `radius-tag` (6px) for `EST.` and `NEW`. Data panels (receipts, fiber legends) use thin `border` rules and dashed lines instead of boxes. Receipts get a torn zigzag edge (`receipt-edge`, `receipt-edge-bottom`).

## Depth and materials

- `shadow-card` for resting cards, `shadow-float` for floating controls (dock, sheets, counter), `shadow-lift` for a garment cut-out in flight. Dark mode trades shadows for a faint edge.
- **Frosted glass only on floating controls over moving content**: the dock, the top bar while scrolling, camera buttons, the counter panel. Keep it subtle (`bg-card/85 backdrop-blur-xl`). No Liquid Glass refraction, no glossy highlights, no glass on glass. With Reduce Transparency on, surfaces go solid.

## Imagery

Listing photos are 4:5, `radius-image`, with a faint inner ring so white photos don't melt into white cards. Garments detected in the user's photo appear as cut-outs along their outline (`GarmentCutout`). No stock photos and no decorative illustration. The sample outfit and garment art in previews stand in for real photos.

## Iconography

[Lucide](https://lucide.dev) at a 1.75 stroke, 20px by default (16px in small buttons). Icons inside `Button` use `data-icon="inline-start"` or `"inline-end"` and no size classes. No emoji. No leaf, globe or recycling symbols. Status uses shapes (solid, half, hollow dots), not icons.

## Motion

Motion is the most important part of Sift's feel. It follows Apple's fluid-interface rules:

- **Respond on press**, not release. Buttons scale to 0.97 on pointer down.
- **Springs, not timed curves**, for anything that moves. Default `spring.ui` (no bounce, 0.4s). Bounce only when a tap or gesture gave the motion energy (`spring.pop` for the heart, `spring.label` for garment labels, `spring.sheet` for sheets).
- **Everything can be interrupted** and starts from where it is on screen.
- **Enter and leave along the same path.** A sheet that rises from the dock goes back into it.
- **Animate only transform and opacity** (plus the trace's stroke). `layout` animations move cards when the list re-ranks; cards never just reload.
- **Loading is a gentle fade**, never a spinner: content breathes between full and half opacity (`animate-pulse`, 2s). Reading a photo shows the scan line.
- **Reduce Motion** turns movement into fades (`MotionConfig reducedMotion="user"`), stops the breathing and skips the theme-toggle circle.

| Spring | Bounce / duration | Use |
| --- | --- | --- |
| `spring.ui` | 0 / 0.4s | Default: moves, reorders, morphs |
| `spring.snappy` | 0 / 0.25s | Presses, toggles, count changes |
| `spring.sheet` | 0.15 / 0.35s | Sheets and the dock |
| `spring.pop` | 0.3 / 0.45s | The heart, the NEW tag |
| `spring.label` | 0.15 / 0.45s | Garment labels springing out |

The step-by-step choreography for each signature moment is in the Motion section.

## Accessibility

AA contrast in both themes, 44px targets, color never the only signal (every status has a shape and a word), a visible focus ring, Reduce Motion and Reduce Transparency respected, and text that scales.

## Building with Sift

- In the app, import components from `@/components/sift/*` and `@/components/ui/*`. Token values live in `tokens.json`; the app's CSS is generated from it with `npm run tokens`, so edit the JSON, never the CSS.
- On this page every component is live on `window.Sift` (for example `Sift.MatchCard`). `Sift.samples` holds the sample data the previews use. Sample prices and footprints are illustrative, never real figures.
- Use semantic utilities (`bg-card`, `text-muted-foreground`) and the `type-*` styles. Never raw hex values or manual `dark:` overrides.
