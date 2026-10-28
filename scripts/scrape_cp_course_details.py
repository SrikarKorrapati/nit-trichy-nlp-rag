from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import objc
import requests
from Foundation import NSBundle
from PyPDF2 import PdfReader

import Quartz


ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / "work"
OUTPUT_DIR = ROOT / "data"
COURSES_PATH = OUTPUT_DIR / "nit_trichy_cp_courses.json"
PDF_CACHE_DIR = WORK_DIR / "cp_course_pdfs"

DEFAULT_DETAILS_JSONL = OUTPUT_DIR / "nit_trichy_cp_course_details.jsonl"
DEFAULT_DETAILS_CSV = OUTPUT_DIR / "nit_trichy_cp_course_details.csv"
DEFAULT_DETAILS_SUMMARY = OUTPUT_DIR / "nit_trichy_cp_course_details_summary.md"

HEADERS = {
    "User-Agent": "NIT-Trichy-NLP-Student-Project/1.0 (+course-plan PDF OCR; public files)"
}


def load_vision() -> tuple[object, object]:
    NSBundle.bundleWithPath_("/System/Library/Frameworks/Vision.framework").load()
    return objc.lookUpClass("VNRecognizeTextRequest"), objc.lookUpClass("VNImageRequestHandler")


VNRecognizeTextRequest, VNImageRequestHandler = load_vision()


SECTION_HEADINGS = [
    "Syllabus",
    "COURSE OBJECTIVES",
    "MAPPING OF COS with POS",
    "Course Outcomes",
    "COURSE OVERVIEW",
    "COURSE TEACHING AND LEARNING ACTIVITIES",
    "COURSE ASSESSMENT METHODS",
    "COURSE EXIT SURVEY",
    "ATTENDANCE POLICY",
    "COURSE POLICY",
    "COMPENSATION ASSESSMENT POLICY",
    "ACADEMIC DISHONESTY & PLAGIARISM",
    "ADDITIONAL INFORMATION",
    "FOR APPROVAL",
]


def safe_filename(row: dict) -> str:
    raw = f"{row.get('id')}_{row.get('course_code')}_{row.get('session')}.pdf"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)


def download_pdf(row: dict) -> Path | None:
    pdf_url = row.get("pdf_url")
    if not pdf_url:
        return None

    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = PDF_CACHE_DIR / safe_filename(row)
    if path.exists() and path.stat().st_size > 0:
        return path

    response = requests.get(pdf_url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    return path


def extract_text_layer(pdf_path: Path) -> list[str]:
    try:
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return pages
    except Exception:
        return []


def page_to_image(doc, page_number: int, scale: float = 2.6):
    page = Quartz.CGPDFDocumentGetPage(doc, page_number)
    box = Quartz.CGPDFPageGetBoxRect(page, Quartz.kCGPDFMediaBox)
    width, height = int(box.size.width * scale), int(box.size.height * scale)
    color_space = Quartz.CGColorSpaceCreateDeviceRGB()
    ctx = Quartz.CGBitmapContextCreate(
        None,
        width,
        height,
        8,
        0,
        color_space,
        Quartz.kCGImageAlphaPremultipliedLast,
    )
    Quartz.CGContextSetRGBFillColor(ctx, 1, 1, 1, 1)
    Quartz.CGContextFillRect(ctx, Quartz.CGRectMake(0, 0, width, height))
    Quartz.CGContextScaleCTM(ctx, scale, scale)
    Quartz.CGContextDrawPDFPage(ctx, page)
    return Quartz.CGBitmapContextCreateImage(ctx)


def ocr_pdf(pdf_path: Path, max_pages: int = 8) -> tuple[list[str], int]:
    pdf_path_str = str(pdf_path)
    url = Quartz.CFURLCreateFromFileSystemRepresentation(
        None, pdf_path_str.encode(), len(pdf_path_str), False
    )
    doc = Quartz.CGPDFDocumentCreateWithURL(url)
    if not doc:
        return [], 0

    page_count = Quartz.CGPDFDocumentGetNumberOfPages(doc)
    pages_to_read = min(page_count, max_pages)
    pages: list[str] = []

    for page_number in range(1, pages_to_read + 1):
        image = page_to_image(doc, page_number)
        request = VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(1)
        request.setUsesLanguageCorrection_(True)
        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(image, {})
        handler.performRequests_error_([request], None)

        lines = []
        for observation in request.results() or []:
            candidates = observation.topCandidates_(1)
            if candidates:
                lines.append(str(candidates[0].string()))
        pages.append("\n".join(lines))

    return pages, page_count


def clean_text(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def lines_from_text(text: str) -> list[str]:
    return [clean_text(line) for line in text.splitlines() if clean_text(line)]


def find_value_after(lines: list[str], labels: list[str], stop_labels: list[str] | None = None) -> str:
    stop_labels = stop_labels or []
    normalized_labels = [label.lower() for label in labels]
    normalized_stops = [label.lower() for label in stop_labels]
    for index, line in enumerate(lines):
        lower = line.lower()
        if any(label in lower for label in normalized_labels):
            values = []
            for candidate in lines[index + 1 : index + 5]:
                c_lower = candidate.lower()
                if any(stop in c_lower for stop in normalized_stops):
                    break
                if len(candidate) <= 2 and not candidate.isdigit():
                    continue
                values.append(candidate)
            return " ".join(values).strip()
    return ""


def extract_between(text: str, start_patterns: list[str], end_patterns: list[str]) -> str:
    lower = text.lower()
    start_index = -1
    start_len = 0
    for pattern in start_patterns:
        match = re.search(re.escape(pattern.lower()), lower)
        if match and (start_index == -1 or match.start() < start_index):
            start_index = match.start()
            start_len = len(pattern)
    if start_index == -1:
        return ""

    content_start = start_index + start_len
    end_index = len(text)
    for pattern in end_patterns:
        match = re.search(re.escape(pattern.lower()), lower[content_start:])
        if match:
            end_index = min(end_index, content_start + match.start())
    return clean_text(text[content_start:end_index])


def extract_emails(text: str) -> list[str]:
    emails = re.findall(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    cleaned = []
    for email in emails:
        cleaned.append(re.sub(r"\s+", "", email).lower())
    return sorted(set(cleaned))


def extract_phones(text: str) -> list[str]:
    phones = re.findall(r"(?:\+?\d[\d\s-]{7,}\d)", text)
    return sorted(set(re.sub(r"\s+", "", phone) for phone in phones))


def infer_course_type(text: str) -> str:
    lower = text.lower()
    if "core course" in lower and "elective course" in lower:
        core_index = lower.find("core course")
        elective_index = lower.find("elective course")
        window = lower[max(0, core_index - 30) : elective_index + 30]
        if "☑" in window or "✓" in window or "core course" in window:
            return "Core course"
    if "elective course" in lower:
        return "Elective course"
    if "core course" in lower:
        return "Core course"
    return ""


def parse_details(row: dict, pages: list[str], page_count: int, extraction_method: str) -> dict:
    full_text = clean_text("\n\n".join(pages))
    lines = lines_from_text(full_text)

    end_for_syllabus = [heading for heading in SECTION_HEADINGS if heading != "Syllabus"]
    course_objective_end = [heading for heading in SECTION_HEADINGS if heading != "COURSE OBJECTIVES"]

    return {
        "id": row.get("id"),
        "program": row.get("program"),
        "department": row.get("department"),
        "semester": row.get("semester"),
        "session": row.get("session"),
        "course_code": row.get("course_code"),
        "course_name": row.get("course_name"),
        "uploaded_by": row.get("uploaded_by"),
        "uploaded_on": row.get("uploaded_on"),
        "pdf_url": row.get("pdf_url", ""),
        "assessment_structure_json": row.get("assessment_structure"),
        "pdf_page_count": page_count,
        "pages_extracted": len(pages),
        "extraction_method": extraction_method,
        "programme_and_specialization": find_value_after(
            lines,
            ["programme and", "program and", "specialization"],
            ["Course Title"],
        ),
        "course_title_pdf": find_value_after(lines, ["Course Title"], ["Course Code"]),
        "course_code_pdf": find_value_after(lines, ["Course Code"], ["No. of", "Course Code of Pre"]),
        "credits": find_value_after(lines, ["No. of Credits", "No. of Credlts"], ["Course Code of Pre", "Session"]),
        "prerequisites": find_value_after(lines, ["Pre-requisite", "requisite subject"], ["Session"]),
        "section": find_value_after(lines, ["Section"], ["Name of Faculty"]),
        "faculty": find_value_after(lines, ["Name of Faculty"], ["Department", "Email", "Emall"]),
        "emails": extract_emails(full_text),
        "phone_numbers": extract_phones(full_text),
        "course_coordinators": find_value_after(lines, ["Name of Course Coordinator"], ["E-mail", "Telephone"]),
        "course_type_pdf": infer_course_type(full_text),
        "syllabus": extract_between(full_text, ["Syllabus (approved in Bos)", "Syllabus"], end_for_syllabus),
        "course_objectives": extract_between(full_text, ["COURSE OBJECTIVES"], course_objective_end),
        "course_outcomes": extract_between(full_text, ["Course Outcomes"], ["COURSE OVERVIEW", "COURSE TEACHING"]),
        "course_overview": extract_between(full_text, ["COURSE OVERVIEW"], ["COURSE TEACHING AND LEARNING ACTIVITIES", "COURSE ASSESSMENT METHODS"]),
        "teaching_learning_activities": extract_between(full_text, ["COURSE TEACHING AND LEARNING ACTIVITIES"], ["COURSE ASSESSMENT METHODS"]),
        "assessment_methods": extract_between(full_text, ["COURSE ASSESSMENT METHODS"], ["COURSE EXIT SURVEY", "ATTENDANCE POLICY"]),
        "exit_survey": extract_between(full_text, ["COURSE EXIT SURVEY"], ["ATTENDANCE POLICY"]),
        "attendance_policy": extract_between(full_text, ["ATTENDANCE POLICY", "ArrENDANCE POLICY"], ["COURSE POLICY"]),
        "course_policy": extract_between(full_text, ["COURSE POLICY"], ["COMPENSATION ASSESSMENT POLICY"]),
        "compensation_assessment_policy": extract_between(full_text, ["COMPENSATION ASSESSMENT POLICY"], ["ACADEMIC DISHONESTY"]),
        "academic_dishonesty_policy": extract_between(full_text, ["ACADEMIC DISHONESTY & PLAGIARISM"], ["ADDITIONAL INFORMATION", "FOR APPROVAL"]),
        "additional_information": extract_between(full_text, ["ADDITIONAL INFORMATION"], ["FOR APPROVAL"]),
        "raw_ocr_text": full_text,
    }


def loaded_ids(details_jsonl: Path) -> set[str]:
    if not details_jsonl.exists():
        return set()
    ids = set()
    with details_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    ids.add(str(json.loads(line).get("id")))
                except json.JSONDecodeError:
                    pass
    return ids


def process_row(row: dict, max_pages: int) -> dict:
    if not row.get("pdf_url"):
        return parse_details(row, [], 0, "no_pdf")

    pdf_path = download_pdf(row)
    if not pdf_path:
        return parse_details(row, [], 0, "no_pdf")

    text_pages = extract_text_layer(pdf_path)
    joined_text = "\n".join(text_pages)
    if len(joined_text.strip()) > 200:
        page_count = len(text_pages)
        return parse_details(row, text_pages[:max_pages], page_count, "pdf_text")

    ocr_pages, page_count = ocr_pdf(pdf_path, max_pages=max_pages)
    return parse_details(row, ocr_pages, page_count, "apple_vision_ocr")


def rebuild_csv_and_summary(details_jsonl: Path, details_csv: Path, details_summary: Path) -> None:
    rows = []
    if details_jsonl.exists():
        with details_jsonl.open("r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]

    fieldnames = [
        "id",
        "program",
        "department",
        "semester",
        "session",
        "course_code",
        "course_name",
        "pdf_url",
        "pdf_page_count",
        "pages_extracted",
        "extraction_method",
        "course_title_pdf",
        "credits",
        "prerequisites",
        "faculty",
        "emails",
        "phone_numbers",
        "course_type_pdf",
        "syllabus",
        "course_objectives",
        "course_outcomes",
        "course_overview",
        "assessment_methods",
        "attendance_policy",
        "course_policy",
    ]

    with details_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["emails"] = "; ".join(row.get("emails") or [])
            csv_row["phone_numbers"] = "; ".join(row.get("phone_numbers") or [])
            writer.writerow(csv_row)

    with details_summary.open("w", encoding="utf-8") as f:
        with_pdf = sum(bool(row.get("pdf_url")) for row in rows)
        with_syllabus = sum(bool(row.get("syllabus")) for row in rows)
        with_objectives = sum(bool(row.get("course_objectives")) for row in rows)
        f.write("# NIT Trichy Course Plan Detail Extraction Summary\n\n")
        f.write(f"- Course rows processed: {len(rows)}\n")
        f.write(f"- Rows with PDF URL: {with_pdf}\n")
        f.write(f"- Rows with extracted syllabus section: {with_syllabus}\n")
        f.write(f"- Rows with extracted course objectives section: {with_objectives}\n")
        f.write(f"- JSONL output: `{details_jsonl}`\n")
        f.write(f"- CSV output: `{details_csv}`\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and OCR NIT Trichy course-plan PDFs.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N unprocessed rows.")
    parser.add_argument("--max-pages", type=int, default=8, help="Maximum pages to extract per PDF.")
    parser.add_argument("--fresh", action="store_true", help="Start a fresh details JSONL file.")
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of shards.")
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based shard index.")
    parser.add_argument(
        "--output-prefix",
        default=str(OUTPUT_DIR / "nit_trichy_cp_course_details"),
        help="Output prefix without extension. JSONL, CSV, and summary files are derived from it.",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = json.loads(COURSES_PATH.read_text(encoding="utf-8"))
    if args.shard_count < 1:
        raise ValueError("--shard-count must be >= 1")
    if not (0 <= args.shard_index < args.shard_count):
        raise ValueError("--shard-index must be between 0 and shard-count - 1")
    rows = [row for index, row in enumerate(rows) if index % args.shard_count == args.shard_index]

    output_prefix = Path(args.output_prefix)
    details_jsonl = output_prefix.with_suffix(".jsonl")
    details_csv = output_prefix.with_suffix(".csv")
    details_summary = output_prefix.with_name(output_prefix.name + "_summary.md")

    if args.fresh and details_jsonl.exists():
        details_jsonl.unlink()

    done = loaded_ids(details_jsonl)
    processed = 0
    with details_jsonl.open("a", encoding="utf-8") as out:
        for row in rows:
            row_id = str(row.get("id"))
            if row_id in done:
                continue
            if args.limit is not None and processed >= args.limit:
                break

            processed += 1
            print(
                f"[{processed}] {row.get('program')} | {row.get('department')} | "
                f"{row.get('course_code')} | {row.get('course_name')}",
                flush=True,
            )
            try:
                detail = process_row(row, max_pages=args.max_pages)
            except Exception as exc:
                detail = {
                    **{key: row.get(key) for key in row},
                    "error": f"{type(exc).__name__}: {exc}",
                    "raw_ocr_text": "",
                }
            out.write(json.dumps(detail, ensure_ascii=False) + "\n")
            out.flush()
            time.sleep(0.1)

    rebuild_csv_and_summary(details_jsonl, details_csv, details_summary)
    print(f"Processed {processed} new rows")
    print(f"Saved details to {details_jsonl}")
    print(f"Saved CSV to {details_csv}")


if __name__ == "__main__":
    main()
