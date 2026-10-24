// Landing prototypes: the flip (sort reshuffle), the break-even race, the wear dial (cobalt lens).
export const VARIANTS = ['flip', 'race', 'dial'] as const;
export type Variant = (typeof VARIANTS)[number];
