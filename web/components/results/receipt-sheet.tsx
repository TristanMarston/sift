'use client';

import { ChevronDown, ExternalLink, X } from 'lucide-react';
import { AnimatePresence, motion, useDragControls, type PanInfo } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { Button } from '@/components/ui/button';
import { ecoParts, wearReasons } from '@/lib/explain';
import { ease, spring } from '@/lib/motion';
import { CONDITION, levelText, MARKET, perWearText, priceText, typicalText } from '@/lib/results';
import type { Fact, Level, Result, SearchResponse } from '@/lib/search';
import { useMedia } from '@/lib/use-media';
import { breakEvenVerdict } from '@/lib/wear';
import { cn } from '@/lib/utils';
import { useMarkerStyle, type MarkerStyle } from '@/lib/marker-style';
import { FactRow, LevelDots, noEvidence, sentence } from './evidence';
import { EcoHero, LevelBadge } from './markers';
import { ListingPhoto } from './result-row';

const QUALITY: Record<Level, string> = {
    high: 'Several signs it’s built to last.',
    medium: 'Some signs it’s built to last.',
    low: 'Signs it may wear out sooner than most.',
    unknown: 'Not enough evidence yet. It stays in the list, with no boost.',
};

const CONFIDENCE: Record<Level, string> = {
    high: 'Several firm facts stand behind this estimate.',
    medium: 'Some firm evidence stands behind this estimate.',
    low: 'Only likely facts stand behind this estimate.',
    unknown: 'No evidence yet, so the estimate is the typical lifespan for the category.',
};

// What each eco part says when the listing gives nothing for it.
const EMPTY: Record<string, string> = { fibers: 'Not stated', durability: 'Typical for the category', shipping: 'Not stated', circularity: 'Nothing extra stated' };

type Props = { r: Result; typical: SearchResponse['typical']; count?: number; onClose: () => void };

/** "Oct 24" from the listing's scraped_at. Undefined when the API didn't send one (older responses, saved samples). */
const checked = (iso?: string) => {
    const d = iso ? new Date(iso) : null;
    return d && !Number.isNaN(d.getTime()) ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : undefined;
};

/**
 * Everything behind one result's cost per wear, in plain cards: the math first (price ÷ expected wears, and how the
 * wears were reached), then quality, eco and a typical look-alike. Each card shows a summary; its evidence and
 * sources open with a button. The link to buy sits right under the item. Phone: a sheet from the bottom (drag the
 * handle down to close). Desktop: a panel from the right. The photo grows out of the row it came from.
 */
export function ReceiptSheet({ r, typical, count, onClose }: Props) {
    const wide = useMedia('(min-width: 1024px)');
    const drag = useDragControls();
    const panel = useRef<HTMLDivElement>(null);

    useEffect(() => {
        panel.current?.focus();
        const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    // Close on a firm pull or a quick flick down, using the finger's speed, not just where it let go.
    const onDragEnd = (_: unknown, info: PanInfo) => {
        if (info.offset.y + info.velocity.y * 0.2 > 140) onClose();
    };

    const off = wide ? { x: '100%' } : { y: '100%' };
    const w = r.wear;
    const c = r.cost;
    const cpw = perWearText(w.cpw_cents.at_mid);
    const [fullTitle, setFullTitle] = useState(false);

    return (
        <>
            <motion.div className='fixed inset-0 z-30 bg-black/40' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25, ease: ease.out }} onClick={onClose} aria-hidden />
            <motion.div
                ref={panel}
                role='dialog'
                aria-modal='true'
                aria-label={`Why ${r.title} is ${cpw} a wear`}
                tabIndex={-1}
                className={cn(
                    'fixed z-40 flex flex-col bg-background text-foreground shadow-float outline-none',
                    wide ? 'inset-y-0 right-0 w-[min(460px,100vw)]' : 'inset-x-0 bottom-0 max-h-[92dvh] rounded-t-sheet',
                )}
                initial={off}
                animate={{ x: 0, y: 0 }}
                exit={off}
                transition={spring.sheet}
                drag={wide ? false : 'y'}
                dragControls={drag}
                dragListener={false}
                dragConstraints={{ top: 0, bottom: 0 }}
                dragElastic={{ top: 0, bottom: 0.9 }}
                onDragEnd={onDragEnd}
            >
                {/* Handle (phone) and close */}
                <div className='relative flex h-11 shrink-0 items-center justify-center' onPointerDown={(e) => !wide && drag.start(e)} style={{ touchAction: 'none' }}>
                    {!wide && <span className='h-1.5 w-10 rounded-pill bg-muted-foreground/30' />}
                    <Button variant='ghost' size='icon-sm' aria-label='Close' onClick={onClose} className='absolute top-1.5 right-2'>
                        <X strokeWidth={1.75} />
                    </Button>
                </div>

                <div className='flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]'>
                    {/* The item, and the way to buy it */}
                    <div className='flex gap-4'>
                        <ListingPhoto r={r} className='w-[104px]' />
                        <div className='flex min-w-0 flex-1 flex-col gap-2'>
                            {/* Two lines at most; tap to read the rest of a long listing title. */}
                            <h2 onClick={() => setFullTitle((f) => !f)} className={cn('type-headline text-pretty', !fullTitle && 'line-clamp-2 cursor-pointer')}>
                                {r.title}
                            </h2>
                            {/* Size and condition decide whether it's worth tapping through, so they're chips, not fine print. */}
                            <div className='flex flex-wrap gap-1.5'>
                                <span className='rounded-pill bg-foreground px-2.5 py-1 type-footnote font-semibold text-background'>{r.size ? `Size ${r.size}` : 'Size unknown'}</span>
                                <span className='rounded-pill bg-secondary px-2.5 py-1 type-footnote font-semibold'>{r.condition ? CONDITION[r.condition] : 'Condition unknown'}</span>
                            </div>
                            <p className='type-footnote text-muted-foreground'>
                                {MARKET[r.marketplace]}, {Math.round(r.match.similarity * 100)}% look match
                            </p>
                        </div>
                    </div>
                    <div>
                        <Button size='lg' className='w-full' render={<a href={r.url} target='_blank' rel='noreferrer' />} nativeButton={false}>
                            View on {MARKET[r.marketplace]}
                            <ExternalLink data-icon='inline-end' strokeWidth={1.75} />
                        </Button>
                        {checked(r.scraped_at) && <p className='mt-1.5 text-center type-footnote text-muted-foreground'>Price checked {checked(r.scraped_at)}. Listings can sell or change.</p>}
                    </div>

                    {/* The math: price ÷ expected wears, then how the wears were reached */}
                    <Card>
                        <h3 className='flex items-center gap-2 type-title-2'>
                            Why it’s {cpw} a wear <EstTag />
                        </h3>
                        <div className='mt-4 grid grid-cols-[1fr_auto_1fr_auto_1fr] items-start gap-x-2 text-center'>
                            <Term value={priceText(c.total_cents)} label='Price with shipping and fees' />
                            <Op>÷</Op>
                            <Term value={String(w.expected_wears.mid)} label='Wears it should last' />
                            <Op>=</Op>
                            <Term value={cpw} label='Cost per wear' strong />
                        </div>

                        <div className='mt-5 rounded-image bg-secondary p-3'>
                            <p className='type-callout font-semibold'>How we got {w.expected_wears.mid} wears</p>
                            <ul className='mt-2 flex flex-col gap-2'>
                                {wearReasons(r).map((s) => (
                                    <li key={s.label} className='type-footnote text-pretty'>
                                        <span className='text-muted-foreground'>{s.label}: </span>
                                        {sentence(s.value)}
                                    </li>
                                ))}
                            </ul>
                            <p className='mt-2 type-footnote text-pretty text-muted-foreground'>
                                So about {w.expected_wears.mid}, somewhere between {w.expected_wears.low} and {w.expected_wears.high}.
                            </p>
                        </div>

                        <p className='mt-5 type-callout font-semibold'>If you wear it</p>
                        <div className='mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4'>
                            {(
                                [
                                    ['30 times', w.cpw_cents.at_30],
                                    ['60 times', w.cpw_cents.at_60],
                                    ['100 times', w.cpw_cents.at_100],
                                    [`${w.expected_wears.mid} times (expected)`, w.cpw_cents.at_mid],
                                ] as const
                            ).map(([label, cents], i) => (
                                <div key={label} className={cn('rounded-image px-3 py-2', i === 3 ? 'bg-primary text-primary-foreground' : 'bg-secondary')}>
                                    <p className='type-headline tabular'>{perWearText(cents)}</p>
                                    <p className={cn('type-footnote', i === 3 ? 'text-primary-foreground/80' : 'text-muted-foreground')}>{label}</p>
                                </div>
                            ))}
                        </div>

                        <Details label='Show the numbers behind this'>
                            <ul className='flex flex-col gap-1.5 pb-2 type-footnote text-pretty'>
                                <li>Listed at {priceText(c.price_cents)}</li>
                                <li>{c.free_shipping ? 'Free shipping' : c.shipping_cents !== null ? `Shipping ${priceText(c.shipping_cents)}` : 'Shipping unknown'}</li>
                                {c.fee_cents > 0 && (
                                    <li>
                                        {MARKET[r.marketplace]} buyer fee {r.marketplace === 'depop' ? 'up to ' : ''}
                                        {priceText(c.fee_cents)}
                                    </li>
                                )}
                                {c.original_price_cents !== null && c.original_price_cents > c.price_cents && <li>Seller marked it down from {priceText(c.original_price_cents)}</li>}
                                {c.retail_price_cents !== null && <li>New retail {priceText(c.retail_price_cents)}</li>}
                            </ul>
                            <Facts facts={w.facts} />
                        </Details>
                    </Card>

                    <QualityCard r={r} />
                    <EcoCard eco={r.eco} />

                    {typical && (
                        <Card>
                            <h3 className='type-headline'>Compared with a typical look-alike</h3>
                            <Bars rows={[{ label: 'This one', cents: w.cpw_cents.at_mid, strong: true }, { label: 'Typical', cents: typical.cpw_cents }]} />
                            <p className='mt-3 type-callout font-semibold text-pretty'>
                                {
                                    {
                                        cheaper: 'It costs less than a typical look-alike up front.',
                                        wins: `It costs more up front, but wear it ${w.break_even_wears}+ times and it works out cheaper.`,
                                        never: `It costs more up front and likely won’t make it back: that takes ${w.break_even_wears}+ wears, more than the ${w.expected_wears.high} it should last.`,
                                    }[breakEvenVerdict(w.break_even_wears, w.expected_wears.high)]
                                }
                            </p>
                            <p className='mt-2 type-footnote text-pretty text-muted-foreground'>{typicalText(typical, count)}</p>
                        </Card>
                    )}

                    <p className='flex flex-wrap items-center gap-x-2 px-1 pt-1 type-footnote text-pretty text-muted-foreground'>
                        <span className='font-semibold text-foreground'>How sure we are: {levelText(r.confidence)}</span>
                        {r.confidence !== 'unknown' && <LevelDots level={r.confidence} className='text-foreground' />}
                        <span>{CONFIDENCE[r.confidence]}</span>
                    </p>
                </div>
            </motion.div>
        </>
    );
}

/** Quality: the level and what it means, then the evidence behind a button. `style` forces a marker look. */
export function QualityCard({ r, style }: { r: Result; style?: MarkerStyle }) {
    const level = noEvidence(r) ? 'unknown' : r.quality.level;
    return (
        <Card>
            <h3 className='flex items-center justify-between gap-3 type-headline'>
                Quality
                <LevelBadge kind='quality' level={level} style={style} />
            </h3>
            <p className='mt-2 type-callout text-pretty text-muted-foreground'>{QUALITY[level]}</p>
            {r.quality.facts.length > 0 && (
                <Details label={`Show the evidence (${r.quality.facts.length})`}>
                    <Facts facts={r.quality.facts} />
                </Details>
            )}
        </Card>
    );
}

/** The eco score's four parts, each with what the listing says for it, then the evidence behind a button. */
export function EcoCard({ eco, style: forced }: { eco: Result['eco']; style?: MarkerStyle }) {
    const chosen = useMarkerStyle();
    const style = forced ?? chosen;
    const parts = ecoParts(eco);
    const facts = parts.flatMap((p) => p.facts);
    return (
        <Card>
            <h3 className='flex items-center justify-between gap-3 type-headline'>
                Eco
                {/* The dots look keeps the level by the title; the others show it big just below. */}
                {style === 'dots' || style === 'chips' ? <LevelBadge kind='eco' level={eco.level} style={style} /> : null}
            </h3>
            <EcoHero eco={eco} style={style} />
            <p className='mt-1 type-footnote text-pretty text-muted-foreground'>Every listing here is secondhand, so none needs a new garment made. The score compares them on four things:</p>
            <ul className='mt-3 flex flex-col gap-3'>
                {parts.map((p) => (
                    <li key={p.key}>
                        <p className='flex items-baseline justify-between gap-3 type-footnote'>
                            <span className='font-semibold'>{p.label}</span>
                            <span className='shrink-0 text-muted-foreground'>{Math.round(p.weight * 100)}% of the score</span>
                        </p>
                        {p.score !== null && (
                            <div className='mt-1 h-1.5 overflow-hidden rounded-pill bg-secondary' role='img' aria-label={`${Math.round(p.score * 100)} out of 100`}>
                                <div className='h-full rounded-pill bg-primary' style={{ width: `${Math.round(p.score * 100)}%` }} />
                            </div>
                        )}
                        <p className='mt-1 type-footnote text-pretty text-muted-foreground'>
                            {p.facts.length ? p.facts.map((f) => (p.key === 'circularity' && f.kind !== 'certification' ? f.label : sentence(f.value))).join(', ') : EMPTY[p.key]}
                        </p>
                    </li>
                ))}
            </ul>
            {facts.length > 0 && (
                <Details label={`Show the evidence (${facts.length})`}>
                    <Facts facts={facts} />
                </Details>
            )}
        </Card>
    );
}

const Card = ({ children }: { children: React.ReactNode }) => <section className='rounded-card bg-card p-4 shadow-card'>{children}</section>;

function Term({ value, label, strong }: { value: string; label: string; strong?: boolean }) {
    return (
        <div className='min-w-0'>
            <p className={cn('font-serif text-[26px] leading-8 tracking-tight tabular', strong && 'text-primary')}>{value}</p>
            <p className='mt-1 type-footnote text-balance text-muted-foreground'>{label}</p>
        </div>
    );
}

const Op = ({ children }: { children: React.ReactNode }) => (
    <span aria-hidden className='pt-1 type-headline text-muted-foreground'>
        {children}
    </span>
);

/** Cost per wear side by side, as bars on the same scale. */
function Bars({ rows }: { rows: { label: string; cents: number; strong?: boolean }[] }) {
    const max = Math.max(...rows.map((r) => r.cents), 1);
    return (
        <div className='mt-3 flex flex-col gap-2'>
            {rows.map((r) => (
                <div key={r.label} className='grid grid-cols-[4.5rem_1fr_auto] items-center gap-3 type-footnote'>
                    <span className={r.strong ? 'font-semibold' : 'text-muted-foreground'}>{r.label}</span>
                    <div className='h-2.5 overflow-hidden rounded-pill bg-secondary'>
                        <div className={cn('h-full rounded-pill', r.strong ? 'bg-primary' : 'bg-muted-foreground/50')} style={{ width: `${(r.cents / max) * 100}%` }} />
                    </div>
                    <span className={cn('tabular', r.strong && 'font-semibold')}>{perWearText(r.cents)} a wear</span>
                </div>
            ))}
        </div>
    );
}

/** The evidence and its sources, one tap away so the card stays short. */
function Details({ label, children }: { label: string; children: React.ReactNode }) {
    const [open, setOpen] = useState(false);
    return (
        <div className='mt-4'>
            <button
                type='button'
                aria-expanded={open}
                onClick={() => setOpen((o) => !o)}
                className='inline-flex h-9 items-center gap-1.5 rounded-pill bg-secondary px-3.5 type-footnote font-semibold outline-none transition-transform duration-100 active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-ring'
            >
                {open ? 'Hide' : label}
                <ChevronDown className={cn('size-4 transition-transform duration-200', open && 'rotate-180')} strokeWidth={1.75} aria-hidden />
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div key='details' className='overflow-hidden' initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={spring.ui}>
                        <div className='pt-3'>{children}</div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

const Facts = ({ facts }: { facts: Fact[] }) => (
    <ul>
        {facts.map((f, i) => (
            <FactRow key={`${f.kind}-${i}`} fact={f} />
        ))}
    </ul>
);
