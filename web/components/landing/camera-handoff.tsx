'use client';

import { AnimatePresence, motion } from 'motion/react';
import { useRouter } from 'next/navigation';
import { CameraBar } from '@/components/sift/camera-controls';

export type HandoffFrom = { x: number; y: number; w: number; h: number; shape: 'rect' | 'circle'; radius?: number };

// Clip paths for the start (the centerpiece's box) and the end (the whole screen).
function clips(f: HandoffFrom) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (f.shape === 'circle') {
        const [cx, cy] = [f.x + f.w / 2, f.y + f.h / 2];
        return { from: `circle(${f.w / 2}px at ${cx}px ${cy}px)`, to: `circle(${Math.hypot(Math.max(cx, vw - cx), Math.max(cy, vh - cy))}px at ${cx}px ${cy}px)` };
    }
    const r = f.radius ?? 28;
    return { from: `inset(${f.y}px ${vw - f.x - f.w}px ${vh - f.y - f.h}px ${f.x}px round ${r}px)`, to: 'inset(0px 0px 0px 0px round 0px)' };
}

/** The centerpiece grows into the camera. Closing shrinks it back into the same place. */
export function CameraHandoff({ from, onClose }: { from: HandoffFrom | null; onClose: () => void }) {
    const router = useRouter();
    const c = from ? clips(from) : null;
    return (
        <AnimatePresence>
            {from && c && (
                <motion.div
                    key='camera'
                    className='fixed inset-0 z-50 bg-camera'
                    initial={{ clipPath: c.from }}
                    animate={{ clipPath: c.to }}
                    exit={{ clipPath: c.from }}
                    transition={{ type: 'spring', bounce: 0, duration: 0.55 }}
                >
                    <motion.div className='absolute inset-0' initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.3, duration: 0.3 } }} exit={{ opacity: 0, transition: { duration: 0.12 } }}>
                        {/* Viewfinder placeholder until the real camera flow exists. */}
                        <div className='absolute inset-x-0 top-14 mx-auto aspect-[3/4] max-w-md'>
                            <div className='absolute top-1/2 left-1/2 size-24 -translate-1/2 rounded-3xl border-2 border-camera-foreground/40' />
                        </div>
                        <div className='absolute inset-0 mx-auto max-w-md'>
                            <CameraBar onClose={onClose} onShutter={() => router.push('/design#scan')} onUpload={() => router.push('/design#scan')} />
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
