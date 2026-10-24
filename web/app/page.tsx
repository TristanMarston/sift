'use client';

import { useRouter } from 'next/navigation';
import { IntroScreen } from '@/components/sift/intro-screen';

// The scanner flow isn't built yet; actions open the design lab for now.
export default function Home() {
    const router = useRouter();
    const lab = () => router.push('/design#scan');
    return <IntroScreen className='mx-auto w-full max-w-md flex-1' onScan={lab} onUpload={lab} onDescribe={lab} onSecretHold={lab} />;
}
