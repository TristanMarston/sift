// Plain-language breakdowns for the item panel. Free of runtime imports so `node --test` can run it directly.
import type { EcoPartKey, Fact, Level, Result } from './search';

export type EcoPartView = { key: EcoPartKey; label: string; weight: number; score: number | null; facts: Fact[] };

// The four parts of the eco score and their weights (schema/API.md, eco). Used until the API sends `eco.parts`.
const PARTS: { key: EcoPartKey; label: string; weight: number; kinds: string[] }[] = [
    { key: 'fibers', label: 'Fabric', weight: 0.35, kinds: ['natural_fibers', 'materials', 'fabric_unknown', 'synthetic_share', 'animal_materials'] },
    { key: 'durability', label: 'How long it lasts', weight: 0.3, kinds: ['durability'] },
    { key: 'shipping', label: 'Where it ships from', weight: 0.15, kinds: ['shipping'] },
    { key: 'circularity', label: 'Second life', weight: 0.2, kinds: ['vintage', 'deadstock', 'upcycled', 'recycled', 'organic', 'certification'] },
];

/** The eco score's parts, each with the facts behind it. "Secondhand" applies to every listing, so it's in none. */
export function ecoParts(eco: Result['eco']): EcoPartView[] {
    if (eco.parts) return eco.parts.map((p) => ({ ...p, facts: eco.facts.filter((f) => f.part === p.key) }));
    return PARTS.map(({ kinds, ...p }) => ({ ...p, score: null, facts: eco.facts.filter((f) => kinds.includes(f.kind)) }));
}

// Which way quality moves the expected wears (the API's quality multiplier is above 1 for high and medium).
const QUALITY: Record<Level, string> = {
    high: 'High: lasts longer than most',
    medium: 'Medium: lasts a little longer than most',
    low: 'Low: wears out sooner than most',
    unknown: 'Unknown: no evidence, so no change',
};

/** How the expected number of wears was reached: the category's typical lifespan, then quality and condition. */
export function wearReasons(r: Pick<Result, 'wear' | 'quality'>): { label: string; value: string }[] {
    if (r.wear.steps) return r.wear.steps;
    const fact = (kind: string) => r.wear.facts.find((f) => f.kind === kind)?.value;
    const baseline = fact('baseline');
    const condition = fact('condition');
    return [
        ...(baseline ? [{ label: 'Typical lifespan', value: baseline }] : []),
        { label: 'Quality', value: QUALITY[r.quality.level] },
        ...(condition ? [{ label: 'Condition', value: condition }] : []),
    ];
}
