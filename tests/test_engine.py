from __future__ import annotations

from nitt_rag.engine import NITTAssistant
from nitt_rag.entities import extract_entities
from nitt_rag.data import DocumentChunk
from nitt_rag.retrieval import SearchResult
import pytest


@pytest.fixture(scope="module")
def assistant() -> NITTAssistant:
    return NITTAssistant()


def test_entity_extraction_course_code() -> None:
    entities = extract_entities("Show AR507 and CSIR11B for July2026")
    assert "AR507" in entities["course_codes"]
    assert "CSIR11B" in entities["course_codes"]
    assert entities["sessions"]


def test_assistant_returns_answer(assistant: NITTAssistant) -> None:
    response = assistant.ask("What is the course plan for AR507?", top_k=3)
    assert response.results
    assert response.answer
    assert response.category == "course_plan"


@pytest.mark.parametrize("question", [
    "who is teaching natural language processing course?",
    "Who teaches CA6D3?",
    "Who is the faculty for Natural Language Processing?",
])
def test_nlp_faculty_answer(assistant: NITTAssistant, question: str) -> None:
    response = assistant.ask(question, top_k=6)
    assert "**Dr. S. Sangeetha** is listed as the faculty" in response.answer
    assert "Course coordinator: Dr. Ashwinth J" in response.answer
    assert "Jan2026" in response.answer
    assert "CA6D3" in response.answer
    assert "Syllabus:" not in response.answer
    assert response.sources[0]["url"].endswith("/CA6D3_Jan2026.pdf")
    assert all(r.chunk.metadata["course_code"] == "CA6D3" for r in response.results)


def test_unknown_course_does_not_borrow_a_teacher(assistant: NITTAssistant) -> None:
    response = assistant.ask("Who teaches Quantum Dragon Linguistics?", top_k=6)
    assert not response.results
    assert "could not find" in response.answer


def test_missing_faculty_does_not_use_coordinator() -> None:
    chunk = DocumentChunk("test", "Test course", "https://example.org/plan.pdf", "Test Course",
                          "course_plans", {"course_code": "TEST101", "course_name": "Test Course",
                                           "session": "Jan2026", "course_coordinators": "Dr. Coordinator"})
    result = SearchResult(1, 1, 1, chunk)
    answer = NITTAssistant.compose_answer("Who teaches TEST101?", "course_plan", [], [result])
    assert "missing from the extracted record" in answer
    assert "Course coordinator: Dr. Coordinator" in answer
    assert "is listed as the faculty" not in answer
