'use client';

import { motion, useReducedMotion } from 'motion/react';
import { EstTag } from '@/components/sift/status-badge';
import { cutout } from '@/lib/garments';
import { perWear } from '@/lib/wear';
import { cn } from '@/lib/utils';
import { race } from './samples';

// The same illustrative pair as the race (no real pair showed a clear win). Every number carries EST.
const { fragile, sturdy } = race;
const TEES = [
    { r: fragile, wins: false, float: 0 },
    { r: sturdy, wins: true, float: 1.6 },
];
const perWearText = (cents: number) => `$${(cents / 100).toFixed(2)}`;
const dollars = (cents: number) => `$${Math.round(cents / 100)}`;

/**
 * E · One comparison that never changes, so any glance, from any distance, gets the whole idea: two tees,
 * how long each lasts, and what each costs per wear. Big numbers read from across a room; the math is for
 * whoever walks up. The only motion is a slow float and a soft pulse around the winner.
 */
export function HeroBillboard() {
    const reduce = useReducedMotion();
    return (
        <div className='absolute inset-0 flex flex-col px-4 pb-2 lg:px-0' aria-label='Two tees compared by cost per wear'>
            <p className='shrink-0 pt-1 text-center type-headline text-stage-foreground/85 lg:text-[24px] lg:leading-8'>Two tees, worn until they wear out</p>
            <div className='grid min-h-0 flex-1 grid-cols-2 gap-4 pt-3 lg:gap-10 lg:pt-6'>
                {TEES.map(({ r, wins, float }) => {
                    const g = cutout(r.garment);
                    const pw = perWear(r.cents, r.lasts);
                    return (
                        <div key={r.garment} className='flex min-h-0 flex-col items-center text-center'>
                            <motion.div
                                className='relative min-h-0 w-full flex-1'
                                animate={reduce ? undefined : { y: [0, -8, 0] }}
                                transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: float }}
                            >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src={g.src} alt={`${g.name}, ${g.color}`} draggable={false} className='absolute inset-0 size-full object-contain drop-shadow-[0_18px_24px_rgba(0,0,0,0.22)]' />
                            </motion.div>
                            <p className='mt-2 type-callout font-semibold text-pretty lg:text-[22px] lg:leading-7'>{r.note}</p>
                            <p className='type-footnote text-stage-foreground/85 lg:text-[20px] lg:leading-7'>{dollars(r.cents)} to buy</p>
                            <div className={cn('relative mt-2 rounded-[22px] px-3 py-1.5 lg:mt-4 lg:rounded-[32px] lg:px-6 lg:py-3', wins && 'bg-stage-foreground text-stage')}>
                                {wins && !reduce && (
                                    <motion.span
                                        aria-hidden
                                        className='absolute -inset-1 rounded-[26px] border-2 border-stage-accent lg:rounded-[36px]'
                                        animate={{ opacity: [0, 0.9, 0], scale: [0.98, 1.04, 1.08] }}
                                        transition={{ duration: 3, repeat: Infinity, repeatDelay: 3.5, ease: 'easeOut' }}
                                    />
                                )}
                                <p className='font-serif text-[56px] leading-[56px] tracking-tight tabular lg:text-[112px] lg:leading-[104px]'>{perWearText(pw)}</p>
                                <p className={cn('flex items-center justify-center gap-1.5 type-callout lg:text-[22px] lg:leading-7', wins ? 'text-stage/85' : 'text-stage-foreground/85')}>
                                    a wear <EstTag className={wins ? 'text-stage/85' : 'text-stage-foreground/85'} />
                                </p>
                            </div>
                            <p className='mt-1.5 type-footnote tabular text-stage-foreground/85 lg:mt-3 lg:text-[18px]'>
                                {dollars(r.cents)} ÷ {r.lasts} wears
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
