"""multilingual-e5-small with ONNX Runtime on CPU: semantic search without PyTorch in the Space image.

Same model and pooling as sentence-transformers (mean over tokens, then L2 normalise). e5 expects a prefix:
"query: " for search text and "passage: " for indexed text; symmetric matching uses "query: " on both sides.
Checked against sentence-transformers in tests/test_embed.py (cosine of the two vectors above 0.999).
"""

from __future__ import annotations

from functools import cached_property

import numpy as np

E5_REPO = "intfloat/multilingual-e5-small"
E5_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
DIM = 384


class E5:
    def __init__(self, max_length: int = 64, threads: int | None = None):
        self.max_length = max_length
        self.threads = threads

    @cached_property
    def _session(self):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(E5_REPO, "onnx/model.onnx", revision=E5_REVISION)
        opts = ort.SessionOptions()
        if self.threads:
            opts.intra_op_num_threads = self.threads
        return ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])

    @cached_property
    def _tokenizer(self):
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(hf_hub_download(E5_REPO, "onnx/tokenizer.json", revision=E5_REVISION))
        tok.enable_truncation(self.max_length)
        tok.enable_padding(pad_id=1, pad_token="<pad>")
        return tok

    def encode(self, texts: list[str], prefix: str = "query: ", batch_size: int = 64) -> np.ndarray:
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        names = {i.name for i in self._session.get_inputs()}
        for start in range(0, len(texts), batch_size):
            enc = self._tokenizer.encode_batch([prefix + t for t in texts[start : start + batch_size]])
            ids = np.array([e.ids for e in enc], dtype=np.int64)
            mask = np.array([e.attention_mask for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in names:
                feed["token_type_ids"] = np.zeros_like(ids)
            hidden = self._session.run(None, feed)[0]
            summed = (hidden * mask[..., None]).sum(axis=1)
            vec = summed / np.clip(mask.sum(axis=1, keepdims=True), 1, None)
            out[start : start + len(enc)] = vec / np.linalg.norm(vec, axis=1, keepdims=True)
        return out
