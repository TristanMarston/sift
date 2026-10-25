'use client';

import { Footprints, ShieldCheck } from 'lucide-react';
import { useMarkerStyle, type MarkerStyle } from '@/lib/marker-style';
import { dots, levelText } from '@/lib/results';
import type { Level, Result } from '@/lib/search';
import { cn } from '@/lib/utils';
import { LevelDots, MarkerLine, noEvidence } from './evidence';

// The quality and eco markers in four looks (compare them on /design/markers). Every look is a level, never a
// number (DESCRIPTION.md §10.1), and none colours "good" green: weight and fill carry the level, not hue.

type Kind = 'quality' | 'eco';
const NAME: Record<Kind, string> = { quality: 'Quality', eco: 'Eco' };
const ICON = { quality: ShieldCheck, eco: Footprints };
const LEVELS: Level[] = ['low', 'medium', 'high'];

/** The look in use: a forced one (the comparison page) or the one picked in this browser. */
function useStyle(forced?: MarkerStyle) {
    const chosen = useMarkerStyle();
    return forced ?? chosen;
}

/** Three segments filled to the level. `wide` stretches them across the card. */
export function Meter({ level, wide, className }: { level: Level; wide?: boolean; className?: string }) {
    const n = dots(level);
    return (
        <span role='img' aria-label={levelText(level)} className={cn('flex', wide ? 'w-full gap-1' : 'gap-0.5', className)}>
            {[0, 1, 2].map((i) => (
                <span key={i} className={cn('rounded-pill', wide ? 'h-3 flex-1' : 'h-1.5 w-3.5', i < n ? 'bg-foreground' : 'bg-foreground/15')} />
            ))}
        </span>
    );
}

/** A ring in three arcs, filled to the level. */
export function Ring({ level, size = 22, className }: { level: Level; size?: number; className?: string }) {
    const n = dots(level);
    const stroke = size > 40 ? 7 : 3;
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const arc = c / 3;
    const gap = stroke + (size > 40 ? 4 : 2); // round caps add half a stroke at each end
    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role='img' aria-label={levelText(level)} className={cn('shrink-0 -rotate-90', className)}>
            {[0, 1, 2].map((i) => (
                <circle
                    key={i}
                    cx={size / 2}
                    cy={size / 2}
                    r={r}
                    fill='none'
                    strokeWidth={stroke}
                    strokeLinecap='round'
                    strokeDasharray={`${arc - gap} ${c - arc + gap}`}
                    strokeDashoffset={-i * arc - gap / 2}
                    className={i < n ? 'stroke-foreground' : 'stroke-foreground/15'}
                />
            ))}
        </svg>
    );
}

// Chips get heavier as the level rises: solid, tinted, outlined, dashed for unknown.
const CHIP: Record<Level, string> = {
    high: 'bg-foreground text-background',
    medium: 'bg-foreground/10 text-foreground',
    low: 'border border-foreground/30 text-foreground',
    unknown: 'border border-dashed border-muted-foreground/50 text-muted-foreground',
};

export function Chip({ kind, level, big }: { kind: Kind; level: Level; big?: boolean }) {
    const Icon = ICON[kind];
    return (
        <span className={cn('inline-flex items-center gap-1 rounded-pill font-semibold whitespace-nowrap', big ? 'px-3 py-1 type-callout' : 'px-2 py-0.5 type-footnote', CHIP[level])}>
            <Icon className={big ? 'size-4' : 'size-3.5'} strokeWidth={2} aria-hidden />
            <span className='font-normal opacity-75'>{NAME[kind]}</span>
            {levelText(level)}
        </span>
    );
}

/** The markers on a result row. */
export function RowMarkers({ r, style: forced }: { r: Result; style?: MarkerStyle }) {
    const style = useStyle(forced);
    if (style === 'dots') return <MarkerLine r={r} />;
    const levels: Record<Kind, Level> = { quality: noEvidence(r) ? 'unknown' : r.quality.level, eco: r.eco.level };
    if (style === 'chips')
        return (
            <p className='flex flex-wrap gap-1.5 pt-1'>
                <Chip kind='quality' level={levels.quality} />
                <Chip kind='eco' level={levels.eco} />
            </p>
        );
    return (
        <div className='grid grid-cols-2 gap-2 pt-1'>
            {(['quality', 'eco'] as const).map((k) => (
                <div key={k} className='flex min-w-0 items-center gap-1.5'>
                    {style === 'rings' && <Ring level={levels[k]} />}
                    <div className='min-w-0'>
                        <p className='type-footnote leading-4 text-muted-foreground'>{NAME[k]}</p>
                        <p className='flex items-center gap-1.5 type-footnote leading-4 font-semibold'>
                            {style === 'meter' && <Meter level={levels[k]} />}
                            {levelText(levels[k])}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}

/** The level beside a card title in the item panel. */
export function LevelBadge({ kind, level, style: forced }: { kind: Kind; level: Level; style?: MarkerStyle }) {
    const style = useStyle(forced);
    if (style === 'chips') return <Chip kind={kind} level={level} big />;
    return (
        <span className='inline-flex items-center gap-2 type-callout font-semibold'>
            {style === 'rings' && <Ring level={level} size={28} />}
            {levelText(level)}
            {style === 'dots' && level !== 'unknown' && <LevelDots level={level} />}
            {style === 'meter' && <Meter level={level} />}
        </span>
    );
}

/** The top of the Eco card: the level, big, and how it ranks against the other matches. */
export function EcoHero({ eco, style: forced }: { eco: Result['eco']; style?: MarkerStyle }) {
    const style = useStyle(forced);
    const pct = typeof eco.percentile === 'number' ? eco.percentile : null;
    const greener = pct !== null && <p className='type-callout font-semibold'>Greener than {pct}% of these matches</p>;
    // How this listing ranks among the matches, as a filled track.
    const track = pct !== null && (
        <div className='h-2 overflow-hidden rounded-pill bg-secondary' role='img' aria-label={`Greener than ${pct}% of these matches`}>
            <div className='h-full rounded-pill bg-foreground' style={{ width: `${Math.max(pct, 3)}%` }} />
        </div>
    );

    if (style === 'dots') return greener ? <div className='mt-1'>{greener}</div> : null;
    if (style === 'meter')
        return (
            <div className='mt-3 flex flex-col gap-2'>
                <Meter level={eco.level} wide />
                <div className='grid grid-cols-3 type-footnote text-muted-foreground'>
                    {LEVELS.map((l, i) => (
                        <span key={l} className={cn(i === 1 && 'text-center', i === 2 && 'text-right', l === eco.level && 'font-semibold text-foreground')}>
                            {levelText(l)}
                        </span>
                    ))}
                </div>
                {greener && <div className='mt-1 flex flex-col gap-1.5'>{greener}{track}</div>}
            </div>
        );
    if (style === 'chips')
        return (
            <div className='mt-3 flex flex-col gap-1.5'>
                {greener}
                {track}
            </div>
        );
    return (
        <div className='mt-3 flex items-center gap-4'>
            <div className='relative grid place-items-center'>
                <Ring level={eco.level} size={76} />
                <span className='absolute type-callout font-semibold'>{levelText(eco.level)}</span>
            </div>
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
                {greener ?? <p className='type-callout font-semibold'>{levelText(eco.level)} eco</p>}
                {track}
            </div>
        </div>
    );
}
