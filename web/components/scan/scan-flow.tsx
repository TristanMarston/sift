'use client';

import { AnimatePresence } from 'motion/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { CameraScreen, type SearchState } from '@/components/camera/camera-screen';
import { cropShot, type Shot } from '@/components/camera/capture';
import { ResultsScreen } from '@/components/results/results-screen';
import { indexSize, search } from '@/lib/api';
import type { Box } from '@/lib/detect';
import { categoryLabel } from '@/lib/results';
import { finished, resumed, type GarmentSearch, type SavedScan, type View } from '@/lib/resume';
import { clearScan, saveScan } from '@/lib/saved-scan';
import type { Garment } from '@/lib/types';

export type { GarmentSearch };

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const COUNTER_AT_LEAST = 1600; // the count rolls up and the market names light before results take over
const RESULTS = '/results';
const SCAN = '/scan';
const FRESH: View = { selected: '', sort: 'cpw', mix: 10, openId: null }; // a new scan opens on closest match; drag left for value

type Props = {
    onClose: () => void;
    initialFile?: File | null;
    resume?: { saved: SavedScan; at: 'photo' | 'results' }; // a refresh: pick up the saved scan where it was
};

/**
 * One continuous screen from photo to results (design system: Screens and flow). The camera traces the garments,
 * every garment's search starts at once, the live counter runs, then the selected garment lifts out of the photo
 * and flies into the results header as the screen turns from dark to light. Back returns to the photo, which
 * offers a clear way back to the results. The latest scan is kept in this browser, so a refresh keeps it.
 */
export function ScanFlow({ onClose, initialFile, resume }: Props) {
    // Built once on the first render from the saved scan.
    const [restored] = useState(() => {
        if (!resume) return null;
        const { photo, aspect, garments, results } = resume.saved;
        return { shot: { blob: photo, url: URL.createObjectURL(photo), aspect } as Shot, garments, ...resumed(garments, results) };
    });
    const [stage, setStage] = useState<'camera' | 'results'>(resume?.at === 'results' ? 'results' : 'camera');
    const [scan, setScan] = useState<{ shot: Shot; garments: Garment[] } | null>(restored && { shot: restored.shot, garments: restored.garments });
    const [searches, setSearches] = useState<Record<string, GarmentSearch>>(restored?.searches ?? {});
    const [view, setView] = useState<View>(resume?.saved.view ?? FRESH);
    const [counter, setCounter] = useState<SearchState | null>(resume ? { total: 0, lifted: false, selectedId: resume.saved.view.selected } : null);
    const [seen, setSeen] = useState(!!resume); // results have shown once: the photo offers a way back to them
    const [drawing, setDrawing] = useState(false); // "Draw a box" on the photo
    const run = useRef(0); // ignores searches that finish after a Retake
    const canReturn = useRef(false); // read by the Forward handler below
    useEffect(() => void (canReturn.current = seen && !!scan), [seen, scan]);

    // Back (button or swipe) from /results returns to the frozen photo; Forward goes back to the results.
    useEffect(() => {
        const onPop = () => {
            if (window.location.pathname === RESULTS) return void (canReturn.current && setStage('results'));
            setStage('camera');
            setCounter((c) => c && { ...c, lifted: false });
        };
        window.addEventListener('popstate', onPop);
        return () => window.removeEventListener('popstate', onPop);
    }, []);

    const showResults = () => {
        setStage('results');
        setSeen(true);
        if (window.location.pathname !== RESULTS) window.history.pushState(null, '', RESULTS);
    };

    const searchOne = useCallback(async (id: number, shot: Shot, g: Garment) => {
        try {
            const resp = await search(await cropShot(shot, g.bbox), g.category, g.brand ?? null);
            if (id !== run.current) return;
            setSearches((s) => ({ ...s, [g.id]: { status: 'done', resp } }));
            // With no category, the backend reads one from the photo: "Searched jackets".
            setCounter((c) => (c && c.selectedId === g.id ? { ...c, label: categoryLabel(resp.query.category, 'lower') ?? c.label } : c));
        } catch {
            if (id === run.current) setSearches((s) => ({ ...s, [g.id]: { status: 'error' } }));
        }
    }, []);

    // After a refresh: search again whatever hadn't come back, and let Back from the results land on the photo.
    const resumedOnce = useRef(false);
    useEffect(() => {
        if (!restored || resumedOnce.current) return;
        resumedOnce.current = true;
        if (resume?.at === 'results') {
            window.history.replaceState(null, '', SCAN);
            window.history.pushState(null, '', RESULTS);
        }
        for (const g of restored.garments) if (restored.rerun.includes(g.id)) searchOne(run.current, restored.shot, g);
    }, [restored, resume, searchOne]);

    // Keep the latest scan in this browser. A short wait means dragging the slider doesn't write on every step.
    useEffect(() => {
        if (!scan) return;
        const t = setTimeout(() => saveScan({ photo: scan.shot.blob, aspect: scan.shot.aspect, garments: scan.garments, results: finished(searches), view }), 300);
        return () => clearTimeout(t);
    }, [scan, searches, view]);

    const start = async (shot: Shot, garments: Garment[]) => {
        const id = ++run.current;
        const first = garments[0].id;
        setScan({ shot, garments });
        setView({ ...FRESH, selected: first });
        setSearches(Object.fromEntries(garments.map((g) => [g.id, { status: 'loading' }])));
        const t0 = performance.now();
        const total = await indexSize();
        if (id !== run.current) return;
        setCounter({ total, lifted: false, selectedId: first, label: categoryLabel(garments[0].category, 'lower') });
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
        setView(FRESH);
        clearScan();
    };

    const retry = (gid: string) => {
        const g = scan?.garments.find((x) => x.id === gid);
        if (!scan || !g) return;
        setSearches((s) => ({ ...s, [gid]: { status: 'loading' } }));
        searchOne(run.current, scan.shot, g);
    };

    const select = (gid: string) => {
        setView((v) => ({ ...v, selected: gid, openId: null }));
        setCounter((c) => c && { ...c, selectedId: gid });
    };

    // "Wrong garment? Draw a box": back to the photo to mark the garment detection missed.
    const startDraw = () => {
        setDrawing(true);
        window.history.back(); // to /scan; popstate shows the photo
    };

    // The drawn box becomes its own garment and tab. No category: the backend reads it from the crop.
    const boxDrawn = (box: Box) => {
        if (!scan) return;
        setDrawing(false);
        const g: Garment = { id: `box-${scan.garments.length}`, category: '', label: 'Your box', attributes: {}, bbox: box };
        setScan({ shot: scan.shot, garments: [...scan.garments, g] });
        setSearches((s) => ({ ...s, [g.id]: { status: 'loading' } }));
        select(g.id);
        showResults();
        searchOne(run.current, scan.shot, g);
    };

    const current = searches[view.selected];
    const count = current?.status === 'done' ? current.resp.results.length : null;

    return (
        <div className='relative size-full'>
            <CameraScreen
                onClose={onClose}
                initialFile={initialFile}
                restored={restored && { shot: restored.shot, garments: restored.garments }}
                onTraced={start}
                onRetake={retake}
                search={counter}
                onShowResults={seen ? showResults : undefined}
                showResultsLabel={count === null ? 'See results' : `See ${count} look-${count === 1 ? 'alike' : 'alikes'}`}
                handedOff={stage === 'results'}
                drawing={drawing && stage === 'camera'}
                onBoxDrawn={boxDrawn}
                onCancelDraw={() => setDrawing(false)}
            />
            <AnimatePresence>
                {stage === 'results' && scan && (
                    <ResultsScreen
                        key='results'
                        shot={scan.shot}
                        garments={scan.garments}
                        searches={searches}
                        view={view}
                        onView={(patch) => setView((v) => ({ ...v, ...patch }))}
                        onSelect={select}
                        onBack={() => window.history.back()}
                        onRetry={retry}
                        onDrawBox={startDraw}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
