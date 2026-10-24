'use client';

import { motion } from 'motion/react';
import { ease } from '@/lib/motion';
import type { Fiber, FiberClass } from '@/lib/types';
import { cn } from '@/lib/utils';

const CLASS: Record<string, FiberClass> = {
    cotton: 'plant', linen: 'plant', hemp: 'plant', ramie: 'plant',
    wool: 'animal', merino: 'animal', silk: 'animal', cashmere: 'animal', alpaca: 'animal', mohair: 'animal',
    viscose: 'regenerated', rayon: 'regenerated', lyocell: 'regenerated', tencel: 'regenerated', modal: 'regenerated',
    polyester: 'synthetic', nylon: 'synthetic', polyamide: 'synthetic', acrylic: 'synthetic', elastane: 'synthetic', spandex: 'synthetic',
};
export const fiberClass = (name: string): FiberClass => CLASS[name.toLowerCase()] ?? 'unknown';

const FILL: Record<FiberClass, string> = {
    plant: 'bg-fiber-plant',
    animal: 'bg-fiber-animal',
    regenerated: 'bg-fiber-regenerated',
    synthetic: 'bg-fiber-synthetic',
    unknown: 'hatch',
};

type Props = {
    fibers: Fiber[];
    uncertain?: string[]; // fibers the tag reader wasn't sure about: underlined, tap to fix
    onFix?: (name: string) => void;
    className?: string;
};

/** Fiber mix from a tag. Segments fill one after another; anything unaccounted for is hatched. */
export function FiberBar({ fibers, uncertain = [], onFix, className }: Props) {
    const rest = Math.max(0, 100 - fibers.reduce((s, f) => s + f.pct, 0));
    const parts = rest ? [...fibers, { name: 'unknown', pct: rest }] : fibers;
    return (
        <div className={cn('flex flex-col gap-3', className)}>
            <div className='flex h-3.5 w-full overflow-hidden rounded-pill bg-muted' role='img' aria-label={parts.map((f) => `${f.pct}% ${f.name}`).join(', ')}>
                {parts.map((f, i) => (
                    <motion.div
                        key={f.name}
                        className={cn('h-full border-r-2 border-card last:border-r-0', FILL[fiberClass(f.name)])}
                        initial={{ width: 0 }}
                        animate={{ width: `${f.pct}%` }}
                        transition={{ duration: 0.7, delay: 0.15 + i * 0.35, ease: ease.out }}
                    />
                ))}
            </div>
            <ul className='flex flex-col gap-1.5'>
                {parts.map((f) => {
                    const cls = fiberClass(f.name);
                    const unsure = uncertain.includes(f.name);
                    return (
                        <li key={f.name} className='flex items-center gap-2.5'>
                            <span className={cn('size-2.5 shrink-0 rounded-[3px]', FILL[cls])} />
                            <span className='w-10 type-data tabular'>{f.pct}%</span>
                            <button
                                type='button'
                                disabled={!unsure}
                                onClick={() => onFix?.(f.name)}
                                className={cn('type-callout capitalize disabled:cursor-default', unsure && 'underline decoration-primary decoration-dotted decoration-2 underline-offset-4')}
                            >
                                {f.name === 'unknown' ? 'Not on the tag' : f.name}
                            </button>
                            <span className='type-footnote text-muted-foreground'>{unsure ? 'Check this' : cls === 'unknown' ? '' : cls}</span>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}
