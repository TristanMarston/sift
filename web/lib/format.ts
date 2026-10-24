// Number formats used everywhere in Sift.

/** $48, or $48.50 when there are cents. */
export const price = (cents: number) => `$${(cents / 100).toFixed(cents % 100 ? 2 : 0)}`;

/** 18,432 */
export const count = (n: number) => Math.round(n).toLocaleString('en-US');

/** Estimates keep 2 meaningful digits: 4.1, 2.0, 2,700. Always shown with an est. tag. */
export const est = (n: number) => (Math.abs(n) < 100 ? n.toPrecision(2) : Number(n.toPrecision(2)).toLocaleString('en-US'));

/** 1.2s */
export const seconds = (ms: number) => `${(ms / 1000).toFixed(1)}s`;
