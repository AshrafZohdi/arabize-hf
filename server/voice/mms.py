"""Arabic speech with facebook/mms-tts-ara (VITS), ONNX export by Xenova, on ONNX Runtime. No PyTorch needed.

The tokenizer is ported from transformers' VitsTokenizer: lower case, keep only characters in the vocabulary
(Arabic letters and space; diacritics are not in it), then put the blank token (id 0) between every character
(`add_blank`). The model does not need uroman (`is_uroman` is false).
"""

from __future__ import annotations

import json
import re
from functools import cached_property

import numpy as np

REPO = "Xenova/mms-tts-ara"
REVISION = "e9dd80f91dcc6fb96b590806bb15421ec6d381c4"
LICENCE = "CC BY-NC 4.0 (facebook/mms-tts-ara)"


def prepare(text: str) -> str:
    """Arabic part only: drop brackets with English, Latin letters, digits and punctuation the model cannot say."""
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[A-Za-z0-9]+", " ", text)
    return " ".join(text.split())


class MmsArabic:
    lang = "ar"
    name = "mms-tts-ara (onnx)"

    def __init__(self, model_file: str = "onnx/model.onnx", threads: int = 4):
        self.model_file, self.threads = model_file, threads

    @cached_property
    def _vocab(self) -> dict[str, int]:
        from huggingface_hub import hf_hub_download

        return json.loads(open(hf_hub_download(REPO, "vocab.json", revision=REVISION), encoding="utf-8").read())

    @cached_property
    def rate(self) -> int:
        from huggingface_hub import hf_hub_download

        return int(json.loads(open(hf_hub_download(REPO, "config.json", revision=REVISION)).read())["sampling_rate"])

    @cached_property
    def _session(self):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.threads
        return ort.InferenceSession(hf_hub_download(REPO, self.model_file, revision=REVISION), opts, providers=["CPUExecutionProvider"])

    def token_ids(self, text: str) -> list[int]:
        chars = [c for c in prepare(text).lower() if c in self._vocab]
        ids = [self._vocab[c] for c in chars]
        out = [0] * (len(ids) * 2 + 1)
        out[1::2] = ids
        return out

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        ids = self.token_ids(text)
        if len(ids) <= 1:
            raise ValueError("no Arabic letters to say")
        x = np.array([ids], dtype=np.int64)
        wave = self._session.run(["waveform"], {"input_ids": x, "attention_mask": np.ones_like(x)})[0][0]
        return wave.astype(np.float32), self.rate
