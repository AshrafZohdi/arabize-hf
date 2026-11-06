"""Keep the endpoints awake during judging: a 1-token request to each every 5 minutes (they sleep after 15 idle
minutes). Fanar always; the Oryx photo reader too, unless --fanar-only. Stop it with Ctrl+C when the pitch ends; the
endpoints then scale to zero by themselves.

    .venv/bin/python scripts/keep_warm.py
"""

import sys
import time
from datetime import datetime

from huggingface_hub import InferenceClient

ENDPOINTS = {
    "fanar": "https://6aecccd0fef6e9d4f612646c.endpoints.huggingface.cloud",
    "oryx-ivu": "https://6aee154662710132ca851829.endpoints.huggingface.cloud",
}
if "--fanar-only" in sys.argv:
    ENDPOINTS.pop("oryx-ivu")
clients = {name: InferenceClient(base_url=url, timeout=300) for name, url in ENDPOINTS.items()}  # token from `hf auth login`

while True:
    for name, client in clients.items():
        started = time.time()
        try:
            client.chat_completion(messages=[{"role": "user", "content": "مرحبا"}], max_tokens=1, extra_body={"chat_template_kwargs": {"no_thinking": True}})
            print(datetime.now().strftime("%H:%M:%S"), name, f"awake ({time.time() - started:.1f} s)", flush=True)
        except Exception as e:
            print(datetime.now().strftime("%H:%M:%S"), name, "waking or failing:", type(e).__name__, flush=True)
    time.sleep(300)
