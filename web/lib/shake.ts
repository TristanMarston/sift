// Test-only: rewrites a /search response so the cheapest match is no longer the best value per wear, to exercise
// the slider and the "drops to #N" headline. Recomputes orders the way backend/src/backend/ranker.py does.
import type { Result, SearchResponse } from './search';

// A steady 0.3x to 3x per id, so the same response always shakes the same way.
const factor = (id: string) => {
    let h = 0;
    for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return 0.3 + (h % 1000) / 1000 * 2.7;
};

const sortIds = (ids: string[], key: (id: string) => number) => [...ids].sort((a, b) => key(a) - key(b) || (a < b ? -1 : a > b ? 1 : 0));

/** slider[i] sorts by i/10 x match rank + (1 - i/10) x value rank, ties by id (schema/API.md §3). */
function slider(cpw: string[], match: string[]) {
    const n = cpw.length;
    const pc = new Map(cpw.map((x, p) => [x, n - p]));
    const pm = new Map(match.map((x, p) => [x, n - p]));
    return Array.from({ length: 11 }, (_, i) => sortIds(cpw, (x) => -(i * pm.get(x)! + (10 - i) * pc.get(x)!)));
}

export function shake(resp: SearchResponse): SearchResponse {
    const cheapest = resp.headline.cheapest_id;
    const results: Result[] = resp.results.map((r) => {
        const f = r.id === cheapest ? 0.1 : factor(r.id); // the cheapest wears out fast
        const w = r.wear.expected_wears;
        const mid = Math.max(1, Math.round(w.mid * f));
        return {
            ...r,
            wear: {
                ...r.wear,
                expected_wears: { low: Math.max(1, Math.round(w.low * f)), high: Math.max(1, Math.round(w.high * f)), mid },
                cpw_cents: { ...r.wear.cpw_cents, at_mid: Math.round(r.cost.total_cents / mid) },
            },
        };
    });
    const at = new Map(results.map((r) => [r.id, r.wear.cpw_cents.at_mid]));
    const cpw = sortIds(results.map((r) => r.id), (id) => at.get(id)!);
    return {
        ...resp,
        results,
        orders: { ...resp.orders, cpw },
        slider: slider(cpw, resp.orders.match),
        headline: { ...resp.headline, cheapest_rank_by_cpw: cheapest ? cpw.indexOf(cheapest) + 1 : null },
    };
}
