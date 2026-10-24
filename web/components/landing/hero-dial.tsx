'use client';

import { animate, AnimatePresence, motion, useMotionValue, useReducedMotion, useTransform, type AnimationPlaybackControls, type MotionValue } from 'motion/react';
import { useEffect, useId, useRef, useState } from 'react';
import { price } from '@/lib/format';
import { cutout } from '@/lib/garments';
import { ease, spring } from '@/lib/motion';
import { perWear } from '@/lib/wear';
import { GarmentFigure } from './garment-figure';
import { dialItems, metaLine } from './samples';

const BLADES = 8;
const TICKS = 72;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

// Iris geometry in a -50..50 box: an octagon hole that grows and turns as it opens.
const verts = (o: number) =>
    Array.from({ length: BLADES }, (_, k) => {
        const a = ((k * 360) / BLADES + (1 - o) * 40) * (Math.PI / 180);
        const r = 3 + o * 46;
        return [r * Math.cos(a), r * Math.sin(a)];
    });
const irisPath = (o: number) => 'M-60-60H60V60H-60Z M' + verts(o).map((p) => p.map((n) => n.toFixed(2)).join(' ')).join('L') + 'Z';
// Each blade edge continues past its corner to the rim.
const seamPath = (o: number) =>
    verts(o)
        .map((a, k, v) => {
            const b = v[(k + 1) % BLADES];
            const [dx, dy] = [b[0] - a[0], b[1] - a[1]];
            const L = Math.hypot(dx, dy) || 1;
            const [ux, uy] = [dx / L, dy / L];
            const bb = b[0] * ux + b[1] * uy;
            const t = -bb + Math.sqrt(Math.max(0, bb * bb - (b[0] ** 2 + b[1] ** 2 - 2500)));
            return `M${b[0].toFixed(2)} ${b[1].toFixed(2)}L${(b[0] + ux * t).toFixed(2)} ${(b[1] + uy * t).toFixed(2)}`;
        })
        .join('');
// A pie slice from 12 o'clock, clockwise, covering share p of the ring. It lights the ticks.
const wedge = (p: number) => {
    if (p <= 0) return 'M0 0Z';
    if (p >= 1) return 'M-60-60H60V60H-60Z';
    const a = p * 2 * Math.PI;
    return `M0 0L0 -60A60 60 0 ${p > 0.5 ? 1 : 0} 1 ${(60 * Math.sin(a)).toFixed(2)} ${(-60 * Math.cos(a)).toFixed(2)}Z`;
};

function Iris({ open }: { open: MotionValue<number> }) {
    const d = useTransform(open, irisPath);
    const seams = useTransform(open, seamPath);
    return (
        <svg viewBox='-50 -50 100 100' className='absolute inset-0 size-full' aria-hidden>
            <motion.path d={d} fill='#141728' fillRule='evenodd' />
            <motion.path d={seams} fill='none' stroke='rgba(255,255,255,0.12)' strokeWidth='0.5' />
        </svg>
    );
}

/** The ring's 72 ticks. They light up clockwise from the top as the wear count climbs. */
function Dial({ progress }: { progress: MotionValue<number> }) {
    const mask = 'dial-' + useId().replace(/[^a-zA-Z0-9]/g, '');
    const d = useTransform(progress, wedge);
    const ticks = (lit: boolean) =>
        Array.from({ length: TICKS }, (_, k) => {
            const a = (k * (360 / TICKS) * Math.PI) / 180;
            const major = k % 6 === 0;
            const [r1, r2] = major ? [45, 49.5] : [46.5, 49];
            const p = (r: number, f: (x: number) => number) => +(r * f(a)).toFixed(2); // rounded so server and browser agree
            return <line key={k} x1={p(r1, Math.cos)} y1={p(r1, Math.sin)} x2={p(r2, Math.cos)} y2={p(r2, Math.sin)} stroke='white' strokeOpacity={lit ? 1 : major ? 0.45 : 0.25} strokeWidth={lit ? (major ? 1.1 : 0.8) : major ? 0.8 : 0.5} strokeLinecap='round' />;
        });
    return (
        <svg viewBox='-50 -50 100 100' className='absolute -inset-[10%] size-[120%]' aria-hidden>
            <defs>
                <mask id={mask}>
                    <motion.path d={d} fill='white' />
                </mask>
            </defs>
            <g>{ticks(false)}</g>
            <g mask={`url(#${mask})`}>{ticks(true)}</g>
        </svg>
    );
}

type Phase = 'idle' | 'count' | 'done';

/** 5 · The lens is the scan button. An iris opens on a garment; as the ring counts wears, its price per wear drops. Tap to scan. */
export function HeroDial({ onOpen }: { onOpen: (el: HTMLElement) => void }) {
    const reduce = useReducedMotion();
    const ref = useRef<HTMLButtonElement>(null);
    const open = useMotionValue(0.06);
    const wear = useMotionValue(0);
    const [i, setI] = useState(0);
    const [shown, setShown] = useState(false);
    const [phase, setPhase] = useState<Phase>('idle');
    const item = dialItems[i % dialItems.length];
    const g = cutout(item.garment);
    const cur = useRef(dialItems[0]); // the loop's garment, read by the transforms below

    const progress = useTransform(wear, (w) => w / cur.current.wears);
    const pw = useTransform(wear, (w) => price(w < 1 ? cur.current.cents : perWear(cur.current.cents, Math.round(w))));
    const count = useTransform(wear, (w) => `Wear ${Math.round(w)}`);

    useEffect(() => {
        let alive = true;
        let run: AnimationPlaybackControls | undefined;
        (async () => {
            if (reduce) {
                // Still frame per garment, swapped with a fade.
                open.set(0.95);
                setShown(true);
                for (let n = 0; alive; n++) {
                    cur.current = dialItems[n % dialItems.length];
                    setI(n);
                    wear.jump(cur.current.wears);
                    setPhase('done');
                    await wait(4500);
                }
                return;
            }
            for (let n = 0; alive; n++) {
                cur.current = dialItems[n % dialItems.length];
                setI(n);
                wear.jump(0);
                setPhase('idle');
                run = animate(open, 0.95, { type: 'spring', bounce: 0.12, duration: 0.8 });
                await run;
                if (!alive) break;
                setShown(true);
                await wait(900);
                if (!alive) break;
                setPhase('count');
                run = animate(wear, cur.current.wears, { duration: 3.4, ease: 'linear' });
                await run;
                if (!alive) break;
                setPhase('done');
                await wait(2000);
                if (!alive) break;
                setShown(false);
                run = animate(open, 0.06, { type: 'spring', bounce: 0, duration: 0.55 });
                await run;
                if (!alive) break;
                await wait(300);
            }
        })();
        return () => {
            alive = false;
            run?.stop();
        };
    }, [reduce, open, wear]);

    return (
        <div className='absolute inset-0 grid place-items-center'>
            <div className='-translate-y-[5%]'>
                <motion.button
                    ref={ref}
                    type='button'
                    aria-label='Scan an outfit'
                    onClick={() => ref.current && onOpen(ref.current)}
                    whileTap={{ scale: 0.96 }}
                    transition={spring.snappy}
                    className='relative size-[min(70vw,38dvh,400px)] rounded-full outline-none focus-visible:ring-4 focus-visible:ring-stage-foreground/60 lg:size-[min(38vw,62dvh,520px)]'
                >
                    <Dial progress={progress} />
                    <motion.div className='absolute -inset-[5%] rounded-full bg-stage-foreground/25 blur-2xl' animate={reduce ? undefined : { opacity: [0.45, 0.85, 0.45] }} transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }} aria-hidden />
                    <div className='absolute inset-0 rounded-full border-[6px] border-stage-foreground shadow-[0_0_48px_rgba(255,255,255,0.35)]' />
                    <div className='absolute inset-[6px] overflow-hidden rounded-full' style={{ background: 'radial-gradient(circle at 36% 28%, #2a3050 0%, #0e1020 60%, #07080f 100%)' }} aria-hidden>
                        <AnimatePresence mode='popLayout'>
                            <motion.div key={item.id} className='absolute inset-x-[21%] top-[17%] bottom-[29%]' initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                                <GarmentFigure g={g} traced={shown} line='#ffffff' />
                            </motion.div>
                        </AnimatePresence>
                        <Iris open={open} />
                        <AnimatePresence>
                            {shown && (
                                <motion.div key={item.id} className='absolute inset-0' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }} transition={{ duration: 0.35, ease: ease.out }}>
                                    <span className='absolute inset-x-0 top-[9%] text-center type-label text-white/85 uppercase'>{metaLine(item)}</span>
                                    <span className='absolute bottom-[15%] left-1/2 flex -translate-x-1/2 items-baseline gap-1 rounded-pill bg-stage-foreground px-3.5 py-1 whitespace-nowrap text-stage shadow-float'>
                                        <motion.span className='font-serif text-[22px] leading-7 tabular lg:text-[28px] lg:leading-9'>{pw}</motion.span>
                                        {phase !== 'idle' && <span className='type-footnote font-semibold'>a wear</span>}
                                    </span>
                                    <span className='absolute inset-x-0 bottom-[7%] text-center type-label text-white/85 uppercase'>
                                        {phase === 'done' ? `${item.wears} wears · est.` : phase === 'count' ? <motion.span className='tabular'>{count}</motion.span> : 'Price'}
                                    </span>
                                </motion.div>
                            )}
                        </AnimatePresence>
                        <svg viewBox='-50 -50 100 100' className='pointer-events-none absolute inset-0 size-full' aria-hidden>
                            <path d='M-36 -18A40 40 0 0 1-14-37' fill='none' stroke='rgba(255,255,255,0.35)' strokeWidth='2.2' strokeLinecap='round' />
                        </svg>
                    </div>
                    {/* Sits just outside the dial, at any lens size. */}
                    <motion.span className='absolute top-[115%] left-1/2 -translate-x-1/2 type-callout whitespace-nowrap text-stage-foreground' animate={reduce ? undefined : { opacity: [0.6, 1, 0.6] }} transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}>
                        Scan an outfit
                    </motion.span>
                </motion.button>
            </div>
        </div>
    );
}
