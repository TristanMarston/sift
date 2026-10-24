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
 * The Wear Receipt: everything behind one result, line by line, on receipt paper. The link to buy sits right under
 * the item. Every line opens to its source, status and date; anything we don't know says unknown. Phone: a sheet from the bottom (drag the handle down to
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
                                {Math.round(r.match.similarity * 100)}% look match{r.match.band === 'exact' ? ' · Exact match' : r.match.band === 'close' ? ' · Close match' : ''}
                            </p>
                            <p className='mt-auto flex items-baseline gap-1.5'>
                                <span className='font-serif text-[34px] leading-9 tracking-tight tabular'>{perWearText(w.cpw_cents.at_mid)}</span>
                                <span className='type-callout text-muted-foreground'>a wear</span>
                                <EstTag className='self-center' />
                            </p>
                        </div>
                    </div>

                    <Button size='lg' className='mt-4 w-full' render={<a href={r.url} target='_blank' rel='noreferrer' />} nativeButton={false}>
                        View on {MARKET[r.marketplace]}
                        <ExternalLink data-icon='inline-end' strokeWidth={1.75} />
                    </Button>

                    {/* The receipt */}
                    <div className='mt-5 bg-receipt-paper px-4 pt-4 pb-7 text-receipt-ink receipt-edge-bottom'>
                        <h3 className='font-serif text-xl leading-7'>Wear Receipt</h3>
                        <p className='type-footnote text-pretty text-muted-foreground'>How it works out to {perWearText(w.cpw_cents.at_mid)} a wear. Tap a line for its source.</p>

                        <Section title='Cost' value={priceText(c.total_cents)}>
                            <Lines
                                lines={[
                                    c.original_price_cents && c.original_price_cents > c.price_cents ? `Seller marked it down from ${priceText(c.original_price_cents)}` : null,
                                    c.free_shipping ? 'Free shipping' : c.shipping_cents !== null ? `Includes ${priceText(c.shipping_cents)} shipping` : 'Shipping unknown',
                                    c.fee_cents ? `Includes ${r.marketplace === 'depop' ? 'up to ' : ''}${priceText(c.fee_cents)} ${MARKET[r.marketplace]} buyer fee` : null,
                                    c.retail_price_cents ? `New retail ${priceText(c.retail_price_cents)}` : null,
                                ]}
                            />
                        </Section>

                        <Section title='Quality' value={<LevelValue level={r.quality.level} />}>
                            {noEvidence(r) ? <Lines lines={['Not enough evidence yet. It stays in the list, with no boost.']} /> : <Facts facts={r.quality.facts} />}
                        </Section>

                        <Section title='Eco' value={<LevelValue level={r.eco.level} />}>
                            <Lines lines={[`Greener than ${r.eco.percentile}% of these matches`]} />
                            {r.eco.facts.length ? <Facts facts={r.eco.facts} /> : <Lines lines={['No eco facts stated.']} />}
                        </Section>

                        <Section title='Expected wears' value={`${w.expected_wears.low}–${w.expected_wears.high}`} estimate>
                            <Lines lines={[w.basis === 'category_baseline' ? 'No quality evidence, so this is the typical lifespan for the category.' : `About ${w.expected_wears.mid} in the middle of the range.`]} />
                            <Facts facts={w.facts} />
                        </Section>

                        <Section title='Cost per wear' estimate>
                            <div className='mt-2 grid grid-cols-4 gap-1 text-center'>
                                {(
                                    [
                                        ['30 wears', w.cpw_cents.at_30],
                                        ['60 wears', w.cpw_cents.at_60],
                                        ['100 wears', w.cpw_cents.at_100],
                                        [`${w.expected_wears.mid} expected`, w.cpw_cents.at_mid],
                                    ] as const
                                ).map(([label, cents], i) => (
                                    <div key={label} className={cn('rounded-md px-0.5 py-2', i === 3 && 'bg-receipt-ink/[0.07]')}>
                                        <p className='font-mono text-[15px] leading-5 font-medium tabular'>{perWearText(cents)}</p>
                                        <p className='mt-0.5 type-footnote text-muted-foreground'>{label}</p>
                                    </div>
                                ))}
                            </div>
                        </Section>

                        {typical && (
                            <Section title='Against the typical match'>
                                <Lines lines={[`The typical match costs ${priceText(typical.price_cents)}, about ${perWearText(typical.cpw_cents)} a wear.`]} />
                                {{
                                    cheaper: <Verdict head='It costs less than the typical match up front.' />,
                                    wins: <Verdict head={`Break-even: wear this ${w.break_even_wears}+ times to win.`} note="If you won't wear it that often, the cheaper one is the better buy." />,
                                    never: (
                                        <Verdict
                                            head='Unlikely to beat the typical match on cost per wear.'
                                            note={`It would take ${w.break_even_wears}+ wears, more than the ${w.expected_wears.high} it's expected to last.`}
                                        />
                                    ),
                                }[breakEvenVerdict(w.break_even_wears, w.expected_wears.high)]}
                            </Section>
                        )}

                        <Section title='Confidence' value={<LevelValue level={r.confidence} />}>
                            <Lines lines={[CONFIDENCE[r.confidence]]} />
                        </Section>
                    </div>
                </div>
            </motion.div>
        </>
    );
}

/** A receipt section: its title, a dot leader, and the total it adds up to. */
function Section({ title, value, estimate, children }: { title: string; value?: React.ReactNode; estimate?: boolean; children: React.ReactNode }) {
    return (
        <section className='mt-4 border-t border-dashed border-receipt-ink/25 pt-4'>
            <div className='flex items-baseline'>
                <h4 className='flex items-center gap-1.5 type-headline'>
                    {title}
                    {estimate && <EstTag className='self-center' />}
                </h4>
                {value !== undefined && (
                    <>
                        <span className='leader' />
                        <span className='font-mono text-[15px] font-medium tabular'>{value}</span>
                    </>
                )}
            </div>
            {children}
        </section>
    );
}

const LevelValue = ({ level }: { level: Level }) => (
    <span className='inline-flex items-center gap-2 font-sans font-semibold'>
        {levelText(level)}
        {level !== 'unknown' && <LevelDots level={level} />}
    </span>
);

const Lines = ({ lines }: { lines: (string | null)[] }) => (
    <>
        {lines.filter(Boolean).map((l) => (
            <p key={l} className='mt-1.5 type-callout text-pretty text-muted-foreground'>
                {l}
            </p>
        ))}
    </>
);

const Verdict = ({ head, note }: { head: string; note?: string }) => (
    <>
        <p className='mt-2 type-callout font-semibold text-pretty'>{head}</p>
        {note && <p className='mt-0.5 type-footnote text-pretty text-muted-foreground'>{note}</p>}
    </>
);

const Facts = ({ facts }: { facts: Fact[] }) => (
    <ul className='mt-1'>
        {facts.map((f, i) => (
            <FactLine key={`${f.kind}-${i}`} fact={f} />
        ))}
    </ul>
);
