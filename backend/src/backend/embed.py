"""Image embeddings shared by the ingest pipeline and /search. Same function on both sides.

Marqo-FashionSigLIP's vision tower as ONNX (372 MB, fp32): the same model as the open_clip weights without the
text tower or torch. Preprocessing follows the model's config: pad to square (ours, so tall crops are not
squashed), resize to 224 bicubic, scale to [-1, 1]."""
from functools import cache

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from PIL import Image

REPO, FILE = "Marqo/marqo-fashionSigLIP", "onnx/vision_model.onnx"
MODEL_ID = f"{REPO}:{FILE}"
DIM, SIZE = 768, 224


@cache
def _session():
    return ort.InferenceSession(hf_hub_download(REPO, FILE), providers=["CPUExecutionProvider"])


def _square(im: Image.Image) -> Image.Image:
    im = im.convert("RGB")
    side = max(im.size)
    if im.width == im.height:
        return im
    canvas = Image.new("RGB", (side, side), "white")
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return canvas


def _pixels(images) -> np.ndarray:
    x = np.stack([np.asarray(_square(im).resize((SIZE, SIZE), Image.BICUBIC), np.float32) for im in images])
    return ((x / 255 - 0.5) / 0.5).transpose(0, 3, 1, 2)


def _run(x: np.ndarray) -> np.ndarray:
    s = _session()
    names = [o.name for o in s.get_outputs()]
    out = "image_embeds" if "image_embeds" in names else names[0]
    return s.run([out], {s.get_inputs()[0].name: x})[0]


def embed_images(images: list[Image.Image], batch_size: int = 64) -> np.ndarray:
    """(n, 768) float32, L2-normalized."""
    out = [np.empty((0, DIM), np.float32)]
    for i in range(0, len(images), batch_size):
        v = _run(_pixels(images[i:i + batch_size])).astype(np.float32)
        out.append(v / np.linalg.norm(v, axis=1, keepdims=True))
    return np.concatenate(out)


def embed_image(image: Image.Image) -> np.ndarray:
    """(768,) float32, L2-normalized."""
    return embed_images([image])[0]
