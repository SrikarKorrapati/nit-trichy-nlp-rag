# Project Report: NIT Trichy Academic RAG Assistant

## Problem Domain

This project belongs to the following NLP domains:

- Information Retrieval
- Question Answering
- Information Extraction
- Text Summarization

The system answers questions about NIT Trichy academic information using scraped public documents and course-plan data.

## Dataset

The project uses two main data collections:

1. **NIT Trichy website documents**
   - Academic programmes
   - Curriculum and syllabus PDFs
   - Fee circulars
   - Department information

2. **NIT Trichy course-plan portal data**
   - Course codes
   - Course names
   - Departments
   - Programmes
   - Semesters and sessions
   - Faculty details when available
   - Syllabus, objectives, outcomes, assessment methods, and raw OCR text from course-plan PDFs

Original local demonstration dataset size (not bundled in this public repository; the included example contains two courses):

- 623 website document chunks
- 1,132 course-plan detail chunks
- 1,755 total retrievable chunks

## Algorithms Implemented

### 1. TF-IDF Vectorization

Each document chunk is converted into a sparse TF-IDF vector. This gives higher weight to important terms and lower weight to very common terms.

Used in:

- `nitt_rag/retrieval.py`

### 2. Cosine Similarity

The user query is vectorized using the same TF-IDF model. Cosine similarity ranks document chunks by weighted term overlap.

Used in:

- `nitt_rag/retrieval.py`

### 3. BM25 Retrieval

BM25 is implemented as a second retrieval algorithm. It improves ranking for exact keyword and course-code-heavy queries.

Used in:

- `nitt_rag/retrieval.py`

### 4. Naive Bayes Question Classification

A Multinomial Naive Bayes classifier predicts the type of question:

- course plan
- fees
- curriculum
- admissions
- department
- academics
- placements
- student facilities

Used in:

- `nitt_rag/classifier.py`

### 5. TextRank Summarization

Retrieved chunks are summarized by building a sentence similarity graph and ranking sentences with PageRank.

Used in:

- `nitt_rag/summarizer.py`

### 6. Rule-Based Information Extraction

Regex and dictionary rules extract:

- course codes
- emails
- phone numbers
- sessions
- years
- departments
- programmes
- URLs

Used in:

- `nitt_rag/entities.py`

## RAG Architecture

The project uses a classical RAG pipeline:

```text
Question
  -> Question classifier
  -> TF-IDF retrieval
  -> BM25 retrieval
  -> Hybrid ranking
  -> TextRank context summarization
  -> Template answer generation
  -> Source display
```

No LLM is required. The generation step is template-based and grounded in retrieved documents.

## Interfaces

The project provides:

- Streamlit web app: `app.py`
- Command-line interface: `python3 -m nitt_rag.cli "question"`
- Reusable scraping scripts in `scripts/`
- Tests in `tests/`

## Example Questions

- What is the course plan for AR507?
- Show courses related to Natural Language Processing.
- What is the syllabus for Data Structures?
- What fees information is available for B.Tech 2026?
- Which CSE courses are available in July2026?
