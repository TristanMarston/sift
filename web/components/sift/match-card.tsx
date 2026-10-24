'use client';

import { motion } from 'motion/react';
import { Skeleton } from '@/components/ui/skeleton';
import { est } from '@/lib/format';
import { spring } from '@/lib/motion';
import type { Match, Receipt } from '@/lib/types';
import { cn } from '@/lib/utils';
import { HeartButton } from './heart-button';
import { ListingImage } from './listing-image';
import { MarketLine, PriceLine } from './market-line';
import { ReasonChip } from './reason-chip';
import { EstTag, StatusDot } from './status-badge';

type Props = {
    match: Match;
    size?: 'large' | 'compact'; // large for Exact match, compact for the Similar style grid
    liked?: boolean;
    onLike?: () => void;
    moved?: number; // places moved up after Update; the marker fades after ~2s
    isNew?: boolean; // entered the list after Update
    className?: string;
};

/** One resale listing. `layout` lets cards glide to new positions when the list re-ranks. */
export function MatchCard({ match, size = 'large', liked = false, onLike, moved, isNew, className }: Props) {
    const { listing: l, reasons, receipt } = match;
    const large = size === 'large';
    return (
        <motion.article layout='position' transition={spring.ui} className={cn('flex flex-col gap-3', large && 'rounded-card bg-card p-3 shadow-card', className)}>
            <ListingImage src={l.image_url} art={l.art} alt={l.title}>
                <div className='absolute top-2.5 left-2.5 flex gap-1.5'>
                    {moved ? (
                        // Shows, holds, then fades out on its own (~2.8s).
                        <motion.span
                            key={moved}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: [0, 1, 1, 0], y: [6, 0, 0, 0] }}
                            transition={{ duration: 2.8, times: [0, 0.12, 0.85, 1], ease: 'easeOut' }}
                            className='rounded-tag bg-primary px-1.5 py-0.5 type-label tabular text-primary-foreground'
                        >
                            <span aria-hidden>▲ </span>
                            <span className='sr-only'>Moved up </span>
                            {moved}
                        </motion.span>
                    ) : null}
                    {isNew && (
                        <motion.span initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={spring.pop} className='rounded-tag bg-primary-tint px-1.5 py-0.5 type-label text-primary-tint-foreground'>
                            NEW
                        </motion.span>
                    )}
                </div>
                {onLike && <HeartButton liked={liked} onToggle={onLike} className='absolute top-2 right-2' />}
            </ListingImage>

            <div className={cn('flex flex-col gap-1.5', large && 'px-1 pb-1')}>
                {large ? (
                    <div className='flex items-start justify-between gap-3'>
                        <h3 className='type-headline'>{l.title}</h3>
                        <PriceLine cents={l.price_cents} retailCents={l.retail_price_cents} className='flex-col items-end gap-0' />
                    </div>
                ) : (
                    <>
                        <h3 className='line-clamp-2 type-callout'>{l.title}</h3>
                        <PriceLine cents={l.price_cents} retailCents={l.retail_price_cents} />
                    </>
                )}
                <MarketLine parts={[l.marketplace, `Size ${l.size}`, large ? l.condition : undefined]} />
                <div className='mt-1 flex flex-wrap gap-1.5'>
                    {(large ? reasons : reasons.slice(0, 2)).map((r) => (
                        <ReasonChip key={r.label} {...r} />
                    ))}
                </div>
                {receipt && <ReceiptSummary receipt={receipt} />}
            </div>
        </motion.article>
    );
}

/** One-line digest of a receipt: 2 verified · 1 unknown · 4.1 kg CO₂ est. */
export function ReceiptSummary({ receipt }: { receipt: Receipt }) {
    const n = (s: string) => receipt.badges.filter((b) => b.status === s).length;
    return (
        <p className='mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 type-footnote text-muted-foreground'>
            {(['verified', 'claimed', 'unknown'] as const).map((s) =>
                n(s) ? (
                    <span key={s} className='inline-flex items-center gap-1.5'>
                        <StatusDot status={s} />
                        {n(s)} {s}
                    </span>
                ) : null,
            )}
            <span className='inline-flex items-center gap-1.5 tabular'>
                {est(receipt.co2_saved_kg_est)} kg CO₂ saved <EstTag />
            </span>
        </p>
    );
}

/** Placeholder while results load. Breathes gently (Skeleton's pulse), never spins. */
export function MatchCardSkeleton({ size = 'large' }: { size?: 'large' | 'compact' }) {
    return (
        <div className={cn('flex flex-col gap-3', size === 'large' && 'rounded-card bg-card p-3 shadow-card')}>
            <Skeleton className='aspect-[4/5] rounded-image' />
            <Skeleton className='h-4 w-2/3 rounded-pill' />
            <Skeleton className='h-3 w-1/3 rounded-pill' />
        </div>
    );
}
