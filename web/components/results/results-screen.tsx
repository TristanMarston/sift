'use client';

import { ChevronLeft, SearchX, WifiOff } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useState } from 'react';
import type { Shot } from '@/components/camera/capture';
import type { GarmentSearch } from '@/components/scan/scan-flow';
import { GarmentCutout } from '@/components/sift/garment-tabs';
import { Notice } from '@/components/sift/notice';
import { ThemeToggle } from '@/components/sift/theme-toggle';
import { Button } from '@/components/ui/button';
import { ease, spring } from '@/lib/motion';
import { headline, ordered, perWearText, priceText } from '@/lib/results';
import type { Sort } from '@/lib/search';
import type { Garment } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ReceiptSheet } from './receipt-sheet';
import { ResultRow, RowSkeleton } from './result-row';
import { SortControl } from './sort-control';

type Props = {
    shot: Shot;
    garments: Garment[];
    searches: Record<string, GarmentSearch>;
    selected: string;
    onSelect: (id: string) => void;
    onBack: () => void;
    onRetry: (id: string) => void;
};

const fade = (delay = 0) => ({ initial: { opacity: 0 }, animate: { opacity: 1, transition: { delay, duration: 0.35, ease: ease.out } } });
const rows = { show: { transition: { staggerChildren: 0.04, delayChildren: 0.15 } } };

/**
 * Look-alikes for one garment, ranked by cost per wear. The backend sends every order; switching sorts only
 * picks another list, so the rows reshuffle instantly. Tap a row for its Wear Receipt.
 */
export function ResultsScreen({ shot, garments, searches, selected, onSelect, onBack, onRetry }: Props) {
    const [sort, setSort] = useState<Sort>('cpw');
    const [openId, setOpenId] = useState<string | null>(null);
    const garment = garments.find((g) => g.id === selected) ?? garments[0];
    const current = searches[garment.id];
    const resp = current?.status === 'done' ? current.resp : null;
    const list = resp ? ordered(resp, sort) : [];
    const head = resp && sort === 'cpw' ? headline(resp) : null;
    const open = resp?.results.find((r) => r.id === openId) ?? null;

    const status = !current || current.status === 'loading' ? 'Searching…' : current.status === 'error' ? "The search didn't finish" : `${list.length} look-${list.length === 1 ? 'alike' : 'alikes'}`;

    return (
        <motion.div className='fixed inset-0 z-10' exit={{ opacity: 0, transition: { duration: 0.25 } }}>
            {/* Only the background fades from the dark camera, so the garment flying in stays solid. */}
            <motion.div className='absolute inset-0 bg-background' initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4, ease: ease.out }} />
            <div className={cn('absolute inset-0 text-foreground', open ? 'overflow-hidden' : 'overflow-y-auto')}>
                <motion.header {...fade(0.1)} className='sticky top-0 z-20 flex h-[calc(3.5rem+env(safe-area-inset-top))] items-center justify-between bg-background/85 px-2 pt-[env(safe-area-inset-top)] backdrop-blur-md'>
                    <Button variant='ghost' size='sm' onClick={onBack} className='pl-2'>
                        <ChevronLeft data-icon='inline-start' strokeWidth={1.75} />
                        Photo
                    </Button>
                    {resp?.sample && <span className='rounded-pill bg-secondary px-2.5 py-1 type-footnote font-semibold text-muted-foreground'>Sample results</span>}
                    <ThemeToggle />
                </motion.header>

                <main className='mx-auto w-full max-w-5xl px-4 pb-16 lg:px-8'>
                    {/* Your garment: it flies here from the photo (same layoutId as in the camera). */}
                    <section className='flex flex-col gap-3 pt-1 pb-4'>
                        {garments.length > 1 && (
                            <div role='tablist' aria-label='Garments in your photo' className='flex gap-2.5 overflow-x-auto [scrollbar-width:none]'>
                                {garments.map((g) => (
                                    <button key={g.id} type='button' role='tab' aria-selected={g.id === garment.id} aria-label={g.label} onClick={() => (onSelect(g.id), setOpenId(null))} className='relative shrink-0 rounded-image outline-none focus-visible:ring-2 focus-visible:ring-ring'>
                                        <motion.div layoutId={`garment-${g.id}`} transition={spring.ui} className='size-16 rounded-image bg-card p-1.5 shadow-card'>
                                            <GarmentCutout garment={g} src={shot.url} aspect={shot.aspect} />
                                        </motion.div>
                                        {g.id === garment.id && <motion.span layoutId='garment-ring' transition={spring.ui} className='absolute inset-0 rounded-image ring-2 ring-primary' />}
                                    </button>
                                ))}
                            </div>
                        )}
                        <div className='flex items-center gap-3.5'>
                            {garments.length === 1 && (
                                <motion.div layoutId={`garment-${garment.id}`} transition={spring.ui} className='size-16 shrink-0 rounded-image bg-card p-1.5 shadow-card'>
                                    <GarmentCutout garment={garment} src={shot.url} aspect={shot.aspect} />
                                </motion.div>
                            )}
                            <motion.div {...fade(0.15)} className='min-w-0'>
                                <h1 className='truncate type-title-1'>{garment.label}</h1>
                                <p className='type-footnote text-muted-foreground' aria-live='polite'>
                                    {status}
                                </p>
                            </motion.div>
                        </div>
                    </section>

                    {resp && list.length > 0 && (
                        <>
                            <motion.div {...fade(0.2)} className='sticky top-[calc(3.5rem+env(safe-area-inset-top))] z-10 -mx-4 bg-background/85 px-4 py-2 backdrop-blur-md lg:-mx-8 lg:px-8'>
                                <SortControl value={sort} onChange={setSort} className='lg:max-w-xl' />
                            </motion.div>

                            <AnimatePresence initial={false} mode='popLayout'>
                                {head && (
                                    <motion.div key={head.kind} layout initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={spring.ui} className='pt-3 pb-1'>
                                        <p className='type-title-2 text-balance'>{head.kind === 'drops' ? `The cheapest match drops to #${head.rank}` : 'The cheapest match is also the best value per wear'}</p>
                                        {resp.typical && (
                                            <p className='mt-1 type-footnote text-muted-foreground'>
                                                The typical match costs {priceText(resp.typical.price_cents)}, about {perWearText(resp.typical.cpw_cents)} a wear.
                                            </p>
                                        )}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <motion.ol key={garment.id} initial='hidden' animate='show' variants={rows} className='mt-3 grid gap-3 lg:grid-cols-2'>
                                {list.map((r, i) => (
                                    <ResultRow key={r.id} r={r} rank={i + 1} sort={sort} cheapest={r.id === resp.headline.cheapest_id} open={r.id === openId} onOpen={() => setOpenId(r.id)} />
                                ))}
                            </motion.ol>

                            <p className='mt-8 max-w-prose type-footnote text-pretty text-muted-foreground'>
                                Listings from Depop, Poshmark, Grailed, Mercari and eBay. Cost per wear is the price divided by how many times it&apos;s likely to be worn, an estimate.
                                {resp.sample && ` ${resp.sample.note}`}
                            </p>
                        </>
                    )}

                    {(!current || current.status === 'loading') && (
                        <ol className='mt-3 grid gap-3 lg:grid-cols-2' aria-hidden>
                            {Array.from({ length: 6 }, (_, i) => (
                                <RowSkeleton key={i} />
                            ))}
                        </ol>
                    )}

                    {current?.status === 'error' && (
                        <Notice
                            icon={WifiOff}
                            title="Couldn't load look-alikes"
                            body="The search didn't answer. Check the connection and try again."
                            actions={<Button onClick={() => onRetry(garment.id)}>Try again</Button>}
                        />
                    )}

                    {resp && list.length === 0 && (
                        <Notice
                            icon={SearchX}
                            title='Nothing close yet'
                            body='No listing looked enough like this. Try a clearer photo of just this piece.'
                            actions={
                                <Button variant='secondary' onClick={onBack}>
                                    Back to the photo
                                </Button>
                            }
                        />
                    )}
                </main>
            </div>

            <AnimatePresence>{open && resp && <ReceiptSheet key={open.id} r={open} typical={resp.typical} onClose={() => setOpenId(null)} />}</AnimatePresence>
        </motion.div>
    );
}
