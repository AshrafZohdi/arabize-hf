"""Build and execute notebooks/eda.ipynb (stage 1). Run: python notebooks/build_eda.py

The notebook reads the raw snapshot (checked against data/manifest.json), saves charts to data/reports/,
and writes data/reports/eda.md and data/reports/eda_summary.json from the numbers it computes.
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent

CELLS = [
    ("md", "# Term bank EDA (stage 1)\n\nSources: Darby's own glossary, GIST (`Jerry999/multilingual-terminology`, Arabic.csv) and the Microsoft glossary (`ymoslem/MS-Glossary-EN-AR`), at the revisions pinned in `data/manifest.json`. Nothing here changes the raw files."),
    ("code", """import json, re, sys
from collections import Counter
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data.pipeline import read_source, verify_raw, REPORTS
from data.text import (arabic_share, is_latin_only, keeps_acronym_only, split_packed, acronym_kinds, is_acronym_term,
                       normalise_en, en_key, DIACRITIC, TATWEEL, PRESENTATION_FORM, EASTERN_DIGIT, HTML_TAG, EXTRA_WS)
from server.terms import Term, TermFinder
verify_raw()
REPORTS.mkdir(parents=True, exist_ok=True)
pd.set_option('display.width', 160); pd.set_option('display.max_colwidth', 50)
S = {}  # summary numbers for the report"""),
    ("md", "## 1. Load and align columns\n\nEvery source becomes `source, row_id, en, ar`. Our glossary uses `term_en`/`term_msa`; GIST `English`/`Arabic`; MS `text_en`/`text_ar` (the card's other column names do not exist in the file)."),
    ("code", """g = read_source('gist'); m = read_source('ms'); o1 = read_source('darby_glossary'); o2 = read_source('darby_computing')
frames = [
    pd.DataFrame({'source': 'darby', 'row_id': o1.index.astype(str), 'en': o1.term_en, 'ar': o1.term_msa}),
    pd.DataFrame({'source': 'darby', 'row_id': ('c' + o2.index.astype(str)), 'en': o2.term_en, 'ar': o2.term_msa}),
    pd.DataFrame({'source': 'gist', 'row_id': g['Index'].astype(str), 'en': g.English, 'ar': g.Arabic}),
    pd.DataFrame({'source': 'ms', 'row_id': m.index.astype(str), 'en': m.text_en, 'ar': m.text_ar}),
]
df = pd.concat(frames, ignore_index=True).fillna('')
counts = df.groupby('source').size().rename('rows')
S['rows'] = counts.to_dict(); S['rows_total'] = int(len(df))
counts"""),
    ("md", "## 2. Nulls and empty strings"),
    ("code", """empty = df.assign(en_empty=df.en.str.strip() == '', ar_empty=df.ar.str.strip() == '').groupby('source')[['en_empty', 'ar_empty']].sum()
S['empty'] = {k: {c: int(v) for c, v in r.items()} for k, r in empty.iterrows()}
empty"""),
    ("md", "## 3. Duplicates\n\nExact, case-insensitive, and after the matching key (`en_key`: lower case, singular, hyphens as spaces, acronyms keep case). Within each source and across sources."),
    ("code", """df['en_norm'] = df.en.map(normalise_en)
df['key'] = df.en.map(en_key)
dup = {}
for src, d in df.groupby('source'):
    dup[src] = {
        'exact_pairs': int(d.duplicated(['en', 'ar']).sum()),
        'exact_en': int(d.en.duplicated().sum()),
        'case_insensitive_en': int(d.en.str.lower().duplicated().sum()),
        'same_key': int(d.key.duplicated().sum()),
    }
S['duplicates_within'] = dup
keys_by_src = {s: set(d.key) for s, d in df.groupby('source')}
S['overlap'] = {
    'darby_gist': len(keys_by_src['darby'] & keys_by_src['gist']),
    'darby_ms': len(keys_by_src['darby'] & keys_by_src['ms']),
    'gist_ms': len(keys_by_src['gist'] & keys_by_src['ms']),
    'all_three': len(keys_by_src['darby'] & keys_by_src['gist'] & keys_by_src['ms']),
}
S['unique_keys_all'] = int(df.key.nunique())
display(pd.DataFrame(dup).T); S['overlap'], S['unique_keys_all']"""),
    ("code", """# Keys that differ only by case are kept apart on purpose (IT vs it). How often does that happen?
lower_groups = df.groupby(df.key.str.lower()).key.nunique()
case_split = lower_groups[lower_groups > 1]
S['case_split_keys'] = int(len(case_split))
df[df.key.str.lower().isin(case_split.index[:12])][['source', 'en', 'ar']].sort_values('en').head(24)"""),
    ("md", "## 4. Untranslated rows\n\nArabic empty, identical to the English, Latin script only, or only the English acronym with no Arabic word."),
    ("code", """df['ar_same_as_en'] = df.ar.str.strip().str.lower() == df.en.str.strip().str.lower()
df['ar_latin_only'] = df.ar.map(is_latin_only)
df['ar_acronym_only'] = df.ar.map(keeps_acronym_only)
df['ar_mixed_script'] = df.ar.map(lambda s: 0 < arabic_share(s) < 1)
untr = df.groupby('source')[['ar_same_as_en', 'ar_latin_only', 'ar_acronym_only', 'ar_mixed_script']].sum()
S['untranslated'] = {k: {c: int(v) for c, v in r.items()} for k, r in untr.iterrows()}
display(untr)
df[df.ar_latin_only | df.ar_mixed_script][['source', 'en', 'ar']].head(25)"""),
    ("md", "## 5. Acronyms and short forms in English"),
    ("code", """df['acr_kinds'] = df.en.map(acronym_kinds)
df['is_acronym'] = df.en.map(is_acronym_term)
kind_counts = Counter(k for ks in df.acr_kinds for k in ks)
S['acronym_kinds'] = dict(kind_counts)
S['acronym_terms'] = df.groupby('source').is_acronym.sum().astype(int).to_dict()
print(kind_counts)
top = df[df.is_acronym].assign(n=1).groupby('en').agg(n=('n', 'sum'), sources=('source', lambda s: ','.join(sorted(set(s)))), ar=('ar', 'first'))
top = top.sort_values(['n', 'en'], ascending=[False, True]).head(50)
S['acronym_top50'] = top.reset_index()[['en', 'sources', 'ar']].to_dict('records')
top"""),
    ("code", """# Acronyms whose Arabic keeps the acronym only, or is Latin only: the core of the stage 3 work queue.
acr = df[df.is_acronym]
S['acronyms_without_arabic_meaning'] = int((acr.ar_latin_only | acr.ar_acronym_only).sum())
S['acronyms_with_mixed_arabic'] = int(acr.ar_mixed_script.sum())
acr[['source', 'en', 'ar']].sample(min(20, len(acr)), random_state=0)"""),
    ("md", "## 6. Script analysis of the Arabic values"),
    ("code", """script = pd.DataFrame({
    'source': df.source,
    'diacritics': df.ar.str.contains(DIACRITIC),
    'tatweel': df.ar.str.contains(TATWEEL, regex=False),
    'presentation_forms': df.ar.str.contains(PRESENTATION_FORM),
    'eastern_digits': df.ar.str.contains(EASTERN_DIGIT),
    'western_digits': df.ar.str.contains(r'[0-9]'),
    'html': df.ar.str.contains(HTML_TAG) | df.en.str.contains(HTML_TAG),
    'extra_whitespace': df.ar.str.contains(EXTRA_WS) | df.en.str.contains(EXTRA_WS),
    'latin_punct_in_ar': df.ar.str.contains(r'[,;?]') & df.ar.map(lambda s: arabic_share(s) > 0),
    'brackets': df.ar.str.contains(r'[()\\[\\]]'),
})
sc = script.groupby('source').sum()
S['script'] = {k: {c: int(v) for c, v in r.items()} for k, r in sc.iterrows()}
df['arabic_share'] = df.ar.map(arabic_share)
S['arabic_share_lt_1'] = df[df.arabic_share < 1].groupby('source').size().astype(int).to_dict()
sc"""),
    ("md", "## 7. Several translations packed into one cell"),
    ("code", """df['variants'] = df.ar.map(split_packed)
df['n_variants'] = df.variants.map(len)
packed = df[df.n_variants > 1]
S['packed'] = packed.groupby('source').size().astype(int).to_dict()
packed[['source', 'en', 'ar', 'n_variants']].head(20)"""),
    ("md", "## 8. Conflicts: the same English term with different Arabic across sources\n\nCompared with `ar_compare_key` (no diacritics, unified alef, ى and ة, no leading ال), so المصدر and مصدر agree."),
    ("code", """from data.text import ar_compare_key
df['akey'] = df.ar.map(ar_compare_key)
multi = df.groupby('key').filter(lambda d: d.source.nunique() > 1)
conf = multi.groupby('key').filter(lambda d: d.akey.nunique() > 1)
S['conflicting_keys'] = int(conf.key.nunique())
S['agreeing_cross_source_keys'] = int(multi.key.nunique() - conf.key.nunique())
pairs = Counter()
for _, d in conf.groupby('key'):
    srcs = sorted(set(d.source))
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            pairs[f'{srcs[i]}-{srcs[j]}'] += 1
S['conflict_pairs'] = dict(pairs)
darby_conf = conf[conf.key.isin(conf[conf.source == 'darby'].key)].sort_values(['key', 'source'])
S['darby_conflicts'] = darby_conf[['key', 'source', 'ar']].to_dict('records')
print(pairs)
darby_conf[['key', 'source', 'en', 'ar']]"""),
    ("md", "## 9. Length distributions"),
    ("code", """df['en_chars'] = df.en.str.len(); df['en_words'] = df.en.str.split().map(len)
df['ar_chars'] = df.ar.str.len(); df['ar_words'] = df.ar.str.split().map(len)
lens = df.groupby('source')[['en_chars', 'en_words', 'ar_chars', 'ar_words']].describe().T
S['length'] = {src: {'en_words_max': int(d.en_words.max()), 'en_chars_p99': float(d.en_chars.quantile(.99)), 'single_word_share': round(float((d.en_words == 1).mean()), 3)} for src, d in df.groupby('source')}
fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
for src, d in df.groupby('source'):
    axes[0].hist(d.en_words.clip(upper=8), bins=range(1, 10), alpha=.55, label=src, density=True)
    axes[1].hist(d.en_chars.clip(upper=60), bins=30, alpha=.55, label=src, density=True)
axes[0].set_title('English words per term (8 = 8 or more)'); axes[1].set_title('English characters per term (60 = 60 or more)')
for a in axes: a.legend()
fig.tight_layout(); fig.savefig(REPORTS / 'eda_lengths.png', dpi=120)
junk = df[(df.en.str.strip().str.len() <= 1) | df.en.str.fullmatch(r'[\\d\\W_]+') | (df.en_words > 8)]
S['junk_candidates'] = junk.groupby('source').size().astype(int).to_dict()
display(junk[['source', 'en', 'ar']].head(20))"""),
    ("md", "## 10. Coverage and noise in real text\n\nThe term finder is run on the English text of our 7 lessons plus the demo email, once per source. Coverage: which terms appear. Noise: terms highlighted per 100 words. A source that marks every second word is useless for highlighting."),
    ("code", """lesson_text = []
for p in sorted((ROOT / 'content').glob('day-*.json')):
    for b in json.loads(p.read_text(encoding='utf-8'))['blocks']:
        for v in (b.get('en'), b.get('text', {}).get('en') if isinstance(b.get('text'), dict) else None):
            if isinstance(v, str): lesson_text.append(re.sub(r'\\[\\[([^|\\]]+)(?:\\|[^\\]]+)?\\]\\]', r'\\1', v))
demo = 'Before you send the summary to the client, check it for hallucinations. Give the model more context in your prompt and ask it to cite the source paragraph.'
corpus = '\\n'.join(lesson_text + [demo])
n_words = len(re.findall(r'[A-Za-z]+', corpus))
noise, hits_by = {}, {}
for src, d in df.groupby('source'):
    f = TermFinder([Term(id=f'{src}:{r}', en=e, ar=a, source=src) for r, e, a in zip(d.row_id, d.en, d.ar) if e.strip()])
    hits = f.find(corpus)
    hits_by[src] = Counter(h.text.lower() for h in hits)
    noise[src] = {'matches': len(hits), 'per_100_words': round(100 * len(hits) / n_words, 1), 'distinct_terms': len(hits_by[src])}
S['corpus_words'] = n_words; S['noise'] = noise
display(pd.DataFrame(noise).T)
for src in ('gist', 'ms'):
    print(src, 'most frequent matches:', hits_by[src].most_common(25))"""),
    ("code", """# Which MS matches are everyday words? Single-word MS terms that our lesson text uses most.
ms_single = df[(df.source == 'ms') & (df.en_words == 1)]
S['ms_single_word_terms'] = int(len(ms_single))
for label, sub in (('ms multi-word only', df[(df.source == 'ms') & (df.en_words > 1)]), ('ms single-word only', ms_single)):
    f = TermFinder([Term(id=f'ms:{r}', en=e, ar=a, source='ms') for r, e, a in zip(sub.row_id, sub.en, sub.ar) if e.strip()])
    hits = f.find(corpus)
    noise[label] = {'matches': len(hits), 'per_100_words': round(100 * len(hits) / n_words, 1), 'distinct_terms': len({h.text.lower() for h in hits})}
    print(label, noise[label], Counter(h.text.lower() for h in hits).most_common(15))
S['noise'] = noise
demo_hits = {src: [h.text for h in TermFinder([Term(id=f'{src}:{r}', en=e, ar=a, source=src) for r, e, a in zip(d.row_id, d.en, d.ar) if e.strip()]).find(demo)] for src, d in df.groupby('source')}
S['demo_email_matches'] = demo_hits
demo_hits"""),
    ("md", "## 11. Summary and report"),
    ("code", """(REPORTS / 'eda_summary.json').write_text(json.dumps(S, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
r = S
lines = [
    '# Term bank EDA: summary',
    '',
    'Generated by `notebooks/eda.ipynb` from the raw snapshot pinned in `data/manifest.json`. Numbers are recomputed on every run.',
    '',
    '## Rows',
    '',
    '| Source | Rows | Empty English | Empty Arabic | Acronym terms | Packed variants |',
    '|---|---|---|---|---|---|',
]
for s in ('darby', 'gist', 'ms'):
    lines.append(f"| {s} | {r['rows'][s]} | {r['empty'][s]['en_empty']} | {r['empty'][s]['ar_empty']} | {r['acronym_terms'].get(s, 0)} | {r['packed'].get(s, 0)} |")
lines += [
    '',
    f"All sources: {r['rows_total']} rows, {r['unique_keys_all']} unique matching keys.",
    '',
    '## Duplicates',
    '',
    '| Source | Exact (en, ar) pairs | Same English | Same English ignoring case | Same matching key |',
    '|---|---|---|---|---|',
] + [f"| {s} | {d['exact_pairs']} | {d['exact_en']} | {d['case_insensitive_en']} | {d['same_key']} |" for s, d in r['duplicates_within'].items()] + [
    '',
    f"Across sources (same key): Darby and GIST {r['overlap']['darby_gist']}, Darby and MS {r['overlap']['darby_ms']}, GIST and MS {r['overlap']['gist_ms']}, all three {r['overlap']['all_three']}. "
    f"Keys that differ only by case (kept apart, like IT and it): {r['case_split_keys']}.",
    '',
    '## Untranslated or partly translated Arabic',
    '',
    '| Source | Arabic same as English | Latin only | Acronym only | Mixed Arabic and Latin |',
    '|---|---|---|---|---|',
] + [f"| {s} | {d['ar_same_as_en']} | {d['ar_latin_only']} | {d['ar_acronym_only']} | {d['ar_mixed_script']} |" for s, d in r['untranslated'].items()] + [
    '',
    f"Acronym terms whose Arabic has no Arabic meaning (Latin or acronym only): {r['acronyms_without_arabic_meaning']}. Acronym terms with mixed Arabic and Latin: {r['acronyms_with_mixed_arabic']}.",
    f"Short-form patterns in English: {', '.join(f'{k} {v}' for k, v in sorted(r['acronym_kinds'].items()))}.",
    '',
    '## Script issues in Arabic',
    '',
    '| Source | ' + ' | '.join(next(iter(r['script'].values())).keys()) + ' |',
    '|---|' + '---|' * len(next(iter(r['script'].values()))),
] + [f"| {s} | " + ' | '.join(str(v) for v in d.values()) + ' |' for s, d in r['script'].items()] + [
    '',
    '## Conflicts across sources',
    '',
    f"{r['conflicting_keys']} English keys have different Arabic in different sources ({', '.join(f'{k}: {v}' for k, v in r['conflict_pairs'].items())}); {r['agreeing_cross_source_keys']} cross-source keys agree. "
    'Conflicts with our own glossary (ours wins in stage 2):',
    '',
] + [f"- `{c['key']}` {c['source']}: {c['ar']}" for c in r['darby_conflicts']] + [
    '',
    '## Length and junk',
    '',
] + [f"- {s}: single-word share {d['single_word_share']}, longest English term {d['en_words_max']} words, 99th percentile {d['en_chars_p99']:.0f} characters." for s, d in r['length'].items()] + [
    f"- Junk candidates (one character, no letters, or more than 8 words): {r['junk_candidates']}.",
    '',
    '![Lengths](eda_lengths.png)',
    '',
    '## Coverage and noise in real text',
    '',
    f"Term finder run on the English text of the 7 lessons and the demo email ({r['corpus_words']} words), one source at a time:",
    '',
    '| Source | Matches | Per 100 words | Distinct terms |',
    '|---|---|---|---|',
] + [f"| {s} | {d['matches']} | {d['per_100_words']} | {d['distinct_terms']} |" for s, d in r['noise'].items()] + [
    '',
    'Demo email matches: ' + '; '.join(f"{s}: {', '.join(v) or 'none'}" for s, v in r['demo_email_matches'].items()) + '.',
]
(REPORTS / 'eda.md').write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
print('\\n'.join(lines[:60]))"""),
]


def main() -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src) for kind, src in CELLS]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
    nbformat.write(nb, ROOT / "notebooks" / "eda.ipynb")
    print("wrote notebooks/eda.ipynb, data/reports/eda.md")


if __name__ == "__main__":
    main()
