import type { Transition } from 'motion/react';

// Springs use Apple's model: bounce 0 = critically damped (no overshoot), duration ≈ response.
// Default to `ui`. Use bounce only when a gesture or tap gave the motion energy.
export const spring = {
    ui: { type: 'spring', bounce: 0, duration: 0.4 }, // move, resize, reorder, morph
    snappy: { type: 'spring', bounce: 0, duration: 0.25 }, // presses and small toggles
    sheet: { type: 'spring', bounce: 0.15, duration: 0.35 }, // sheets and the dock
    pop: { type: 'spring', bounce: 0.3, duration: 0.45 }, // heart, count changes
    label: { type: 'spring', bounce: 0.15, duration: 0.45 }, // garment labels springing out
} satisfies Record<string, Transition>;

export const ease = {
    trace: [0.65, 0, 0.35, 1], // the outline drawing around a garment
    out: [0.2, 0, 0, 1], // fades and reveals
} as const;

// The tracing choreography (see scan-trace.tsx).
export const trace = {
    duration: 0.7, // one outline
    stagger: 0.15, // between garments, top to bottom
    lift: 0.4, // dimming outside the garments
    labelGap: 0.1, // label appears this long after its outline closes
} as const;
