'use client';

import { Check, Mic } from 'lucide-react';
import { motion } from 'motion/react';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

type Props = {
    label: string;
    selected?: boolean;
    fromVoice?: boolean; // added by speech: shows a small mic mark
    layoutId?: string; // lets a chip fly in from the transcript
    onToggle?: () => void;
    className?: string;
};

/** A value or filter the user can switch on and off. */
export function ValueChip({ label, selected, fromVoice, layoutId, onToggle, className }: Props) {
    return (
        <motion.button
            type='button'
            layout
            layoutId={layoutId}
            transition={spring.ui}
            whileTap={{ scale: 0.95 }}
            aria-pressed={!!selected}
            onClick={onToggle}
            className={cn(
                'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-pill px-4 type-callout transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
                selected ? 'bg-primary-tint text-primary-tint-foreground' : 'bg-secondary text-secondary-foreground',
                className,
            )}
        >
            {fromVoice && <Mic className='size-3.5' aria-label='From your voice' />}
            {label}
            {selected && <Check className='-mr-1 size-4' aria-hidden />}
        </motion.button>
    );
}
