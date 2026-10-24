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

export const STATUS_WORD: Record<FactStatus, string> = { verified: 'Verified', claimed: 'As declared', inferred: 'Likely', unknown: 'Unknown' };

const SOURCE: Record<string, string> = {
    specifics: 'Listing details',
    listing_text: 'Listing description',
    product_line: 'Known product line',
    tag_image: 'Care tag photo',
    model: 'Read by our model',
    brand_table: 'Brand facts, checked by the team',
    baseline: 'Sift assumption',
};

/** "cotton" reads as "Cotton"; "eBay" stays as it is. */
const sentence = (v: string) => (/^[a-z](?![A-Z])/.test(v) ? v[0].toUpperCase() + v.slice(1) : v);

const date = (iso: string) => {
    const d = new Date(`${iso}T12:00:00`);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

/**
 * One receipt line: a small label and how sure we are on top, the value below in full size. Tap it for where it
 * came from: source, the words it was read from, and the date.
 */
export function FactLine({ fact }: { fact: Fact }) {
    const [open, setOpen] = useState(false);
    return (
        <li>
            <button type='button' aria-expanded={open} onClick={() => setOpen((o) => !o)} className='w-full rounded-md py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring'>
                <span className='flex items-center gap-1.5 type-footnote text-muted-foreground'>
                    <StatusDot status={fact.status} />
                    <span className='min-w-0 flex-1 truncate'>{fact.label}</span>
                    <span className='shrink-0'>{STATUS_WORD[fact.status]}</span>
                    <ChevronDown className={cn('size-4 shrink-0 transition-transform duration-200', open && 'rotate-180')} strokeWidth={1.75} aria-hidden />
                </span>
                <span className='mt-0.5 block pl-4 type-callout font-medium text-pretty text-receipt-ink'>{sentence(fact.value)}</span>
            </button>
            <AnimatePresence initial={false}>
                {open && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25, ease: ease.out }} className='overflow-hidden'>
                        <div className='mb-2 ml-1 flex flex-col gap-1 border-l-2 border-receipt-ink/15 pl-3 type-footnote text-muted-foreground'>
                            {fact.snippet && <p className='text-pretty italic'>“{fact.snippet}”</p>}
                            <p>
                                {SOURCE[fact.source] ?? fact.source}, {date(fact.as_of)}
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
