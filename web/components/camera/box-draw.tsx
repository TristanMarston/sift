'use client';

import { useRef, useState } from 'react';
import type { Box } from '@/lib/detect';
import { boxFrom } from '@/lib/photo';

const MIN = 0.08; // smaller than this is a stray tap, not a garment

type Point = { x: number; y: number };

/**
 * Drag a rectangle over the frozen photo to mark the garment detection missed (DESCRIPTION.md §4.3). The box
 * follows the finger 1:1 from where it touched; everything outside it dims, like the trace's lift.
 */
export function BoxDraw({ onDone }: { onDone: (box: Box) => void }) {
    const ref = useRef<HTMLDivElement>(null);
    const live = useRef<{ a: Point; b: Point } | null>(null); // the drag itself, read on release
    const [drag, setDrag] = useState<{ a: Point; b: Point } | null>(null); // what's drawn

    const at = (e: React.PointerEvent): Point => {
        const r = ref.current!.getBoundingClientRect();
        return { x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height };
    };
    const box = drag && boxFrom(drag.a, drag.b);

    return (
        <div
            ref={ref}
            className='absolute inset-0 z-10 cursor-crosshair touch-none'
            onPointerDown={(e) => {
                try {
                    e.currentTarget.setPointerCapture(e.pointerId); // keep tracking even if the finger leaves the photo
                } catch {}
                const p = at(e);
                live.current = { a: p, b: p };
                setDrag(live.current);
            }}
            onPointerMove={(e) => {
                if (!live.current) return;
                live.current = { a: live.current.a, b: at(e) };
                setDrag(live.current);
            }}
            onPointerUp={() => {
                const d = live.current;
                live.current = null;
                setDrag(null);
                const b = d && boxFrom(d.a, d.b);
                if (b && b.w >= MIN && b.h >= MIN) onDone(b);
            }}
            onPointerCancel={() => {
                live.current = null;
                setDrag(null);
            }}
            role='application'
            aria-label='Drag around the garment you mean'
        >
            {box && (
                <div
                    className='pointer-events-none absolute rounded-[10px] border-2 border-trace-line shadow-[0_0_0_9999px_var(--camera-scrim),inset_0_0_0_1px_var(--trace-halo)]'
                    style={{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.w * 100}%`, height: `${box.h * 100}%` }}
                />
            )}
        </div>
    );
}
