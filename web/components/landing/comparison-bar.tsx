'use client';

import { motion } from 'motion/react';
import Link from 'next/link';
import { useSyncExternalStore } from 'react';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { VARIANTS, type Variant } from './variants';

type Palette = 'ink' | 'forest';
const KEY = 'sift-palette';
const STAGE = { ink: '#f3f4f2', forest: '#103520' } as const; // Safari's bar color on the landing

const read = (): Palette => (document.documentElement.dataset.palette === 'ink' ? 'ink' : 'forest');
const subscribe = (cb: () => void) => {
    const o = new MutationObserver(cb);
    o.observe(document.documentElement, { attributes: true, attributeFilter: ['data-palette'] });
    return () => o.disconnect();
};

function setPalette(p: Palette) {
    const root = document.documentElement;
    if (p === 'ink') root.dataset.palette = 'ink';
    else delete root.dataset.palette;
    try {
        localStorage.setItem(KEY, p);
    } catch {}
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (meta) meta.content = STAGE[p];
}

const LABEL: Record<Variant, string> = { dial: 'Dial', flip: 'Flip', race: 'Race', billboard: 'Billboard', equation: 'Equation', wall: 'Wall' };

/** On /landing only: switch between the landing designs (kept for demos) and the forest or light ("Ink") landing. */
export function ComparisonBar({ current }: { current: Variant }) {
    const palette = useSyncExternalStore(subscribe, read, () => 'forest' as Palette);
    return (
        <div className='relative z-20 flex items-center gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] lg:px-8'>
            <nav aria-label='Landing designs' className='flex shrink-0 gap-0.5 rounded-pill bg-stage-foreground/10 p-0.5'>
                {VARIANTS.map((v) => (
                    <Link key={v} href={`/landing/${v}`} aria-current={v === current ? 'page' : undefined} className='relative grid h-7 place-items-center px-2.5 type-footnote font-semibold'>
                        {v === current && <motion.span layoutId='variant-pill' transition={spring.ui} className='absolute inset-0 rounded-pill bg-stage-foreground' />}
                        <span className={cn('relative', v === current ? 'text-stage' : 'text-stage-foreground')}>{LABEL[v]}</span>
                    </Link>
                ))}
            </nav>
            <div role='radiogroup' aria-label='Landing palette' className='flex shrink-0 gap-0.5 rounded-pill bg-stage-foreground/10 p-0.5'>
                {(['forest', 'ink'] as const).map((p) => (
                    <button key={p} type='button' role='radio' aria-checked={palette === p} onClick={() => setPalette(p)} className='relative grid h-7 place-items-center px-2.5 type-footnote font-semibold'>
                        {palette === p && <motion.span layoutId='palette-pill' transition={spring.ui} className='absolute inset-0 rounded-pill bg-stage-foreground' />}
                        <span className={cn('relative', palette === p ? 'text-stage' : 'text-stage-foreground')}>{p === 'ink' ? 'Ink' : 'Forest'}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}
