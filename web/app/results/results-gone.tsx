'use client';

import { Camera } from 'lucide-react';
import Link from 'next/link';
import { Notice } from '@/components/sift/notice';
import { TopBar } from '@/components/sift/top-bar';
import { Button } from '@/components/ui/button';

export function ResultsGone() {
    return (
        <div className='flex min-h-dvh flex-col bg-background'>
            <TopBar />
            <main className='grid flex-1 place-items-center pb-16'>
                <Notice
                    icon={Camera}
                    title='Scan again to see results'
                    body="There's no saved scan in this browser yet."
                    actions={<Button render={<Link href='/scan' />} nativeButton={false}>Scan an outfit</Button>}
                />
            </main>
        </div>
    );
}
