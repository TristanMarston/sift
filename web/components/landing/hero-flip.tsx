'use client';

import { ArrowDown } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useEffect, useState } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { price } from '@/lib/format';
import { cutout } from '@/lib/garments';
import { ease, spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { byPerWear, byPrice, cheapestDropsTo, perWear } from '@/lib/wear';
import { GarmentFigure } from './garment-figure';
import { flipSets, metaLine, type Listing } from './samples';

// One set's timeline, in ms. Steps: 1 scan, 2 trace, 3 label, 4 cards by price, 5 tap, 6 sorted by cost per wear.
const T = [400, 1150, 1900, 2700, 5000, 5350];
const NEXT = 10800;
const reorder = { type: 'spring', bounce: 0.15, duration: 0.7 } as const;

/** 1 · The scan plays itself, then the sort flips from price to cost per wear and the cards reshuffle. Loops. */
export function HeroFlip() {
    const [i, setI] = useState(0);
    const [step, setStep] = useState(0);
    const set = flipSets[i % flipSets.length];
    const photo = cutout(set.photo);

    useEffect(() => {
        const ts = T.map((ms, k) => setTimeout(() => setStep(k + 1), ms));
        ts.push(
            setTimeout(() => {
                setStep(0);
                setI((n) => n + 1);
            }, NEXT),
        );
        return () => ts.forEach(clearTimeout);
    }, [i]);

    const compact = step >= 4;
    const flipped = step >= 6;
    const list = flipped ? byPerWear(set.listings) : byPrice(set.listings);
    const priceOrder = byPrice(set.listings).map((l) => l.id);

    return (
        <div className='absolute inset-0 px-4 pb-1 lg:px-0' aria-hidden>
            <AnimatePresence mode='wait'>
                <motion.div key={i} className='relative size-full' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.35 } }} transition={{ duration: 0.45, ease: ease.out }}>
                    {!compact && (
                        <>
                            <motion.div layoutId={`photo-${i}`} transition={spring.ui} className='absolute inset-x-0 top-[2%] mx-auto aspect-square h-[78%] max-w-full'>
                                <GarmentFigure g={photo} scanning={step === 1} traced={step >= 2} lifted={step >= 2} line='var(--stage-accent)' />
                            </motion.div>
                            <AnimatePresence>
                                {step === 3 && (
                                    <motion.span
                                        className='absolute top-[82%] left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-pill bg-card px-3.5 py-2 type-footnote font-semibold whitespace-nowrap text-card-foreground shadow-float'
                                        initial={{ opacity: 0, y: 12, scale: 0.85 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.9 }}
                                        transition={spring.label}
                                    >
                                        <span className='size-2 rounded-full bg-primary' />
                                        {set.label}
                                    </motion.span>
                                )}
                            </AnimatePresence>
                        </>
                    )}

                    {compact && (
                        <div className='absolute inset-0 flex flex-col gap-2.5 lg:justify-center lg:gap-3'>
                            <div className='flex items-center gap-3 lg:gap-4'>
                                <motion.div layoutId={`photo-${i}`} transition={spring.ui} className='size-14 shrink-0 lg:size-20'>
                                    <GarmentFigure g={photo} traced line='var(--stage-accent)' />
                                </motion.div>
                                <motion.div className='flex-1' initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ ...spring.ui, delay: 0.15 }}>
                                    <SortToggle perWear={flipped} tapping={step === 5} />
                                </motion.div>
                            </div>
                            <ol className='flex min-h-0 flex-1 flex-col gap-1.5 lg:flex-none lg:gap-2.5'>
                                {list.map((l, k) => (
                                    <FlipCard key={l.id} l={l} rank={k + 1} perWear={flipped} cheapest={l.id === priceOrder[0]} delay={0.2 + priceOrder.indexOf(l.id) * 0.07} />
                                ))}
                            </ol>
                            <div className='flex h-9 shrink-0 items-center justify-center'>
                                <AnimatePresence>
                                    {flipped && (
                                        <motion.span
                                            className='flex items-center gap-1.5 rounded-pill bg-stage-foreground px-3.5 py-1.5 type-footnote font-semibold text-stage'
                                            initial={{ opacity: 0, y: 10, scale: 0.9 }}
                                            animate={{ opacity: 1, y: 0, scale: 1 }}
                                            transition={{ ...spring.pop, delay: 0.45 }}
                                        >
                                            <ArrowDown className='size-4' strokeWidth={2} />
                                            The cheapest match drops to #{cheapestDropsTo(set.listings)}
                                        </motion.span>
                                    )}
                                </AnimatePresence>
                            </div>
                        </div>
                    )}
                </motion.div>
            </AnimatePresence>
        </div>
    );
}

/** The results screen's sort control, played by itself: a touch lands on "Cost per wear" and the pill slides over. */
function SortToggle({ perWear, tapping }: { perWear: boolean; tapping: boolean }) {
    return (
        <motion.div className='relative grid h-11 grid-cols-2 rounded-pill bg-stage-foreground/10 p-1' animate={{ scale: tapping ? 0.97 : 1 }} transition={spring.snappy}>
            <motion.span className='absolute inset-y-1 left-1 w-[calc(50%-4px)] rounded-pill bg-stage-foreground shadow-float' animate={{ x: perWear ? '100%' : '0%' }} transition={spring.ui} />
            {['Price', 'Cost per wear'].map((t, k) => (
                <span key={t} className={cn('relative grid place-items-center type-callout whitespace-nowrap transition-colors duration-300', (k === 1) === perWear ? 'text-stage' : 'text-stage-foreground')}>
                    {t}
                </span>
            ))}
            <AnimatePresence>
                {tapping && (
                    <motion.span
                        className='absolute top-1/2 left-3/4 size-11 -translate-1/2 rounded-full bg-stage-foreground/25'
                        initial={{ scale: 0.3, opacity: 0 }}
                        animate={{ scale: 1.5, opacity: [0, 0.9, 0] }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.6, ease: ease.out }}
                    />
                )}
            </AnimatePresence>
        </motion.div>
    );
}

type CardProps = { l: Listing; rank: number; perWear: boolean; cheapest: boolean; delay: number };

/** A look-alike: price first, then price ÷ expected wears. */
function FlipCard({ l, rank, perWear: pw, cheapest, delay }: CardProps) {
    const g = cutout(l.garment);
    return (
        <motion.li
            layout
            className='flex min-h-0 flex-1 items-center gap-2.5 rounded-[14px] bg-card px-3 text-card-foreground shadow-float lg:h-[84px] lg:flex-none lg:gap-4 lg:px-4'
            initial={{ opacity: 0, y: -28, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ default: { ...spring.sheet, delay }, layout: reorder }}
        >
            <span className='w-4 shrink-0 type-data tabular text-muted-foreground'>{rank}</span>
            <span className='grid aspect-square h-[76%] max-h-16 shrink-0 place-items-center rounded-xl bg-secondary p-1'>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={g.src} alt='' draggable={false} className='size-full object-contain' />
            </span>
            <span className='flex min-w-0 flex-1 flex-col gap-0.5'>
                <span className='flex items-center gap-1.5'>
                    <span className='truncate type-callout font-semibold'>{l.title}</span>
                    {cheapest && <span className='shrink-0 rounded-tag bg-primary-tint px-1 py-px type-label text-primary-tint-foreground'>CHEAPEST</span>}
                </span>
                <span className='truncate type-data text-muted-foreground'>{metaLine(l)}</span>
            </span>
            <span className='flex shrink-0 flex-col items-end gap-0.5'>
                <AnimatePresence mode='popLayout' initial={false}>
                    <motion.span key={pw ? 'wear' : 'price'} className='flex items-center gap-1.5' initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={spring.snappy}>
                        <span className='font-serif text-[22px] leading-6 tabular lg:text-[26px] lg:leading-7'>{price(pw ? perWear(l.cents, l.wears) : l.cents)}</span>
                        {pw && <EstTag />}
                    </motion.span>
                </AnimatePresence>
                <span className={cn('type-label text-muted-foreground uppercase transition-opacity duration-300', pw ? 'opacity-100' : 'opacity-0')}>÷ {l.wears} wears</span>
            </span>
        </motion.li>
    );
}
