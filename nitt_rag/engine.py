from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .classifier import QuestionClassifier
from .data import DocumentChunk, load_chunks
from .entities import extract_entities
from .retrieval import HybridRetriever, SearchResult
from .summarizer import textrank_summary


def is_faculty_question(question: str) -> bool:
    return bool(re.search(
        r"\bwho\b.{0,35}\b(?:teach(?:es|ing)?|taught)\b"
        r"|\b(?:faculty|instructor|lecturer|professor|teacher|coordinator)\b",
        question,
        re.IGNORECASE,
    ))


def matches_named_course(question: str, row: dict[str, Any]) -> bool:
    query = " " + " ".join(re.findall(r"\w+", question.casefold())) + " "
    for key in ("course_code", "course_name"):
        value = " ".join(re.findall(r"\w+", str(row.get(key) or "").casefold()))
        if value and f" {value} " in query:
            return True
    return False


@dataclass
class Answer:
    question: str
    category: str
    category_confidence: float
    answer: str
    entities: dict[str, list[str]]
    results: list[SearchResult]
    sources: list[dict[str, Any]]


class NITTAssistant:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.chunks: list[DocumentChunk] = load_chunks(data_dir) if data_dir else load_chunks()
        if not self.chunks:
            raise RuntimeError("No data chunks found. Check the data/ directory.")
        self.retriever = HybridRetriever(self.chunks)
        self.classifier = QuestionClassifier()

    def choose_collection(self, category: str) -> str | None:
        if category == "course_plan":
            return "course_plans"
        if category in {"fees", "curriculum", "academics", "admissions", "department"}:
            return None
        return None

    def ask(self, question: str, top_k: int = 8) -> Answer:
        category, confidence = self.classifier.predict(question)
        collection = self.choose_collection(category)
        results = self.retriever.search(question, top_k=top_k, collection=collection)
        if is_faculty_question(question):
            # Only use records identifying the named course, never a nearby topic's teacher.
            results = [r for r in results if r.chunk.collection == "course_plans"
                       and matches_named_course(question, r.chunk.metadata)]
        context = "\n\n".join(result.chunk.text[:4000] for result in results[:5])
        summary_sentences = textrank_summary(context, max_sentences=5)
        entities = extract_entities(question + "\n" + context)

        answer_text = self.compose_answer(question, category, summary_sentences, results)
        sources = []
        seen = set()
        for result in results:
            url = result.chunk.source_url
            key = (result.chunk.title, url)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "title": result.chunk.title,
                    "url": url,
                    "collection": result.chunk.collection,
                    "score": round(result.score, 4),
                }
            )

        return Answer(
            question=question,
            category=category,
            category_confidence=confidence,
            answer=answer_text,
            entities=entities,
            results=results,
            sources=sources,
        )

    @staticmethod
    def compose_answer(
        question: str,
        category: str,
        summary_sentences: list[str],
        results: list[SearchResult],
    ) -> str:
        if not results or results[0].score <= 0:
            return (
                "I could not find relevant NIT Trichy context in the current dataset. "
                "Add more documents or refine the query."
            )

        if is_faculty_question(question):
            lines = ["According to the available NIT Trichy course plans:", ""]
            for result in results:
                row = result.chunk.metadata
                course = f"{row.get('course_name')} ({row.get('course_code')})"
                session = str(row.get("session") or "session not recorded")
                faculty = str(row.get("faculty") or "").strip()
                if faculty:
                    lines.append(f"**{faculty}** is listed as the faculty for **{course}**, **{session}**.")
                else:
                    lines.append(f"The faculty name for **{course}**, **{session}**, is missing from the extracted record.")
                if row.get("program"):
                    lines.append(f"- Program: {row['program']}")
                if row.get("faculty_department"):
                    lines.append(f"- Department: {row['faculty_department']}")
                if row.get("course_coordinators"):
                    lines.append(f"- Course coordinator: {row['course_coordinators']}")
                if row.get("pdf_url"):
                    lines.append(f"- [Source course plan]({row['pdf_url']})")
                lines.append("")
            lines.append("Teaching assignments are specific to the session shown above.")
            return "\n".join(lines)

        if category == "course_plan" and results[0].chunk.collection == "course_plans":
            row = results[0].chunk.metadata
            lines = [
                "Based on the closest NIT Trichy course-plan record:",
                f"- Course: {row.get('course_code')} - {row.get('course_name')}",
                f"- Program: {row.get('program')}",
                f"- Department: {row.get('department')}",
                f"- Semester/session: {row.get('semester')} / {row.get('session')}",
            ]
            if row.get("credits"):
                lines.append(f"- Credits: {row.get('credits')}")
            if row.get("faculty"):
                lines.append(f"- Faculty: {row.get('faculty')}")
            if row.get("syllabus"):
                lines.append(f"- Syllabus: {str(row.get('syllabus'))[:700]}")
            if row.get("course_objectives"):
                lines.append(f"- Objectives: {str(row.get('course_objectives'))[:700]}")
            if row.get("assessment_structure"):
                lines.append(f"- Assessment structure: {row.get('assessment_structure')}")
            elif row.get("assessment_methods"):
                lines.append(f"- Assessment methods: {str(row.get('assessment_methods'))[:700]}")
            if row.get("pdf_url"):
                lines.append(f"- Source PDF: {row.get('pdf_url')}")
            return "\n".join(line for line in lines if line and "None" not in line)

        intro = {
            "course_plan": "Based on the retrieved NIT Trichy course-plan records:",
            "fees": "Based on the retrieved NIT Trichy fee documents:",
            "curriculum": "Based on the retrieved NIT Trichy curriculum and syllabus documents:",
            "admissions": "Based on the retrieved NIT Trichy admission-related documents:",
            "department": "Based on the retrieved NIT Trichy department information:",
            "academics": "Based on the retrieved NIT Trichy academic documents:",
        }.get(category, "Based on the retrieved NIT Trichy documents:")

        bullets = "\n".join(f"- {sentence}" for sentence in summary_sentences[:5])
        if not bullets:
            bullets = f"- {results[0].chunk.text[:600]}"

        return f"{intro}\n{bullets}"
