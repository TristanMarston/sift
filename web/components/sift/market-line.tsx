import { price } from '@/lib/format';
import { cn } from '@/lib/utils';

/** Mono meta line: DEPOP · SIZE M · GOOD */
export function MarketLine({ parts, className }: { parts: (string | undefined)[]; className?: string }) {
    return <p className={cn('type-data uppercase tabular text-muted-foreground', className)}>{parts.filter(Boolean).join(' · ')}</p>;
}

/** Price, with retail crossed out only when it's known. */
export function PriceLine({ cents, retailCents, className }: { cents: number; retailCents?: number; className?: string }) {
    return (
        <p className={cn('flex items-baseline gap-2', className)}>
            <span className='type-headline tabular'>{price(cents)}</span>
            {retailCents ? (
                <s className='type-data tabular text-muted-foreground'>
                    <span className='sr-only'>Retail </span>
                    {price(retailCents)}
                </s>
            ) : null}
        </p>
    );
}
