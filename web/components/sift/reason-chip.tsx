import { Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';

/** Why a listing matched. A miss is shown plainly in grey, never in red. */
export function ReasonChip({ label, ok, className }: { label: string; ok: boolean; className?: string }) {
    return (
        <span
            className={cn(
                'inline-flex h-7 items-center gap-1 rounded-pill px-2.5 type-footnote',
                ok ? 'bg-secondary text-secondary-foreground' : 'border border-border text-muted-foreground',
                className,
            )}
        >
            {ok ? <Check className='size-3.5 text-primary' aria-label='Matches' /> : <X className='size-3.5' aria-label='Differs' />}
            {label}
        </span>
    );
}
