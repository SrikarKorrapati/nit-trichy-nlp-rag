# NIT Trichy Academic RAG Assistant

A Streamlit question-answering project using classical NLP to retrieve NIT Trichy academic information and show source citations. It combines retrieval, information extraction, classification, and extractive summarization. Answers use templates and retrieved evidence; no external LLM or API key is required.

## Quick start

Python 3.11 or newer is recommended.

```bash
git clone https://github.com/SrikarKorrapati/nit-trichy-nlp-rag.git
cd nit-trichy-nlp-rag
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
bash run_demo.sh
```

Open http://localhost:8501. On Windows, activate the virtual environment with `.venv\Scripts\activate`, then run `python scripts/use_demo_data.py` and `python -m streamlit run app.py --server.port 8501`.

The public repository includes **two example course records**, AR507 and CA6D3. The startup script installs them only if no local application corpus exists. Full scraped documents, caches, and evaluation evidence remain outside Git. See [example sources](examples/README.md) and [data formats](data/README.md).

## Classical algorithms

| Algorithm | Purpose | Implementation |
|---|---|---|
| TF-IDF | Weight terms in document and query vectors | `nitt_rag/retrieval.py` |
| Cosine similarity | Rank query/document vector similarity | `nitt_rag/retrieval.py` |
| BM25 | Rank keyword and course-code matches | `nitt_rag/retrieval.py` |
| Multinomial Naive Bayes | Classify the question category | `nitt_rag/classifier.py` |
| TextRank | Extract representative context sentences | `nitt_rag/summarizer.py` |
| Rule-based extraction | Extract course codes, sessions, and other entities | `nitt_rag/entities.py` |

```text
Question -> classification -> TF-IDF + BM25 retrieval
         -> evidence ranking -> TextRank -> template answer + citations
```

Faculty questions match the named course or course code, include the academic session, and distinguish an instructor from a coordinator. An unmatched course does not inherit another course's teacher.

## Try it

- What is the course plan for AR507?
- Who is teaching Natural Language Processing?
- Who teaches CA6D3?

```bash
python3 scripts/use_demo_data.py
python3 -m nitt_rag.cli "Who teaches CA6D3?"
```

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/use_demo_data.py
python3 -m pytest -q
```

## Adding more public data

The scripts in `scripts/` collect website documents and course metadata from [nitt.edu](https://www.nitt.edu/home/) and [cp.nitt.edu](https://cp.nitt.edu/). `scrape_nitt.py` is the original bounded academic crawler with topic/year filters, not the later comprehensive site audit. Review its scope before running it.

```bash
python3 scripts/scrape_nitt.py
python3 scripts/scrape_cp_courses.py
```

Course-PDF OCR in `scrape_cp_course_details.py` uses macOS Apple Vision and requires `requirements-ocr-macos.txt`; the app and example data do not require macOS. Its default maximum is eight pages per PDF and can be changed with `--max-pages`. The merge script expects four numbered shard files. Read their command-line options before collecting a larger dataset.

The expanded recursive archive produced later is **not included or indexed** in this app. Keep source URLs, sessions, and extraction limitations with any imported text. Historical notices and teaching assignments may not describe current arrangements, and OCR can misread names, numbers, and tables.

See [the project report](PROJECT_REPORT.md) for the architecture and [evaluation utilities](evaluation/README.md) for the benchmark workflow. This is an independent academic project, not an official NIT Trichy service.
