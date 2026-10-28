from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data"

COURSES_ENDPOINT = "https://cp.nitt.edu/fetch_all_courses_bystudent.php"
BASE_URL = "https://cp.nitt.edu/"

HEADERS = {
    "User-Agent": "NIT-Trichy-NLP-Student-Project/1.0 (+course-plan scrape; public endpoint)"
}


def fetch_courses() -> list[dict]:
    response = requests.get(COURSES_ENDPOINT, headers=HEADERS, timeout=60)
    response.raise_for_status()

    # The endpoint currently emits a UTF-8 BOM, so utf-8-sig is intentional.
    payload = json.loads(response.content.decode("utf-8-sig"))
    if not payload.get("ok"):
        raise RuntimeError(f"Course endpoint returned ok={payload.get('ok')}")

    rows = payload.get("rows", [])
    for row in rows:
        file_path = row.get("file_path") or ""
        row["pdf_url"] = urljoin(BASE_URL, file_path) if file_path else ""
    return rows


def row_to_text(row: dict) -> str:
    parts = [
        f"Program: {row.get('program')}",
        f"Department: {row.get('department')}",
        f"Semester: {row.get('semester')}",
        f"Session: {row.get('session')}",
        f"Course Code: {row.get('course_code')}",
        f"Course Name: {row.get('course_name')}",
        f"Uploaded By: {row.get('uploaded_by')}",
        f"Uploaded On: {row.get('uploaded_on')}",
    ]

    assessment = row.get("assessment_structure")
    if assessment:
        parts.append(f"Assessment Structure: {assessment}")

    if row.get("pdf_url"):
        parts.append(f"Course Plan PDF: {row['pdf_url']}")

    return " | ".join(str(part) for part in parts if part)


def write_outputs(rows: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "nit_trichy_cp_courses.json"
    csv_path = OUTPUT_DIR / "nit_trichy_cp_courses.csv"
    chunks_path = OUTPUT_DIR / "nit_trichy_cp_course_chunks.jsonl"
    summary_path = OUTPUT_DIR / "nit_trichy_cp_courses_summary.md"

    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "id",
        "program",
        "department",
        "semester",
        "session",
        "course_code",
        "course_name",
        "uploaded_by",
        "uploaded_on",
        "file_path",
        "pdf_url",
        "assessment_structure",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    with chunks_path.open("w", encoding="utf-8") as f:
        for row in rows:
            chunk = {
                "chunk_id": f"cp_course_{row.get('id') or row.get('course_code')}",
                "source": "cp.nitt.edu",
                "source_url": COURSES_ENDPOINT,
                "pdf_url": row.get("pdf_url", ""),
                "program": row.get("program"),
                "department": row.get("department"),
                "semester": row.get("semester"),
                "session": row.get("session"),
                "course_code": row.get("course_code"),
                "course_name": row.get("course_name"),
                "text": row_to_text(row),
            }
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    program_counts = Counter(row.get("program") or "Unknown" for row in rows)
    department_counts = Counter(row.get("department") or "Unknown" for row in rows)
    session_counts = Counter(row.get("session") or "Unknown" for row in rows)
    pdf_count = sum(1 for row in rows if row.get("pdf_url"))

    lines = [
        "# NIT Trichy Course Plan Scrape Summary",
        "",
        f"- Endpoint: `{COURSES_ENDPOINT}`",
        f"- Total course rows: {len(rows)}",
        f"- Rows with course-plan PDF URL: {pdf_count}",
        "",
        "## Programs",
        "",
    ]
    for program, count in program_counts.most_common():
        lines.append(f"- {program}: {count}")

    lines.extend(["", "## Sessions", ""])
    for session, count in session_counts.most_common():
        lines.append(f"- {session}: {count}")

    lines.extend(["", "## Top Departments", ""])
    for department, count in department_counts.most_common(30):
        lines.append(f"- {department}: {count}")

    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved {len(rows)} rows to {json_path}")
    print(f"Saved CSV to {csv_path}")
    print(f"Saved RAG chunks to {chunks_path}")
    print(f"Saved summary to {summary_path}")


def main() -> None:
    rows = fetch_courses()
    write_outputs(rows)


if __name__ == "__main__":
    main()
