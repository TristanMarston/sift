import type { Metadata, Viewport } from 'next';
import { notFound } from 'next/navigation';
import { Suspense } from 'react';
import { Landing } from '@/components/landing/landing';
import { VARIANTS, type Variant } from '@/components/landing/variants';

export const metadata: Metadata = { title: 'Sift: buy it once' };

// Safari's bars match the forest landing.
export const viewport: Viewport = { themeColor: '#103520' };

export function generateStaticParams() {
    return VARIANTS.map((variant) => ({ variant }));
}

async function Design({ params }: { params: Promise<{ variant: string }> }) {
    const { variant } = await params;
    if (!VARIANTS.includes(variant as Variant)) notFound();
    return <Landing variant={variant as Variant} compare />;
}

export default function LandingPage({ params }: PageProps<'/landing/[variant]'>) {
    return (
        <Suspense fallback={<div className='min-h-dvh bg-background' />}>
            <Design params={params} />
        </Suspense>
    );
}
