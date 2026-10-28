from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data import DocumentChunk


TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]+")


@dataclass
class SearchResult:
    score: float
    tfidf_score: float
    bm25_score: float
    chunk: DocumentChunk


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lengths) / max(1, len(self.doc_lengths))
        self.term_frequencies = [Counter(tokens) for tokens in self.doc_tokens]
        self.document_frequency: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.document_frequency.update(set(tokens))
        self.n_docs = len(documents)

    def idf(self, term: str) -> float:
        df = self.document_frequency.get(term, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def scores(self, query: str) -> np.ndarray:
        query_terms = tokenize(query)
        scores = np.zeros(self.n_docs)
        for term in query_terms:
            idf = self.idf(term)
            for index, frequencies in enumerate(self.term_frequencies):
                tf = frequencies.get(term, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[index] or 1
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                scores[index] += idf * numerator / denominator
        return scores


class HybridRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.texts = [chunk.text for chunk in chunks]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)
        self.bm25 = BM25Index(self.texts)

    @staticmethod
    def normalize(scores: np.ndarray) -> np.ndarray:
        if scores.size == 0:
            return scores
        max_score = float(scores.max())
        min_score = float(scores.min())
        if max_score == min_score:
            return np.zeros_like(scores)
        return (scores - min_score) / (max_score - min_score)

    def search(self, query: str, top_k: int = 8, collection: str | None = None) -> list[SearchResult]:
        query_vector = self.vectorizer.transform([query])
        tfidf_scores = cosine_similarity(query_vector, self.tfidf_matrix).ravel()
        bm25_scores = self.bm25.scores(query)

        combined = 0.72 * self.normalize(tfidf_scores) + 0.28 * self.normalize(bm25_scores)

        if collection:
            for index, chunk in enumerate(self.chunks):
                if chunk.collection != collection:
                    combined[index] *= 0.25

        normalized_query = re.sub(r"[^A-Za-z0-9]", "", query).upper()
        for index, chunk in enumerate(self.chunks):
            code = str(chunk.metadata.get("course_code") or "")
            normalized_code = re.sub(r"[^A-Za-z0-9]", "", code).upper()
            if normalized_code and normalized_code in normalized_query:
                combined[index] += 0.75
            elif normalized_code and normalized_code.replace(" ", "") in normalized_query:
                combined[index] += 0.5

        ranked_indexes = combined.argsort()[::-1][:top_k]
        results = []
        for index in ranked_indexes:
            results.append(
                SearchResult(
                    score=float(combined[index]),
                    tfidf_score=float(tfidf_scores[index]),
                    bm25_score=float(bm25_scores[index]),
                    chunk=self.chunks[index],
                )
            )
        return results
