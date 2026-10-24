import type { Metadata } from 'next';
import { ResultsPage } from './results-page';

export const metadata: Metadata = { title: 'Sift: results' };

/** A refresh here restores the latest scan saved in this browser; with none saved, it offers a new scan. */
export default function Results() {
    return <ResultsPage />;
}
