# Decisions

Newest last. Each entry: what, why, what was rejected.

## D1. 2026-11-05: No router library
The app has four routes (home, glossary, tutor, lesson). A 40 line pushState router in `web/src/lib/router.tsx` covers links and back/forward. Rejected: react-router (one more dependency for no extra feature we use). FastAPI serves `index.html` for every non-API, non-file path so deep links work.

## D2. 2026-11-05: Fonts from @fontsource packages
Readex Pro, IBM Plex Sans Arabic and IBM Plex Sans come from `@fontsource/*` npm packages. Vite copies the woff2 files into the build, so the Space loads no font from outside at run time (HF_PLAN rule). Only the Arabic and Latin subsets and the weights in `tokens.md` are imported.

## D3. 2026-11-05: i18n without a library
Flat JSON files `web/src/i18n/ar.json` and `en.json` with the same keys, plural forms through `Intl.PluralRules` (Arabic has zero, one, two, few, many, other). A vitest checks identical keys and plural shapes, and no em or en dashes and no Eastern Arabic digits. Rejected: i18next (bigger than the problem).

## D4. 2026-11-05: Tokens as CSS variables mapped into Tailwind 4
`web/src/styles/tokens.css` is the only file with hex values. `index.css` maps them into Tailwind's `@theme` and resets the default palette (`--color-*: initial`), so a component cannot use a Tailwind colour that is not a token.

## D5. 2026-11-05: Pinned versions
Python deps pinned in `requirements.txt` (runtime) and `requirements-dev.txt` (tests). npm deps installed with `--save-exact` and locked in `package-lock.json`; the Docker build uses `npm ci`. Python 3.11 in the container and locally (`uv venv --python 3.11`).
