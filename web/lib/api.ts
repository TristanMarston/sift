// Client for the Sift backend (schema/API.md). The address comes from NEXT_PUBLIC_API_URL.
// With no address set, calls return null and the app uses the contract's fallbacks.
import type { DetectResponse } from './detect';
import { sampleCategory } from './results';
import type { SearchResponse } from './search';

const BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

/** POST /detect: finds the garments in a photo. null when there is no backend, it errors, or it takes over 8 seconds. */
export async function detect(photo: Blob): Promise<DetectResponse | null> {
    if (!BASE) return null;
    try {
        const body = new FormData();
        body.append('image', photo, 'photo.jpg');
        const res = await fetch(`${BASE}/detect`, { method: 'POST', body, signal: AbortSignal.timeout(8000) });
        return res.ok ? ((await res.json()) as DetectResponse) : null;
    } catch {
        return null;
    }
}

/** POST /jpeg: a photo the browser cannot decode (an iPhone HEIC in Chrome) comes back as a JPEG. null without a backend or on error. */
export async function toJpeg(photo: Blob): Promise<Blob | null> {
    if (!BASE) return null;
    try {
        const body = new FormData();
        body.append('image', photo, 'photo');
        const res = await fetch(`${BASE}/jpeg`, { method: 'POST', body, signal: AbortSignal.timeout(15000) });
        return res.ok ? await res.blob() : null;
    } catch {
        return null;
    }
}

/** True when a backend address is set. Without one, results come from the bundled samples. */
export const hasBackend = Boolean(BASE);

/** Listings in the index, for the search counter. The samples come from a 426-listing test scrape. */
export async function indexSize(): Promise<number> {
    if (!BASE) return 426;
    try {
        const res = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(4000) });
        return res.ok ? (((await res.json()) as { index_size?: number }).index_size ?? 0) : 0;
    } catch {
        return 0;
    }
}

/**
 * POST /search for one garment crop. With no backend, the bundled sample for the garment's category
 * (marked `sample`). With a backend, a failure throws so the screen can offer Try again, never a sample in disguise.
 */
export async function search(crop: Blob, category: string): Promise<SearchResponse> {
    if (!BASE) {
        const res = await fetch(`/samples/${sampleCategory(category)}.json`);
        return (await res.json()) as SearchResponse;
    }
    const body = new FormData();
    body.append('image', crop, 'garment.jpg');
    body.append('params', JSON.stringify(category ? { category } : {}));
    const res = await fetch(`${BASE}/search`, { method: 'POST', body, signal: AbortSignal.timeout(15000) });
    if (!res.ok) throw new Error(`search failed: ${res.status}`);
    return (await res.json()) as SearchResponse;
}
