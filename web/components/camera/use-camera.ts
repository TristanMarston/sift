'use client';

import { useEffect, useRef, useState, useSyncExternalStore } from 'react';

export type CameraStatus = 'starting' | 'live' | 'denied' | 'unsupported' | 'error';
type Facing = 'environment' | 'user';

const noop = () => () => {};
// Browsers only offer the camera on HTTPS or localhost; elsewhere mediaDevices is missing.
const useSupported = () => useSyncExternalStore(noop, () => Boolean(navigator.mediaDevices?.getUserMedia), () => true);

/**
 * The live camera for the viewfinder. Asks for permission only while `active` (the camera screen is open).
 * Phones start on the back camera, laptops on their webcam.
 */
export function useCamera(active: boolean) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const trackRef = useRef<MediaStreamTrack | null>(null);
    const supported = useSupported();
    const [facing, setFacing] = useState<Facing>('environment');
    const [attempt, setAttempt] = useState(0); // bumping it restarts the camera
    const [state, setState] = useState<{ status: CameraStatus; mirrored: boolean; canFlip: boolean; torch?: boolean }>({ status: 'starting', mirrored: false, canFlip: false });

    useEffect(() => {
        if (!active || !supported) return;
        let stream: MediaStream | undefined;
        let cancelled = false;
        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1920 } }, audio: false })
            .then(async (s) => {
                stream = s;
                if (cancelled) return s.getTracks().forEach((t) => t.stop());
                const video = videoRef.current;
                if (video) {
                    video.srcObject = s;
                    await video.play().catch(() => {});
                }
                const track = s.getVideoTracks()[0];
                trackRef.current = track;
                const cameras = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput').length;
                const settings = track.getSettings();
                const caps = (track.getCapabilities?.() ?? {}) as MediaTrackCapabilities & { torch?: boolean };
                if (cancelled) return;
                setState({
                    status: 'live',
                    // Mirror selfie cameras only. A laptop webcam often reports no facing mode, so a single camera counts as one.
                    mirrored: settings.facingMode ? settings.facingMode === 'user' : facing === 'user' || cameras < 2,
                    canFlip: cameras > 1,
                    torch: caps.torch ? false : undefined, // undefined = no flash control (iPhone Safari)
                });
            })
            .catch((e: DOMException) => {
                if (!cancelled) setState((p) => ({ ...p, status: e.name === 'NotAllowedError' || e.name === 'SecurityError' ? 'denied' : 'error' }));
            });
        return () => {
            cancelled = true;
            stream?.getTracks().forEach((t) => t.stop());
            trackRef.current = null;
        };
    }, [active, supported, facing, attempt]);

    const flip = () => {
        setState((p) => ({ ...p, status: 'starting', torch: undefined }));
        setFacing((f) => (f === 'environment' ? 'user' : 'environment'));
    };

    const toggleTorch = async () => {
        const track = trackRef.current;
        if (!track || state.torch === undefined) return;
        const on = !state.torch;
        await track.applyConstraints({ advanced: [{ torch: on } as MediaTrackConstraintSet] }).catch(() => {});
        setState((p) => ({ ...p, torch: on }));
    };

    const retry = () => {
        setState((p) => ({ ...p, status: 'starting' }));
        setAttempt((n) => n + 1);
    };

    return { videoRef, ...state, status: supported ? state.status : ('unsupported' as CameraStatus), flip, toggleTorch, retry };
}
