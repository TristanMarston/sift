import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

type Props = {
    icon: LucideIcon;
    title: string;
    body?: string;
    tone?: 'neutral' | 'error';
    surface?: 'content' | 'camera'; // camera = on the dark scanner
    actions?: React.ReactNode; // every notice offers a way forward
    className?: string;
};

/** Empty, no-match and error states. Say what happened, then what to do. */
export function Notice({ icon: Icon, title, body, tone = 'neutral', surface = 'content', actions, className }: Props) {
    const cam = surface === 'camera';
    return (
        <div className={cn('flex flex-col items-center gap-3 px-6 py-10 text-center', cam && 'text-camera-foreground', className)} role={tone === 'error' ? 'alert' : undefined}>
            <div
                className={cn(
                    'grid size-14 place-items-center rounded-full',
                    cam ? 'bg-camera-control' : tone === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-secondary text-muted-foreground',
                )}
            >
                <Icon className='size-6' strokeWidth={1.75} />
            </div>
            <h3 className='type-title-2'>{title}</h3>
            {body && <p className={cn('max-w-xs type-body', cam ? 'text-camera-muted' : 'text-muted-foreground')}>{body}</p>}
            {actions && <div className='mt-2 flex flex-wrap justify-center gap-2'>{actions}</div>}
        </div>
    );
}
