from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    source_url: str
    title: str
    collection: str
    metadata: dict[str, Any]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def compact_course_text(row: dict[str, Any]) -> str:
    fields = [
        ("Program", row.get("program")),
        ("Department", row.get("department")),
        ("Semester", row.get("semester")),
        ("Session", row.get("session")),
        ("Course Code", row.get("course_code")),
        ("Course Name", row.get("course_name")),
        ("Credits", row.get("credits")),
        ("Faculty", row.get("faculty")),
        ("Faculty Department", row.get("faculty_department")),
        ("Course Coordinators", row.get("course_coordinators")),
        ("PDF URL", row.get("pdf_url")),
        ("Syllabus", row.get("syllabus")),
        ("Course Objectives", row.get("course_objectives")),
        ("Course Outcomes", row.get("course_outcomes")),
        ("Course Overview", row.get("course_overview")),
        ("Teaching Learning Activities", row.get("teaching_learning_activities")),
        ("Assessment Methods", row.get("assessment_methods")),
        ("Assessment Structure", row.get("assessment_structure")),
        ("Attendance Policy", row.get("attendance_policy")),
        ("Course Policy", row.get("course_policy")),
    ]
    parts = []
    for label, value in fields:
        if value:
            parts.append(f"{label}: {value}")
    raw = row.get("raw_ocr_text")
    if raw:
        parts.append(f"Raw Extracted Text: {raw[:3000]}")
    return " | ".join(parts)


def load_chunks(data_dir: Path = DATA_DIR) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []

    academic_path = data_dir / "nit_trichy_chunks.jsonl"
    for row in read_jsonl(academic_path):
        text = row.get("text", "")
        if not text:
            continue
        chunks.append(
            DocumentChunk(
                chunk_id=row.get("chunk_id", f"academic_{len(chunks)}"),
                text=text,
                source_url=row.get("source_url", ""),
                title=row.get("title", "NIT Trichy academic document"),
                collection="nitt_website",
                metadata=row,
            )
        )

    course_details_path = data_dir / "nit_trichy_cp_course_details.json"
    if course_details_path.exists():
        for row in load_course_details(data_dir):
            text = compact_course_text(row)
            if not text:
                continue
            course_code = row.get("course_code") or "course"
            course_name = row.get("course_name") or "NIT Trichy course"
            title = f"{course_code} - {course_name}"
            chunks.append(
                DocumentChunk(
                    chunk_id=f"cp_course_detail_{row.get('id')}",
                    text=text,
                    source_url=row.get("pdf_url") or "https://cp.nitt.edu/fetch_all_courses_bystudent.php",
                    title=title,
                    collection="course_plans",
                    metadata=row,
                )
            )
    else:
        course_path = data_dir / "nit_trichy_cp_course_detail_chunks.jsonl"
        for row in read_jsonl(course_path):
            text = row.get("text", "")
            if not text:
                continue
            course_code = row.get("course_code") or "course"
            course_name = row.get("course_name") or "NIT Trichy course"
            title = f"{course_code} - {course_name}"
            chunks.append(
                DocumentChunk(
                    chunk_id=row.get("chunk_id", f"course_{len(chunks)}"),
                    text=text,
                    source_url=row.get("source_url", ""),
                    title=title,
                    collection="course_plans",
                    metadata=row,
                )
            )

    return chunks


def load_course_details(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    path = data_dir / "nit_trichy_cp_course_details.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
