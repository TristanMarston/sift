// Landing designs, all at /landing/<name> for demos. The receipt wall is also the home page.
export const VARIANTS = ['dial', 'flip', 'race', 'billboard', 'equation', 'wall'] as const;
export type Variant = (typeof VARIANTS)[number];
