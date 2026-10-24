'use client';

import { Heart } from 'lucide-react';
import { motion } from 'motion/react';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

/** Like a listing. Sits on the photo; the heart pops when filled. */
export function HeartButton({ liked, onToggle, className }: { liked: boolean; onToggle?: () => void; className?: string }) {
    return (
        <motion.button
            type='button'
            whileTap={{ scale: 0.88 }}
            transition={spring.snappy}
            aria-label='Like'
            aria-pressed={liked}
            onClick={onToggle}
            className={cn(
                'grid size-10 place-items-center rounded-full bg-card/85 shadow-card backdrop-blur-md outline-none focus-visible:ring-2 focus-visible:ring-ring',
                className,
            )}
        >
            <motion.span key={String(liked)} initial={{ scale: liked ? 0.5 : 1 }} animate={{ scale: 1 }} transition={spring.pop}>
                <Heart className={cn('size-5', liked ? 'fill-primary text-primary' : 'text-foreground')} strokeWidth={1.75} />
            </motion.span>
        </motion.button>
    );
}
