'use client';

import { ExternalLink, X } from 'lucide-react';
import { motion, useDragControls, type PanInfo } from 'motion/react';
import { useEffect, useRef } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { Button } from '@/components/ui/button';
import { ease, spring } from '@/lib/motion';
import { levelText, MARKET, marketLine, perWearText, priceText } from '@/lib/results';
import type { Fact, Level, Result, SearchResponse } from '@/lib/search';
import { useMedia } from '@/lib/use-media';
import { breakEvenVerdict } from '@/lib/wear';
import { cn } from '@/lib/utils';
import { FactLine, LevelDots, noEvidence } from './evidence';
import { ListingPhoto } from './result-row';

const CONFIDENCE: Record<Level, string> = {
    high: 'Several firm facts stand behind this estimate.',
    medium: 'Some firm evidence stands behind this estimate.',
    low: 'Only likely facts stand behind this estimate.',
    unknown: 'No evidence yet: the estimate is the typical lifespan for the category.',
};

type Props = { r: Result; typical: SearchResponse['typical']; onClose: () => void };

/**
 * The Wear Receipt: everything behind one result, line by line, on receipt paper. Every line opens to its source,
 * status and date; anything we don't know says unknown. Phone: a sheet from the bottom (drag the handle down to
 * close). Desktop: a panel from the right. The photo grows out of the row it came from.
 */
export function ReceiptSheet({ r, typical, onClose }: Props) {
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

    return (
        <>
            <motion.div className='fixed inset-0 z-30 bg-black/40' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25, ease: ease.out }} onClick={onClose} aria-hidden />
            <motion.div
                ref={panel}
                role='dialog'
                aria-modal='true'
                aria-label={`Wear Receipt: ${r.title}`}
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
                    <Button variant='ghost' size='icon-sm' aria-label='Close receipt' onClick={onClose} className='absolute top-1.5 right-2'>
                        <X strokeWidth={1.75} />
                    </Button>
                </div>

                <div className='min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]'>
                    {/* The item */}
                    <div className='flex gap-4'>
                        <ListingPhoto r={r} className='w-[120px]' />
                        <div className='flex min-w-0 flex-1 flex-col gap-1'>
                            <h2 className='line-clamp-3 type-headline text-pretty'>{r.title}</h2>
                            <p className='type-footnote text-muted-foreground'>{marketLine(r)}</p>
                            <p className='type-footnote text-muted-foreground'>
                                {Math.round(r.match.similarity * 100)}% look match{r.match.band === 'exact' ? ' · Exact match' : ''}
                            </p>
                            <p className='mt-auto flex items-baseline gap-1.5'>
                                <span className='font-serif text-[34px] leading-9 tracking-tight tabular'>{perWearText(w.cpw_cents.at_mid)}</span>
                                <span className='type-callout text-muted-foreground'>a wear</span>
                                <EstTag className='self-center' />
                            </p>
                        </div>
                    </div>

                    {/* The receipt */}
                    <div className='mt-5 bg-receipt-paper px-4 pt-4 pb-6 text-receipt-ink receipt-edge-bottom'>
                        <p className='flex items-baseline justify-between type-label text-receipt-ink/70'>
                            <span>SIFT · WEAR RECEIPT</span>
                            <span>{MARKET[r.marketplace].toUpperCase()}</span>
                        </p>

                        <Section label='COST' value={priceText(c.total_cents)}>
                            <Lines
                                lines={[
                                    c.original_price_cents && c.original_price_cents > c.price_cents ? `Seller marked it down from ${priceText(c.original_price_cents)}` : null,
                                    c.free_shipping ? 'Free shipping' : c.shipping_cents !== null ? `Includes ${priceText(c.shipping_cents)} shipping` : 'Shipping unknown',
                                    c.fee_cents ? `Includes ${r.marketplace === 'depop' ? 'up to ' : ''}${priceText(c.fee_cents)} ${MARKET[r.marketplace]} buyer fee` : null,
                                    c.retail_price_cents ? `New retail ${priceText(c.retail_price_cents)}` : null,
                                ]}
                            />
                        </Section>

                        <Section label='QUALITY' value={<LevelValue level={r.quality.level} />}>
                            {noEvidence(r) ? <p className='py-1.5 type-receipt'>Not enough evidence yet. It stays in the list, with no boost.</p> : <Facts facts={r.quality.facts} />}
                        </Section>

                        <Section label='ECO' value={<LevelValue level={r.eco.level} />}>
                            {r.eco.facts.length ? <Facts facts={r.eco.facts} /> : <p className='py-1.5 type-receipt'>No eco facts stated.</p>}
                        </Section>

                        <Section label='EXPECTED WEARS' value={`${w.expected_wears.low}–${w.expected_wears.high}`} estimate>
                            <Lines lines={[w.basis === 'category_baseline' ? 'No quality evidence, so this is the typical lifespan for the category.' : `About ${w.expected_wears.mid} in the middle of the range.`]} />
                            <Facts facts={w.facts} />
                        </Section>

                        <Section label='COST PER WEAR' estimate>
                            <div className='grid grid-cols-4 gap-1 pt-2 text-center'>
                                {(
                                    [
                                        ['30 wears', w.cpw_cents.at_30],
                                        ['60 wears', w.cpw_cents.at_60],
                                        ['100 wears', w.cpw_cents.at_100],
                                        [`${w.expected_wears.mid} expected`, w.cpw_cents.at_mid],
                                    ] as const
                                ).map(([label, cents], i) => (
                                    <div key={label} className={cn('rounded-md py-1.5', i === 3 && 'bg-receipt-ink/[0.06]')}>
                                        <p className='type-receipt font-semibold tabular'>{perWearText(cents)}</p>
                                        <p className='type-footnote text-receipt-ink/70'>{label}</p>
                                    </div>
                                ))}
                            </div>
                        </Section>

                        {typical && (
                            <Section label='VS. TYPICAL MATCH'>
                                <Lines lines={[`The typical match costs ${priceText(typical.price_cents)}, about ${perWearText(typical.cpw_cents)} a wear.`]} />
                                {{
                                    cheaper: <p className='pt-1 type-receipt font-semibold'>It costs less than the typical match up front.</p>,
                                    wins: (
                                        <>
                                            <p className='pt-1 type-receipt font-semibold'>Break-even: wear this {w.break_even_wears}+ times to win.</p>
                                            <p className='pt-0.5 type-footnote text-receipt-ink/70'>If you won&apos;t wear it that often, the cheaper one is the better buy.</p>
                                        </>
                                    ),
                                    never: (
                                        <>
                                            <p className='pt-1 type-receipt font-semibold'>Unlikely to beat the typical match on cost per wear.</p>
                                            <p className='pt-0.5 type-footnote text-receipt-ink/70'>
                                                It would take {w.break_even_wears}+ wears, more than the {w.expected_wears.high} it&apos;s expected to last.
                                            </p>
                                        </>
                                    ),
                                }[breakEvenVerdict(w.break_even_wears, w.expected_wears.high)]}
                            </Section>
                        )}

                        <Section label='CONFIDENCE' value={<LevelValue level={r.confidence} />}>
                            <Lines lines={[CONFIDENCE[r.confidence]]} />
                        </Section>
                    </div>

                    <Button size='lg' className='mt-5 w-full' render={<a href={r.url} target='_blank' rel='noreferrer' />} nativeButton={false}>
                        View on {MARKET[r.marketplace]}
                        <ExternalLink data-icon='inline-end' strokeWidth={1.75} />
                    </Button>
                    <p className='mt-3 text-center type-footnote text-pretty text-muted-foreground'>Evidence suggests, it doesn&apos;t promise. Tap any line for its source.</p>
                </div>
            </motion.div>
        </>
    );
}

function Section({ label, value, estimate, children }: { label: string; value?: React.ReactNode; estimate?: boolean; children: React.ReactNode }) {
    return (
        <section className='border-t border-dashed border-receipt-ink/30 pt-3 mt-3 first-of-type:mt-3'>
            <p className='flex items-end type-label text-receipt-ink/70'>
                <span className='flex items-center gap-1.5'>
                    {label}
                    {estimate && <EstTag className='text-receipt-ink/70' />}
                </span>
                {value !== undefined && (
                    <>
                        <span className='leader' />
                        <span className='type-receipt font-semibold text-receipt-ink normal-case tracking-normal'>{value}</span>
                    </>
                )}
            </p>
            {children}
        </section>
    );
}

const LevelValue = ({ level }: { level: Level }) => (
    <span className='inline-flex items-center gap-2'>
        {levelText(level)}
        {level !== 'unknown' && <LevelDots level={level} />}
    </span>
);

const Lines = ({ lines }: { lines: (string | null)[] }) => (
    <>
        {lines.filter(Boolean).map((l) => (
            <p key={l} className='pt-1.5 type-receipt text-pretty'>
                {l}
            </p>
        ))}
    </>
);

const Facts = ({ facts }: { facts: Fact[] }) => (
    <ul className='pt-1'>
        {facts.map((f, i) => (
            <FactLine key={`${f.kind}-${i}`} fact={f} />
        ))}
    </ul>
);
