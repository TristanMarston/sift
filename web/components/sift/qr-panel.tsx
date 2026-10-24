import { cn } from '@/lib/utils';

// Placeholder pattern only. Swap in a real QR encoder in the app.
function QRPlaceholder({ seed, className }: { seed: string; className?: string }) {
    const N = 25;
    let s = [...seed].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
    const rand = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
    const finder = (x: number, y: number) => [[0, 0], [N - 7, 0], [0, N - 7]].some(([fx, fy]) => x >= fx && x < fx + 7 && y >= fy && y < fy + 7);
    let d = '';
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) if (!finder(x, y) && rand() > 0.52) d += `M${x} ${y}h1v1h-1z`;
    const eye = (x: number, y: number) => <path key={`${x}${y}`} d={`M${x} ${y}h7v7h-7zM${x + 1} ${y + 1}v5h5v-5zM${x + 2} ${y + 2}h3v3h-3z`} fillRule='evenodd' />;
    return (
        <svg viewBox={`-1 -1 ${N + 2} ${N + 2}`} className={className} role='img' aria-label='QR code'>
            <g fill='currentColor'>
                <path d={d} />
                {[eye(0, 0), eye(N - 7, 0), eye(0, N - 7)]}
            </g>
        </svg>
    );
}

/** Receipt-styled hand-off: the judge scans it and opens /r/[id] on their own phone. */
export function QRPanel({ code, className }: { code: string; className?: string }) {
    return (
        <div className={cn('drop-shadow-[0_8px_20px_rgba(0,0,0,0.10)]', className)}>
            <div className='receipt-edge flex flex-col items-center gap-1 bg-receipt-paper px-6 py-9 text-center text-receipt-ink'>
                <p className='type-label'>TAKE YOUR PICKS WITH YOU</p>
                <QRPlaceholder seed={code} className='my-4 size-40' />
                <p className='type-callout'>Scan to open your picks on your phone.</p>
                <p className='type-data text-receipt-ink/70'>/r/{code}</p>
            </div>
        </div>
    );
}
