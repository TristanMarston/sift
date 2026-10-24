import type { Metadata } from 'next';
import { ResultsGone } from './results-gone';

export const metadata: Metadata = { title: 'Sift: results' };

/** Results live only while the page is open (photos never leave the visit), so a refresh here offers a new scan. */
export default function Results() {
    return <ResultsGone />;
}
