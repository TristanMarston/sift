'use client';

import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { cutout } from '@/lib/garments';
import { spring } from '@/lib/motion';
import { perWear } from '@/lib/wear';
import { cn } from '@/lib/utils';
import { GarmentFigure } from './garment-figure';
import { dialItems, listingLine } from './samples';

const HOLD = 7000; // every frame is a complete equation; nothing changes for 7 seconds
const perWearText = (cents: number) => `$${(cents / 100).toFixed(2)}`;
const dollars = (cents: number) => `$${Math.round(cents / 100)}`;

/** A number that rolls to its next value in place: the old one slides up and out as the new one slides in. */
function Roll({ value, className }: { value: string; className?: string }) {
    return (
        <span className={cn('relative inline-grid overflow-hidden', className)}>
            <AnimatePresence mode='popLayout' initial={false}>
                <motion.span key={value} className='col-start-1 row-start-1' initial={{ y: '60%', opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '-60%', opacity: 0 }} transition={spring.ui}>
                    {value}
                </motion.span>
            </AnimatePresence>
        </span>
    );
}

/**
 * F · One garment and its whole equation, set like a fraction: price over wears equals cost per wear. Every 7
 * seconds the numbers roll to the next garment in place, so any glance lands on a complete equation.
 */
export function HeroEquation() {
    const reduce = useReducedMotion();
    const [i, setI] = useState(0);
    const item = dialItems[i % dialItems.length];
    const g = cutout(item.garment);

    useEffect(() => {
        const id = setInterval(() => setI((n) => n + 1), HOLD);
        return () => clearInterval(id);
    }, []);

    return (
        <div className='absolute inset-0 flex flex-col items-center px-4 pb-1 lg:px-0' aria-label='Cost per wear equals price divided by wears'>
            <Roll value={listingLine(item)} className='shrink-0 pt-1 text-center type-headline text-stage-foreground/85 lg:text-[24px] lg:leading-8' />

            <motion.div className='relative min-h-0 w-full max-w-md flex-1 py-2' animate={reduce ? undefined : { y: [0, -8, 0] }} transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}>
                <AnimatePresence mode='popLayout' initial={false}>
                    <motion.div key={item.id} className='absolute inset-0' initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.03 }} transition={{ duration: 0.7, ease: [0.2, 0, 0, 1] }}>
                        <GarmentFigure g={g} traced line='var(--stage-accent)' lifted />
                    </motion.div>
                </AnimatePresence>
            </motion.div>

            {/* price / wears = cost per wear */}
            <div className='flex shrink-0 items-center gap-3 lg:gap-6'>
                <div className='flex flex-col items-center'>
                    <Roll value={dollars(item.cents)} className='font-serif text-[40px] leading-[44px] tracking-tight tabular lg:text-[72px] lg:leading-[76px]' />
                    <span className='my-1 h-[3px] w-full min-w-24 rounded-pill bg-stage-foreground lg:my-2 lg:h-1 lg:min-w-44' aria-hidden />
                    <span className='flex items-baseline gap-1.5 type-callout lg:text-[24px] lg:leading-8'>
                        <Roll value={String(item.wears)} className='font-semibold tabular' /> wears
                    </span>
                </div>
                <span className='font-serif text-[40px] leading-none text-stage-foreground/85 lg:text-[72px]' aria-hidden>
                    =
                </span>
                <div className='flex flex-col items-start'>
                    <Roll value={perWearText(perWear(item.cents, item.wears))} className='font-serif text-[56px] leading-[56px] tracking-tight tabular lg:text-[112px] lg:leading-[104px]' />
                    <span className='flex items-center gap-1.5 type-callout text-stage-foreground/85 lg:text-[22px] lg:leading-7'>
                        a wear <EstTag className='text-stage-foreground/85' />
                    </span>
                </div>
            </div>

            <div className='mt-3 flex shrink-0 gap-1.5' aria-hidden>
                {dialItems.map((d, k) => (
                    <span key={d.id} className={cn('size-1.5 rounded-full transition-colors duration-500', k === i % dialItems.length ? 'bg-stage-foreground' : 'bg-stage-foreground/25')} />
                ))}
            </div>
        </div>
    );
}
