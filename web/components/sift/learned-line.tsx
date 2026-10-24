'use client';

import { motion } from 'motion/react';
import { ease } from '@/lib/motion';
import { cn } from '@/lib/utils';

/** "Learned: you like boxy fits and earth tones." The words arrive one at a time after Update. */
export function LearnedLine({ text, className }: { text: string; className?: string }) {
    return (
        <p key={text} className={cn('flex flex-wrap items-baseline gap-x-[0.3em]', className)} aria-label={`Learned: ${text}`}>
            <span className='type-callout text-primary' aria-hidden>
                Learned:
            </span>
            {text.split(' ').map((word, i) => (
                <motion.span
                    key={i}
                    aria-hidden
                    className='type-quote'
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, ease: ease.out, delay: 0.2 + i * 0.06 }}
                >
                    {word}
                </motion.span>
            ))}
        </p>
    );
}
