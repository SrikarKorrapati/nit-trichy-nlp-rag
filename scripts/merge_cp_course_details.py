from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data"

COURSES_PATH = OUTPUT_DIR / "nit_trichy_cp_courses.json"
FINAL_JSON = OUTPUT_DIR / "nit_trichy_cp_course_details.json"
FINAL_JSONL = OUTPUT_DIR / "nit_trichy_cp_course_details.jsonl"
FINAL_CSV = OUTPUT_DIR / "nit_trichy_cp_course_details.csv"
FINAL_CHUNKS = OUTPUT_DIR / "nit_trichy_cp_course_detail_chunks.jsonl"
FINAL_SUMMARY = OUTPUT_DIR / "nit_trichy_cp_course_details_summary.md"


CSV_FIELDS = [
    "id",
    "program",
    "department",
    "semester",
    "session",
    "course_code",
    "course_name",
    "uploaded_by",
    "uploaded_on",
    "pdf_url",
    "pdf_page_count",
    "pages_extracted",
    "extraction_method",
    "programme_and_specialization",
    "course_title_pdf",
    "course_code_pdf",
    "credits",
    "prerequisites",
    "section",
    "faculty",
    "emails",
    "phone_numbers",
    "course_coordinators",
    "course_type_pdf",
    "syllabus",
    "course_objectives",
    "course_outcomes",
    "course_overview",
    "teaching_learning_activities",
    "assessment_methods",
    "assessment_structure",
    "exit_survey",
    "attendance_policy",
    "course_policy",
    "compensation_assessment_policy",
    "academic_dishonesty_policy",
    "additional_information",
    "error",
]


TEXT_SECTION_FIELDS = [
    "syllabus",
    "course_objectives",
    "course_outcomes",
    "course_overview",
    "teaching_learning_activities",
    "assessment_methods",
    "exit_survey",
    "attendance_policy",
    "course_policy",
    "compensation_assessment_policy",
    "academic_dishonesty_policy",
    "additional_information",
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def clean_section_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned_lines = []
    for line in str(text).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "NATIONAL INSTITUTE OF TECHNOLOGY" in stripped.upper():
            continue
        if re_match_page_footer(stripped):
            continue
        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines).strip()


def re_match_page_footer(line: str) -> bool:
    normalized = (
        line.replace(" ", "")
        .replace("è", "e")
        .replace("é", "e")
        .replace("È", "e")
        .lower()
    )
    if normalized.startswith("page") and ("of" in normalized or "f" in normalized):
        return True
    return False


def sanitize_row(row: dict) -> dict:
    row = dict(row)
    for field in TEXT_SECTION_FIELDS:
        row[field] = clean_section_text(row.get(field))

    assessment_raw = row.get("assessment_structure_json")
    if assessment_raw:
        try:
            parsed = json.loads(assessment_raw)
            row["assessment_structure"] = parsed.get("assessments", parsed)
        except (TypeError, json.JSONDecodeError):
            row["assessment_structure"] = assessment_raw
    else:
        row["assessment_structure"] = ""

    raw_text = (row.get("raw_ocr_text") or "").lower()
    if "core course" in raw_text and "elective course" in raw_text:
        # Vision OCR does not reliably preserve checkbox state, so avoid a false label.
        row["course_type_pdf"] = "Unknown - checkbox not OCR-readable"

    return row


def row_text(row: dict) -> str:
    parts = [
        f"Program: {row.get('program')}",
        f"Department: {row.get('department')}",
        f"Semester: {row.get('semester')}",
        f"Session: {row.get('session')}",
        f"Course Code: {row.get('course_code')}",
        f"Course Name: {row.get('course_name')}",
        f"Credits: {row.get('credits')}",
        f"Faculty: {row.get('faculty')}",
        f"Course Type: {row.get('course_type_pdf')}",
        f"Syllabus: {row.get('syllabus')}",
        f"Course Objectives: {row.get('course_objectives')}",
        f"Course Outcomes: {row.get('course_outcomes')}",
        f"Course Overview: {row.get('course_overview')}",
        f"Assessment Methods: {row.get('assessment_methods')}",
        f"Assessment Structure: {row.get('assessment_structure')}",
        f"Raw OCR Text: {row.get('raw_ocr_text')}",
    ]
    return " | ".join(str(part) for part in parts if part and not part.endswith(": None"))


def main() -> None:
    course_rows = json.loads(COURSES_PATH.read_text(encoding="utf-8"))
    course_order = {str(row.get("id")): index for index, row in enumerate(course_rows)}

    details_by_id: dict[str, dict] = {}
    duplicate_ids: list[str] = []
    for shard_index in range(4):
        shard_path = OUTPUT_DIR / f"nit_trichy_cp_course_details_shard{shard_index}.jsonl"
        for row in load_jsonl(shard_path):
            row_id = str(row.get("id"))
            if row_id in details_by_id:
                duplicate_ids.append(row_id)
            details_by_id[row_id] = row

    rows = sorted(
        (sanitize_row(row) for row in details_by_id.values()),
        key=lambda row: course_order.get(str(row.get("id")), 10**9),
    )
    missing_ids = [str(row.get("id")) for row in course_rows if str(row.get("id")) not in details_by_id]
    error_rows = [row for row in rows if row.get("error")]

    FINAL_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with FINAL_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with FINAL_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["emails"] = "; ".join(row.get("emails") or [])
            csv_row["phone_numbers"] = "; ".join(row.get("phone_numbers") or [])
            if isinstance(row.get("assessment_structure"), (list, dict)):
                csv_row["assessment_structure"] = json.dumps(row.get("assessment_structure"), ensure_ascii=False)
            writer.writerow(csv_row)

    with FINAL_CHUNKS.open("w", encoding="utf-8") as f:
        for row in rows:
            chunk = {
                "chunk_id": f"cp_course_detail_{row.get('id')}",
                "source": "cp.nitt.edu",
                "source_url": row.get("pdf_url") or "https://cp.nitt.edu/fetch_all_courses_bystudent.php",
                "program": row.get("program"),
                "department": row.get("department"),
                "semester": row.get("semester"),
                "session": row.get("session"),
                "course_code": row.get("course_code"),
                "course_name": row.get("course_name"),
                "text": row_text(row),
            }
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    with FINAL_SUMMARY.open("w", encoding="utf-8") as f:
        f.write("# NIT Trichy Course Plan Detail Extraction Summary\n\n")
        f.write(f"- Expected course rows: {len(course_rows)}\n")
        f.write(f"- Merged detail rows: {len(rows)}\n")
        f.write(f"- Missing rows: {len(missing_ids)}\n")
        f.write(f"- Duplicate row ids seen while merging: {len(duplicate_ids)}\n")
        f.write(f"- Rows with errors: {len(error_rows)}\n")
        f.write(f"- Rows with PDF URLs: {sum(bool(row.get('pdf_url')) for row in rows)}\n")
        f.write(f"- Rows extracted with Apple Vision OCR: {sum(row.get('extraction_method') == 'apple_vision_ocr' for row in rows)}\n")
        f.write(f"- Rows with syllabus section: {sum(bool(row.get('syllabus')) for row in rows)}\n")
        f.write(f"- Rows with course objectives: {sum(bool(row.get('course_objectives')) for row in rows)}\n")
        if missing_ids:
            f.write("\n## Missing IDs\n\n")
            f.write(", ".join(missing_ids[:100]))
            if len(missing_ids) > 100:
                f.write(f"\n... {len(missing_ids) - 100} more")
        if error_rows:
            f.write("\n\n## Sample Errors\n\n")
            for row in error_rows[:20]:
                f.write(f"- {row.get('id')} {row.get('course_code')}: {row.get('error')}\n")

    print(f"Merged {len(rows)} rows")
    print(f"Missing {len(missing_ids)} rows")
    print(f"Errors {len(error_rows)} rows")
    print(f"Saved {FINAL_JSON}")
    print(f"Saved {FINAL_CSV}")
    print(f"Saved {FINAL_CHUNKS}")


if __name__ == "__main__":
    main()
