'use client';

import { AnimatePresence, motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

/** Re-ranks the list from likes. The count rolls when it changes. */
export function UpdateButton({ count, onClick, size = 'default', className }: { count: number; onClick?: () => void; size?: 'default' | 'sm'; className?: string }) {
    return (
        <Button size={size} onClick={onClick} className={cn('pr-2', className)} aria-label={`Update with ${count} liked`}>
            Update
            <span className='relative grid h-7 min-w-7 place-items-center overflow-hidden rounded-pill bg-primary-foreground/20 px-2 type-data tabular'>
                <AnimatePresence mode='popLayout' initial={false}>
                    <motion.span key={count} initial={{ y: '110%' }} animate={{ y: 0 }} exit={{ y: '-110%' }} transition={spring.snappy}>
                        {count}
                    </motion.span>
                </AnimatePresence>
            </span>
        </Button>
    );
}
