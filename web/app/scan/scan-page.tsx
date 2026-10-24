'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ScanFlow } from '@/components/scan/scan-flow';
import type { SavedScan } from '@/lib/resume';
import { isReload, loadScan } from '@/lib/saved-scan';

/** A refresh here comes back to the saved photo; a fresh visit or a shared link opens the camera. */
export function ScanPage() {
    const router = useRouter();
    const [saved, setSaved] = useState<SavedScan | null | undefined>(); // undefined: still checking
    useEffect(() => void (isReload() ? loadScan() : Promise.resolve(null)).then(setSaved), []);
    return (
        <div className='fixed inset-0 bg-camera'>
            {saved !== undefined && <ScanFlow onClose={() => router.push('/')} resume={saved ? { saved, at: 'photo' } : undefined} />}
        </div>
    );
}
