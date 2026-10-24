'use client';

import { AnimatePresence } from 'motion/react';
import Image from 'next/image';
import { useEffect, useState } from 'react';
import { photoOf } from '@/components/results/result-row';
import { ReceiptSheet } from '@/components/results/receipt-sheet';
import { MARKET, perWearText, priceText } from '@/lib/results';
import type { Result, SearchResponse } from '@/lib/search';
import { useMedia } from '@/lib/use-media';
import { cn } from '@/lib/utils';

type WallItem = { category: string; typical: SearchResponse['typical']; result: Result };
type Wall = { meta: { source: string; index_size: number }; items: WallItem[] };

// Seconds per card: each column drifts at its own slow pace (roughly 25px a second), so the wall never lines up.
const PACE = [9, 10.5, 9.6];

/**
 * G · Real listings from the live catalog drift up the screen in columns, each card showing what it costs per
 * wear. There is no beginning or end, so any glance shows the product working. Tap a card for its Wear Receipt.
 */
export function HeroWall() {
    const wide = useMedia('(min-width: 1024px)');
    // Three columns everywhere: on a phone, smaller square cards so several rows show at once and it reads as a wall.
    const [wall, setWall] = useState<Wall | null>(null);
    const [open, setOpen] = useState<WallItem | null>(null);

    useEffect(() => {
        let alive = true;
        fetch('/landing/wall.json')
            .then((r) => r.json() as Promise<Wall>)
            .then((w) => alive && setWall(w), () => {});
        return () => {
            alive = false;
        };
    }, []);

    const n = 3;
    const columns = Array.from({ length: n }, (_, c) => (wall?.items ?? []).filter((_, k) => k % n === c));

    return (
        <div className='absolute inset-0 overflow-hidden px-4 lg:px-0'>
            <div className='absolute inset-x-4 inset-y-0 grid gap-2 [mask-image:linear-gradient(to_bottom,transparent,#000_6%,#000_78%,transparent)] lg:inset-x-0 lg:gap-4' style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
                {wall
                    ? columns.map((items, c) => (
                          <div key={c} className={cn('wall-drift flex flex-col gap-2 lg:gap-4', open && '[animation-play-state:paused]')} style={{ '--dur': `${items.length * PACE[c % PACE.length]}s`, '--delay': `${-c * 23}s` } as React.CSSProperties}>
                              {[...items, ...items].map((it, k) => (
                                  <WallCard key={`${it.result.id}-${k}`} it={it} copy={k >= items.length} wide={wide} onOpen={() => setOpen(it)} />
                              ))}
                          </div>
                      ))
                    : Array.from({ length: n }, (_, c) => (
                          <div key={c} className='flex flex-col gap-3' aria-hidden>
                              {Array.from({ length: 4 }, (_, k) => (
                                  <div key={k} className='aspect-square animate-pulse rounded-[16px] bg-stage-foreground/10 lg:aspect-[4/5] lg:rounded-card' />
                              ))}
                          </div>
                      ))}
            </div>

            {/* The one line to read from across the room. */}
            <div className='pointer-events-none absolute inset-x-0 bottom-0 flex justify-center bg-linear-to-t from-stage via-stage/90 to-transparent px-4 pt-14 pb-2 lg:pt-20'>
                <p className='rounded-pill bg-stage-foreground px-4 py-2 text-center type-headline text-stage lg:px-6 lg:py-3 lg:text-[24px] lg:leading-8'>
                    {(wall?.meta.index_size ?? 20501).toLocaleString('en-US')} listings, ranked by cost per wear
                </p>
            </div>

            <AnimatePresence>{open && <ReceiptSheet key={open.result.id} r={open.result} typical={open.typical} onClose={() => setOpen(null)} />}</AnimatePresence>
        </div>
    );
}

/** One listing on the wall: its photo, what it costs per wear (big), and its price and market. */
function WallCard({ it, copy, wide, onOpen }: { it: WallItem; copy: boolean; wide: boolean; onOpen: () => void }) {
    const r = it.result;
    return (
        <button
            type='button'
            onClick={onOpen}
            tabIndex={copy ? -1 : 0}
            aria-hidden={copy || undefined}
            aria-label={copy ? undefined : `${r.title}: ${perWearText(r.wear.cpw_cents.at_mid)} a wear. Open its Wear Receipt`}
            className='flex flex-col gap-1.5 rounded-[16px] bg-card p-1.5 text-left text-card-foreground shadow-card outline-none transition-transform duration-100 active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-ring lg:gap-2 lg:rounded-card lg:p-2.5'
        >
            <span className={cn('relative overflow-hidden rounded-image bg-muted', wide ? 'aspect-[4/5]' : 'aspect-square')}>
                <Image src={photoOf(r)} alt='' fill sizes='(min-width: 1024px) 220px, 30vw' quality={70} className='object-cover' />
            </span>
            <span className='px-0.5 pb-0.5 lg:px-1'>
                <span className='flex items-baseline gap-1'>
                    <span className='font-serif text-[21px] leading-6 tracking-tight tabular lg:text-[34px] lg:leading-9'>{perWearText(r.wear.cpw_cents.at_mid)}</span>
                    <span className='text-[12px] text-muted-foreground lg:type-footnote'>/wear</span>
                </span>
                <span className='block truncate text-[12px] leading-4 text-muted-foreground lg:type-footnote'>
                    {priceText(r.cost.total_cents)} · {MARKET[r.marketplace]}
                </span>
            </span>
        </button>
    );
}
