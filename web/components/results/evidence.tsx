'use client';

import { ChevronDown, ExternalLink } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useState } from 'react';
import { StatusDot } from '@/components/sift/status-badge';
import { ease } from '@/lib/motion';
import { dots, levelText } from '@/lib/results';
import type { Fact, FactStatus, Level, Result } from '@/lib/search';
import { cn } from '@/lib/utils';

/** A level as three dots. Never a number (DESCRIPTION.md §10.1); the word is always there for screen readers. */
export function LevelDots({ level, className }: { level: Level; className?: string }) {
    const n = dots(level);
    return (
        <span className={cn('inline-flex items-center gap-[3px]', className)} role='img' aria-label={levelText(level)}>
            {[0, 1, 2].map((i) => (
                <span key={i} className={cn('size-[7px] rounded-full', i < n ? 'bg-current' : 'border border-current opacity-35')} />
            ))}
        </span>
    );
}

/** No quality facts at all: the honest state (DESCRIPTION.md §6). */
export const noEvidence = (r: Pick<Result, 'quality'>) => r.quality.level === 'unknown' && r.quality.facts.length === 0;

/** A marker on a row: dots for a level, the word "unknown" when there is none (empty dots would read as zero). */
function Marker({ name, level }: { name: string; level: Level }) {
    return (
        <span className='inline-flex items-center gap-1.5'>
            {name} {level === 'unknown' ? <span>unknown</span> : <LevelDots level={level} className='text-foreground' />}
        </span>
    );
}

/** "Quality ●●○ · Eco ●○○", or "Not enough evidence yet · Eco unknown". */
export function MarkerLine({ r, className }: { r: Result; className?: string }) {
    return (
        <p className={cn('flex flex-wrap items-center gap-x-3 gap-y-0.5 type-footnote text-muted-foreground', className)}>
            {noEvidence(r) ? <span>Not enough evidence yet</span> : <Marker name='Quality' level={r.quality.level} />}
            <Marker name='Eco' level={r.eco.level} />
        </p>
    );
}

export const STATUS_WORD: Record<FactStatus, string> = { verified: 'verified', claimed: 'as declared', inferred: 'likely', unknown: 'unknown' };

const SOURCE: Record<string, string> = {
    specifics: 'Listing details',
    listing_text: 'Listing description',
    product_line: 'Known product line',
    tag_image: 'Care tag photo',
    model: 'Read by our model',
    brand_table: 'Brand facts, checked by the team',
    baseline: 'Sift assumption',
};

const date = (iso: string) => {
    const d = new Date(`${iso}T12:00:00`);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

/** One receipt line. Tap it for where it came from: source, the words it was read from, and the date. */
export function FactLine({ fact }: { fact: Fact }) {
    const [open, setOpen] = useState(false);
    return (
        <li>
            <button type='button' aria-expanded={open} onClick={() => setOpen((o) => !o)} className='flex w-full items-start gap-2 rounded-md py-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring'>
                <StatusDot status={fact.status} className='mt-[5px]' />
                <span className='min-w-0 flex-1 type-receipt'>
                    <span className='text-receipt-ink/70'>{fact.label} </span>
                    <span className='text-receipt-ink'>{fact.value}</span>
                </span>
                <span className='shrink-0 pt-px type-footnote text-receipt-ink/70'>{STATUS_WORD[fact.status]}</span>
                <ChevronDown className={cn('mt-0.5 size-4 shrink-0 text-receipt-ink/50 transition-transform duration-200', open && 'rotate-180')} strokeWidth={1.75} aria-hidden />
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25, ease: ease.out }} className='overflow-hidden'>
                        <div className='mb-2 ml-[18px] flex flex-col gap-1 border-l border-dashed border-receipt-ink/25 pl-3 type-footnote text-receipt-ink/80'>
                            {fact.snippet && <p className='text-pretty italic'>“{fact.snippet}”</p>}
                            <p>
                                {SOURCE[fact.source] ?? fact.source} · {date(fact.as_of)}
                            </p>
                            {fact.source_url && (
                                <a href={fact.source_url} target='_blank' rel='noreferrer' className='inline-flex items-center gap-1 self-start text-primary underline-offset-2 hover:underline'>
                                    Open source <ExternalLink className='size-3.5' strokeWidth={1.75} aria-hidden />
                                </a>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </li>
    );
}
