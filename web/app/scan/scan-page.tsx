'use client';

import { useRouter } from 'next/navigation';
import { ScanFlow } from '@/components/scan/scan-flow';

export function ScanPage() {
    const router = useRouter();
    return (
        <div className='fixed inset-0 bg-camera'>
            <ScanFlow onClose={() => router.push('/')} />
        </div>
    );
}
