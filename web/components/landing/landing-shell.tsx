'use client';

import { Camera } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { CameraHandoff, type HandoffFrom } from './camera-handoff';
import { Logo } from '@/components/sift/logo';
import { health } from '@/lib/api';
import { ComparisonBar } from './comparison-bar';
import type { Variant } from './variants';

export type OpenCamera = (el: HTMLElement | null, shape?: 'rect' | 'circle', photo?: File | null) => void;

// Source for the footnote (DESCRIPTION.md §18).
const WRAP_URL = 'https://sustainablebrands.com/read/behavior-change/trending-while-wrap-scottish-designers-tout-merits-of-durable-fashion-mango-has-a-different-idea';
// const MARKETS = ['Depop', 'Poshmark', 'Grailed', 'Mercari', 'eBay']; // its line is commented out below to keep the landing one screen
const SCAN = '/scan';
// The camera, and the results it opens, live over this page at /scan and /results.
const atScan = () => [SCAN, '/results'].includes(window.location.pathname);

type Props = {
    variant: Variant;
    scanButton?: boolean; // false when the centerpiece itself is the scan button
    compare?: boolean; // /landing pages: show the design and palette switcher
    hero: (open: OpenCamera) => React.ReactNode;
};

/**
 * Landing layout on the full cobalt stage (both themes). Phone: name on top, the centerpiece in the middle,
 * headline and actions below. Desktop: text on the left, centerpiece on the right.
 */
export function LandingShell({ variant, scanButton = true, compare = false, hero }: Props) {
    const router = useRouter();
    const heroRef = useRef<HTMLDivElement>(null);
    const hold = useRef<ReturnType<typeof setTimeout>>(undefined);
    const uploadRef = useRef<HTMLInputElement>(null);
    const [from, setFrom] = useState<HandoffFrom | null>(null);
    const [file, setFile] = useState<File | null>(null);

    // The camera lives at /scan over this page: Back (button or swipe) shrinks it back into the lens.
    // Wake the API while people look at the landing, so the first scan doesn't wait on a cold start.
    useEffect(() => void health(), []);

    // The home page is always forest, even after visiting a light ("Ink") comparison page.
    useEffect(() => {
        if (!compare) delete document.documentElement.dataset.palette;
    }, [compare]);

    useEffect(() => {
        const onPop = () => !atScan() && setFrom(null);
        window.addEventListener('popstate', onPop);
        return () => window.removeEventListener('popstate', onPop);
    }, []);

    const open: OpenCamera = (el, shape = 'rect', photo: File | null = null) => {
        if (!el) return;
        const r = el.getBoundingClientRect();
        setFile(photo);
        setFrom({ x: r.left, y: r.top, w: r.width, h: r.height, shape });
        if (!atScan()) window.history.pushState(null, '', SCAN);
    };
    const close = () => (atScan() ? window.history.back() : setFrom(null));
    // "Upload a photo" opens the photo picker right away, then the camera screen with that photo.
    const uploaded = (photo?: File) => photo && open(heroRef.current, 'rect', photo);
    // Holding the name for 1s loads cached demo results. The results screen isn't built yet, so it opens the lab.
    const startHold = () => (hold.current = setTimeout(() => router.push('/design#scan'), 1000));
    const endHold = () => clearTimeout(hold.current);

    return (
        <div className='relative flex min-h-dvh w-full flex-col overflow-hidden bg-stage text-stage-foreground'>
            <header className='relative z-20 flex h-14 shrink-0 items-center px-4 lg:h-16 lg:px-8'>
                <span className='select-none [--logo-leaf:var(--stage-accent)]' onPointerDown={startHold} onPointerUp={endHold} onPointerLeave={endHold} onContextMenu={(e) => e.preventDefault()}>
                    <Logo className='h-8 text-stage-foreground lg:h-10' />
                </span>
            </header>
            {compare && <ComparisonBar current={variant} />}

            <main className='mx-auto flex w-full max-w-6xl flex-1 flex-col lg:grid lg:grid-cols-[1fr_1.1fr] lg:items-center lg:gap-16 lg:px-8 lg:pb-12'>
                <div ref={heroRef} className='relative min-h-[max(44dvh,300px)] flex-1 lg:order-2 lg:h-[min(78dvh,720px)] lg:min-h-0 lg:flex-none'>
                    {hero(open)}
                </div>

                <div className='relative z-10 flex flex-col gap-3 px-5 pt-2 pb-[max(1rem,env(safe-area-inset-bottom))] lg:order-1 lg:gap-5 lg:px-0 lg:pb-0'>
                    <h1 className='type-display text-balance lg:text-[72px] lg:leading-[72px]'>Just buy once.</h1>
                    <p className='type-body text-pretty text-stage-foreground/85 lg:max-w-md lg:text-xl lg:leading-7'>An expensive shirt you wear every day is worth more than a cheap one you wear twice.</p>
                    {scanButton && (
                        <Button variant='stage' size='lg' onClick={() => open(heroRef.current)} className='mt-1 w-full lg:w-auto lg:self-start'>
                            <Camera data-icon='inline-start' strokeWidth={1.75} />
                            Scan an outfit
                        </Button>
                    )}
                    <input
                        ref={uploadRef}
                        type='file'
                        accept='image/*'
                        className='hidden'
                        onChange={(e) => {
                            uploaded(e.target.files?.[0]);
                            e.target.value = '';
                        }}
                    />
                    <Button variant='stage-link' size='sm' onClick={() => uploadRef.current?.click()} className={scanButton ? 'self-center px-1 lg:self-start' : 'self-start px-1'}>
                        Upload a photo
                    </Button>
                    <footer className='flex flex-col gap-1.5 border-t border-stage-foreground/20 pt-3 lg:max-w-md'>
                        <p className='type-footnote text-pretty text-stage-foreground/85'>
                            Wearing clothes 9 months longer cuts their carbon, water and waste footprint by about 20–30%.{' '}
                            <a href={WRAP_URL} target='_blank' rel='noreferrer' className='underline decoration-stage-foreground/40 underline-offset-2 hover:decoration-stage-foreground'>
                                WRAP
                            </a>
                        </p>
                        {/* <p className='type-label text-stage-foreground/85 uppercase'>{MARKETS.join(' · ')}</p> */}
                    </footer>
                </div>
            </main>

            <CameraHandoff from={from} file={file} onClose={close} />
        </div>
    );
}
