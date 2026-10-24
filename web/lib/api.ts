// Client for the Sift backend (schema/API.md). The address comes from NEXT_PUBLIC_API_URL.
// With no address set, calls return null and the app uses the contract's fallbacks.
import type { DetectResponse } from './detect';

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
