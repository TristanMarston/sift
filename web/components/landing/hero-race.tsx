'use client';

import { animate, AnimatePresence, motion, useMotionValue, useMotionValueEvent, useReducedMotion, useTransform, type AnimationPlaybackControls, type MotionValue } from 'motion/react';
import { useEffect, useState } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { price } from '@/lib/format';
import { cutout } from '@/lib/garments';
import { ease, spring } from '@/lib/motion';
import { breakEven, perWear, spentAt, timesBought } from '@/lib/wear';
import { race, type Racer } from './samples';

const { fragile, sturdy, wears: N } = race;
const EVEN = breakEven(fragile, sturdy, N) ?? N;
const TOP = spentAt(N, fragile.cents, fragile.lasts) * 1.1; // chart headroom, in cents
const y = (cents: number) => 94 - (cents / TOP) * 86; // chart units: 0 top, 100 bottom
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Total spent over time: a staircase for the one that wears out, a flat line for the one that lasts.
function spendPath(r: Racer) {
    let d = `M0 ${y(r.cents)}`;
    for (let k = 1; k * r.lasts < N; k++) d += ` H${k * r.lasts} V${y(r.cents * (k + 1))}`;
    return d + ` H${N}`;
}

const perWearText = (r: Racer) => (w: number) => {
    const n = Math.max(1, Math.round(w));
    return price(perWear(spentAt(n, r.cents, r.lasts), n));
};

/** 2 · Wears tick up. The fragile tee wears out and gets bought again; the lines of total spent cross. Loops. */
export function HeroRace() {
    const reduce = useReducedMotion();
    const wear = useMotionValue(0);
    const [bought, setBought] = useState(1);
    const [even, setEven] = useState(false);
    const [done, setDone] = useState(false);
    const [visible, setVisible] = useState(true);

    useMotionValueEvent(wear, 'change', (w) => {
        setBought(timesBought(w, fragile.lasts));
        setEven(w >= EVEN);
    });

    useEffect(() => {
        let alive = true;
        let run: AnimationPlaybackControls | undefined;
        (async () => {
            while (alive) {
                wear.jump(0);
                setDone(false);
                setVisible(true);
                await wait(700);
                if (!alive) break;
                if (reduce) wear.jump(N);
                else {
                    run = animate(wear, N, { duration: 6.5, ease: 'linear' });
                    await run;
                }
                if (!alive) break;
                setDone(true);
                await wait(3800);
                if (!alive) break;
                setVisible(false);
                await wait(450);
            }
        })();
        return () => {
            alive = false;
            run?.stop();
        };
    }, [reduce, wear]);

    const x = useTransform(wear, (w) => `${(w / N) * 100}%`);
    const count = useTransform(wear, (w) => String(Math.round(w)));

    return (
        <motion.div className='absolute inset-0 flex flex-col gap-3 px-4 pb-1 lg:gap-5 lg:px-0' animate={{ opacity: visible ? 1 : 0 }} transition={{ duration: 0.4, ease: ease.out }} aria-hidden>
            <div className='grid min-h-0 flex-[1.5] grid-cols-2 gap-3 lg:gap-6'>
                <Column r={fragile} wear={wear} bought={bought} dashed />
                <Column r={sturdy} wear={wear} bought={1} />
            </div>

            <div className='relative min-h-[72px] flex-[0.8] lg:max-h-60 lg:flex-1'>
                <span className='absolute top-0 left-0 type-label text-stage-foreground/85 uppercase'>Total spent</span>
                <div className='absolute inset-y-0 right-11 left-0'>
                    <svg viewBox={`0 0 ${N} 100`} preserveAspectRatio='none' className='absolute inset-0 size-full overflow-visible'>
                        <defs>
                            <clipPath id='race-reveal'>
                                <motion.rect x='0' y='-10' height='120' width={wear} />
                            </clipPath>
                        </defs>
                        <line x1='0' x2={N} y1='99' y2='99' stroke='white' strokeOpacity='0.25' vectorEffect='non-scaling-stroke' />
                        <g clipPath='url(#race-reveal)' fill='none' vectorEffect='non-scaling-stroke' strokeLinejoin='round'>
                            <path d={spendPath(fragile)} stroke='white' strokeOpacity='0.7' strokeWidth='2' strokeDasharray='5 4' vectorEffect='non-scaling-stroke' />
                            <path d={spendPath(sturdy)} stroke='white' strokeWidth='3' vectorEffect='non-scaling-stroke' />
                        </g>
                    </svg>
                    <motion.span className='absolute inset-y-0 w-px bg-white/35' style={{ left: x }} />
                    <AnimatePresence>
                        {even && (
                            <motion.span
                                className='absolute size-3.5 -translate-1/2 rounded-full border-[3px] border-stage bg-stage-foreground shadow-[0_0_0_4px_rgba(255,255,255,0.3)]'
                                style={{ left: `${(EVEN / N) * 100}%`, top: `${y(sturdy.cents)}%` }}
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                exit={{ scale: 0 }}
                                transition={spring.pop}
                            />
                        )}
                    </AnimatePresence>
                </div>
                <AnimatePresence>
                    {done && (
                        <>
                            <EndLabel key='f' top={y(spentAt(N, fragile.cents, fragile.lasts))} text={price(spentAt(N, fragile.cents, fragile.lasts))} />
                            <EndLabel key='s' top={y(sturdy.cents)} text={price(sturdy.cents)} />
                        </>
                    )}
                </AnimatePresence>
            </div>

            <div className='flex h-9 shrink-0 items-center justify-between gap-3'>
                <span className='type-label text-stage-foreground/85 uppercase'>
                    Wear <motion.span className='tabular text-stage-foreground'>{count}</motion.span> of {N}
                </span>
                <AnimatePresence>
                    {even && (
                        <motion.span
                            className='rounded-pill bg-stage-foreground px-3.5 py-1.5 type-footnote font-semibold whitespace-nowrap text-stage'
                            initial={{ opacity: 0, y: 10, scale: 0.9 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0 }}
                            transition={spring.pop}
                        >
                            Break-even at {EVEN} wears
                        </motion.span>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
}

function EndLabel({ top, text }: { top: number; text: string }) {
    return (
        <motion.span className='absolute right-0 -translate-y-1/2 type-data tabular text-stage-foreground' style={{ top: `${top}%` }} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={spring.ui}>
            {text}
        </motion.span>
    );
}

type ColumnProps = { r: Racer; wear: MotionValue<number>; bought: number; dashed?: boolean };

/** One tee: its photo (a fresh copy drops in each time the last one wears out), its cost per wear so far, and how many were bought. */
function Column({ r, wear, bought, dashed }: ColumnProps) {
    const g = cutout(r.garment);
    const pw = useTransform(wear, perWearText(r));
    return (
        <div className='flex min-h-0 flex-col gap-1 lg:gap-1.5'>
            <div className='relative min-h-0 flex-1'>
                <AnimatePresence initial={false}>
                    <motion.div
                        key={bought}
                        className='absolute inset-0'
                        initial={{ opacity: 0, y: -28, scale: 0.92 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 14, scale: 0.8, transition: { duration: 0.35, ease: ease.out } }}
                        transition={spring.sheet}
                    >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={g.src} alt='' draggable={false} className='size-full object-contain drop-shadow-[0_14px_20px_rgba(0,0,40,0.3)]' />
                    </motion.div>
                </AnimatePresence>
                <AnimatePresence>
                    {bought > 1 && (
                        <motion.span key={bought} className='absolute top-0 right-0 rounded-pill bg-stage-foreground px-2 py-0.5 type-data font-medium tabular text-stage' initial={{ opacity: 0, y: 8 }} animate={{ opacity: [0, 1, 1, 0], y: -10 }} transition={{ duration: 1.2, times: [0, 0.15, 0.7, 1] }}>
                            +{price(r.cents)}
                        </motion.span>
                    )}
                </AnimatePresence>
                <span className='absolute bottom-0 left-0 rounded-pill bg-white/15 px-2 py-0.5 type-label text-stage-foreground uppercase backdrop-blur-sm'>
                    Tees bought · <span className='tabular'>{bought}</span>
                </span>
            </div>
            <span className='flex items-center gap-2'>
                <svg viewBox='0 0 16 4' className='h-1 w-4 shrink-0' aria-hidden>
                    <line x1='0' x2='16' y1='2' y2='2' stroke='white' strokeWidth={dashed ? 2 : 3} strokeDasharray={dashed ? '4 3' : undefined} strokeOpacity={dashed ? 0.7 : 1} />
                </svg>
                <span className='truncate type-footnote font-semibold lg:type-callout lg:font-semibold'>{r.note}</span>
            </span>
            <span className='flex items-center gap-1.5'>
                <span className='flex items-baseline gap-0.5'>
                    <motion.span className='font-serif text-[26px] leading-7 tabular lg:text-[34px] lg:leading-9'>{pw}</motion.span>
                    <span className='type-footnote text-stage-foreground/85'>/wear</span>
                </span>
                <EstTag className='text-stage-foreground/85' />
            </span>
        </div>
    );
}
