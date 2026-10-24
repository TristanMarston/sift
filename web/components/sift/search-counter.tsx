'use client';

import { motion, useMotionValue, useTransform } from 'motion/react';
import { useEffect, useState } from 'react';
import { seconds } from '@/lib/format';
import { cn } from '@/lib/utils';
import { RollingNumber } from './rolling-number';

type Props = {
    total: number; // the real index size
    marketplaces: readonly string[];
    elapsedMs?: number; // set when the search returns; until then the timer runs
    label?: string | null; // what's being searched: "jackets"
    className?: string;
};

/** "Searching 18,432 listings" with marketplace names lighting up and a real timer. */
export function SearchCounter({ total, marketplaces, elapsedMs, label, className }: Props) {
    const done = elapsedMs !== undefined;
    const [lit, setLit] = useState(0);
    const ms = useMotionValue(0);
    const timer = useTransform(ms, seconds);

    useEffect(() => {
        const id = setInterval(() => setLit((n) => (n >= marketplaces.length ? n : n + 1)), 220);
        return () => clearInterval(id);
    }, [marketplaces.length]);

    useEffect(() => {
        if (elapsedMs !== undefined) return ms.set(elapsedMs);
        const start = performance.now();
        let raf = requestAnimationFrame(function tick(now) {
            ms.set(now - start);
            raf = requestAnimationFrame(tick);
        });
        return () => cancelAnimationFrame(raf);
    }, [done, elapsedMs, ms]);

    return (
        <div className={cn('flex flex-col gap-2 rounded-card bg-camera-control p-4 text-camera-foreground backdrop-blur-xl', className)} role='status' aria-live='polite'>
            <div className='flex items-center justify-between type-footnote text-camera-muted'>
                <span>
                    {done ? 'Searched' : 'Searching'}
                    {label ? ` ${label}` : ''}
                </span>
                <motion.span className='type-data tabular text-camera-foreground'>{timer}</motion.span>
            </div>
            <p className='flex items-baseline gap-2'>
                <RollingNumber value={total} duration={1.1} className='type-counter' />
                <span className='type-callout text-camera-muted'>listings</span>
            </p>
            <p className='flex flex-wrap gap-x-2 gap-y-1 type-data uppercase'>
                {marketplaces.map((m, i) => (
                    <motion.span key={m} initial={{ opacity: 0.3 }} animate={{ opacity: i < lit ? 1 : 0.3 }} transition={{ duration: 0.3 }}>
                        {m}
                        {i < marketplaces.length - 1 && <span className='ml-2 text-camera-muted'>·</span>}
                    </motion.span>
                ))}
            </p>
        </div>
    );
}
