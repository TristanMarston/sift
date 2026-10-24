'use client';

import { ArrowUp, Camera } from 'lucide-react';
import { motion } from 'motion/react';
import { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { ease, spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { ThemeToggle } from './theme-toggle';

type Props = {
    onScan?: () => void;
    onDescribe?: (text: string) => void;
    onUpload?: () => void;
    onSecretHold?: () => void; // 1s press on the name loads cached results (demo fallback)
    className?: string;
};

/** The landing page is the scanner's intro: name, promise, one big action. */
export function IntroScreen({ onScan, onDescribe, onUpload, onSecretHold, className }: Props) {
    const hold = useRef<ReturnType<typeof setTimeout>>(undefined);
    const startHold = () => (hold.current = setTimeout(() => onSecretHold?.(), 1000));
    const endHold = () => clearTimeout(hold.current);
    const rise = (i: number) => ({ initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, ease: ease.out, delay: 0.1 + i * 0.08 } });

    return (
        <div className={cn('flex min-h-full flex-col bg-background px-4 pt-2 pb-8', className)}>
            <div className='flex h-14 items-center justify-between'>
                <span className='px-1 type-wordmark select-none' onPointerDown={startHold} onPointerUp={endHold} onPointerLeave={endHold} onContextMenu={(e) => e.preventDefault()}>
                    Sift
                </span>
                <ThemeToggle />
            </div>
            <div className='flex flex-1 flex-col justify-end gap-8 pt-16'>
                <div className='flex flex-col gap-4'>
                    <motion.h1 {...rise(0)} className='type-display text-balance'>
                        The clothes you like already exist secondhand.
                    </motion.h1>
                    <motion.p {...rise(1)} className='type-body text-pretty text-muted-foreground'>
                        Point your camera at an outfit. Sift finds it on Depop, Poshmark, Grailed and eBay.
                    </motion.p>
                </div>
                <motion.div {...rise(2)} className='flex flex-col gap-3'>
                    <motion.div layoutId='camera-surface' transition={spring.ui} className='rounded-pill'>
                        <Button size='lg' onClick={onScan} className='w-full'>
                            <Camera data-icon='inline-start' strokeWidth={1.75} />
                            Scan an outfit
                        </Button>
                    </motion.div>
                    <form
                        className='flex h-13 items-center gap-2 rounded-pill border border-input bg-card pr-1.5 pl-5 focus-within:ring-2 focus-within:ring-ring'
                        onSubmit={(e) => {
                            e.preventDefault();
                            const text = new FormData(e.currentTarget).get('fit')?.toString().trim();
                            if (text) onDescribe?.(text);
                        }}
                    >
                        <input name='fit' aria-label='Describe a fit' placeholder='Describe a fit: 90s skater' className='min-w-0 flex-1 bg-transparent type-body outline-none placeholder:text-muted-foreground' />
                        <Button type='submit' size='icon-sm' variant='secondary' aria-label='Search'>
                            <ArrowUp strokeWidth={1.75} />
                        </Button>
                    </form>
                    <Button variant='link' size='sm' onClick={onUpload} className='self-center text-muted-foreground'>
                        Upload a photo
                    </Button>
                </motion.div>
            </div>
        </div>
    );
}
