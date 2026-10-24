'use client';

import { AnimatePresence } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import { CameraScreen, type SearchState } from '@/components/camera/camera-screen';
import { cropShot, type Shot } from '@/components/camera/capture';
import { ResultsScreen } from '@/components/results/results-screen';
import { indexSize, search } from '@/lib/api';
import type { SearchResponse } from '@/lib/search';
import type { Garment } from '@/lib/types';

export type GarmentSearch = { status: 'loading' } | { status: 'done'; resp: SearchResponse } | { status: 'error' };

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const COUNTER_AT_LEAST = 1600; // the count rolls up and the market names light before results take over
const RESULTS = '/results';

type Props = { onClose: () => void; initialFile?: File | null };

/**
 * One continuous screen from photo to results (design system: Screens and flow). The camera traces the garments,
 * every garment's search starts at once, the live counter runs, then the selected garment lifts out of the photo
 * and flies into the results header as the screen turns from dark to light. Back returns to the photo.
 */
export function ScanFlow({ onClose, initialFile }: Props) {
    const [stage, setStage] = useState<'camera' | 'results'>('camera');
    const [scan, setScan] = useState<{ shot: Shot; garments: Garment[] } | null>(null);
    const [searches, setSearches] = useState<Record<string, GarmentSearch>>({});
    const [selected, setSelected] = useState('');
    const [counter, setCounter] = useState<SearchState | null>(null);
    const [seen, setSeen] = useState(false); // results have shown once: Back leaves the counter as a way back to them
    const run = useRef(0); // ignores searches that finish after a Retake

    // Back (button or swipe) from /results returns to the frozen photo.
    useEffect(() => {
        const onPop = () => {
            if (window.location.pathname === RESULTS) return;
            setStage('camera');
            setCounter((c) => c && { ...c, lifted: false }); // the finished counter now reopens the results
        };
        window.addEventListener('popstate', onPop);
        return () => window.removeEventListener('popstate', onPop);
    }, []);

    const showResults = () => {
        setStage('results');
        setSeen(true);
        if (window.location.pathname !== RESULTS) window.history.pushState(null, '', RESULTS);
    };

    const searchOne = async (id: number, shot: Shot, g: Garment) => {
        try {
            const resp = await search(await cropShot(shot, g.bbox), g.category);
            if (id === run.current) setSearches((s) => ({ ...s, [g.id]: { status: 'done', resp } }));
        } catch {
            if (id === run.current) setSearches((s) => ({ ...s, [g.id]: { status: 'error' } }));
        }
    };

    const start = async (shot: Shot, garments: Garment[]) => {
        const id = ++run.current;
        const first = garments[0].id;
        setScan({ shot, garments });
        setSelected(first);
        setSearches(Object.fromEntries(garments.map((g) => [g.id, { status: 'loading' }])));
        const t0 = performance.now();
        const total = await indexSize();
        if (id !== run.current) return;
        setCounter({ total, lifted: false, selectedId: first });
        const all = garments.map((g) => searchOne(id, shot, g));
        await all[0];
        const elapsedMs = performance.now() - t0;
        if (id !== run.current) return;
        setCounter((c) => c && { ...c, elapsedMs }); // the timer freezes at the real search time: "Searched · 1.2s"
        await wait(Math.max(500, COUNTER_AT_LEAST - elapsedMs)); // then the count finishes rolling
        if (id !== run.current) return;
        setCounter((c) => c && { ...c, lifted: true }); // the garment lifts out of the photo
        await wait(320);
        if (id === run.current) showResults();
    };

    const retake = () => {
        run.current++;
        setSeen(false);
        setScan(null);
        setSearches({});
        setCounter(null);
    };

    const retry = (gid: string) => {
        if (!scan) return;
        const g = scan.garments.find((x) => x.id === gid);
        if (!g) return;
        setSearches((s) => ({ ...s, [gid]: { status: 'loading' } }));
        searchOne(run.current, scan.shot, g);
    };

    const select = (gid: string) => {
        setSelected(gid);
        setCounter((c) => c && { ...c, selectedId: gid });
    };

    return (
        <div className='relative size-full'>
            <CameraScreen
                onClose={onClose}
                initialFile={initialFile}
                onTraced={start}
                onRetake={retake}
                search={counter}
                onShowResults={seen ? showResults : undefined}
                handedOff={stage === 'results'}
            />
            <AnimatePresence>
                {stage === 'results' && scan && (
                    <ResultsScreen key='results' shot={scan.shot} garments={scan.garments} searches={searches} selected={selected} onSelect={select} onBack={() => window.history.back()} onRetry={retry} />
                )}
            </AnimatePresence>
        </div>
    );
}
