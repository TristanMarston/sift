'use client';

import { Mic } from 'lucide-react';
import { motion } from 'motion/react';
import { useRef } from 'react';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

export type MicState = 'idle' | 'listening' | 'processing';

type Props = {
    state?: MicState;
    onPressStart?: () => void;
    onPressEnd?: (heldMs: number) => void; // under ~250ms means a tap: show "Hold to talk"
    className?: string;
};

/** Push to talk. Responds on press, not release. Space or Enter works the same way. */
export function MicButton({ state = 'idle', onPressStart, onPressEnd, className }: Props) {
    const down = useRef(0);
    const start = () => {
        down.current = performance.now();
        onPressStart?.();
    };
    const end = () => {
        if (!down.current) return;
        onPressEnd?.(performance.now() - down.current);
        down.current = 0;
    };
    const listening = state === 'listening';

    return (
        <div className={cn('relative grid size-16 place-items-center', className)}>
            {listening &&
                [0, 0.8].map((delay) => (
                    <motion.span
                        key={delay}
                        aria-hidden
                        className='absolute inset-0 rounded-full border-2 border-primary'
                        initial={{ scale: 1, opacity: 0.5 }}
                        animate={{ scale: 1.7, opacity: 0 }}
                        transition={{ duration: 1.6, ease: 'easeOut', repeat: Infinity, delay }}
                    />
                ))}
            <motion.button
                type='button'
                aria-label='Hold to talk'
                aria-pressed={listening}
                animate={{ scale: listening ? 1.08 : 1 }}
                whileTap={{ scale: 0.94 }}
                transition={spring.snappy}
                onPointerDown={(e) => {
                    try {
                        e.currentTarget.setPointerCapture(e.pointerId); // keep tracking if the finger slides off
                    } catch {}
                    start();
                }}
                onPointerUp={end}
                onPointerCancel={end}
                onKeyDown={(e) => (e.key === ' ' || e.key === 'Enter') && !e.repeat && start()}
                onKeyUp={(e) => (e.key === ' ' || e.key === 'Enter') && end()}
                onContextMenu={(e) => e.preventDefault()}
                className={cn(
                    'relative grid size-16 touch-none place-items-center rounded-full bg-primary text-primary-foreground shadow-float outline-none select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    state === 'processing' && 'animate-pulse',
                )}
            >
                <Mic className='size-7' strokeWidth={1.75} />
            </motion.button>
        </div>
    );
}
