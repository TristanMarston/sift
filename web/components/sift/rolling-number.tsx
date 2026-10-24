'use client';

import { animate, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react';
import { useEffect } from 'react';
import { count } from '@/lib/format';
import { cn } from '@/lib/utils';

type Props = {
    value: number;
    from?: number;
    duration?: number;
    format?: (v: number) => string;
    className?: string;
};

/** Counts up to a number (search count, footprint estimates). Digits stay aligned. */
export function RollingNumber({ value, from = 0, duration = 1, format = count, className }: Props) {
    const reduce = useReducedMotion();
    const mv = useMotionValue(reduce ? value : from);
    const text = useTransform(mv, format);

    useEffect(() => {
        if (reduce) return mv.set(value);
        const controls = animate(mv, value, { duration, ease: [0.2, 0, 0, 1] });
        return () => controls.stop();
    }, [value, duration, reduce, mv]);

    return <motion.span className={cn('tabular', className)}>{text}</motion.span>;
}
