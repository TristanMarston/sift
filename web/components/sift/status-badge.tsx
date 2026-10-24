import { cn } from '@/lib/utils';
import type { BadgeStatus } from '@/lib/types';

const LABEL: Record<BadgeStatus, string> = { verified: 'Verified', claimed: 'Claimed', inferred: 'Likely', unknown: 'Unknown' };

/** Shape carries the meaning, color backs it up: solid (verified), half (as declared), dashed ring (likely), hollow (unknown). */
export function StatusDot({ status, className }: { status: BadgeStatus; className?: string }) {
    const color = { verified: 'text-verified', claimed: 'text-claimed', inferred: 'text-claimed', unknown: 'text-unknown' }[status];
    return (
        <svg viewBox='0 0 10 10' aria-hidden className={cn('size-2.5 shrink-0', color, className)}>
            {status === 'verified' && <circle cx='5' cy='5' r='4.5' fill='currentColor' />}
            {status === 'claimed' && (
                <>
                    <circle cx='5' cy='5' r='4' fill='none' stroke='currentColor' strokeWidth='1.5' />
                    <path d='M5 1a4 4 0 0 0 0 8z' fill='currentColor' />
                </>
            )}
            {status === 'inferred' && <circle cx='5' cy='5' r='4' fill='none' stroke='currentColor' strokeWidth='1.5' strokeDasharray='2.1 1.5' />}
            {status === 'unknown' && <circle cx='5' cy='5' r='4' fill='none' stroke='currentColor' strokeWidth='1.5' />}
        </svg>
    );
}

/** "Organic cotton · Verified". Every value claim in Sift uses this. */
export function StatusBadge({ value, status, note, className }: { value: string; status: BadgeStatus; note?: string; className?: string }) {
    return (
        <span className={cn('inline-flex items-center gap-1.5 type-footnote', className)}>
            <StatusDot status={status} />
            <span className='text-foreground'>{value}</span>
            <span className='text-muted-foreground'>
                · {LABEL[status]}
                {note ? ` · ${note}` : ''}
            </span>
        </span>
    );
}

/** Marks every estimated number. */
export function EstTag({ className }: { className?: string }) {
    return (
        <span className={cn('inline-flex h-4 items-center rounded-tag border border-current/30 px-1 type-label text-muted-foreground', className)}>
            EST.
        </span>
    );
}
