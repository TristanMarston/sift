'use client';

import { useRouter } from 'next/navigation';
import { CameraScreen } from '@/components/camera/camera-screen';

export function ScanPage() {
    const router = useRouter();
    return (
        <div className='fixed inset-0 bg-camera'>
            <CameraScreen onClose={() => router.push('/')} />
        </div>
    );
}
