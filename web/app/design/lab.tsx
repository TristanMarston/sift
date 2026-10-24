'use client';

import { CameraOff, RotateCcw, ScanSearch, Shirt, SearchX, TagIcon } from 'lucide-react';
import { AnimatePresence, LayoutGroup, motion } from 'motion/react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { BottomDock } from '@/components/sift/bottom-dock';
import { CameraBar, TagFrame } from '@/components/sift/camera-controls';
import { FiberBar } from '@/components/sift/fiber-bar';
import { FootprintStat } from '@/components/sift/footprint-stat';
import { GarmentTabs } from '@/components/sift/garment-tabs';
import { ImpactReceipt } from '@/components/sift/impact-receipt';
import { IntroScreen } from '@/components/sift/intro-screen';
import { LearnedLine } from '@/components/sift/learned-line';
import { MatchCard, MatchCardSkeleton } from '@/components/sift/match-card';
import type { MicState } from '@/components/sift/mic-button';
import { Notice } from '@/components/sift/notice';
import { QRPanel } from '@/components/sift/qr-panel';
import { ReasonChip } from '@/components/sift/reason-chip';
import { SampleOutfit } from '@/components/sift/sample-outfit';
import { ScanTrace, type ScanPhase } from '@/components/sift/scan-trace';
import { SearchCounter } from '@/components/sift/search-counter';
import { EstTag, StatusBadge } from '@/components/sift/status-badge';
import { TopBar } from '@/components/sift/top-bar';
import { ValueChip } from '@/components/sift/value-chip';
import { VoiceSheet, type VoicePhase } from '@/components/sift/voice-sheet';
import { price } from '@/lib/format';
import { spring } from '@/lib/motion';
import * as S from '@/lib/sample-data';

const COLORS = ['background', 'card', 'foreground', 'muted-foreground', 'primary', 'primary-tint', 'secondary', 'muted', 'input', 'destructive', 'verified', 'claimed', 'unknown', 'fiber-plant', 'fiber-animal', 'fiber-regenerated', 'fiber-synthetic', 'receipt-paper', 'camera', 'camera-control'];
const TYPE = [
    ['type-display', 'The clothes you like already exist secondhand.'],
    ['type-title-1', 'Wool chore coat'],
    ['type-title-2', 'Exact match'],
    ['type-numeral', '50%'],
    ['type-quote', 'you like boxy fits and earth tones.'],
    ['type-headline', 'Carhartt chore coat'],
    ['type-body', 'Point your camera at an outfit.'],
    ['type-callout', 'Natural fibers'],
    ['type-footnote', 'Polyester sheds microplastics every wash.'],
    ['type-data', 'DEPOP · SIZE M · GOOD'],
    ['type-counter', '18,432'],
    ['type-label', 'EST.'],
];
const NAV = ['Colors', 'Type', 'Controls', 'Intro', 'Scan', 'Results', 'Tag', 'Receipt', 'States'];

function Section({ title, note, onReplay, children }: { title: string; note?: string; onReplay?: () => void; children: React.ReactNode }) {
    return (
        <section id={title.toLowerCase()} className='flex scroll-mt-16 flex-col gap-5'>
            <div className='flex items-end justify-between gap-3'>
                <div className='flex flex-col gap-1'>
                    <h2 className='type-title-2'>{title}</h2>
                    {note && <p className='type-footnote text-muted-foreground'>{note}</p>}
                </div>
                {onReplay && (
                    <Button variant='secondary' size='sm' onClick={onReplay}>
                        <RotateCcw data-icon='inline-start' strokeWidth={1.75} />
                        Replay
                    </Button>
                )}
            </div>
            {children}
        </section>
    );
}

const Phone = ({ children, dark, className = '' }: { children: React.ReactNode; dark?: boolean; className?: string }) => (
    <div className={`relative mx-auto w-full max-w-sm overflow-clip rounded-[32px] ring-1 ring-border ${dark ? 'bg-camera' : 'bg-background'} ${className}`}>{children}</div>
);

export function Lab() {
    return (
        <div className='min-h-full'>
            <TopBar />
            <main className='mx-auto flex w-full max-w-5xl flex-col gap-16 px-4 pt-4 pb-40'>
                <div className='flex flex-col gap-3'>
                    <h1 className='type-title-1'>Design lab</h1>
                    <p className='max-w-prose type-body text-muted-foreground'>Every piece here is the real component, running on sample data. Switch themes with the button at the top right.</p>
                    <nav className='-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none]'>
                        {NAV.map((n) => (
                            <a key={n} href={`#${n.toLowerCase()}`} className='shrink-0 rounded-pill bg-secondary px-4 py-2 type-callout'>
                                {n}
                            </a>
                        ))}
                    </nav>
                </div>
                <Foundations />
                <Controls />
                <Section title='Intro' note='The landing page. Hold the name for 1s to load cached results.'>
                    <Phone className='h-[640px]'>
                        <IntroScreen onSecretHold={() => alert('Cached results would load here.')} />
                    </Phone>
                </Section>
                <ScanDemo />
                <ResultsDemo />
                <TagDemo />
                <ReceiptDemo />
                <States />
            </main>
        </div>
    );
}

function Foundations() {
    return (
        <>
            <Section title='Colors' note='Light by default. Camera colors are identical in both themes.'>
                <div className='grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-10'>
                    {COLORS.map((c) => (
                        <div key={c} className='flex flex-col gap-1.5'>
                            <div className='aspect-square rounded-image ring-1 ring-border ring-inset' style={{ background: `var(--${c})` }} />
                            <span className='type-data text-[11px] text-muted-foreground'>{c}</span>
                        </div>
                    ))}
                </div>
            </Section>
            <Section title='Type' note='Fraunces for big moments, Figtree for UI, DM Mono for data.'>
                <div className='flex flex-col divide-y divide-border rounded-card bg-card px-5 shadow-card'>
                    {TYPE.map(([cls, sample]) => (
                        <div key={cls} className='flex flex-col gap-1 py-4 md:flex-row md:items-baseline md:gap-6'>
                            <span className='w-32 shrink-0 type-data text-muted-foreground'>{cls}</span>
                            <span className={cls}>{sample}</span>
                        </div>
                    ))}
                </div>
            </Section>
        </>
    );
}

function Controls() {
    const [on, setOn] = useState<Set<string>>(new Set(['natural_fibers']));
    const toggle = (id: string) => setOn((s) => new Set(s.has(id) ? [...s].filter((x) => x !== id) : [...s, id]));
    return (
        <Section title='Controls' note='Buttons, chips, reasons, badges and the est. tag.'>
            <div className='grid gap-6 md:grid-cols-2'>
                <div className='flex flex-col gap-4 rounded-card bg-card p-5 shadow-card'>
                    <div className='flex flex-wrap items-center gap-2'>
                        <Button>Scan an outfit</Button>
                        <Button variant='secondary'>Retake</Button>
                        <Button variant='outline'>Type it in</Button>
                        <Button variant='ghost'>Cancel</Button>
                    </div>
                    <div className='flex flex-wrap items-center gap-2'>
                        <Button size='lg'>Want this look with better materials?</Button>
                        <Button size='sm' variant='secondary'>Scan tag</Button>
                        <Button variant='link' size='sm'>Upload a photo</Button>
                    </div>
                    <div className='flex flex-wrap items-center gap-2 rounded-image bg-camera p-3'>
                        <Button variant='camera' size='sm'>Type it in</Button>
                        <Button variant='camera' size='icon' aria-label='Upload'>
                            <ScanSearch strokeWidth={1.75} />
                        </Button>
                    </div>
                </div>
                <div className='flex flex-col gap-4 rounded-card bg-card p-5 shadow-card'>
                    <div className='flex flex-wrap gap-2'>
                        {S.values.map((v) => (
                            <ValueChip key={v.id} label={v.label} selected={on.has(v.id)} fromVoice={v.id === 'low_carbon' && on.has(v.id)} onToggle={() => toggle(v.id)} />
                        ))}
                    </div>
                    <div className='flex flex-wrap gap-1.5'>
                        <ReasonChip label='Same cut' ok />
                        <ReasonChip label='Same color' ok />
                        <ReasonChip label='Different graphic' ok={false} />
                    </div>
                    <div className='flex flex-col gap-2'>
                        <StatusBadge value='Organic cotton' status='verified' />
                        <StatusBadge value='Small seller' status='claimed' />
                        <StatusBadge value='Low toxins' status='unknown' />
                    </div>
                    <p className='flex items-center gap-2 type-body'>
                        4.1 kg CO₂ saved <EstTag />
                    </p>
                </div>
            </div>
        </Section>
    );
}

function ScanDemo() {
    const [phase, setPhase] = useState<ScanPhase | 'camera'>('camera');
    const [elapsed, setElapsed] = useState<number>();
    const [selected, setSelected] = useState('g1');
    const [run, setRun] = useState(0);
    const shoot = () => {
        setPhase('scanning');
        setTimeout(() => setPhase('tracing'), 1900);
    };
    const reset = () => {
        setPhase('camera');
        setElapsed(undefined);
        setRun((r) => r + 1);
    };
    return (
        <Section title='Scan' note='Tap the shutter. Scan line, outlines, labels, then the live counter. Tap a label to pick a garment.' onReplay={reset}>
            <div className='grid items-start gap-6 md:grid-cols-2'>
                <Phone dark className='aspect-[9/19]'>
                    {/* 3:4 photo between dark bands, like a phone camera. */}
                    <div className='absolute inset-x-0 top-14'>
                        {phase === 'camera' ? (
                            <div className='aspect-[3/4]'>
                                <SampleOutfit />
                            </div>
                        ) : (
                            <ScanTrace
                            key={run}
                            garments={S.garments}
                            phase={phase}
                            selectedId={selected}
                            onSelect={setSelected}
                            onTapEmpty={() => {}}
                            onTraced={() => {
                                setPhase('done');
                                setTimeout(() => setElapsed(1240), 1300);
                            }}
                            >
                                <SampleOutfit />
                            </ScanTrace>
                        )}
                    </div>
                    {phase === 'camera' && <CameraBar flash={false} onShutter={shoot} />}
                    <AnimatePresence>
                        {phase === 'done' && (
                            <motion.div className='absolute inset-x-3 bottom-4' initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }} transition={spring.sheet}>
                                <SearchCounter total={S.INDEX_SIZE} marketplaces={S.marketplaces} elapsedMs={elapsed} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Phone>
                <div className='flex flex-col gap-4'>
                    <p className='type-callout text-muted-foreground'>Garment tabs on results</p>
                    <GarmentTabs garments={S.garments} selectedId={selected} onSelect={setSelected} />
                    <p className='type-callout text-muted-foreground'>Tag camera</p>
                    <Phone dark className='aspect-[9/19]'>
                        <div className='absolute inset-x-0 top-14 aspect-[3/4] overflow-hidden'>
                            <SampleTag />
                            <TagFrame />
                        </div>
                        <CameraBar mode='tag' flash />
                    </Phone>
                </div>
            </div>
        </Section>
    );
}

function ResultsDemo() {
    const [liked, setLiked] = useState<Set<string>>(new Set());
    const [updated, setUpdated] = useState(false);
    const [tab, setTab] = useState('g1');
    const [mic, setMic] = useState<MicState>('idle');
    const [voice, setVoice] = useState<VoicePhase | null>(null);
    const [hint, setHint] = useState(false);
    const [chosen, setChosen] = useState<Set<string>>(new Set());

    const list = updated ? S.coatMatchesAfterUpdate : S.coatMatches;
    const before = S.coatMatches.map((m) => m.listing.id);
    const after = S.coatMatchesAfterUpdate.map((m) => m.listing.id);
    const moved = (id: string) => (updated && before.includes(id) ? Math.max(0, before.indexOf(id) - after.indexOf(id)) : 0);
    const like = (id: string) => setLiked((s) => new Set(s.has(id) ? [...s].filter((x) => x !== id) : [...s, id]));
    const mapped = S.utterance.mapped.map((m) => ({ ...m, label: S.values.find((v) => v.id === m.id)!.label }));

    const card = (m: (typeof list)[number], size: 'large' | 'compact') => (
        <motion.div key={m.listing.id} layout='position' transition={spring.ui} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.96 }}>
            <MatchCard match={m} size={size} liked={liked.has(m.listing.id)} onLike={() => like(m.listing.id)} moved={moved(m.listing.id)} isNew={updated && !before.includes(m.listing.id)} />
        </motion.div>
    );

    return (
        <Section
            title='Results'
            note='Like a few, press Update in the bar. Hold the mic to speak your values.'
            onReplay={() => {
                setUpdated(false);
                setLiked(new Set());
                setChosen(new Set());
                setVoice(null);
            }}
        >
            <Phone className='max-w-md'>
                <div className='flex flex-col gap-6 px-4 pt-4 pb-32'>
                    <GarmentTabs garments={S.garments} selectedId={tab} onSelect={setTab} />
                    <div className='-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none]'>
                        {S.values.map((v) => (
                            <ValueChip key={v.id} label={v.label} selected={chosen.has(v.id)} fromVoice={chosen.has(v.id)} onToggle={() => setChosen((s) => new Set(s.has(v.id) ? [...s].filter((x) => x !== v.id) : [...s, v.id]))} />
                        ))}
                    </div>
                    {updated && <LearnedLine text={S.learned} />}
                    <LayoutGroup>
                        <h3 className='type-title-2'>Exact match</h3>
                        <div className='flex flex-col gap-4'>
                            <AnimatePresence mode='popLayout'>{list.filter((m) => m.band === 'exact').map((m) => card(m, 'large'))}</AnimatePresence>
                        </div>
                        <h3 className='type-title-2'>Similar style</h3>
                        <div className='grid grid-cols-2 gap-x-3 gap-y-6'>
                            <AnimatePresence mode='popLayout'>{list.filter((m) => m.band === 'similar').map((m) => card(m, 'compact'))}</AnimatePresence>
                        </div>
                    </LayoutGroup>
                </div>
                <div className='sticky bottom-0 flex flex-col gap-2 px-3 pb-3'>
                    <AnimatePresence>
                        {voice && (
                            <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={spring.sheet} className='-mx-3'>
                                <VoiceSheet phase={voice} transcript={S.utterance.text} mapped={mapped} />
                            </motion.div>
                        )}
                        {hint && (
                            <motion.p initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className='self-center rounded-pill bg-foreground px-3 py-1.5 type-footnote text-background'>
                                Hold to talk
                            </motion.p>
                        )}
                    </AnimatePresence>
                    <BottomDock
                        likedCount={liked.size}
                        micState={mic}
                        onMicStart={() => {
                            setMic('listening');
                            setVoice('listening');
                        }}
                        onMicEnd={(held) => {
                            setMic('idle');
                            if (held < 250) {
                                setVoice(null);
                                setHint(true);
                                return void setTimeout(() => setHint(false), 1500);
                            }
                            setVoice('transcript');
                            setTimeout(() => setVoice('mapped'), 1400);
                            setTimeout(() => {
                                setVoice(null);
                                setChosen(new Set(S.utterance.mapped.map((m) => m.id)));
                            }, 3400);
                        }}
                        onUpdate={() => {
                            setUpdated(true);
                            setLiked(new Set());
                        }}
                    />
                </div>
            </Phone>
            <div className='grid gap-6 md:grid-cols-2'>
                <div className='flex flex-col gap-3'>
                    <p className='type-callout text-muted-foreground'>Loading: a gentle fade, never a spinner</p>
                    <div className='grid grid-cols-2 gap-3'>
                        <MatchCardSkeleton size='compact' />
                        <MatchCardSkeleton size='compact' />
                    </div>
                </div>
                <div className='flex flex-col gap-3'>
                    <p className='type-callout text-muted-foreground'>Voice sheet, transcript step</p>
                    <VoiceSheet phase='transcript' transcript={S.utterance.text} mapped={mapped} className='rounded-b-card' />
                </div>
            </div>
        </Section>
    );
}

function TagDemo() {
    const [run, setRun] = useState(0);
    const { fibers, footprint_est } = S.tagReading;
    return (
        <Section title='Tag' note='The tag result sheet. Bars fill piece by piece, numbers count up.' onReplay={() => setRun((r) => r + 1)}>
            <div key={run} className='mx-auto flex w-full max-w-md flex-col gap-6 rounded-sheet bg-card p-6 shadow-float'>
                <div className='flex items-center gap-3'>
                    <div className='size-12 overflow-hidden rounded-lg'>
                        <SampleTag />
                    </div>
                    <div>
                        <p className='type-headline'>Your shirt</p>
                        <p className='type-footnote text-muted-foreground'>Made in {S.tagReading.country}</p>
                    </div>
                </div>
                <p className='flex items-baseline gap-2'>
                    <span className='type-numeral'>50%</span>
                    <span className='type-title-2'>polyester</span>
                </p>
                <FiberBar fibers={fibers} />
                <p className='type-body'>Polyester sheds microplastics every wash.</p>
                <div className='grid grid-cols-2 gap-4'>
                    <FootprintStat size='md' value={footprint_est.co2_kg} unit='kg' label='CO₂ to make it new' />
                    <FootprintStat size='md' value={footprint_est.water_l} unit='L' label='Water to make it new' />
                </div>
                <Button size='lg'>Want this look with better materials?</Button>
            </div>
        </Section>
    );
}

function ReceiptDemo() {
    const p = S.teePick;
    const pick = {
        title: p.listing.title,
        source: `${p.listing.marketplace} · small seller`,
        price: price(p.listing.price_cents),
        priceNote: `${price(p.listing.retail_price_cents!)} retail, ${price(p.receipt!.dollars_saved!)} saved`,
        materials: p.receipt!.materials,
        co2: p.receipt!.co2_saved_kg_est,
        water: p.receipt!.water_saved_l_est,
        badges: p.receipt!.badges,
    };
    const yours = { ...S.yourShirt, co2: S.yourShirt.co2_kg_est, water: S.yourShirt.water_l_est, badges: S.yourShirtBadges };
    return (
        <Section title='Receipt' note='Your garment vs this pick, then the QR hand-off. Sample values.'>
            <div className='grid items-start gap-8 md:grid-cols-2'>
                <ImpactReceipt yours={yours} pick={pick} stamp='OCT 25 · 10:42' className='mx-auto w-full max-w-md' />
                <QRPanel code='7KQ2' className='mx-auto w-full max-w-xs' />
            </div>
        </Section>
    );
}

function States() {
    return (
        <Section title='States' note='Every state offers a way forward.'>
            <div className='grid gap-4 md:grid-cols-2'>
                <div className='rounded-card bg-card shadow-card'>
                    <Notice icon={Shirt} title='No exact match' body='This one might be one of a kind. Similar styles are below.' />
                </div>
                <div className='rounded-card bg-card shadow-card'>
                    <Notice icon={SearchX} title='Nothing close yet' body='Try describing it instead.' actions={<Button variant='secondary'>Describe it instead</Button>} />
                </div>
                <div className='rounded-card bg-card shadow-card'>
                    <Notice icon={TagIcon} tone='error' title="Couldn't read this tag" body='Get closer and fill the frame, or type the fibers in.' actions={<><Button variant='secondary'>Retake</Button><Button variant='outline'>Type it in</Button></>} />
                </div>
                <div className='rounded-card bg-camera'>
                    <Notice icon={CameraOff} surface='camera' title="Camera's off" body='Upload a photo instead, or allow the camera in Settings.' actions={<Button variant='camera'>Upload a photo</Button>} />
                </div>
            </div>
        </Section>
    );
}

/** Stand-in tag photo for the tag camera. */
function SampleTag() {
    return (
        <svg viewBox='0 0 300 400' preserveAspectRatio='xMidYMid slice' className='size-full' aria-label='Sample care tag' role='img'>
            <rect width='300' height='400' fill='#3d4a63' />
            <rect x='92' y='96' width='116' height='170' rx='4' fill='#f4f2ec' />
            <g fill='#2a2a2a' fontFamily='monospace' fontSize='11' textAnchor='middle'>
                <text x='150' y='130'>50% COTTON</text>
                <text x='150' y='148'>50% POLYESTER</text>
                <text x='150' y='178'>MADE IN</text>
                <text x='150' y='194'>HONDURAS</text>
                <text x='150' y='228' fontSize='9'>MACHINE WASH COLD</text>
            </g>
        </svg>
    );
}
