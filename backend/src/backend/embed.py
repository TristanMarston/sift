"""Image embeddings shared by the ingest pipeline and /search. Same function on both sides."""

from functools import cache

import numpy as np
import open_clip
import torch
from PIL import Image

MODEL_ID = "hf-hub:Marqo/marqo-fashionSigLIP"
DIM = 768


@cache
def _model():
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_ID)
    return model.eval().to(device), preprocess, device


def embed_images(images: list[Image.Image], batch_size: int = 64) -> np.ndarray:
    """(n, 768) float32, L2-normalized."""
    model, preprocess, device = _model()
    out = [np.empty((0, DIM), np.float32)]
    with torch.inference_mode():
        for i in range(0, len(images), batch_size):
            x = torch.stack([preprocess(im.convert("RGB")) for im in images[i : i + batch_size]]).to(device)
            out.append(model.encode_image(x, normalize=True).float().cpu().numpy())
    return np.concatenate(out)


def embed_image(image: Image.Image) -> np.ndarray:
    """(768,) float32, L2-normalized."""
    return embed_images([image])[0]
