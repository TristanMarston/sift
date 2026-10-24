// Display rules for the results screen. The backend owns every number and order (schema/API.md §3);
// these only pick and format. Free of runtime imports so `node --test` can run it directly.
import type { Level, Result, SearchResponse, Sort } from './search';

/** The results in the order the backend sent for this sort. */
export function ordered(resp: SearchResponse, sort: Sort): Result[] {
    const byId = new Map(resp.results.map((r) => [r.id, r]));
    return resp.orders[sort].flatMap((id) => byId.get(id) ?? []);
}

export type Headline = { kind: 'drops'; rank: number } | { kind: 'best' } | null;

/**
 * "The cheapest match drops to #N" only when that's a real drop (#3 or lower). When the cheapest is also the best
 * value per wear we say that (DESCRIPTION.md §10.5). At #2 neither line is true, so there's no headline.
 */
export function headline(resp: SearchResponse): Headline {
    const rank = resp.headline.cheapest_rank_by_cpw;
    if (rank === null) return null;
    if (rank >= 3) return { kind: 'drops', rank };
    return rank === 1 ? { kind: 'best' } : null;
}

const dollars = (cents: number) => `$${(cents / 100).toFixed(cents % 100 ? 2 : 0)}`;

/** Cost per wear always shows cents: $0.30, $48.00. */
export const perWearText = (cents: number) => `$${(cents / 100).toFixed(2)}`;
export const priceText = dollars;

const LEVEL: Record<Level, string> = { high: 'High', medium: 'Medium', low: 'Low', unknown: 'Unknown' };
export const levelText = (l: Level) => LEVEL[l];

/** The big number on a row follows the sort, so each reshuffle explains itself. */
export function bigNumber(r: Result, sort: Sort): { value: string; unit: string } {
    if (sort === 'cpw') return { value: perWearText(r.wear.cpw_cents.at_mid), unit: '/wear' };
    if (sort === 'price') return { value: dollars(r.cost.total_cents), unit: '' };
    if (sort === 'match') return { value: `${Math.round(r.match.similarity * 100)}%`, unit: 'match' };
    return { value: LEVEL[r.eco.level], unit: 'eco' };
}

/** Filled dots out of three. A level, never a number (DESCRIPTION.md §10.1). */
export const dots = (l: Level) => ({ high: 3, medium: 2, low: 1, unknown: 0 })[l];

export const MARKET: Record<Result['marketplace'], string> = { depop: 'Depop', poshmark: 'Poshmark', grailed: 'Grailed', mercari: 'Mercari', ebay: 'eBay' };
export const CONDITION: Record<NonNullable<Result['condition']>, string> = { new_with_tags: 'New with tags', like_new: 'Like new', good: 'Good', fair: 'Fair' };

/** "Poshmark · M · Good". A missing value says unknown, it's never dropped. */
export const marketLine = (r: Pick<Result, 'marketplace' | 'size' | 'condition'>) =>
    [MARKET[r.marketplace], r.size ?? 'Size unknown', r.condition ? CONDITION[r.condition] : 'Condition unknown'].join(' · ');

/** The garment's box from /detect as pixels, padded a little so the crop keeps its edges, clamped to the photo. */
export function cropRect(box: { x: number; y: number; w: number; h: number }, W: number, H: number, pad = 0.04) {
    const clamp = (n: number) => Math.min(1, Math.max(0, n));
    const [x0, y0, x1, y1] = [clamp(box.x - pad), clamp(box.y - pad), clamp(box.x + box.w + pad), clamp(box.y + box.h + pad)];
    const [sx, sy] = [Math.round(x0 * W), Math.round(y0 * H)];
    return { sx, sy, sw: Math.round(x1 * W) - sx, sh: Math.round(y1 * H) - sy };
}

const SAMPLES = ['jackets_outerwear', 'sweaters_knitwear', 'sneakers'];

/** Which bundled sample to show without a backend: the garment's own category, else the jacket demo prop. */
export const sampleCategory = (category: string) => (SAMPLES.includes(category) ? category : 'jackets_outerwear');
