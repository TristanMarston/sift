'use client';

import { Images, X, Zap, ZapOff } from 'lucide-react';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

type BarProps = {
    mode?: 'outfit' | 'tag';
    hint?: string;
    flash?: boolean; // undefined = the phone can't control the flash, so the button is hidden
    onFlash?: () => void;
    onClose?: () => void;
    onShutter?: () => void;
    onUpload?: () => void;
    onTypeInstead?: () => void;
    className?: string;
};

/** Camera chrome, laid out like Apple Camera. Sits over the viewfinder; always dark. */
export function CameraBar({ mode = 'outfit', hint, flash, onFlash, onClose, onShutter, onUpload, onTypeInstead, className }: BarProps) {
    return (
        <div className={cn('pointer-events-none absolute inset-0 flex flex-col justify-between p-4 text-camera-foreground', className)}>
            <div className='pointer-events-auto flex items-center justify-between'>
                <Button variant='camera' size='icon-sm' aria-label='Close camera' onClick={onClose}>
                    <X strokeWidth={1.75} />
                </Button>
                {flash !== undefined && (
                    <Button variant='camera' size='icon-sm' aria-label={flash ? 'Turn flash off' : 'Turn flash on'} aria-pressed={flash} onClick={onFlash}>
                        {flash ? <Zap strokeWidth={1.75} className='fill-current' /> : <ZapOff strokeWidth={1.75} />}
                    </Button>
                )}
            </div>
            <div className='pointer-events-auto flex flex-col items-center gap-4'>
                <p className='type-callout text-camera-muted'>{hint ?? (mode === 'tag' ? 'Fill the frame with the tag' : 'Fit the whole outfit')}</p>
                <div className='grid w-full grid-cols-[1fr_auto_1fr] items-center'>
                    <Button variant='camera' size='icon' aria-label='Upload a photo' onClick={onUpload} className='justify-self-start'>
                        <Images strokeWidth={1.75} />
                    </Button>
                    <Shutter onClick={onShutter} />
                    {mode === 'tag' ? (
                        <Button variant='camera' size='sm' onClick={onTypeInstead} className='justify-self-end'>
                            Type it in
                        </Button>
                    ) : (
                        <span />
                    )}
                </div>
            </div>
        </div>
    );
}

/** White ring with a disc that presses in. */
export function Shutter({ onClick }: { onClick?: () => void }) {
    return (
        <motion.button
            type='button'
            aria-label='Take photo'
            onClick={onClick}
            whileTap='pressed'
            className='grid size-[76px] place-items-center rounded-full border-4 border-camera-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-camera'
        >
            <motion.span className='size-[58px] rounded-full bg-camera-foreground' variants={{ pressed: { scale: 0.86 } }} transition={spring.snappy} />
        </motion.button>
    );
}

/** Care-label shaped guide for the tag camera. Everything outside it dims. */
export function TagFrame({ className }: { className?: string }) {
    const corner = 'absolute size-7 border-camera-foreground';
    return (
        <motion.div
            className={cn('pointer-events-none absolute top-[44%] left-1/2 aspect-[5/7] w-[56%] max-w-64 -translate-x-1/2 -translate-y-1/2 rounded-[18px] shadow-[0_0_0_9999px_var(--camera-scrim)]', className)}
            initial={{ scale: 1.08, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={spring.ui}
        >
            <span className={cn(corner, 'top-0 left-0 rounded-tl-[18px] border-t-[3px] border-l-[3px]')} />
            <span className={cn(corner, 'top-0 right-0 rounded-tr-[18px] border-t-[3px] border-r-[3px]')} />
            <span className={cn(corner, 'bottom-0 left-0 rounded-bl-[18px] border-b-[3px] border-l-[3px]')} />
            <span className={cn(corner, 'right-0 bottom-0 rounded-br-[18px] border-r-[3px] border-b-[3px]')} />
        </motion.div>
    );
}
