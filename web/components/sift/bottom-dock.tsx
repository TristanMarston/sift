'use client';

import { Tag } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { MicButton, type MicState } from './mic-button';
import { UpdateButton } from './update-button';

type Props = {
    likedCount: number;
    micState?: MicState;
    onScanTag?: () => void;
    onMicStart?: () => void;
    onMicEnd?: (heldMs: number) => void;
    onUpdate?: () => void;
    className?: string;
};

/** Floating bar on results: Scan tag · hold-to-talk mic · Update (after the first like). */
export function BottomDock({ likedCount, micState, onScanTag, onMicStart, onMicEnd, onUpdate, className }: Props) {
    return (
        <div className={cn('grid h-20 w-full grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-[40px] border border-border bg-card/85 px-2.5 shadow-float backdrop-blur-xl', className)}>
            <Button variant='secondary' size='sm' onClick={onScanTag} className='justify-self-start'>
                <Tag data-icon='inline-start' strokeWidth={1.75} />
                Scan tag
            </Button>
            <MicButton state={micState} onPressStart={onMicStart} onPressEnd={onMicEnd} />
            <div className='justify-self-end'>
                <AnimatePresence>
                    {likedCount > 0 && (
                        <motion.div initial={{ opacity: 0, x: 16, scale: 0.9 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, x: 16, scale: 0.9 }} transition={spring.sheet}>
                            <UpdateButton size='sm' count={likedCount} onClick={onUpdate} />
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
