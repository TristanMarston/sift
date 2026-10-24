'use client';

import { Camera } from 'lucide-react';
import { animate, AnimatePresence, motion, useMotionValue, useReducedMotion, useTransform, type AnimationPlaybackControls, type MotionValue } from 'motion/react';
import { useEffect, useId, useRef, useState } from 'react';
import { EstTag } from '@/components/sift/status-badge';
import { price } from '@/lib/format';
import { cutout } from '@/lib/garments';
import { ease, spring } from '@/lib/motion';
import { perWear, wearSteps } from '@/lib/wear';
import { GarmentFigure } from './garment-figure';
import { dialItems, listingLine } from './samples';

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
            <motion.path d={d} fill='#0b1710' fillRule='evenodd' />
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
            return <line key={k} x1={p(r1, Math.cos)} y1={p(r1, Math.sin)} x2={p(r2, Math.cos)} y2={p(r2, Math.sin)} stroke='currentColor' strokeOpacity={lit ? 1 : major ? 0.45 : 0.25} strokeWidth={lit ? (major ? 1.1 : 0.8) : major ? 0.8 : 0.5} strokeLinecap='round' />;
        });
    return (
        <svg viewBox='-50 -50 100 100' className='absolute -inset-[10%] size-[120%] text-stage-foreground' aria-hidden>
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

/** Cost per wear always shows cents, so the number keeps its width as it falls: $38.00, $7.60, $0.19. */
const perWearText = (cents: number) => `$${(cents / 100).toFixed(2)}`;
const wearsText = (n: number) => `${n} ${n === 1 ? 'wear' : 'wears'}`;

/**
 * 5 · The lens is the scan button. An iris opens on a garment, then the price per wear steps down as the
 * wear count climbs (1, 5, 20, 50, all), with the division spelled out under the lens. Tap to scan.
 */
export function HeroDial({ onOpen }: { onOpen: (el: HTMLElement) => void }) {
    const reduce = useReducedMotion();
    const ref = useRef<HTMLButtonElement>(null);
    const open = useMotionValue(0.06);
    const wear = useMotionValue(1);
    const [i, setI] = useState(0);
    const [shown, setShown] = useState(false);
    const [phase, setPhase] = useState<Phase>('idle');
    const item = dialItems[i % dialItems.length];
    const g = cutout(item.garment);
    const cur = useRef(dialItems[0]); // the loop's garment, read by the transforms below

    // Everything reads from one wear count, so the ring, the number and the division always agree.
    const progress = useTransform(wear, (w) => w / cur.current.wears);
    const pw = useTransform(wear, (w) => perWearText(perWear(cur.current.cents, Math.max(1, Math.round(w)))));
    const worn = useTransform(wear, (w) => wearsText(Math.max(1, Math.round(w))));

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
                    await wait(5000);
                }
                return;
            }
            for (let n = 0; alive; n++) {
                cur.current = dialItems[n % dialItems.length];
                setI(n);
                wear.jump(1);
                setPhase('idle');
                run = animate(open, 0.95, { type: 'spring', bounce: 0.12, duration: 0.8 });
                await run;
                if (!alive) break;
                setShown(true); // worn once: cost per wear is the full price
                await wait(1400);
                if (!alive) break;
                setPhase('count');
                for (const step of wearSteps(cur.current.wears).slice(1)) {
                    run = animate(wear, step, { duration: 0.7, ease: [0.4, 0, 0.2, 1] });
                    await run;
                    if (!alive) break;
                    await wait(550);
                    if (!alive) break;
                }
                if (!alive) break;
                setPhase('done');
                await wait(2400);
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

    // Sized from the hero's own box, so the lens, its label and the readout always fit whatever the screen.
    return (
        <div className='absolute inset-0 flex flex-col items-center justify-center [container-type:size] [--lens:min(62cqw,calc((100cqh-170px)/1.2),380px)] lg:[--lens:min(70cqw,calc((100cqh-240px)/1.2),460px)]'>
            {/* Room for the dial ring, which reaches 10% past the lens. */}
            <div className='grid size-[calc(var(--lens)*1.2)] shrink-0 place-items-center'>
                <motion.button
                    ref={ref}
                    type='button'
                    aria-label='Scan an outfit'
                    onClick={() => ref.current && onOpen(ref.current)}
                    whileTap={{ scale: 0.96 }}
                    transition={spring.snappy}
                    className='relative size-(--lens) rounded-full outline-none focus-visible:ring-4 focus-visible:ring-stage-foreground/60'
                >
                    <Dial progress={progress} />
                    <motion.div className='absolute -inset-[5%] rounded-full bg-stage-accent/35 blur-2xl' animate={reduce ? undefined : { opacity: [0.45, 0.85, 0.45] }} transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }} aria-hidden />
                    <div className='absolute inset-0 rounded-full border-[6px] border-stage-foreground shadow-[0_0_48px_color-mix(in_srgb,var(--stage-accent)_55%,transparent)]' />
                    <div className='absolute inset-[6px] overflow-hidden rounded-full' style={{ background: 'radial-gradient(circle at 36% 28%, #1f3a2b 0%, #0c1a12 60%, #060d09 100%)' }} aria-hidden>
                        <AnimatePresence mode='popLayout'>
                            <motion.div key={item.id} className='absolute inset-[18%]' initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                                <GarmentFigure g={g} traced={shown} line='var(--trace-line)' />
                            </motion.div>
                        </AnimatePresence>
                        <Iris open={open} />
                        <svg viewBox='-50 -50 100 100' className='pointer-events-none absolute inset-0 size-full' aria-hidden>
                            <path d='M-36 -18A40 40 0 0 1-14-37' fill='none' stroke='rgba(255,255,255,0.35)' strokeWidth='2.2' strokeLinecap='round' />
                        </svg>
                    </div>
                </motion.button>
            </div>

            {/* The lens's label sits right under the ring so it reads as part of it. Same action as the lens. */}
            <motion.button
                type='button'
                tabIndex={-1}
                aria-hidden
                onClick={() => ref.current && onOpen(ref.current)}
                whileTap={{ scale: 0.96 }}
                transition={spring.snappy}
                className='-mt-1 flex shrink-0 items-center gap-1.5 rounded-pill bg-stage-foreground px-4 py-2 type-callout font-semibold text-stage shadow-float'
            >
                <Camera className='size-4' strokeWidth={2} />
                Scan an outfit
            </motion.button>

            <motion.div className='mt-5 flex flex-col items-center gap-1 text-center lg:mt-8' animate={{ opacity: shown ? 1 : 0, y: shown ? 0 : 6 }} transition={{ duration: 0.35, ease: ease.out }} aria-hidden>
                <AnimatePresence mode='wait' initial={false}>
                    <motion.span key={item.id} className='type-footnote text-stage-foreground/85 lg:type-callout' initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                        {listingLine(item)}
                    </motion.span>
                </AnimatePresence>
                <span className='flex items-baseline gap-1.5'>
                    <motion.span className='font-serif text-[44px] leading-[44px] tracking-tight tabular lg:type-numeral'>{pw}</motion.span>
                    <span className='type-callout text-stage-foreground/85'>a wear</span>
                </span>
                <span className='flex h-5 items-center gap-1.5 type-callout tabular text-stage-foreground/85'>
                    {price(item.cents)} ÷ <motion.span className='font-semibold text-stage-foreground'>{worn}</motion.span>
                    {phase === 'done' && <EstTag className='text-stage-foreground/85' />}
                </span>
            </motion.div>
        </div>
    );
}
