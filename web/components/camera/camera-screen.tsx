'use client';

import { CameraOff, Images, RotateCcw, SwitchCamera, X, Zap, ZapOff } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Shutter } from '@/components/sift/camera-controls';
import { GarmentCutout } from '@/components/sift/garment-tabs';
import { Notice } from '@/components/sift/notice';
import { SearchCounter } from '@/components/sift/search-counter';
import { ScanTrace, type ScanPhase } from '@/components/sift/scan-trace';
import { Button } from '@/components/ui/button';
import { detect } from '@/lib/api';
import { toGarments, type Box } from '@/lib/detect';
import { ease, spring } from '@/lib/motion';
import { MARKET } from '@/lib/results';
import type { Garment } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BoxDraw } from './box-draw';
import { captureFrame, photoFromFile, type Shot } from './capture';
import { useCamera } from './use-camera';

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const SCAN_AT_LEAST = 1400; // the scan line gets one full pass even when detection is instant
const SLOW_AFTER = 5000; // a cold API takes ~10s to find garments: say so instead of looking stuck
const MARKETS = Object.values(MARKET);

export type SearchState = { total: number; elapsedMs?: number; lifted: boolean; selectedId: string; label?: string | null };

type Props = {
    onClose: () => void;
    initialFile?: File | null; // opened from "Upload a photo": skip the live camera until Retake
    onTraced?: (shot: Shot, garments: Garment[]) => void; // tracing landed: start the search
    onRetake?: () => void;
    search?: SearchState | null; // while set, the search counter replaces the shutter row
    onShowResults?: () => void; // after Back from results: the finished counter reopens them
    handedOff?: boolean; // results are showing: the lifted garment now lives in their header, and the camera rests
    drawing?: boolean; // "Draw a box": drag around the garment detection missed
    onBoxDrawn?: (box: Box) => void;
    onCancelDraw?: () => void;
};

/**
 * The scanner, laid out like Apple Camera and always dark: close and flash on top, a 3:4 viewfinder,
 * then the hint, upload, shutter and camera flip. The shutter flashes and freezes the frame, the scan line
 * runs while garments are found, then each garment is traced. Retake is always one tap away.
 */
export function CameraScreen({ onClose, initialFile, onTraced, onRetake, search, onShowResults, handedOff = false, drawing = false, onBoxDrawn, onCancelDraw }: Props) {
    const reduce = useReducedMotion();
    const fileRef = useRef<HTMLInputElement>(null);
    const [wantCamera, setWantCamera] = useState(!initialFile);
    const { videoRef, status, mirrored, canFlip, torch, flip, toggleTorch, retry } = useCamera(wantCamera && !handedOff); // camera light off while results show
    const [shot, setShot] = useState<Shot | null>(null);
    const [phase, setPhase] = useState<ScanPhase>('scanning');
    const [garments, setGarments] = useState<Garment[]>([]);
    const [flashKey, setFlashKey] = useState(0);
    const [slow, setSlow] = useState(false);
    const run = useRef(0); // ignores a scan that finishes after Retake

    const scan = useCallback(async (next: Shot) => {
        const id = ++run.current;
        setShot(next);
        setPhase('scanning');
        setGarments([]);
        setSlow(false);
        const slowTimer = setTimeout(() => id === run.current && setSlow(true), SLOW_AFTER);
        const [res] = await Promise.all([detect(next.blob), wait(SCAN_AT_LEAST)]);
        clearTimeout(slowTimer);
        if (id !== run.current) return;
        setGarments(toGarments(res));
        setPhase('tracing');
    }, []);

    // Opened from "Upload a photo" on the landing page.
    const started = useRef(false);
    useEffect(() => {
        if (!initialFile || started.current) return;
        started.current = true;
        photoFromFile(initialFile).then(scan, () => setWantCamera(true));
    }, [initialFile, scan]);

    // Free the photo's memory when it's replaced or the screen closes.
    useEffect(() => () => void (shot && URL.revokeObjectURL(shot.url)), [shot]);

    const takePhoto = async () => {
        const video = videoRef.current;
        if (status !== 'live' || !video?.videoWidth) return;
        setFlashKey((k) => k + 1);
        scan(await captureFrame(video));
    };

    const upload = async (file?: File) => {
        if (file) scan(await photoFromFile(file));
    };

    const retake = () => {
        run.current++;
        setShot(null);
        setGarments([]);
        setWantCamera(true);
        onRetake?.();
    };

    const live = !shot && status === 'live';
    const hint = live ? 'Fit the whole outfit' : '';
    const lifted = search?.lifted ? garments.find((g) => g.id === search.selectedId) : undefined;

    return (
        <div className='relative flex size-full flex-col bg-camera text-camera-foreground select-none'>
            {/* Top band */}
            <div className='flex shrink-0 items-center justify-between px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-3'>
                <AnimatePresence mode='popLayout' initial={false}>
                    {shot ? (
                        <motion.div key='retake' initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2, ease: ease.out }}>
                            <Button variant='camera' size='sm' onClick={retake}>
                                <RotateCcw data-icon='inline-start' strokeWidth={1.75} />
                                Retake
                            </Button>
                        </motion.div>
                    ) : (
                        <motion.div key='close' initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2, ease: ease.out }}>
                            <Button variant='camera' size='icon-sm' aria-label='Close camera' onClick={onClose}>
                                <X strokeWidth={1.75} />
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>
                {shot ? (
                    <Button variant='camera' size='icon-sm' aria-label='Close camera' onClick={onClose}>
                        <X strokeWidth={1.75} />
                    </Button>
                ) : (
                    torch !== undefined && (
                        <Button variant='camera' size='icon-sm' aria-label={torch ? 'Turn flash off' : 'Turn flash on'} aria-pressed={torch} onClick={toggleTorch}>
                            {torch ? <Zap strokeWidth={1.75} className='fill-current' /> : <ZapOff strokeWidth={1.75} />}
                        </Button>
                    )
                )}
            </div>

            {/* Viewfinder: a 3:4 frame that fits whatever room is left, like a phone camera. */}
            <div className='relative grid min-h-0 flex-1 place-items-center px-0 [container-type:size] sm:px-4'>
                <div className='relative aspect-[3/4] w-[min(100cqw,calc(100cqh*0.75),448px)] overflow-hidden bg-black sm:rounded-[14px]'>
                    <video ref={videoRef} playsInline muted autoPlay className={cn('absolute inset-0 size-full object-cover transition-opacity duration-300', mirrored && '-scale-x-100', live ? 'opacity-100' : 'opacity-0')} aria-label='Camera preview' />
                    {!shot && <CameraState status={status} onUpload={() => fileRef.current?.click()} onRetry={retry} waiting={wantCamera} />}
                </div>
                {shot && (
                    <div className='absolute inset-0 grid place-items-center sm:px-4'>
                        <div className='relative' style={{ width: `min(100cqw, calc(100cqh * ${shot.aspect}), 448px)` }}>
                            <ScanTrace
                                garments={garments}
                                phase={phase}
                                photo={shot.url}
                                aspect={shot.aspect}
                                scanningHint={slow ? 'Waking up the scanner…' : undefined}
                                onTraced={() => {
                                    setPhase('done');
                                    onTraced?.(shot, garments);
                                }}
                                className='w-full sm:rounded-[14px]'
                            />
                            {/* The garment lifts out of the photo, then flies into the results header (same layoutId). */}
                            {drawing && onBoxDrawn && <BoxDraw onDone={onBoxDrawn} />}
                            {lifted && !handedOff && (
                                <motion.div
                                    layoutId={`garment-${lifted.id}`}
                                    className='absolute drop-shadow-[0_18px_28px_rgba(0,0,0,0.5)]'
                                    style={{ left: `${lifted.bbox.x * 100}%`, top: `${lifted.bbox.y * 100}%`, width: `${lifted.bbox.w * 100}%`, height: `${lifted.bbox.h * 100}%` }}
                                    initial={{ scale: 1 }}
                                    animate={{ scale: 1.04 }}
                                    transition={spring.ui}
                                >
                                    <GarmentCutout garment={lifted} src={shot.url} aspect={shot.aspect} />
                                </motion.div>
                            )}
                        </div>
                    </div>
                )}
                {/* The shutter flash: a quick white bloom over the frozen frame. */}
                <AnimatePresence>
                    {flashKey > 0 && !reduce && (
                        <motion.div key={flashKey} className='pointer-events-none absolute inset-0 bg-white' initial={{ opacity: 0.85 }} animate={{ opacity: 0 }} transition={{ duration: 0.45, ease: ease.out }} />
                    )}
                </AnimatePresence>
            </div>

            {/* Bottom band: the shutter row, or the live search counter once garments are traced. */}
            <div className='relative flex shrink-0 flex-col items-center gap-4 px-4 pt-4 pb-[max(1.25rem,env(safe-area-inset-bottom))]'>
                <AnimatePresence>
                    {drawing && (
                        <motion.div key='draw' className='absolute inset-x-4 bottom-[max(1.25rem,env(safe-area-inset-bottom))] z-20 mx-auto flex max-w-md items-center justify-between gap-3 rounded-card bg-camera-control px-4 py-3 backdrop-blur-xl' initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 40 }} transition={spring.sheet}>
                            <p className='type-callout text-camera-foreground'>Drag around the garment you mean</p>
                            <Button variant='camera' size='sm' onClick={onCancelDraw}>
                                Cancel
                            </Button>
                        </motion.div>
                    )}
                    {search && !drawing && (
                        <motion.div key='counter' className='absolute inset-x-4 bottom-[max(1.25rem,env(safe-area-inset-bottom))] z-10 mx-auto max-w-md' initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 40 }} transition={spring.sheet}>
                            {/* Always the same element, so the count never restarts. After Back from results it reopens them. */}
                            <button type='button' onClick={onShowResults} disabled={!onShowResults || search.lifted} aria-label={onShowResults ? 'Show results' : undefined} className='block w-full rounded-card text-left outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default'>
                                <SearchCounter total={search.total} marketplaces={MARKETS} elapsedMs={search.elapsedMs} label={search.label} />
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
                <p className='h-5 type-callout text-camera-muted' aria-live='polite'>
                    {hint}
                </p>
                <div className={cn('grid w-full max-w-md grid-cols-[1fr_auto_1fr] items-center transition-opacity duration-200', (search || drawing) && 'pointer-events-none opacity-0')}>
                    <Button variant='camera' size='icon' aria-label='Upload a photo' onClick={() => fileRef.current?.click()} className='justify-self-start'>
                        <Images strokeWidth={1.75} />
                    </Button>
                    <Shutter onClick={takePhoto} disabled={!live} />
                    {canFlip && !shot ? (
                        <Button variant='camera' size='icon' aria-label='Switch camera' onClick={flip} className='justify-self-end'>
                            <SwitchCamera strokeWidth={1.75} />
                        </Button>
                    ) : (
                        <span />
                    )}
                </div>
            </div>

            <input
                ref={fileRef}
                type='file'
                accept='image/*'
                className='hidden'
                onChange={(e) => {
                    upload(e.target.files?.[0]);
                    e.target.value = ''; // picking the same photo again still fires
                }}
            />
        </div>
    );
}

type StateProps = { status: ReturnType<typeof useCamera>['status']; waiting: boolean; onUpload: () => void; onRetry: () => void };

/** Everything the viewfinder can say before there's a picture. Each problem offers a way forward. */
function CameraState({ status, waiting, onUpload, onRetry }: StateProps) {
    const upload = (
        <Button variant='stage' size='sm' onClick={onUpload}>
            <Images data-icon='inline-start' strokeWidth={1.75} />
            Upload a photo
        </Button>
    );
    return (
        <AnimatePresence>
            {status === 'starting' && waiting && (
                // Only shows if the permission prompt (or a slow camera) takes a moment.
                <motion.p key='starting' className='absolute inset-x-0 top-1/2 -translate-y-1/2 px-8 text-center type-callout text-camera-muted' initial={{ opacity: 0 }} animate={{ opacity: 1, transition: { delay: 0.5 } }} exit={{ opacity: 0 }}>
                    Allow camera access to scan
                </motion.p>
            )}
            {(status === 'denied' || status === 'unsupported' || status === 'error') && (
                <motion.div key={status} className='absolute inset-0 grid place-items-center' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    {status === 'denied' && <Notice surface='camera' icon={CameraOff} title="Camera's off" body='Upload a photo instead, or allow the camera in Settings.' actions={upload} />}
                    {status === 'unsupported' && <Notice surface='camera' icon={CameraOff} title="Can't open the camera here" body="This address doesn't allow camera access. Upload a photo instead." actions={upload} />}
                    {status === 'error' && (
                        <Notice
                            surface='camera'
                            icon={CameraOff}
                            title="Couldn't start the camera"
                            body='Another app may be using it. Try again, or upload a photo.'
                            actions={
                                <>
                                    <Button variant='camera' size='sm' onClick={onRetry}>
                                        Try again
                                    </Button>
                                    {upload}
                                </>
                            }
                        />
                    )}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
