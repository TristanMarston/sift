import { est } from '@/lib/format';
import type { BadgeStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { EstTag, StatusDot } from './status-badge';

export type ReceiptSide = {
    title: string;
    source: string;
    price?: string; // "Owned" when it's yours
    priceNote?: string; // "$34 retail, $16 saved"
    materials: string;
    co2: number;
    water: number;
    badges: { value: string; status: BadgeStatus; note?: string }[];
};

const LABEL: Record<BadgeStatus, string> = { verified: 'Verified', claimed: 'Claimed', inferred: 'Likely', unknown: 'Unknown' };

function Row({ label, a, b, estimate }: { label: string; a: React.ReactNode; b: React.ReactNode; estimate?: boolean }) {
    return (
        <div className='py-2'>
            <p className='flex items-center gap-1.5 type-label text-receipt-ink/70'>
                {label}
                {estimate && <EstTag className='text-receipt-ink/70' />}
            </p>
            <div className='mt-1 grid grid-cols-2 gap-x-4'>
                <div>{a}</div>
                <div>{b}</div>
            </div>
        </div>
    );
}

const Rule = () => <hr className='my-2 border-0 border-t border-dashed border-receipt-ink/30' />;
const Status = ({ s }: { s?: { status: BadgeStatus; note?: string } }) =>
    s ? (
        <span className='inline-flex items-center gap-1.5'>
            <StatusDot status={s.status} />
            {s.note ?? LABEL[s.status]}
        </span>
    ) : null;

/** Thermal-receipt comparison: your garment vs this pick, line by line. */
export function ImpactReceipt({ yours, pick, stamp, className }: { yours: ReceiptSide; pick: ReceiptSide; stamp?: string; className?: string }) {
    const values = [...new Set([...pick.badges, ...yours.badges].map((b) => b.value))];
    const find = (side: ReceiptSide, v: string) => side.badges.find((b) => b.value === v);
    return (
        <div className={cn('drop-shadow-[0_8px_20px_rgba(0,0,0,0.10)]', className)}>
            <div className='receipt-edge-bottom bg-receipt-paper px-5 pt-5 pb-9 type-receipt text-receipt-ink'>
                <header className='flex justify-between type-label'>
                    <span>SIFT · IMPACT RECEIPT</span>
                    {stamp && <span className='tabular'>{stamp}</span>}
                </header>
                <Rule />
                <div className='grid grid-cols-2 gap-x-4 type-label'>
                    <span>YOUR GARMENT</span>
                    <span>THIS PICK</span>
                </div>
                <Row label='ITEM' a={<><p>{yours.title}</p><p className='text-receipt-ink/70'>{yours.source}</p></>} b={<><p>{pick.title}</p><p className='text-receipt-ink/70'>{pick.source}</p></>} />
                <Row label='PRICE' a={yours.price ?? 'Owned'} b={<><p className='tabular'>{pick.price}</p>{pick.priceNote && <p className='text-receipt-ink/70'>{pick.priceNote}</p>}</>} />
                <Row label='MATERIALS' a={yours.materials} b={pick.materials} />
                <Row label='CO₂' estimate a={<span className='tabular'>{est(yours.co2)} kg made</span>} b={<span className='tabular'>{est(pick.co2)} kg saved</span>} />
                <Row label='WATER' estimate a={<span className='tabular'>{est(yours.water)} L made</span>} b={<span className='tabular'>{est(pick.water)} L saved</span>} />
                <Rule />
                {values.map((v) => (
                    <Row key={v} label={v.toUpperCase()} a={<Status s={find(yours, v)} />} b={<Status s={find(pick, v)} />} />
                ))}
                <Rule />
                <p className='pt-1 text-receipt-ink/70'>Buying secondhand skips making a new one. Estimates use published lifecycle averages.</p>
            </div>
        </div>
    );
}
