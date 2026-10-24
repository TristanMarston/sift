// Client for the Sift backend (schema/API.md). The address comes from NEXT_PUBLIC_API_URL (Vercel and .env.local).
// With no address set, there's no backend: detection falls back to the whole photo and results come from the
// bundled samples.
import type { DetectResponse } from './detect';
import { apiBases } from './endpoints';
import { sampleCategory } from './results';
import type { SearchResponse } from './search';

const BASES = apiBases(process.env.NEXT_PUBLIC_API_URL, process.env.NODE_ENV === 'development');

/** True when a backend address is set. Without one, results come from the bundled samples. */
export const hasBackend = BASES.length > 0;

/** A non-2xx answer: the API always sends {"error": {code, message}} (schema/API.md, Errors). */
export class ApiError extends Error {
    constructor(
        readonly status: number,
        readonly code: string,
        message: string,
    ) {
        super(message);
    }
}

/**
 * One call, trying each base in turn. A network failure (including a blocked cross-site request) moves on to the
 * next base; a timeout doesn't, since retrying would double the wait.
 */
async function call(path: string, init: RequestInit, timeoutMs: number): Promise<Response> {
    let last: unknown = new Error('No backend address set');
    for (const base of BASES) {
        try {
            const res = await fetch(base + path, { ...init, signal: AbortSignal.timeout(timeoutMs) });
            if (res.ok) return res;
            const body = (await res.json().catch(() => null)) as { error?: { code: string; message: string } } | null;
            throw new ApiError(res.status, body?.error?.code ?? 'internal', body?.error?.message ?? `HTTP ${res.status}`);
        } catch (e) {
            if (e instanceof ApiError || (e instanceof DOMException && e.name === 'TimeoutError')) throw e;
            last = e;
        }
    }
    throw last;
}

let healthCheck: Promise<number | null> | null = null;

/**
 * GET /health, asked once per visit and shared. Calling it early wakes the API's search index (the landing does,
 * so the first scan is quick), and its index_size is the live listing count. null when there's no answer.
 */
export function health(): Promise<number | null> {
    if (!hasBackend) return Promise.resolve(null);
    healthCheck ??= call('/health', {}, 15000)
        .then(async (res) => ((await res.json()) as { index_size?: number }).index_size ?? null)
        .catch(() => {
            healthCheck = null; // let a later caller try again
            return null;
        });
    return healthCheck;
}

/** Listings in the index, for the search counter. The samples come from a 426-listing test scrape. */
export async function indexSize(): Promise<number> {
    if (!hasBackend) return 426;
    return (await health()) ?? 0;
}

/** Detection is ~3s warm and 10–14s when the API has been asleep, so it gets 15 seconds before the whole-photo fallback. */
export const DETECT_TIMEOUT_MS = 15000;

/** POST /detect: finds the garments in a photo. null when there's no backend, it errors, or it takes too long. */
export async function detect(photo: Blob): Promise<DetectResponse | null> {
    if (!hasBackend) return null;
    try {
        const body = new FormData();
        body.append('image', photo, 'photo.jpg');
        const res = await call('/detect', { method: 'POST', body }, DETECT_TIMEOUT_MS);
        return (await res.json()) as DetectResponse;
    } catch {
        return null;
    }
}

/** POST /jpeg: a photo the browser cannot decode (an iPhone HEIC in Chrome) comes back as a JPEG. null without a backend or on error. */
export async function toJpeg(photo: Blob): Promise<Blob | null> {
    if (!hasBackend) return null;
    try {
        const body = new FormData();
        body.append('image', photo, 'photo');
        return await (await call('/jpeg', { method: 'POST', body }, 15000)).blob();
    } catch {
        return null;
    }
}

/**
 * POST /search for one garment crop. No category lets the backend read it from the photo (`query.category` says
 * which). With no backend, the bundled sample for the garment's category (marked `sample`). With a backend, a
 * failure throws so the screen can offer Try again, never a sample in disguise.
 */
export async function search(crop: Blob, category: string, brand: string | null = null): Promise<SearchResponse> {
    if (!hasBackend) {
        const res = await fetch(`/samples/${sampleCategory(category)}.json`);
        return (await res.json()) as SearchResponse;
    }
    const body = new FormData();
    body.append('image', crop, 'garment.jpg');
    body.append('params', JSON.stringify({ ...(category ? { category } : {}), ...(brand ? { brand } : {}) }));
    const res = await call('/search', { method: 'POST', body }, 20000);
    return (await res.json()) as SearchResponse;
}
