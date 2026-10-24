"""Build src/backend/category_text.npy: one FashionSigLIP text vector per category, so /detect can name a garment
by comparing its image vector to these 8 rows. No text model runs in the app.

  uv run --with tokenizers python ml/make_category_text.py

Each row is the normalized mean of several phrasings. Tokenizing follows open_clip for this model: canonicalize
(lowercase, no punctuation), T5 sentencepiece, </s> at the end, padded with </s> to 64 tokens."""
import re
import string

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

from backend.detect import CATEGORIES, CATEGORY_TEXT

REPO, LENGTH = "Marqo/marqo-fashionSigLIP", 64
NAMES = {
    "jackets_outerwear": ["jacket", "coat", "puffer jacket", "denim jacket", "leather jacket", "work jacket", "parka"],
    "hoodies_sweatshirts": ["hoodie", "sweatshirt", "crewneck sweatshirt", "zip up hoodie"],
    "tshirts": ["t shirt", "graphic tee", "short sleeve t shirt", "band tee"],
    "sneakers": ["sneakers", "trainers", "running shoes", "high top sneakers", "skate shoes"],
    "jeans_pants": ["jeans", "pants", "trousers", "cargo pants", "chinos"],
    "sweaters_knitwear": ["sweater", "knit sweater", "cardigan", "wool jumper", "fleece sweater"],
    "shirts": ["button up shirt", "flannel shirt", "dress shirt", "oxford shirt", "blouse"],
    "dresses_skirts": ["dress", "skirt", "midi dress", "mini skirt", "maxi dress"],
}
TEMPLATES = ["a photo of a {}", "a {}", "a secondhand {} for sale", "a product photo of a {}"]


def canonicalize(text: str) -> str:
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()


def main():
    tok = Tokenizer.from_file(hf_hub_download(REPO, "tokenizer.json"))
    pad = tok.token_to_id("</s>")
    sess = ort.InferenceSession(hf_hub_download(REPO, "onnx/text_model.onnx"), providers=["CPUExecutionProvider"])
    rows = []
    for cat in CATEGORIES:
        texts = [canonicalize(t.format(n)) for n in NAMES[cat] for t in TEMPLATES]
        ids = np.full((len(texts), LENGTH), pad, np.int64)
        for i, t in enumerate(texts):
            enc = tok.encode(t).ids
            enc = enc if enc[-1] == pad else enc + [pad]  # the tokenizer may already append </s>
            ids[i, :min(LENGTH, len(enc))] = enc[:LENGTH]
        out = sess.run(None, {sess.get_inputs()[0].name: ids})[0]
        v = (out / np.linalg.norm(out, axis=1, keepdims=True)).mean(0)
        rows.append(v / np.linalg.norm(v))
    np.save(CATEGORY_TEXT, np.stack(rows).astype(np.float32))
    print(f"wrote {CATEGORY_TEXT} {np.stack(rows).shape}")


if __name__ == "__main__":
    main()
