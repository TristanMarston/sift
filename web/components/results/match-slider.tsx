'use client';

import { cn } from '@/lib/utils';

type Props = { value: number; onChange: (v: number) => void; className?: string };

/**
 * Closer match ↔ better value (DESCRIPTION.md §4.6). Eleven stops, each a list the backend already ranked, so
 * dragging reshuffles the rows instantly. 0 is pure cost per wear, 10 is pure look match.
 */
export function MatchSlider({ value, onChange, className }: Props) {
    const words = value === 0 ? 'Best value' : value === 10 ? 'Closest match' : value < 5 ? 'Leaning value' : value > 5 ? 'Leaning match' : 'Balanced';
    return (
        <label className={cn('flex items-center gap-3 type-footnote text-muted-foreground', className)}>
            <span className='shrink-0'>Better value</span>
            <input
                type='range'
                min={0}
                max={10}
                step={1}
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                aria-label='Better value or closer match'
                aria-valuetext={words}
                className='h-6 min-w-0 flex-1 cursor-pointer accent-primary'
            />
            <span className='shrink-0'>Closer match</span>
        </label>
    );
}
