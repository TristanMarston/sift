'use client';

import { motion } from 'motion/react';
import type { Sort } from '@/lib/search';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

const SORTS: { id: Sort; label: string }[] = [
    { id: 'cpw', label: 'Cost per wear' },
    { id: 'price', label: 'Price' },
    { id: 'match', label: 'Look match' },
    { id: 'eco', label: 'Eco' },
];

/** The four sorts as one segmented control. The selected pill slides; the list reshuffles under it. */
export function SortControl({ value, onChange, className }: { value: Sort; onChange: (s: Sort) => void; className?: string }) {
    return (
        <div role='radiogroup' aria-label='Sort results' className={cn('grid grid-cols-[1.35fr_0.8fr_1.1fr_0.75fr] gap-0.5 rounded-pill bg-secondary p-1', className)}>
            {SORTS.map((s) => {
                const on = s.id === value;
                return (
                    <button
                        key={s.id}
                        type='button'
                        role='radio'
                        aria-checked={on}
                        onClick={() => onChange(s.id)}
                        className='relative h-9 rounded-pill px-1 type-footnote font-semibold whitespace-nowrap outline-none transition-transform duration-100 active:scale-[0.96] focus-visible:ring-2 focus-visible:ring-ring'
                    >
                        {on && <motion.span layoutId='sort-pill' transition={spring.ui} className='absolute inset-0 rounded-pill bg-card shadow-card' />}
                        <span className={cn('relative transition-colors duration-200', on ? 'text-foreground' : 'text-muted-foreground')}>{s.label}</span>
                    </button>
                );
            })}
        </div>
    );
}
