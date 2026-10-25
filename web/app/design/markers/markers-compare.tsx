'use client';

import { Check } from 'lucide-react';
import { LayoutGroup } from 'motion/react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { EcoCard, QualityCard } from '@/components/results/receipt-sheet';
import { ResultRow } from '@/components/results/result-row';
import { ThemeToggle } from '@/components/sift/theme-toggle';
import { Button } from '@/components/ui/button';
import { hasBackend, search } from '@/lib/api';
import { setMarkerStyle, useMarkerStyle, type MarkerStyle } from '@/lib/marker-style';
import type { Result, SearchResponse } from '@/lib/search';

const LOOKS: { id: MarkerStyle; name: string; note: string }[] = [
    { id: 'dots', name: 'Dots', note: 'Today’s look: three small dots and the level word.' },
    { id: 'meter', name: 'Meters', note: 'Chunky three-part bars. The eco card gets a full-width meter and a rank bar.' },
    { id: 'chips', name: 'Chips', note: 'Pills that get heavier as the level rises: solid, tinted, outlined, dashed.' },
    { id: 'rings', name: 'Rings', note: 'Gauges filled in thirds. The eco card gets a large ring with the level inside.' },
];

// A Carhartt Detroit jacket listing photo, the demo prop, run through the live search like a scan.
const PROP = 'https://u-mercari-images.mercdn.net/photos/m86859246185_1.jpg?1790776021';

async function load(): Promise<SearchResponse> {
    if (hasBackend) {
        try {
            const photo = await (await fetch(`/_next/image?url=${encodeURIComponent(PROP)}&w=640&q=70`)).blob();
            return await search(photo, 'jackets_outerwear');
        } catch {}
    }
    return (await fetch('/samples/jackets_outerwear.json')).json();
}

/** Four listings that between them show high, medium, low and unknown levels. */
function pick(resp: SearchResponse): Result[] {
    const all = resp.orders.cpw.map((id) => resp.results.find((r) => r.id === id)!).filter(Boolean);
    const want = [(r: Result) => r.quality.level === 'high', (r: Result) => r.quality.level === 'unknown', (r: Result) => r.eco.level === 'low', (r: Result) => r.quality.level === 'medium'];
    const out: Result[] = [];
    for (const w of want) {
        const r = all.find((x) => w(x) && !out.includes(x));
        if (r) out.push(r);
    }
    for (const r of all) if (out.length < 4 && !out.includes(r)) out.push(r);
    return out;
}

export function MarkersCompare() {
    const [resp, setResp] = useState<SearchResponse | null>(null);
    const inUse = useMarkerStyle();
    useEffect(() => void load().then(setResp), []);
    const rows = resp ? pick(resp) : [];

    return (
        <div className='min-h-dvh bg-background text-foreground'>
            <header className='mx-auto flex max-w-[1500px] items-start justify-between gap-4 px-4 pt-8 lg:px-8'>
                <div className='max-w-2xl'>
                    <h1 className='type-title-1'>Quality and eco markers</h1>
                    <p className='mt-2 type-callout text-pretty text-muted-foreground'>
                        Four looks on the same listings{resp?.sample ? ' (bundled sample data)' : ' from the live search'}. Pick one and it shows in your real scans, in this browser only. Then{' '}
                        <Link href='/' className='text-foreground underline underline-offset-2'>
                            scan something
                        </Link>
                        .
                    </p>
                </div>
                <ThemeToggle />
            </header>

            <main className='mx-auto grid max-w-[1500px] grid-cols-1 gap-x-6 gap-y-10 px-4 py-8 md:grid-cols-2 lg:px-8 2xl:grid-cols-4'>
                {LOOKS.map((look) => (
                    <section key={look.id} className='flex min-w-0 flex-col gap-3'>
                        <div className='flex items-start justify-between gap-3'>
                            <div>
                                <h2 className='type-title-2'>{look.name}</h2>
                                <p className='type-footnote text-pretty text-muted-foreground'>{look.note}</p>
                            </div>
                            <Button size='sm' variant={inUse === look.id ? 'default' : 'secondary'} onClick={() => setMarkerStyle(look.id)} className='shrink-0'>
                                {inUse === look.id ? (
                                    <>
                                        <Check data-icon='inline-start' strokeWidth={2} /> In use
                                    </>
                                ) : (
                                    'Use this'
                                )}
                            </Button>
                        </div>
                        {resp ? (
                            <LayoutGroup id={look.id}>
                                <ol className='grid grid-cols-1 gap-3'>
                                    {rows.map((r, i) => (
                                        <ResultRow key={r.id} r={r} rank={i + 1} sort='cpw' cheapest={r.id === resp.headline.cheapest_id} open={false} onOpen={() => {}} markerStyle={look.id} />
                                    ))}
                                </ol>
                                <QualityCard r={rows[0]} style={look.id} />
                                <EcoCard eco={rows[0].eco} style={look.id} />
                            </LayoutGroup>
                        ) : (
                            <div className='h-96 animate-pulse rounded-card bg-card shadow-card' />
                        )}
                    </section>
                ))}
            </main>
        </div>
    );
}
