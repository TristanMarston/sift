# Screens and flow

The demo is one continuous screen at `/` that changes state (intro, camera, scan, results, tag, values), with the web address updating as it goes. The QR page `/r/[id]` is the only separate page. Content screens follow the theme toggle; camera screens are always dark.

## The flow

1. **Intro** → tap Scan an outfit → **Camera** (or type a fit, or upload a photo)
2. **Camera** → shutter → **Scan and trace** → live counter → **Results**
3. **Results** → like 2 or 3 → Update → reshuffled list with the Learned line
4. **Scan tag** → **Tag camera** → **Tag result**
5. **Want this look with better materials?** or hold the mic → **Voice sheet** → values re-rank the list → **Receipts**
6. **QR hand-off** → the judge opens **/r/[id]** on their own phone

## Intro

`IntroScreen`. Light background, `type-wordmark` "Sift" top left, `ThemeToggle` top right. The headline in `type-display` sits low on the screen, with the sub-line under it. Below: a large cobalt **Scan an outfit** button, the **Describe a fit** field and a small **Upload a photo** link. Holding the name for 1 second loads cached results for a known outfit (the hidden demo fallback). The button grows into the camera when tapped.

## Camera

Full-screen `camera` background. The 3:4 viewfinder sits between dark bands. Top band: close (left), flash (right, only when the phone supports it). Bottom band: the hint "Fit the whole outfit", then upload (left) and the shutter (center). No theme toggle here.

## Scan and trace

`ScanTrace` over the frozen photo, then `SearchCounter` in the bottom band. See Motion, moment 1.

## Results

Light content screen. `TopBar` (back, toggle), then `GarmentTabs` showing each traced garment as a cut-out, then the value chips row, then:

- **Exact match**: large `MatchCard`s, one column.
- **Similar style**: compact `MatchCard`s, 2 columns on phones, 3 on desktop.
- An honest **No exact match** `Notice` when there isn't one, with Similar style right below. If nothing is close either: "Nothing close yet" with **Describe it instead**.

The floating `BottomDock` holds **Scan tag**, the hold-to-talk mic and **Update** (after the first like). The Learned line appears above the list after Update.

Cards show the photo, heart, title, price (retail crossed out only when known), the mono meta line, reason chips and, once values are applied, a receipt summary. A similarity score may join the meta line later.

## Tag camera

Same camera layout with a care-label shaped `TagFrame` (everything outside dims), the hint "Fill the frame with the tag", flash when supported, and **Type it in** in the bottom band.

## Tag result

A sheet over results: the tag thumbnail and "Your shirt", the big fiber share ("50% polyester") in `type-numeral`, the `FiberBar` with its legend, one plain-language line ("Polyester sheds microplastics every wash."), two `FootprintStat`s (CO₂ and water to make it new, both est.) and the **Want this look with better materials?** button.

A low-confidence reading still shows: uncertain fibers are underlined with "Check this" and can be tapped to fix. A Retake button is always there; nothing retakes on its own.

## Values and receipts

After the voice sheet, the list re-ranks around the value chips (Natural fibers, Low carbon, Low toxins, Small seller, Max price) and each card gains a receipt summary. Opening a pick shows its `ImpactReceipt`: one receipt with two columns, **Your garment** and **This pick**, line by line. Swipe sideways between picks.

## QR hand-off

A `QRPanel` at the end of the values list: "Take your picks with you", the code, and "Scan to open your picks on your phone."

## /r/[id]

Opens on the judge's own phone, light by default. Their outfit photo at the top, "Your fit · Cal Hacks 13.0" in `type-title-1`, then their picks with receipts. Read-only, no sign-in, no dock.

## Desktop

Same app. Camera, tag and receipt screens stay a centered phone-width column. Results become a 2 or 3 column grid. The webcam or an upload replaces the phone camera.

## States on every screen

| Screen | State | Copy and action |
| --- | --- | --- |
| Camera | Camera blocked | "Camera's off" · Upload a photo instead |
| Scan | No clothes found | "Couldn't find clothes in this photo" · Retake, or tap the garment |
| Results | No exact match | "No exact match. This one might be one of a kind." |
| Results | Nothing close | "Nothing close yet" · Describe it instead |
| Any wait | Over 8 seconds | "Taking longer than usual" · Retry |
| Tag | Unreadable | "Couldn't read this tag" · Retake · Type it in |
| Voice | Mic blocked or nothing heard | The typed box opens, with chips to tap |
