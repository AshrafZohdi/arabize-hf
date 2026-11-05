# Skills inventory

Every skill available to the coding agent on this machine on 2026-11-05, with a note on the ones that matter for Darby. A skill is loaded before the work it covers.

## Hugging Face (installed globally with `hf skills add -g`; `hf-cli` comes from the `huggingface-skills` plugin)

| Skill | Use in Darby |
|---|---|
| `hf-cli:hf-cli` | `hf` CLI: repos, uploads, Spaces, Jobs, buckets, endpoints, collections. Steps 1, 2, 4, 7, 8 |
| `hf-mem` | Memory estimate for the Fanar 2 GGUF on 1x L4 before proposing the endpoint (step 2) |
| `huggingface-local-models` | GGUF quantization choice and llama.cpp serving for the Fanar endpoint (step 2) |
| `huggingface-spaces` | Docker Space front matter, build and run debugging, buckets (steps 1, 7, 9) |
| `huggingface-datasets` | Dataset Viewer API to inspect GIST and MS glossary columns before download (step 4, stage 0) |
| `huggingface-tool-builder` | Reusable scripts over the HF API (pipeline stage 0 manifest, collection creation) |
| `huggingface-gradio` | Gradio MCP server mounted in FastAPI (step 9) |
| `huggingface-community-evals` | lighteval / inspect-ai option for the quality Job (step 8) |
| `huggingface-papers` | Read the GIST paper (arXiv 2412.18367) for dataset card credits |
| `huggingface-trackio` | Optional: log bakeoff metrics (step 8) |
| `transformers-js` | Kokoro English TTS in the browser (step 7) |
| `trl-training`, `huggingface-llm-trainer` | Stretch only: LoRA fine-tune of Fanar in a Job |
| `huggingface-best` | Cross-check model choices (embeddings, TTS) against benchmarks |

Also listed on the HF marketplace, not installed (not relevant): `hf-cloud-*` (AWS SageMaker), `huggingface-lora-space-builder`, `huggingface-paper-publisher`, `huggingface-vision-trainer`, `huggingface-zerogpu`, `train-sentence-transformers`.

MCP: `hf-mcp-server` is connected (user `mashrafzohdi`): Hub search, repo details, `hf_fs`.

## Build, test and ship (relevant)

| Skill | Use in Darby |
|---|---|
| `engineering-skills:senior-frontend` | React 19 + Vite + Tailwind 4 components (steps 1, 3, 6) |
| `engineering-skills:senior-fullstack` | FastAPI serving the built Vite app, API shape |
| `engineering-skills:senior-backend` | FastAPI routes, rate limit, SSE streaming (steps 2, 5) |
| `engineering-skills:senior-ml-engineer` | LLM client, eval, Jobs (steps 2, 4, 8) |
| `engineering-skills:senior-data-engineer` | Term bank pipeline stages 0 to 3 (step 4) |
| `engineering-skills:senior-data-scientist` | EDA notebook and report (step 4, stage 1) |
| `dataviz` | EDA charts and the eval results table |
| `engineering-skills:senior-prompt-engineer`, `marketing-skills:prompt-engineer-toolkit` | Explain, tutor, prompt lab and translation prompts |
| `engineering-skills:ai-security` | Prompt injection: learner text as data, escaping |
| `engineering-skills:senior-devops` | Dockerfile (multi-stage, port 7860) |
| `engineering-skills:senior-qa`, `engineering-skills:tdd-guide` | pytest and vitest structure, data quality gates |
| `engineering-advanced-skills:browser-automation` | Playwright smoke test of the demo path (step 10) |
| `engineering-advanced-skills:full-page-screenshot` | Screenshots into `docs/screenshots/` |
| `engineering-advanced-skills:api-test-suite-builder` | API tests for `/api/*` |
| `engineering-advanced-skills:ship-gate` | Gate before each Space deploy |
| `engineering-advanced-skills:dependency-auditor` | Pinned versions, licence check |
| `engineering-advanced-skills:runbook-generator` | Judging-day runbook (wake endpoint, keep warm, fallback) |
| `design:accessibility-review` | 4.5:1 contrast, 44 px targets, keyboard, RTL (step 10) |
| `design:ux-copy` | Arabic and English UI strings |
| `design:design-system`, `product-skills:ui-design-system` | Tokens into `tokens.css` and Tailwind theme |
| `design:design-critique` | Compare built screens against the `.reference.html` files |
| `web-perf` | Bundle size and load time of the Space |
| `claude-in-chrome`, `run` | Drive the app in a browser at 360 and 1280 px |
| `security-review` | Pass before judging |
| `qa`, `review`, `commit` | Local QA pass, pre-push review, commit messages |
| `simplify`, `code-review` | Cleanup and review of the diff |
| `handover` | Hand-off notes for the team |

## Pitch and README (relevant)

| Skill | Use in Darby |
|---|---|
| `engineering-advanced-skills:codebase-onboarding` | README architecture section |
| `anthropic-skills:pptx`, `c-level-skills:board-deck-builder` | Pitch deck if the team wants one built |
| `marketing-skills:copywriting`, `marketing-skills:copy-editing` | README and dataset card wording |
| `marketing-skills:launch-strategy` | 3 minute demo script |
| `artifact-diagramming` | Architecture diagram (README uses Mermaid) |

## Everything else available (not relevant to Darby)

- Cloudflare: `agents-sdk`, `cloudflare`, `cloudflare-email-service`, `cloudflare-one`, `cloudflare-one-migrations`, `durable-objects`, `nextjs-on-cloudflare`, `sandbox-migrate-to-next`, `sandbox-next`, `sandbox-sdk`, `sandbox-stable`, `turnstile-spin`, `workers-best-practices`, `wrangler`.
- Vercel: `vercel:*` (bootstrap, deploy, env, status, ai-gateway, ai-sdk, auth, build-agents, cdn-caching, chat-sdk, create-a-backend, custom-metrics, deployments-cicd, env-vars, eve, flags-sdk, knowledge-update, marketplace, microfrontends, next-cache-components, next-forge, next-upgrade, nextjs, queues, react-best-practices, routing-middleware, runtime-cache, shadcn, turbopack, vercel-agent, vercel-cli, vercel-connect, vercel-firewall, vercel-functions, vercel-sandbox, vercel-services, vercel-storage, verification, workflow). `vercel:react-best-practices` is worth a glance for React patterns.
- Engineering (other): `adversarial-reviewer`, `aws-solution-architect`, `azure-cloud-architect`, `cloud-security`, `code-reviewer`, `email-template-builder`, `engineering-skills`, `epic-design`, `gcp-cloud-architect`, `incident-commander`, `incident-response`, `ms365-tenant-manager`, `named-persona-adversarial-review`, `red-team`, `security-pen-testing`, `senior-architect`, `senior-computer-vision`, `senior-secops`, `senior-security`, `stripe-integration-expert`, `tech-stack-evaluator`, `threat-detection`.
- Engineering advanced (other): `agent-designer`, `agent-workflow-designer`, `api-design-reviewer`, `changelog-generator`, `chaos-engineering`, `ci-cd-pipeline-builder`, `database-designer`, `database-schema-designer`, `engineering-advanced-skills`, `env-secrets-manager`, `feature-flags-architect`, `focused-fix`, `git-worktree-manager`, `interview-system-designer`, `kubernetes-operator`, `mcp-server-builder`, `migration-architect`, `monorepo-navigator`, `observability-designer`, `performance-profiler`, `pr-review-expert`, `rag-architect`, `secrets-vault-manager`, `self-eval`, `skill-security-auditor`, `skill-tester`, `slo-architect`, `spec-driven-workflow`, `sql-database-assistant`, `tc-tracker`, `tech-debt-tracker`.
- Product: `cs-grill-product`, `cs-product-loop`, `cs-product`, `competitive-teardown`, `experiment-designer`, `landing-page-generator`, `product-analytics`, `product-discovery`, `product-manager-toolkit`, `product-skills`, `product-strategist`, `roadmap-communicator`, `saas-scaffolder`, `spec-to-repo`, `ux-researcher-designer`.
- Marketing (other): `ab-test-setup`, `ad-creative`, `aeo`, `analytics-tracking`, `app-store-optimization`, `brand-guidelines`, `campaign-analytics`, `churn-prevention`, `cold-email`, `competitor-alternatives`, `content-creator`, `content-humanizer`, `content-production`, `content-strategy`, `email-sequence`, `form-cro`, `free-tool-strategy`, `local-seo-manager`, `marketing-context`, `marketing-demand-acquisition`, `marketing-ideas`, `marketing-ops`, `marketing-psychology`, `marketing-skills`, `marketing-strategy-pmm`, `onboarding-cro`, `page-cro`, `paid-ads`, `paywall-upgrade-cro`, `popup-cro`, `pricing-strategy`, `programmatic-seo`, `referral-program`, `schema-markup`, `seo-audit`, `signup-flow-cro`, `site-architecture`, `social-content`, `social-media-analyzer`, `social-media-manager`, `webinar-marketing`, `x-twitter-growth`, `youtube-full`.
- Regulatory and quality: `agent-decision-receipts`, `capa-officer`, `eu-ai-act-specialist`, `fda-consultant-specialist`, `gdpr-dsgvo-expert`, `information-security-manager-iso27001`, `isms-audit-expert`, `iso42001-specialist`, `mdr-745-specialist`, `qms-audit-expert`, `quality-documentation-manager`, `quality-manager-qmr`, `quality-manager-qms-iso13485`, `ra-qm-skills`, `regulatory-affairs-head`, `risk-management-specialist`, `soc2-compliance`.
- Project management: `cs-grill-pm`, `cs-pm-loop`, `cs-pm`, `atlassian-admin`, `atlassian-templates`, `confluence-expert`, `jira-expert`, `meeting-analyzer`, `pm-skills`, `scrum-master`, `senior-pm`, `team-communications`.
- C-level: `agent-protocol`, `arquiteto-de-empresa`, `board-meeting`, `c-level-skills`, `ceo-advisor`, `cfo-advisor`, `change-management`, `chief-ai-officer-advisor`, `chief-customer-officer-advisor`, `chief-data-officer-advisor`, `chief-of-staff`, `chro-advisor`, `ciso-advisor`, `cmo-advisor`, `company-os`, `competitive-intel`, `context-engine`, `coo-advisor`, `cpo-advisor`, `cro-advisor`, `cs-onboard`, `cto-advisor`, `culture-architect`, `decision-logger`, `founder-coach`, `general-counsel-advisor`, `internal-narrative`, `intl-expansion`, `ma-playbook`, `org-health-diagnostic`, `scenario-war-room`, `strategic-alignment`, `vpe-advisor`.
- Business and finance: `business-growth-skills`, `contract-and-proposal-writer`, `customer-success-manager`, `revenue-operations`, `sales-engineer`, `finance-skills`, `financial-analyst`, `saas-metrics-coach`.
- Research: `deep-research` (and `cs-deep-research`), `pulse`, `litreview`, `grants`, `dossier`, `patent`, `syllabus`, `notebooklm`, `anthropic-skills:deep-research`.
- Design (other): `design:design-handoff`, `design:research-synthesis`, `design:user-research`, Figma skills (`figma-*`).
- Self-improvement and memory: `si:extract`, `si:memory-review`, `si:memory-status`, `si:promote`, `si:remember`, `si:self-improving-agent`.
- Anthropic and harness: `anthropic-skills:built-in-browser`, `chrome-browser`, `computer-use`, `docs`, `docx`, `google-workspace`, `import-memory`, `morning`, `pdf`, `skill-creator`, `xlsx`, `artifact-design`, `artifact-capabilities`, `update-config`, `keybindings-help`, `fewer-permission-prompts`, `loop`, `schedule`, `claude-api` (not used: no Claude API in the product), `workflow-authoring`, `init`.
