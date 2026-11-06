"""CPU Job: copy the Q8_0 GGUF and vision projector of Fanar-2-Oryx-IVU into nuvais/Fanar-2-Oryx-IVU-Q8_0-GGUF,
checking each file's sha256 against the source repo's LFS pointer before upload."""

import hashlib
import os

from huggingface_hub import HfApi, hf_hub_download

SRC, REV = "mradermacher/Fanar-2-Oryx-IVU-GGUF", "3dbf1c82aa4298aff7ddc41862e5315dcdd8d0b2"
DST = "nuvais/Fanar-2-Oryx-IVU-Q8_0-GGUF"
FILES = {
    "Fanar-2-Oryx-IVU.Q8_0.gguf": "7ab8ad3377b7ec3efd4567684ce9c290db9443f1cdd9fceffb81f8820a5fd62d",
    "Fanar-2-Oryx-IVU.mmproj-f16.gguf": "31c701d2b14e467c73c8694006e8d9166c2b896639aab58ca62853cb66153e71",
}

api = HfApi(token=os.environ["HF_TOKEN"])
for name, sha in FILES.items():
    path = hf_hub_download(SRC, name, revision=REV, local_dir="/tmp/ivu")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    assert h.hexdigest() == sha, f"{name}: sha256 mismatch"
    api.upload_file(path_or_fileobj=path, path_in_repo=name, repo_id=DST, commit_message=f"Add {name} from {SRC}@{REV[:8]}")
    print("uploaded", name, flush=True)
