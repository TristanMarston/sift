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
