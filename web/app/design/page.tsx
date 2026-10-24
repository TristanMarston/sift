import type { Metadata } from 'next';
import { Lab } from './lab';

export const metadata: Metadata = { title: 'Sift design lab' };

export default function DesignPage() {
    return <Lab />;
}
