'use client';

import { Keyboard } from 'lucide-react';
import { LayoutGroup, motion } from 'motion/react';
import { useId } from 'react';
import { Button } from '@/components/ui/button';
import { ease, spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { ValueChip } from './value-chip';

export type VoicePhase = 'listening' | 'transcript' | 'mapped';

type Props = {
    phase: VoicePhase;
    transcript?: string;
    mapped?: { id: string; phrase: string; label: string }[]; // words the parser turned into chips
    onTypeInstead?: () => void;
    className?: string;
};

// Bar heights for the waveform (fractions), varied so it reads as speech.
const BARS = [0.35, 0.6, 0.9, 0.5, 0.75, 1, 0.55, 0.8, 0.4, 0.95, 0.65, 0.45, 0.85, 0.6, 0.3, 0.7, 0.9, 0.5, 0.65, 0.4];

/** Soft, centered waveform while the mic is held. */
export function Waveform({ className }: { className?: string }) {
    return (
        <div className={cn('flex h-12 items-center justify-center gap-1', className)} aria-hidden>
            {BARS.map((h, i) => (
                <motion.span
                    key={i}
                    className='w-1 rounded-pill bg-primary'
                    initial={{ height: '20%' }}
                    animate={{ height: ['20%', `${h * 100}%`, '30%'] }}
                    transition={{ duration: 0.9 + (i % 5) * 0.12, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut', delay: i * 0.03 }}
                />
            ))}
        </div>
    );
}

/**
 * Speech becomes values. listening: waveform. transcript: words appear one by one, matched phrases highlighted.
 * mapped: each highlight flies down and becomes a chip (shared layoutId).
 */
export function VoiceSheet({ phase, transcript = '', mapped = [], onTypeInstead, className }: Props) {
    const group = useId();
    const words = splitPhrases(transcript, mapped);
    return (
        <LayoutGroup id={group}>
            <div className={cn('flex flex-col gap-5 rounded-t-sheet bg-card px-5 pt-3 pb-6 shadow-float', className)}>
                <span className='mx-auto h-1 w-9 rounded-pill bg-muted-foreground/30' aria-hidden />
                {phase === 'listening' ? (
                    <div className='flex flex-col items-center gap-3 py-2' role='status'>
                        <Waveform />
                        <p className='type-callout text-muted-foreground'>Listening…</p>
                    </div>
                ) : (
                    <p className='min-h-[52px] type-quote' aria-live='polite'>
                        {words.map((w, i) => (
                            <motion.span key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3, ease: ease.out, delay: i * 0.06 }} className={cn('relative', w.id && 'whitespace-nowrap')}>
                                {w.id && phase === 'transcript' && <motion.span layoutId={`${group}-${w.id}`} className='absolute -inset-x-1 -inset-y-0.5 rounded-md bg-primary-tint' transition={spring.ui} />}
                                <span className={cn('relative', w.id && phase === 'mapped' && 'underline decoration-primary/40 decoration-2 underline-offset-4')}>{w.text}</span>{' '}
                            </motion.span>
                        ))}
                    </p>
                )}

                <div className='flex min-h-9 flex-wrap gap-2'>
                    {phase === 'mapped' &&
                        mapped.map((m, i) => (
                            <motion.div key={m.id} initial={{ opacity: 0.6 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.08 }}>
                                <ValueChip layoutId={`${group}-${m.id}`} label={m.label} selected fromVoice />
                            </motion.div>
                        ))}
                </div>

                <Button variant='ghost' size='sm' onClick={onTypeInstead} className='self-center text-muted-foreground'>
                    <Keyboard data-icon='inline-start' strokeWidth={1.75} />
                    Type instead
                </Button>
            </div>
        </LayoutGroup>
    );
}

// Split the transcript so each mapped phrase is one unit.
function splitPhrases(text: string, mapped: { id: string; phrase: string }[]) {
    const out: { text: string; id?: string }[] = [];
    let rest = text;
    while (rest) {
        const hits = mapped.map((m) => ({ m, at: rest.toLowerCase().indexOf(m.phrase.toLowerCase()) })).filter((h) => h.at >= 0);
        const next = hits.sort((a, b) => a.at - b.at)[0];
        if (!next) {
            out.push(...rest.split(' ').filter(Boolean).map((t) => ({ text: t })));
            break;
        }
        out.push(...rest.slice(0, next.at).split(' ').filter(Boolean).map((t) => ({ text: t })));
        const end = next.at + next.m.phrase.length;
        out.push({ text: rest.slice(next.at, end), id: next.m.id });
        rest = rest.slice(end).replace(/^[,.]/, (p) => ((out[out.length - 1].text += p), ''));
    }
    return out;
}
