'use client';

import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { ease, spring, trace } from '@/lib/motion';
import type { Garment, Point } from '@/lib/types';
import { cn } from '@/lib/utils';

export type ScanPhase = 'scanning' | 'tracing' | 'done';

type Props = {
    garments: Garment[];
    phase: ScanPhase;
    photo?: string; // photo URL; or pass the photo as children
    children?: React.ReactNode;
    aspect?: number; // width / height of the photo, default 3:4
    selectedId?: string;
    onSelect?: (id: string) => void;
    onTapEmpty?: (x: number, y: number) => void; // mark a garment the scan missed (fractions)
    onTraced?: () => void; // after the last label lands
    className?: string;
};

// Normalized polygons -> one SVG path in a W × H box.
export const polygons = (g: Garment): Point[][] => (!g.outline?.length ? [] : typeof g.outline[0][0] === 'number' ? [g.outline as Point[]] : (g.outline as Point[][]));
const pathOf = (g: Garment, W: number, H: number) => {
    const polys = polygons(g);
    if (!polys.length) {
        const { x, y, w, h } = g.bbox;
        return `M${x * W} ${y * H}h${w * W}v${h * H}h${-w * W}z`; // no outline: trace the box
    }
    return polys.map((p) => 'M' + p.map(([x, y]) => `${(x * W).toFixed(1)} ${(y * H).toFixed(1)}`).join('L') + 'Z').join('');
};

/**
 * The signature moment. scanning: a soft line sweeps the photo while intel/ works.
 * tracing: a white line draws around each garment (top to bottom), the rest of the photo dims,
 * and a label springs out of each garment. done: labels are tappable.
 */
export function ScanTrace({ garments, phase, photo, children, aspect = 3 / 4, selectedId, onSelect, onTapEmpty, onTraced, className }: Props) {
    const maskId = 'lift' + useId().replace(/:/g, '');
    const [ripple, setRipple] = useState<{ x: number; y: number; k: number } | null>(null);
    const W = 300;
    const H = W / aspect;
    const lastLine = (garments.length - 1) * trace.stagger + trace.duration;

    useEffect(() => {
        if (phase !== 'tracing' || !onTraced) return;
        const t = setTimeout(onTraced, (lastLine + trace.labelGap + 0.45) * 1000);
        return () => clearTimeout(t);
    }, [phase, lastLine, onTraced]);

    const tapPhoto = (e: React.MouseEvent<HTMLDivElement>) => {
        if (phase !== 'done' || !onTapEmpty || e.target !== e.currentTarget) return;
        const r = e.currentTarget.getBoundingClientRect();
        const [x, y] = [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height];
        setRipple({ x, y, k: Date.now() });
        onTapEmpty(x, y);
    };

    return (
        <div className={cn('relative overflow-hidden bg-camera select-none', className)} style={{ aspectRatio: aspect }}>
            <div className='absolute inset-0'>
                {photo ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={photo} alt='Your photo' className='size-full object-cover' />
                ) : (
                    children
                )}
            </div>

            <AnimatePresence>
                {phase === 'scanning' && (
                    <motion.div key='scan' className='absolute inset-0' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.3 } }}>
                        <div className='absolute inset-0 animate-pulse bg-black/30' />
                        <motion.div
                            className='absolute inset-x-0 h-1/4 scan-glow'
                            initial={{ top: '-25%' }}
                            animate={{ top: '100%' }}
                            transition={{ duration: 1.8, ease: ease.trace, repeat: Infinity, repeatDelay: 0.25 }}
                        />
                        <p className='absolute inset-x-0 bottom-6 text-center type-callout text-camera-foreground'>Finding garments…</p>
                    </motion.div>
                )}
            </AnimatePresence>

            {phase !== 'scanning' && (
                <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio='none' className='pointer-events-none absolute inset-0 size-full' aria-hidden>
                    <defs>
                        <mask id={maskId}>
                            <rect width={W} height={H} fill='white' />
                            {garments.map((g) => (
                                <path key={g.id} d={pathOf(g, W, H)} fill='black' />
                            ))}
                        </mask>
                    </defs>
                    <motion.rect
                        width={W}
                        height={H}
                        fill='var(--camera-scrim)'
                        mask={`url(#${maskId})`}
                        initial={{ opacity: phase === 'done' ? 1 : 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: lastLine - 0.2, duration: trace.lift, ease: ease.out }}
                    />
                    {garments.map((g, i) =>
                        (['var(--trace-halo)', 'var(--trace-line)'] as const).map((stroke, j) => (
                            <motion.path
                                key={g.id + j}
                                d={pathOf(g, W, H)}
                                fill='none'
                                stroke={stroke}
                                strokeWidth={j ? 2 : 5}
                                strokeLinejoin='round'
                                strokeLinecap='round'
                                initial={{ pathLength: phase === 'done' ? 1 : 0 }}
                                animate={{ pathLength: 1 }}
                                transition={{ duration: trace.duration, delay: i * trace.stagger, ease: ease.trace }}
                            />
                        )),
                    )}
                </svg>
            )}

            {/* Tap targets follow the garment shapes. */}
            {phase === 'done' && (
                <div className='absolute inset-0' onClick={tapPhoto}>
                    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio='none' className='pointer-events-none absolute inset-0 size-full'>
                        {garments.map((g) => (
                            <path key={g.id} d={pathOf(g, W, H)} fill='transparent' className='pointer-events-auto cursor-pointer' onClick={() => onSelect?.(g.id)} />
                        ))}
                    </svg>
                </div>
            )}

            {phase !== 'scanning' &&
                garments.map((g, i) => (
                    <GarmentLabel
                        key={g.id}
                        garment={g}
                        selected={g.id === selectedId}
                        delay={phase === 'done' ? 0 : i * trace.stagger + trace.duration + trace.labelGap}
                        onClick={() => onSelect?.(g.id)}
                    />
                ))}

            <AnimatePresence>
                {ripple && (
                    <motion.span
                        key={ripple.k}
                        className='pointer-events-none absolute size-16 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-trace-line'
                        style={{ left: `${ripple.x * 100}%`, top: `${ripple.y * 100}%` }}
                        initial={{ scale: 0.2, opacity: 1 }}
                        animate={{ scale: 1, opacity: 0 }}
                        transition={{ duration: 0.6, ease: ease.out }}
                        onAnimationComplete={() => setRipple(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

/** A dot inside the garment and a white pill that springs out of it. */
function GarmentLabel({ garment, selected, delay, onClick }: { garment: Garment; selected: boolean; delay: number; onClick: () => void }) {
    const { x, y, w, h } = garment.bbox;
    const [ax, ay] = [x + w * 0.6, y + h * 0.45];
    const flip = ax > 0.5; // the pill grows toward the side with more room
    const btn = useRef<HTMLButtonElement>(null);
    const pill = useRef<HTMLSpanElement>(null);

    // Never clip at the photo edge: cap the pill to the room on its side (it truncates with an ellipsis).
    useLayoutEffect(() => {
        const box = (btn.current?.offsetParent as HTMLElement | null)?.getBoundingClientRect();
        if (!box || !pill.current) return;
        const room = flip ? ax * box.width : (1 - ax) * box.width;
        pill.current.style.maxWidth = `${Math.max(64, room - 28)}px`;
    }, [ax, flip]);

    return (
        <button
            ref={btn}
            type='button'
            onClick={onClick}
            className={cn('absolute flex -translate-y-1/2 items-center gap-2 outline-none', flip && 'flex-row-reverse')}
            style={flip ? { right: `calc(${(1 - ax) * 100}% - 5px)`, top: `${ay * 100}%` } : { left: `calc(${ax * 100}% - 5px)`, top: `${ay * 100}%` }}
        >
            <motion.span
                className='size-2.5 shrink-0 rounded-full bg-trace-line shadow-[0_0_0_3px_var(--trace-halo)]'
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ ...spring.label, delay: delay - 0.05 }}
            />
            <motion.span
                ref={pill}
                className={cn('max-w-52 truncate rounded-pill bg-camera-foreground px-3 py-1.5 type-footnote font-semibold whitespace-nowrap text-camera shadow-lift', selected && 'ring-2 ring-primary ring-offset-2 ring-offset-camera')}
                style={{ transformOrigin: flip ? 'right center' : 'left center' }}
                initial={{ opacity: 0, scale: 0.6, x: flip ? 8 : -8 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                transition={{ ...spring.label, delay }}
            >
                {garment.label}
            </motion.span>
        </button>
    );
}
