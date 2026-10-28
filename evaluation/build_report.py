"""Build a shareable proof page from the preserved evaluation records."""
from pathlib import Path
from html import escape
import json
import statistics
from collections import Counter

ROOT = Path(__file__).resolve().parent
app = json.loads((ROOT / "app_results.json").read_text())
baseline = json.loads((ROOT / "baseline_raw_response.json").read_text())
judgments = json.loads((ROOT / "judgments.json").read_text())
manifest = json.loads((ROOT / "source_manifest.json").read_text())
app_by_id = {r["id"]: r for r in app["responses"]}
llm_by_id = {r["id"]: r for r in baseline["responses"]}
sources = {r["document"]: r for r in manifest["documents"]}
prefixes = {"CA6D3_Jan2026": "1192", "AR507_July2026": "1551", "ME612_Jan2026": "1390", "CA712_Jan2026": "730"}
latencies = [v for r in app["responses"] for v in r["latency_ms"]]
counts = Counter(c["app_rating"] for c in judgments["cases"])

intro = """This is a 12-question diagnostic of the current NIT Trichy application against an actual fresh-context LLM session instructed to use no browsing, tools or documents. The app had its downloaded corpus. It was not changed during the test. This tests the value of access to local documents; it does not establish superiority over all LLMs or over an assistant given the same sources."""
limitations = """The examples were selected to probe particular capabilities, not sampled randomly. Q01 and Q02 use faculty data manually corrected in the previous test; they are regression examples, not held-out extraction tests, and share one source document. The baseline is a Codex subagent using the inherited model, with no conversation history; the tool did not report an exact backend model identifier. No-tools isolation was instructed and self-reported, not technically enforced. There was one baseline batch, no multi-model comparison, and no blinded independent scoring. The app has a template-based answer generator, not an LLM generator. Broader accuracy, lower hallucination rate and superiority over browsing-enabled LLMs are not demonstrated."""

cards = []
table_rows = []
for case in judgments["cases"]:
    a, b = app_by_id[case["id"]], llm_by_id[case["id"]]
    rating = case["app_rating"]
    slug = rating.lower().replace(" ", "-")
    evidence = ""
    if case["source"]:
        source = sources[case["source"]]
        links = [f'<a href="{escape(source["local_pdf"], quote=True)}#page={case["pages"][0]}">Saved PDF</a>',
                 f'<a href="{escape(source["url"], quote=True)}">Official source</a>']
        for page in case["pages"]:
            img = f'evidence/{prefixes[case["source"]]}_{case["source"]}_p{page}.png'
            links.append(f'<a href="{img}" target="_blank">Page {page} image</a>')
        evidence = '<p class="links">' + ' · '.join(links) + '</p>'
    open_attr = " open" if rating == "Correct" else ""
    cards.append(f'''<article class="case" data-rating="{slug}" id="{case['id']}">
      <div class="case-head"><span class="id">{case['id']}</span><span class="badge {slug}">App: {escape(rating)}</span><span class="badge baseline">LLM: {escape(case['baseline_rating'])}</span></div>
      <h3>{escape(a['question'])}</h3>
      <p><strong>Verified answer / criterion:</strong> {escape(case['expected'])}</p>
      <p class="assessment">{escape(case['reason'])}</p>
      <details{open_attr}><summary>Actual answers and evidence</summary>
        <div class="answers"><section><h4>NIT Trichy application</h4><pre>{escape(a['answer'])}</pre></section>
        <section><h4>LLM without documents</h4><pre>{escape(b['answer'])}</pre></section></div>
        {evidence}<p class="note">{escape(case['note'])}</p>
      </details></article>''')
    table_rows.append(f"| {case['id']} | {a['question']} | {rating} | {case['baseline_rating']} |")

html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>NIT Trichy RAG: evidence and comparison</title>
<style>
:root{color-scheme:light;--ink:#122d37;--muted:#506672;--line:#d7e1e5;--teal:#06695f}*{box-sizing:border-box}body{margin:0;background:#f3f6f6;color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1120px;margin:0 auto;padding:48px 24px 72px}h1{font-size:clamp(30px,4vw,46px);line-height:1.14;letter-spacing:-1.4px;margin:10px 0 20px;max-width:800px}h2{font-size:24px;margin-top:36px}h3{font-size:20px;line-height:1.4;margin:14px 0}h4{font-size:14px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:0 0 10px}.eyebrow{font-size:12px;letter-spacing:2px;font-weight:750;color:var(--teal)}.lead{font-size:18px;max-width:950px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}.stat{padding:20px;border:1px solid var(--line);border-radius:12px;background:white}.stat strong{font-size:34px;display:block;line-height:1.1}.stat span{display:block;color:var(--muted);margin-top:8px;font-size:14px}.note{font-size:14px;color:var(--muted)}.notice{border-left:4px solid #c1801e;background:#fff5e5;padding:16px 20px;border-radius:4px}.controls{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:30px 0 16px}select{padding:10px 14px;font:inherit;border:1px solid var(--line);border-radius:8px;background:white}.case{background:white;border:1px solid var(--line);border-radius:14px;padding:24px;margin-bottom:18px}.case[hidden]{display:none}.case-head{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.id{font-weight:750;margin-right:6px}.badge{font-size:12px;font-weight:700;padding:4px 10px;border-radius:99px;background:#eaf0f3}.correct{background:#e0f1ea;color:#165c40}.partial{background:#fff0cf;color:#7d5310}.fail{background:#fce9e6;color:#9b3327}.safe-abstention{background:#e3eef9;color:#245b8c}.baseline{background:#edf0f2;color:#485864}.assessment{color:var(--muted)}summary{cursor:pointer;color:var(--teal);font-weight:650}.answers{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.answers section{min-width:0;border:1px solid var(--line);border-radius:8px;padding:16px;background:#f8fafb}pre{font:14px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}.links{font-size:14px}a{color:var(--teal);text-underline-offset:3px}.protocol{border:1px solid var(--line);background:white;padding:24px;border-radius:12px}.file-links{display:flex;gap:16px;flex-wrap:wrap}footer{margin-top:40px;color:var(--muted);font-size:13px}@media(max-width:700px){main{padding:28px 16px}.stats{grid-template-columns:1fr 1fr}.answers{grid-template-columns:1fr}.case{padding:18px}.controls{align-items:flex-start;flex-direction:column}}@media print{body{background:white}.controls{display:none}.case{break-inside:avoid}main{padding:0}}
</style></head><body><main><header><div class="eyebrow">NIT TRICHY · EVALUATION · 28 OCTOBER 2026</div><h1>Where document retrieval helps.<br>And where this app still fails.</h1>'''
html += f'<p class="lead">{intro}</p></header>'
html += '<div class="stats">' + ''.join(f'<div class="stat"><strong>{counts[label]}</strong><span>{caption}</span></div>' for label, caption in [('Correct','Correct app answers'),('Partial','Partial app answers'),('Fail','Failed app answers'),('Safe abstention','Safe app abstention')]) + '</div>'
html += '<p class="notice"><strong>Three clean wins over this closed-book baseline:</strong> the CA6D3 faculty, CA6D3 coordinator, and AR507 faculty. The baseline appropriately declined these questions. It did answer the general TF-IDF question correctly; the app failed that question.</p>'
html += '<div class="controls"><strong>All 12 questions, including failures</strong><label>Show <select id="filter"><option value="all">All results</option><option value="correct">Correct</option><option value="partial">Partial</option><option value="fail">Fail</option><option value="safe-abstention">Safe abstention</option></select></label></div>'
html += ''.join(cards)
html += f'''<h2>What the measurements establish</h2><div class="protocol"><p>Among nine questions answerable from the source PDFs, the app gave three fully correct answers, three partial answers and three failures. The baseline abstained on all nine. For the two unsupported cases, the app declined one and returned the wrong session for the other; the baseline declined both. On the general concept question, the baseline answered correctly and the app failed.</p><p>All 36 app calls completed with Python socket connections blocked. Median warm query time was <strong>{statistics.median(latencies):.1f} ms</strong>; index initialization was {app['initialization_ms']/1000:.2f} seconds. All 12 answers were identical across three repeats. This measures local engine execution, not browser latency, and no LLM latency comparison was performed.</p><p>The four official PDFs were downloaded again and matched the saved evidence byte for byte. SHA-256 hashes and HTTP results are preserved in the source manifest.</p></div>
<h2>Scope and limitations</h2><p>{limitations}</p>
<h2>Inspect and reproduce</h2><p>Run <code>python3 evaluation/run_benchmark.py --repeat 3 --output evaluation/app_results_new.json</code> from the project directory. Compare to the preserved original results. A baseline rerun requires a new model session using the saved prompt; the Python script does not call an LLM.</p><nav class="file-links"><a href="EVALUATION_REPORT.md">Written report</a><a href="app_results.json">App outputs + timings</a><a href="baseline_raw_response.json">Actual LLM outputs</a><a href="baseline_prompt.txt">Baseline prompt</a><a href="judgments.json">Scoring rationale</a><a href="source_manifest.json">Source hashes</a></nav><footer>Exploratory comparison, not a general model leaderboard. The application is a classical retrieval + template system.</footer></main>
<script>document.getElementById('filter').addEventListener('change',function(){{document.querySelectorAll('.case').forEach(el=>{{el.hidden=this.value!=='all'&&el.dataset.rating!==this.value;}});}});</script></body></html>'''
(ROOT / "proof.html").write_text(html, encoding="utf-8")

md = f'''# Evidence: NIT Trichy application versus a general LLM without documents

Test date: 28 October 2026 (Asia/Kolkata). [Open the interactive proof page](proof.html).

{intro}

## Defensible conclusion

The current app gives source-verifiable answers to three particular institutional fact questions that this closed-book baseline could not answer. Those successes depend on having the right documents and extracted fields. The evidence does not show that the app is more intelligent or generally more accurate than an LLM.

## Three demonstrated examples

1. **CA6D3 faculty, January 2026:** Dr. S. Sangeetha. [Official course plan](https://cp.nitt.edu/upload/course_pdfs/CA6D3_Jan2026.pdf), page 1. [Saved page image](evidence/1192_CA6D3_Jan2026_p1.png).
2. **CA6D3 coordinator, January 2026:** Dr. Ashwinth J, distinct from the faculty. Same source, page 1. These are two facts from one record, already manually corrected before this evaluation.
3. **AR507 faculty, July 2026:** Dr. K. Thirumaran and Dr. D. Kannamma. [Official course plan](https://cp.nitt.edu/upload/course_pdfs/AR507_July2026.pdf), page 1, also confirmed on page 3. [Saved page image](evidence/1551_AR507_July2026_p1.png).

The actual baseline declined all three. See [its unchanged response](baseline_raw_response.json) and [the application's unchanged responses](app_results.json). These are measured outcomes, not invented example LLM answers.

## Full results

| ID | Question | App | Baseline |
|---|---|---|---|
''' + '\n'.join(table_rows) + f'''

Among the **nine answerable document questions**: app 3 correct, 3 partial, 3 failed; baseline 9 abstentions. Among **two unsupported cases**: app 1 safe abstention and 1 wrong-session failure; baseline 2 appropriate abstentions. For the **general NLP concept** question: baseline correct, app failed. Abstentions are not hallucinations and partial answers are not counted as clean wins.

## What did not work

- AR507's PDF has seven assessment components; the app merges the first two 10-mark items into one 20-percent entry.
- ME612 and CA712 answers omit compensation-assessment rows. CA712 also prints a malformed Credits field; the PDF labels both cycle-test rows identically, which the app does not flag.
- The app misses CA6D3's 4 credits (page 1) and its Monday/Tuesday 4–5 pm consultation hours (page 3).
- A July 2026 CA6D3 query returns a January record. The answer labels January, but does not resolve the requested session.
- The ME612 attendance consequence is in its PDF, but the app answers with assessment weights.
- The general TF-IDF question returns an irrelevant course plan. The baseline gives a correct explanation.

The [per-question judgments](judgments.json) explain every rating. No app logic or dataset fields were modified to improve this evaluation's results. The failures remain visible in the current app.

## Independent operational checks

- All 36 local engine calls (12 questions × 3 repeats) succeeded with Python socket connection functions blocked.
- Warm engine latency: median **{statistics.median(latencies):.1f} ms**, observed range **{min(latencies):.1f}–{max(latencies):.1f} ms**. Index initialization: **{app['initialization_ms']/1000:.2f} seconds**. Browser rendering and PDF acquisition are excluded. No claim of being faster than an LLM is made because baseline latency was not measured.
- All 12 outputs were identical across three repeats on the same corpus. This is a repeatability check, not an accuracy guarantee.
- The app uses no external LLM generation service; its generation stage is template-based. It can operate offline after documents have been downloaded.
- All four source PDFs returned HTTP 200 and exactly matched the saved bytes when rechecked. [Source manifest and SHA-256 hashes](source_manifest.json).

## Experimental limits

{limitations}

The baseline safely admits uncertainty; this experiment does not show that general LLMs necessarily hallucinate. An LLM with browsing or the same PDFs may match or exceed this app. The reported advantage is access to specific evidence, not intrinsic superiority of classical NLP over language models.

The manual rubric was applied after inspecting outputs and source pages. It is not pre-registered or independently adjudicated. The question list was fixed before the evaluation run and all 12 outcomes are retained. The app code and corpus file hashes are recorded so the tested version is identifiable.

## Reproduce the application run

From the project folder:

```bash
python3 evaluation/run_benchmark.py --repeat 3 --output evaluation/app_results_new.json
```

Keep `app_results.json` as the original snapshot. The command reruns the local engine, not the baseline. For another baseline trial, paste [baseline_prompt.txt](baseline_prompt.txt) into a fresh model session with browsing and document tools disabled, retain the raw answers and exact model/settings, and score against [judgments.json](judgments.json). For a stronger study, use randomly selected held-out documents, independent graders, multiple models, and a second baseline supplied with the same sources.

## Evidence files

- [App answers, sources, timings and code/data hashes](app_results.json)
- [Actual baseline response](baseline_raw_response.json), [prompt](baseline_prompt.txt), and [run metadata](baseline_run_metadata.json)
- [Manual scoring and ground truth](judgments.json)
- [Live-source verification manifest](source_manifest.json)
- [CA6D3 source PDF](evidence/CA6D3_Jan2026.pdf), [AR507 source PDF](evidence/AR507_July2026.pdf), [ME612 source PDF](evidence/ME612_Jan2026.pdf), [CA712 source PDF](evidence/CA712_Jan2026.pdf)

Suggested presentation claim: “Our local retrieval system answered three selected NIT Trichy fact questions with verifiable course-plan sources that a fresh LLM without document access could not answer. The same diagnostic exposed extraction and question-routing failures, so broader evaluation is still needed.”
'''
(ROOT / "EVALUATION_REPORT.md").write_text(md, encoding="utf-8")
print("Built proof.html and EVALUATION_REPORT.md")
