import type { Metadata, Viewport } from 'next';
import { notFound, redirect } from 'next/navigation';
import { Suspense } from 'react';
import { Landing } from '@/components/landing/landing';
import { VARIANTS, type Variant } from '@/components/landing/variants';

export const metadata: Metadata = { title: 'Sift: buy it once' };

// Safari's bars match the cobalt stage.
export const viewport: Viewport = { themeColor: '#2b4bf2' };

export function generateStaticParams() {
    return VARIANTS.filter((v) => v !== 'dial').map((variant) => ({ variant }));
}

async function Design({ params }: { params: Promise<{ variant: string }> }) {
    const { variant } = await params;
    if (variant === 'dial') redirect('/'); // the dial is the home page
    if (!VARIANTS.includes(variant as Variant)) notFound();
    return <Landing variant={variant as Variant} />;
}

export default function LandingPage({ params }: PageProps<'/landing/[variant]'>) {
    return (
        <Suspense fallback={<div className='min-h-dvh bg-background' />}>
            <Design params={params} />
        </Suspense>
    );
}
