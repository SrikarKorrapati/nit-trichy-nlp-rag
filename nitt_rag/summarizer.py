from __future__ import annotations

import re

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    sentences = []
    for sentence in SENTENCE_RE.split(text):
        cleaned = re.sub(r"\s+", " ", sentence).strip()
        if len(cleaned.split()) >= 5:
            sentences.append(cleaned)
    return sentences


def textrank_summary(text: str, max_sentences: int = 5) -> list[str]:
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return sentences

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(sentences)
    similarity = cosine_similarity(matrix)

    graph = nx.from_numpy_array(similarity)
    scores = nx.pagerank(graph)
    ranked = sorted(scores, key=scores.get, reverse=True)[:max_sentences]
    ranked_in_order = sorted(ranked)
    return [sentences[index] for index in ranked_in_order]
