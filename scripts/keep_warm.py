"""Keep the Fanar endpoint awake during judging: a 1-token request every 5 minutes (the endpoint sleeps after 15
idle minutes). Stop it with Ctrl+C when the pitch ends; the endpoint then scales to zero by itself.

    .venv/bin/python scripts/keep_warm.py
"""

import time
from datetime import datetime

from huggingface_hub import InferenceClient

URL = "https://6aecccd0fef6e9d4f612646c.endpoints.huggingface.cloud"
client = InferenceClient(base_url=URL, timeout=300)  # uses the token from `hf auth login`

while True:
    started = time.time()
    try:
        client.chat_completion(messages=[{"role": "user", "content": "مرحبا"}], max_tokens=1, extra_body={"chat_template_kwargs": {"no_thinking": True}})
        print(datetime.now().strftime("%H:%M:%S"), f"awake ({time.time() - started:.1f} s)", flush=True)
    except Exception as e:
        print(datetime.now().strftime("%H:%M:%S"), "waking or failing:", type(e).__name__, flush=True)
    time.sleep(300)
