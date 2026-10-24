'use client';

import { count } from '@/lib/format';
import { cn } from '@/lib/utils';
import { RollingNumber } from './rolling-number';
import { EstTag } from './status-badge';

const fmt = (v: number) => (v < 10 ? v.toFixed(1) : count(v));

/** A big estimated number: 2.1 kg CO₂ est. Counts up when it appears. */
export function FootprintStat({ value, unit, label, size = 'lg', className }: { value: number; unit: string; label: string; size?: 'lg' | 'md'; className?: string }) {
    return (
        <div className={cn('flex flex-col gap-1', className)}>
            <p className='flex items-baseline gap-1.5'>
                <RollingNumber value={value} format={fmt} duration={1.2} className={size === 'lg' ? 'type-numeral' : 'type-title-1'} />
                <span className='type-body'>{unit}</span>
                <EstTag className='self-center' />
            </p>
            <p className='type-footnote text-muted-foreground'>{label}</p>
        </div>
    );
}
