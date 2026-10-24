// Turns a /detect response (schema/API.md §1) into garments the scan trace can draw.
import type { Garment } from './types';

export type Box = { x: number; y: number; w: number; h: number }; // fractions of the photo, top-left origin
export type DetectResponse = {
    image: { width: number; height: number };
    garments: { id: string; category: string | null; label: string; brand?: string | null; box: Box; confidence: number }[]; // category null: none of the 8; brand: a logo or label read off the garment
};

/** API.md: with no garments found, the whole photo is searched as one. Inset a little so its trace reads as a frame. */
export const WHOLE_PHOTO: Garment = { id: 'g0', category: '', label: 'Your photo', attributes: {}, bbox: { x: 0.04, y: 0.04, w: 0.92, h: 0.92 } };

const clamp = (n: number) => Math.min(1, Math.max(0, n));
const round = (n: number) => Math.round(n * 1000) / 1000;

function clampBox({ x, y, w, h }: Box): Box {
    const [x0, y0, x1, y1] = [clamp(x), clamp(y), clamp(x + w), clamp(y + h)];
    return { x: round(x0), y: round(y0), w: round(x1 - x0), h: round(y1 - y0) };
}

/** Most confident first, labels in sentence case. No response or no garments: the whole photo. */
export function toGarments(res: DetectResponse | null): Garment[] {
    if (!res?.garments.length) return [WHOLE_PHOTO];
    return [...res.garments]
        .sort((a, b) => b.confidence - a.confidence)
        .map((g) => ({ id: g.id, category: g.category ?? '', label: g.label.charAt(0).toUpperCase() + g.label.slice(1), brand: g.brand ?? null, attributes: {}, bbox: clampBox(g.box) }));
}
