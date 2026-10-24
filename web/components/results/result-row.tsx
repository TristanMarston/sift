'use client';

import { AnimatePresence, motion } from 'motion/react';
import Image from 'next/image';
import { EstTag } from '@/components/sift/status-badge';
import { spring } from '@/lib/motion';
import { bigNumber, marketLine, perWearText, priceText } from '@/lib/results';
import type { Result, Sort } from '@/lib/search';
import { cn } from '@/lib/utils';
import { MarkerLine } from './evidence';

// A touch of bounce: the user's tap gave the reshuffle its energy.
const reorder = { type: 'spring', bounce: 0.15, duration: 0.6 } as const;
// Rows rise in 40ms apart when results first appear (the list staggers them).
const rowIn = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0 } };

export const photoOf = (r: Result) => r.thumb_url ?? r.image_urls[0];

/** The listing photo, 4:5. Shared with the receipt (same layoutId), so it grows into the sheet and back. */
export function ListingPhoto({ r, className, children }: { r: Result; className?: string; children?: React.ReactNode }) {
    return (
        <motion.div layoutId={`photo-${r.id}`} transition={spring.ui} className={cn('relative aspect-[4/5] shrink-0 overflow-hidden rounded-image bg-muted', className)}>
            {/* One size for the row and the receipt, so the photo that flies into the receipt is already loaded. */}
            <Image src={photoOf(r)} alt={r.title} fill sizes='120px' quality={70} className='object-cover' />
            <span className='pointer-events-none absolute inset-0 rounded-image ring-1 ring-black/5 ring-inset' />
            {children}
        </motion.div>
    );
}

type Props = { r: Result; rank: number; sort: Sort; cheapest: boolean; open: boolean; onOpen: () => void };

/** One look-alike: photo with its rank, title, where it is, the evidence levels, and the number the sort is about. */
export function ResultRow({ r, rank, sort, cheapest, open, onOpen }: Props) {
    const big = bigNumber(r, sort);
    // Cost per wear is always on the row: as the big number, or next to it.
    const second = sort === 'cpw' ? priceText(r.cost.total_cents) : sort === 'price' ? `${perWearText(r.wear.cpw_cents.at_mid)}/wear` : `${priceText(r.cost.total_cents)} · ${perWearText(r.wear.cpw_cents.at_mid)}/wear`;
    return (
        <motion.li layout variants={rowIn} transition={{ layout: reorder, default: spring.ui }} className='list-none'>
            <button type='button' onClick={onOpen} className='flex w-full gap-3 rounded-card bg-card p-2.5 text-left text-card-foreground shadow-card outline-none transition-transform duration-100 active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-ring'>
                {open ? (
                    <div className='aspect-[4/5] w-[88px] shrink-0 rounded-image bg-muted' /> // the photo is in the open receipt
                ) : (
                    <ListingPhoto r={r} className='w-[88px]'>
                        <motion.span key={rank} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={spring.pop} className='absolute top-1.5 left-1.5 grid h-5 min-w-5 place-items-center rounded-pill bg-card/90 px-1 type-data font-medium tabular text-foreground backdrop-blur-md'>
                            {rank}
                        </motion.span>
                    </ListingPhoto>
                )}
                <div className='flex min-w-0 flex-1 flex-col gap-0.5 py-0.5'>
                    {(cheapest || r.match.band === 'exact') && (
                        <span className='mb-0.5 flex gap-1'>
                            {cheapest && <span className='rounded-tag bg-primary-tint px-1.5 py-px type-label text-primary-tint-foreground'>CHEAPEST</span>}
                            {r.match.band === 'exact' && <span className='rounded-tag bg-secondary px-1.5 py-px type-label text-secondary-foreground'>EXACT MATCH</span>}
                        </span>
                    )}
                    <h3 className='line-clamp-2 type-callout font-semibold text-pretty'>{r.title}</h3>
                    <p className='truncate type-footnote text-muted-foreground'>{marketLine(r)}</p>
                    <MarkerLine r={r} />
                    <div className='mt-auto flex items-end gap-2 pt-1'>
                        <AnimatePresence mode='popLayout' initial={false}>
                            <motion.span key={sort} className='flex items-baseline gap-1' initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={spring.snappy}>
                                <span className='font-serif text-[26px] leading-7 tracking-tight tabular'>{big.value}</span>
                                {big.unit && <span className='type-footnote text-muted-foreground'>{big.unit}</span>}
                                {sort === 'cpw' && <EstTag className='ml-0.5' />}
                            </motion.span>
                        </AnimatePresence>
                        <span className='ml-auto pb-0.5 type-footnote tabular text-muted-foreground'>{second}</span>
                    </div>
                </div>
            </button>
        </motion.li>
    );
}

/** Breathing placeholder rows while a garment's search runs (no spinners). */
export function RowSkeleton() {
    return (
        <li className='flex animate-pulse list-none gap-3 rounded-card bg-card p-2.5 shadow-card'>
            <div className='aspect-[4/5] w-[88px] rounded-image bg-muted' />
            <div className='flex flex-1 flex-col gap-2 py-1'>
                <div className='h-4 w-4/5 rounded bg-muted' />
                <div className='h-3 w-1/2 rounded bg-muted' />
                <div className='mt-auto h-6 w-1/3 rounded bg-muted' />
            </div>
        </li>
    );
}
