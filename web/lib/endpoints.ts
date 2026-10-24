// Where the app sends API calls. Free of imports so `node --test` can run it directly.

/** Our own site's route that forwards to the API (next.config.ts rewrites). */
export const PROXY = '/api/sift';

/**
 * The bases to try, in order. In development everything goes through the dev server, so a phone on wifi or the
 * HTTPS dev server is never blocked by the API's allowed-origins list. In production the browser calls the API
 * directly (fastest; Vercel addresses starting "sift" are allowed), then our own site if that call is blocked.
 */
export function apiBases(direct: string | undefined, dev: boolean): string[] {
    const base = direct?.replace(/\/$/, '');
    if (!base) return [];
    return dev ? [PROXY] : [base, PROXY];
}
