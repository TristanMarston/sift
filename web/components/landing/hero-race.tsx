'use client';

import { animate, AnimatePresence, motion, useMotionValue, useMotionValueEvent, useReducedMotion, useTransform, type AnimationPlaybackControls, type MotionValue } from 'motion/react';
import { useEffect, useState, useSyncExternalStore } from 'react';
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
// Desktop columns are wider, so the intro zoom has to be gentler there or the tees overlap.
const desktop = '(min-width: 1024px)';
const onResize = (cb: () => void) => {
    const mq = matchMedia(desktop);
    mq.addEventListener('change', cb);
    return () => mq.removeEventListener('change', cb);
};
const useWide = () => useSyncExternalStore(onResize, () => matchMedia(desktop).matches, () => false);

// Total spent over time: a staircase for the one that wears out, a flat line for the one that lasts.
function spendPath(r: Racer) {
    let d = `M0 ${y(r.cents)}`;
    for (let k = 1; k * r.lasts < N; k++) d += ` H${k * r.lasts} V${y(r.cents * (k + 1))}`;
    return d + ` H${N}`;
}

// The story, one beat at a time, so the chart never arrives cold.
// 1 meet the tees (prices only) · 2 how long each lasts · 3 the race (chart) · 4 the result (cost per wear)
type Beat = 1 | 2 | 3 | 4;
const CAPTION: Record<Beat, string> = {
    1: 'Which tee costs less?',
    2: 'Depends on how long it lasts.',
    3: `Total spent over ${N} wears`,
    4: `The ${price(sturdy.cents)} tee costs less per wear.`,
};

/** 2 · Two tees, then how long each lasts, then the race: wears tick up, the fragile one gets bought again, the lines of total spent cross. Loops. */
export function HeroRace() {
    const reduce = useReducedMotion();
    const wear = useMotionValue(0);
    const [beat, setBeat] = useState<Beat>(1);
    const [bought, setBought] = useState(1);
    const [even, setEven] = useState(false);
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
                setVisible(true);
                if (reduce) {
                    wear.jump(N);
                    setBeat(4);
                    await wait(6000);
                    continue;
                }
                setBeat(1);
                await wait(1900);
                if (!alive) break;
                setBeat(2);
                await wait(2000);
                if (!alive) break;
                setBeat(3);
                await wait(800); // the chart settles in before anything moves
                if (!alive) break;
                run = animate(wear, N, { duration: 6, ease: 'linear' });
                await run;
                if (!alive) break;
                setBeat(4);
                await wait(4500);
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

    const count = useTransform(wear, (w) => String(Math.round(w)));
    const intro = beat < 3; // tees large and centered, no chart yet
    const zoom = useWide() ? 1.1 : 1.45;

    return (
        <motion.div className='absolute inset-0 flex flex-col gap-3 px-4 pb-1 lg:gap-5 lg:px-0' animate={{ opacity: visible ? 1 : 0 }} transition={{ duration: 0.4, ease: ease.out }} aria-hidden>
            <div className='relative h-6 shrink-0 lg:h-8'>
                <AnimatePresence mode='wait'>
                    <motion.p key={beat} className='absolute inset-0 text-center type-headline lg:text-[22px] lg:leading-8' initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.3, ease: ease.out }}>
                        {CAPTION[beat]}
                    </motion.p>
                </AnimatePresence>
            </div>

            <motion.div className='relative z-10 grid min-h-0 flex-[1.5] grid-cols-2 gap-3 lg:gap-6' animate={{ y: intro ? '34%' : '0%' }} transition={spring.ui}>
                <Column r={fragile} beat={beat} bought={bought} zoom={zoom} dashed />
                <Column r={sturdy} beat={beat} bought={1} zoom={zoom} />
            </motion.div>

            <motion.div className='relative min-h-[72px] flex-[0.8] lg:max-h-60 lg:flex-1' animate={{ opacity: intro ? 0 : 1, y: intro ? 16 : 0 }} transition={{ ...spring.ui, delay: intro ? 0 : 0.15 }}>
                <div className='absolute inset-y-0 right-11 left-0'>
                    <svg viewBox={`0 0 ${N} 100`} preserveAspectRatio='none' className='absolute inset-0 size-full overflow-visible'>
                        <defs>
                            <clipPath id='race-reveal'>
                                <motion.rect x='0' y='-10' height='120' width={wear} />
                            </clipPath>
                        </defs>
                        <line x1='0' x2={N} y1='99' y2='99' stroke='white' strokeOpacity='0.25' vectorEffect='non-scaling-stroke' />
                        <g clipPath='url(#race-reveal)' fill='none' strokeLinejoin='round'>
                            <path d={spendPath(fragile)} stroke='white' strokeOpacity='0.7' strokeWidth='2' strokeDasharray='5 4' vectorEffect='non-scaling-stroke' />
                            <path d={spendPath(sturdy)} stroke='white' strokeWidth='3' vectorEffect='non-scaling-stroke' />
                        </g>
                    </svg>
                    <Tip r={fragile} wear={wear} />
                    <Tip r={sturdy} wear={wear} />
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
                    {beat === 4 && (
                        <>
                            <EndLabel key='f' top={y(spentAt(N, fragile.cents, fragile.lasts))} text={price(spentAt(N, fragile.cents, fragile.lasts))} />
                            <EndLabel key='s' top={y(sturdy.cents)} text={price(sturdy.cents)} />
                        </>
                    )}
                </AnimatePresence>
            </motion.div>

            <motion.div className='flex h-9 shrink-0 items-center justify-between gap-3' animate={{ opacity: intro ? 0 : 1 }} transition={{ duration: 0.3, delay: intro ? 0 : 0.3 }}>
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
            </motion.div>
        </motion.div>
    );
}

/** The moving tip of a line: each tee as a racer. */
function Tip({ r, wear }: { r: Racer; wear: MotionValue<number> }) {
    const left = useTransform(wear, (w) => `${(w / N) * 100}%`);
    const top = useTransform(wear, (w) => `${y(spentAt(w, r.cents, r.lasts))}%`);
    return <motion.span className='absolute size-2.5 -translate-1/2 rounded-full bg-stage-foreground' style={{ left, top }} />;
}

function EndLabel({ top, text }: { top: number; text: string }) {
    return (
        <motion.span className='absolute right-0 -translate-y-1/2 type-data tabular text-stage-foreground' style={{ top: `${top}%` }} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={spring.ui}>
            {text}
        </motion.span>
    );
}

type ColumnProps = { r: Racer; beat: Beat; bought: number; zoom: number; dashed?: boolean };

/** One tee: its photo (a fresh copy drops in each time the last one wears out), its price, how long it lasts, and finally its cost per wear. */
function Column({ r, beat, bought, zoom, dashed }: ColumnProps) {
    const g = cutout(r.garment);
    const fade = (show: boolean) => ({ animate: { opacity: show ? 1 : 0, y: show ? 0 : 6 }, transition: { duration: 0.35, ease: ease.out } });
    return (
        <div className='flex min-h-0 flex-col gap-1 lg:gap-1.5'>
            <div className='relative min-h-0 flex-1'>
                <motion.div className='absolute inset-0' style={{ originY: 1 }} animate={{ scale: beat < 3 ? zoom : 1 }} transition={spring.ui}>
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
                </motion.div>
                <AnimatePresence>
                    {bought > 1 && (
                        <motion.span key={bought} className='absolute top-0 right-0 rounded-pill bg-stage-foreground px-2 py-0.5 type-data font-medium tabular text-stage' initial={{ opacity: 0, y: 8 }} animate={{ opacity: [0, 1, 1, 0], y: -10 }} transition={{ duration: 1.2, times: [0, 0.15, 0.7, 1] }}>
                            +{price(r.cents)}
                        </motion.span>
                    )}
                </AnimatePresence>
                <motion.span className='absolute bottom-0 left-0 rounded-pill bg-white/15 px-2 py-0.5 type-label text-stage-foreground uppercase backdrop-blur-sm' {...fade(beat >= 3)}>
                    Tees bought · <span className='tabular'>{bought}</span>
                </motion.span>
            </div>
            <motion.span className='flex items-center gap-2' {...fade(beat >= 2)}>
                <svg viewBox='0 0 16 4' className='h-1 w-4 shrink-0' aria-hidden>
                    <line x1='0' x2='16' y1='2' y2='2' stroke='white' strokeWidth={dashed ? 2 : 3} strokeDasharray={dashed ? '4 3' : undefined} strokeOpacity={dashed ? 0.7 : 1} />
                </svg>
                <span className='truncate type-footnote font-semibold lg:type-callout lg:font-semibold'>{r.note}</span>
            </motion.span>
            <span className='relative h-7 lg:h-9'>
                <AnimatePresence mode='popLayout' initial={false}>
                    {beat < 4 ? (
                        <motion.span key='price' className='absolute inset-0 flex items-baseline gap-1' initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={spring.snappy}>
                            <span className='font-serif text-[26px] leading-7 tabular lg:text-[34px] lg:leading-9'>{price(r.cents)}</span>
                        </motion.span>
                    ) : (
                        <motion.span key='wear' className='absolute inset-0 flex items-center gap-1.5' initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={spring.snappy}>
                            <span className='flex items-baseline gap-0.5'>
                                <span className='font-serif text-[26px] leading-7 tabular lg:text-[34px] lg:leading-9'>{price(perWear(spentAt(N, r.cents, r.lasts), N))}</span>
                                <span className='type-footnote text-stage-foreground/85'>/wear</span>
                            </span>
                            <EstTag className='text-stage-foreground/85' />
                        </motion.span>
                    )}
                </AnimatePresence>
            </span>
        </div>
    );
}
