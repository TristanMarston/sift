'use client';

import { ExternalLink } from 'lucide-react';
import { StatusDot } from '@/components/sift/status-badge';
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
export const sentence = (v: string) => (/^[a-z](?![A-Z])/.test(v) ? v[0].toUpperCase() + v.slice(1) : v);

const date = (iso: string) => {
    const d = new Date(`${iso}T12:00:00`);
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

/** One fact, in full: what it is, how sure we are, and where it came from (the words, the source, the date). */
export function FactRow({ fact }: { fact: Fact }) {
    return (
        <li className='border-t border-border py-3 first:border-t-0 first:pt-1'>
            <p className='flex items-center gap-1.5 type-footnote text-muted-foreground'>
                <StatusDot status={fact.status} />
                <span className='min-w-0 flex-1'>{fact.label}</span>
                <span className='shrink-0'>{STATUS_WORD[fact.status]}</span>
            </p>
            <p className='mt-0.5 pl-4 type-callout font-medium text-pretty'>{sentence(fact.value)}</p>
            <div className='mt-1 flex flex-col gap-0.5 pl-4 type-footnote text-pretty text-muted-foreground'>
                {fact.snippet && <p className='italic'>“{fact.snippet}”</p>}
                <p>
                    {SOURCE[fact.source] ?? fact.source}, {date(fact.as_of)}
                    {fact.source_url && (
                        <a href={fact.source_url} target='_blank' rel='noreferrer' className='ml-2 inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline'>
                            Open source <ExternalLink className='size-3.5' strokeWidth={1.75} aria-hidden />
                        </a>
                    )}
                </p>
            </div>
        </li>
    );
}
