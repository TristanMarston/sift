'use client';

import { cn } from '@/lib/utils';

type Props = { value: number; onChange: (v: number) => void; className?: string };

const STOPS = 10;

/**
 * Closer match ↔ better value (DESCRIPTION.md §4.6). Eleven stops, each a list the backend already ranked, so
 * dragging reshuffles the rows instantly. 0 is pure cost per wear, 10 is pure look match. The track, fill and
 * stop dots are drawn behind a native range input, which keeps keyboard and screen reader support; its thumb is
 * 28px inside a 44px touch target. Tapping an end label jumps there.
 */
export function MatchSlider({ value, onChange, className }: Props) {
    const words = value === 0 ? 'Best value' : value === STOPS ? 'Closest match' : value < 5 ? 'Leaning value' : value > 5 ? 'Leaning match' : 'Balanced';
    const end = 'rounded-sm py-1 outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring';
    return (
        <div className={cn('type-footnote text-muted-foreground', className)}>
            <div className='flex justify-between'>
                <button type='button' onClick={() => onChange(0)} className={cn(end, value < 5 && 'font-semibold text-foreground')}>
                    Better value
                </button>
                <button type='button' onClick={() => onChange(STOPS)} className={cn(end, value > 5 && 'font-semibold text-foreground')}>
                    Closer match
                </button>
            </div>
            <div className='relative h-11'>
                {/* Track, fill and stop dots, inset by half the thumb so the stops line up with its centre. */}
                <div aria-hidden className='absolute inset-x-[14px] top-1/2 h-1.5 -translate-y-1/2 rounded-pill bg-secondary'>
                    <div className='absolute inset-y-0 left-0 rounded-pill bg-primary' style={{ width: `${(value / STOPS) * 100}%` }} />
                    <div className='absolute inset-0 flex items-center justify-between'>
                        {Array.from({ length: STOPS + 1 }, (_, i) => (
                            <span key={i} className={cn('size-1 rounded-full', i <= value ? 'bg-primary-foreground/70' : 'bg-muted-foreground/40')} />
                        ))}
                    </div>
                </div>
                <input
                    type='range'
                    min={0}
                    max={STOPS}
                    step={1}
                    value={value}
                    onChange={(e) => onChange(Number(e.target.value))}
                    aria-label='Better value or closer match'
                    aria-valuetext={words}
                    className='range-thumb absolute inset-0 size-full'
                />
            </div>
        </div>
    );
}
