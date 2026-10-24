// Turning the live camera or an uploaded file into the photo we search. Browser-only.
import { coverCrop, fitLongEdge } from '@/lib/photo';
import { cropRect } from '@/lib/results';

export type Shot = { url: string; blob: Blob; aspect: number }; // aspect = width / height

const VIEWFINDER = 3 / 4;

function toShot(canvas: HTMLCanvasElement): Promise<Shot> {
    return new Promise((resolve, reject) =>
        canvas.toBlob((blob) => (blob ? resolve({ blob, url: URL.createObjectURL(blob), aspect: canvas.width / canvas.height }) : reject(new Error('Could not encode the photo'))), 'image/jpeg', 0.9),
    );
}

/** Exactly what the 3:4 viewfinder shows, at most 1024px on the long edge. Never mirrored, even when the preview is. */
export function captureFrame(video: HTMLVideoElement): Promise<Shot> {
    const { sx, sy, sw, sh } = coverCrop(video.videoWidth, video.videoHeight, VIEWFINDER);
    const { w, h } = fitLongEdge(sw, sh);
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d')!.drawImage(video, sx, sy, sw, sh, 0, 0, w, h);
    return toShot(canvas);
}

/** An uploaded photo keeps its own shape (cropping could cut off a garment), scaled to 1024px on the long edge. */
export async function photoFromFile(file: File): Promise<Shot> {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const { w, h } = fitLongEdge(bitmap.width, bitmap.height);
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    return toShot(canvas);
}

/** One garment cut from the photo with a little padding: what /search looks at. */
export async function cropShot(shot: Shot, box: { x: number; y: number; w: number; h: number }): Promise<Blob> {
    const bitmap = await createImageBitmap(shot.blob);
    const { sx, sy, sw, sh } = cropRect(box, bitmap.width, bitmap.height);
    const canvas = document.createElement('canvas');
    canvas.width = sw;
    canvas.height = sh;
    canvas.getContext('2d')!.drawImage(bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
    bitmap.close();
    return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Could not crop the photo'))), 'image/jpeg', 0.9));
}
