'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ScanFlow } from '@/components/scan/scan-flow';
import type { SavedScan } from '@/lib/resume';
import { loadScan } from '@/lib/saved-scan';
import { ResultsGone } from './results-gone';

/** A refresh on the results brings back the latest scan saved in this browser, as it was being viewed. */
export function ResultsPage() {
    const router = useRouter();
    const [saved, setSaved] = useState<SavedScan | null | undefined>(); // undefined: still checking
    useEffect(() => void loadScan().then(setSaved), []);
    if (saved === undefined) return <div className='fixed inset-0 bg-background' />;
    if (!saved) return <ResultsGone />;
    return (
        <div className='fixed inset-0 bg-camera'>
            <ScanFlow onClose={() => router.push('/')} resume={{ saved, at: 'results' }} />
        </div>
    );
}
