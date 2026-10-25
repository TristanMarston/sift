import type { Metadata } from 'next';
import { MarkersCompare } from './markers-compare';

export const metadata: Metadata = { title: 'Sift: marker looks', robots: { index: false } };

/** The quality and eco markers in every look, on the same listings, to pick one for the demo. */
export default function MarkersPage() {
    return <MarkersCompare />;
}
