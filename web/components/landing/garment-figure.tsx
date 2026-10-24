'use client';

import { motion } from 'motion/react';
import type { Cutout } from '@/lib/garments';
import { ease } from '@/lib/motion';
import type { Point } from '@/lib/types';
import { cn } from '@/lib/utils';

const polys = (o: Cutout['outline']): Point[][] => (typeof o[0][0] === 'number' ? [o as Point[]] : (o as Point[][]));

type Props = {
    g: Cutout;
    traced?: boolean; // draw the outline
    scanning?: boolean; // one scan-line pass
    lifted?: boolean; // soft shadow, as if picked up
    line?: string; // outline color
    className?: string;
};

/** A garment cut-out that fits its box (contain), with its real outline ready to trace. */
export function GarmentFigure({ g, traced, scanning, lifted, line = 'var(--primary)', className }: Props) {
    const [W, H] = [g.aspect * 1000, 1000];
    return (
        <div className={cn('grid size-full place-items-center [container-type:size]', className)}>
            <div className='relative' style={{ width: `min(100cqw, ${g.aspect * 100}cqh)`, aspectRatio: g.aspect }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                    src={g.src}
                    alt={`${g.name}, ${g.color}`}
                    draggable={false}
                    className={cn('size-full object-contain transition-[filter] duration-500 select-none', lifted && 'drop-shadow-[0_18px_26px_rgba(0,0,0,0.22)]')}
                />
                {scanning && (
                    <div className='pointer-events-none absolute inset-0 overflow-hidden'>
                        <motion.div
                            className='absolute inset-x-0 h-1/3 border-b-2'
                            style={{ borderColor: line, background: `linear-gradient(to bottom, transparent, color-mix(in srgb, ${line} 18%, transparent))` }}
                            initial={{ top: '-34%' }}
                            animate={{ top: '100%' }}
                            transition={{ duration: 0.85, ease: ease.trace }}
                        />
                    </div>
                )}
                <svg viewBox={`0 0 ${W} ${H}`} className='pointer-events-none absolute inset-0 size-full overflow-visible' style={{ filter: `drop-shadow(0 0 6px ${line})` }} aria-hidden>
                    {polys(g.outline).map((p, i) => (
                        <motion.path
                            key={i}
                            d={'M' + p.map(([x, y]) => `${(x * W).toFixed(1)} ${(y * H).toFixed(1)}`).join('L') + 'Z'}
                            fill='none'
                            stroke={line}
                            strokeWidth={7}
                            strokeLinejoin='round'
                            strokeLinecap='round'
                            initial={{ pathLength: 0, opacity: 0 }}
                            animate={traced ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
                            transition={{ pathLength: { duration: traced ? 0.9 : 0.3, ease: ease.trace }, opacity: { duration: 0.2 } }}
                        />
                    ))}
                </svg>
            </div>
        </div>
    );
}
