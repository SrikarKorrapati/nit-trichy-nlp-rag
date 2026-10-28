# Evaluation utilities

`run_benchmark.py` captures application answers, retrieval provenance, timing, and source hashes for the questions in `questions.json`. It blocks network access while evaluating the local application.

```bash
python3 evaluation/run_benchmark.py --repeat 3
```

The included two-course example cannot answer the full benchmark. Use the full local corpus for those questions. Benchmark results, source PDFs/images, baseline responses, and other run artifacts are not published in this code repository. `build_report.py` is the original report generator and requires those additional local evaluation artifacts; it is not needed to run the app. This repository does not establish general superiority over an LLM.
