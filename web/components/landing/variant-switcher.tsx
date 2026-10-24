'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { VARIANTS, type Variant } from './variants';

/** Prototype-only switcher between landing designs, on the cobalt stage. Remove once one is picked. */
export function VariantSwitcher({ current }: { current: Variant }) {
    return (
        <nav aria-label='Landing designs' className='flex gap-0.5 rounded-pill bg-white/15 p-0.5'>
            {VARIANTS.map((v) => (
                <Link key={v} href={`/landing/${v}`} aria-current={v === current ? 'page' : undefined} className='relative grid h-7 place-items-center px-2.5 type-label uppercase'>
                    {v === current && <motion.span layoutId='variant-pill' transition={spring.ui} className='absolute inset-0 rounded-pill bg-stage-foreground' />}
                    <span className={cn('relative', v === current ? 'text-stage' : 'text-stage-foreground')}>{v}</span>
                </Link>
            ))}
        </nav>
    );
}
