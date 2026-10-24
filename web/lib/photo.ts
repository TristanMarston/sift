// Photo geometry for the camera. Kept free of imports so `node --test` can run it directly.

/** The centered slice of a frame with the given aspect (width / height): what object-fit: cover shows. */
export function coverCrop(srcW: number, srcH: number, aspect: number) {
    const sw = Math.round(Math.min(srcW, srcH * aspect));
    const sh = Math.round(Math.min(srcH, srcW / aspect));
    return { sx: Math.round((srcW - sw) / 2), sy: Math.round((srcH - sh) / 2), sw, sh };
}

/** Scales a size so its long edge is at most `max` (the API asks for ~1024px). Never scales up. */
export function fitLongEdge(w: number, h: number, max = 1024) {
    const k = Math.min(1, max / Math.max(w, h));
    return { w: Math.round(w * k), h: Math.round(h * k) };
}

type Point = { x: number; y: number };
const clamp01 = (n: number) => Math.min(1, Math.max(0, n));
const round3 = (n: number) => Math.round(n * 1000) / 1000;

/** A drag on the photo (fractions, top-left origin) as a box, whichever way it went, kept inside the photo. */
export function boxFrom(a: Point, b: Point) {
    const [x0, x1] = [clamp01(Math.min(a.x, b.x)), clamp01(Math.max(a.x, b.x))];
    const [y0, y1] = [clamp01(Math.min(a.y, b.y)), clamp01(Math.max(a.y, b.y))];
    return { x: round3(x0), y: round3(y0), w: round3(x1 - x0), h: round3(y1 - y0) };
}
