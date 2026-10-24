'use client';

import { motion } from 'motion/react';
import { useId } from 'react';
import { spring } from '@/lib/motion';
import type { Garment } from '@/lib/types';
import { cn } from '@/lib/utils';
import { OutfitShapes } from './sample-outfit';
import { polygons } from './scan-trace';

/**
 * A garment cut out of the photo along its outline.
 * Pass `src` for a real photo; without it the sample outfit is used.
 */
export function GarmentCutout({ garment, src, aspect = 3 / 4, className }: { garment: Garment; src?: string; aspect?: number; className?: string }) {
    const clip = 'cut' + useId().replace(/:/g, '');
    const [W, H] = [300, 300 / aspect];
    const { x, y, w, h } = garment.bbox;
    const pad = 0.04;
    const box = [(x - pad) * W, (y - pad) * H, (w + pad * 2) * W, (h + pad * 2) * H].map((n) => n.toFixed(1)).join(' ');
    const d = polygons(garment)
        .map((p) => 'M' + p.map(([px, py]) => `${px * W} ${py * H}`).join('L') + 'Z')
        .join('');
    return (
        <svg viewBox={box} className={cn('size-full', className)} aria-hidden>
            <clipPath id={clip}>{d ? <path d={d} /> : <rect x={x * W} y={y * H} width={w * W} height={h * H} />}</clipPath>
            <g clipPath={`url(#${clip})`}>{src ? <image href={src} width={W} height={H} preserveAspectRatio='xMidYMid slice' /> : <OutfitShapes />}</g>
        </svg>
    );
}

type Props = { garments: Garment[]; selectedId: string; onSelect?: (id: string) => void; photo?: string; className?: string };

/** One tab per detected garment, shown as its cut-out. */
export function GarmentTabs({ garments, selectedId, onSelect, photo, className }: Props) {
    const ring = 'tab-ring' + useId().replace(/:/g, '');
    return (
        <div role='tablist' aria-label='Garments' className={cn('flex gap-3 overflow-x-auto [scrollbar-width:none]', className)}>
            {garments.map((g) => {
                const selected = g.id === selectedId;
                return (
                    <button key={g.id} role='tab' aria-selected={selected} onClick={() => onSelect?.(g.id)} className='flex w-[68px] shrink-0 flex-col items-center gap-1.5 outline-none'>
                        <span className='relative grid size-[68px] place-items-center rounded-image bg-card p-1.5 shadow-card'>
                            <GarmentCutout garment={g} src={photo} />
                            {selected && <motion.span layoutId={ring} className='absolute inset-0 rounded-image ring-2 ring-primary' transition={spring.ui} />}
                        </span>
                        <span className={cn('w-full truncate text-center type-footnote', selected ? 'font-semibold text-foreground' : 'text-muted-foreground')}>{g.label.split(' · ')[0]}</span>
                    </button>
                );
            })}
        </div>
    );
}
