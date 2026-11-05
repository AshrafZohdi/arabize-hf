---
title: Darby
emoji: 🧭
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
short_description: Learn AI and its English terms in Arabic
license: apache-2.0
---

# Darby (دربي)

Darby ("my path") teaches Arabic-speaking professionals in Qatar how to use AI at work, and the English vocabulary that comes with it, in simple Arabic or Gulf dialect through short game mechanics. Its brain is Fanar 2, the Arabic model built in Qatar by QCRI, served on Hugging Face.

Built for the Qai x Hugging Face Hackathon 01, Doha, November 2026.

Status: work in progress. The full README (architecture, data pipeline, models and datasets with licences) comes with the final build.

## Run locally

```bash
# server (Python 3.11)
uv venv --python 3.11 .venv && uv pip install -r requirements-dev.txt
.venv/bin/uvicorn server.main:app --reload --port 7860

# web (Node 22)
cd web && npm install && npm run dev   # http://localhost:5173, proxies /api to 7860

# tests and build
.venv/bin/pytest
cd web && npm test && npm run build

# container, as the Space runs it
docker build -t darby . && docker run -p 7860:7860 darby
```

Configuration: see `.env.example`.
