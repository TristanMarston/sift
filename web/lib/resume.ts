// What a refresh brings back. Free of runtime imports so `node --test` can run it directly.
import type { SearchResponse, Sort } from './search';
import type { Garment } from './types';

export type GarmentSearch = { status: 'loading' } | { status: 'done'; resp: SearchResponse } | { status: 'error' };

/** How the results were being viewed: restored along with them. */
export type View = { selected: string; sort: Sort; mix: number; openId: string | null };

/** The latest scan, kept in this browser until the next one. */
export type SavedScan = { photo: Blob; aspect: number; garments: Garment[]; results: Record<string, SearchResponse>; view: View };

/** Only searches that came back are worth keeping. */
export function finished(searches: Record<string, GarmentSearch>): Record<string, SearchResponse> {
    return Object.fromEntries(Object.entries(searches).flatMap(([id, s]) => (s.status === 'done' ? [[id, s.resp]] : [])));
}

/** Saved results show at once; any garment without one is searched again. */
export function resumed(garments: Garment[], results: Record<string, SearchResponse>) {
    const searches: Record<string, GarmentSearch> = {};
    const rerun: string[] = [];
    for (const g of garments) {
        const resp = results[g.id];
        searches[g.id] = resp ? { status: 'done', resp } : { status: 'loading' };
        if (!resp) rerun.push(g.id);
    }
    return { searches, rerun };
}
