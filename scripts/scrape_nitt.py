from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.parse import urlunparse

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data"

SEED_URLS = [
    "https://www.nitt.edu/home/academics/programmes/",
    "https://www.nitt.edu/home/academics/curriculum/",
    "https://www.nitt.edu/home/academics/fees_section/",
    "https://www.nitt.edu/home/academics/fees_section/ug_courses_fee_structure/",
    "https://www.nitt.edu/home/academics/fees_section/pg_courses_fee_structure/",
    "https://www.nitt.edu/home/academics/fees_section/ms_phd_fee_structure/",
]

KEYWORDS = (
    "academics",
    "curriculum",
    "syllabus",
    "programme",
    "programmes",
    "fees",
    "fee",
    "calendar",
    "schedule",
    "notices",
)

EXCLUDED_URL_TERMS = (
    "opening",
    "closing",
    "rank",
    "jossa",
    "josaa",
    "csab",
    "dasa",
    "iccr",
    "sii",
    "undertaking",
    "medical",
    "disability",
    "orcr",
    "air-",
    "quick_start",
)

OLD_PDF_YEAR_TERMS = (
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
)

HEADERS = {
    "User-Agent": "NIT-Trichy-NLP-Student-Project/1.0 (+academic project; public pages only)"
}


@dataclass
class SourceDocument:
    source_id: str
    source_url: str
    title: str
    content_type: str
    text: str
    discovered_links: list[str]


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def is_nitt_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return parsed.scheme in {"http", "https"} and (host == "nitt.edu" or host.endswith(".nitt.edu"))


def is_relevant_url(url: str) -> bool:
    if "/+" in urlparse(url).path:
        return False
    lowered = url.lower()
    if any(term in lowered for term in EXCLUDED_URL_TERMS):
        return False
    if lowered.endswith(".pdf") and any(year in lowered for year in OLD_PDF_YEAR_TERMS):
        return False
    return any(keyword in lowered for keyword in KEYWORDS) or lowered.endswith(".pdf")


def normalize_url(url: str) -> str:
    url, _fragment = urldefrag(url)
    parsed = urlparse(url)
    host = parsed.hostname or ""
    netloc = host
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{host}:{parsed.port}"
    scheme = "https" if host.endswith("nitt.edu") else parsed.scheme
    return urlunparse((scheme, netloc, parsed.path, "", parsed.query, ""))


def fetch(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response


def link_priority(url: str) -> tuple[int, int, int, int]:
    lowered = url.lower()
    is_pdf = int(lowered.endswith(".pdf"))
    is_curriculum = int(any(term in lowered for term in ("curriculum", "syllabus")))
    is_current = int(any(year in lowered for year in ("2026", "2025", "2024")))
    is_ug_or_cse = int(any(term in lowered for term in ("b.tech", "btech", "cse", "computer")))
    is_high_value = int(any(term in lowered for term in ("fee", "fees", "curriculum", "syllabus", "b.tech", "btech", "cse")))
    is_broad_department_page = int("/departments/" in lowered and not is_pdf)
    return (is_pdf, is_curriculum, is_current, is_ug_or_cse, is_high_value, -is_broad_department_page)


def parse_html(url: str, html: str) -> tuple[str, str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = clean_text(title_tag.get_text(" ", strip=True)) if title_tag else url
    text = clean_text(soup.get_text(" ", strip=True))

    links = []
    for anchor in soup.find_all("a", href=True):
        linked_url = normalize_url(urljoin(url, anchor["href"]))
        if is_nitt_url(linked_url) and is_relevant_url(linked_url):
            links.append(linked_url)

    return title, text, sorted(set(links), key=link_priority, reverse=True)


def parse_pdf(url: str, content: bytes, max_pages: int = 8) -> tuple[str, str]:
    reader = PdfReader(BytesIO(content))
    pages = []
    for page in list(reader.pages)[:max_pages]:
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        except Exception as exc:
            pages.append(f"[PDF page extraction skipped: {exc}]")

    filename = Path(urlparse(url).path).name
    return filename or url, clean_text("\n".join(pages))


def chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 35) -> Iterable[str]:
    words = text.split()
    if not words:
        return

    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        chunk = words[start : start + chunk_words]
        if len(chunk) < 25 and start != 0:
            break
        yield " ".join(chunk)


def scrape(max_pages: int = 70, delay_seconds: float = 0.7) -> list[SourceDocument]:
    session = requests.Session()
    seed_queue = deque(normalize_url(url) for url in SEED_URLS)
    discovery_queue: deque[str] = deque()
    enqueued = set(seed_queue)
    seen: set[str] = set()
    documents: list[SourceDocument] = []
    sorted_initial_discovery = False

    while (seed_queue or discovery_queue) and len(seen) < max_pages:
        if not seed_queue and not sorted_initial_discovery:
            discovery_queue = deque(sorted(discovery_queue, key=link_priority, reverse=True))
            sorted_initial_discovery = True

        url = seed_queue.popleft() if seed_queue else discovery_queue.popleft()
        if url in seen or not is_nitt_url(url):
            continue

        seen.add(url)
        print(f"Fetching {len(seen):02d}/{max_pages}: {url}", flush=True)

        try:
            response = fetch(session, url)
        except requests.RequestException as exc:
            print(f"  skipped: {exc}")
            continue

        content_type = response.headers.get("content-type", "").lower()
        discovered_links: list[str] = []

        if url.lower().endswith(".pdf") or "application/pdf" in content_type:
            try:
                title, text = parse_pdf(url, response.content)
            except Exception as exc:
                print(f"  pdf extraction failed: {exc}")
                continue
            document_type = "pdf"
        else:
            title, text, discovered_links = parse_html(url, response.text)
            document_type = "html"
            high_priority_links = []
            normal_links = []
            for link in discovered_links:
                if link in seen or link in enqueued:
                    continue
                if link_priority(link)[0] or link_priority(link)[2]:
                    high_priority_links.append(link)
                else:
                    normal_links.append(link)

            for link in reversed(high_priority_links):
                discovery_queue.appendleft(link)
                enqueued.add(link)
            for link in normal_links:
                discovery_queue.append(link)
                enqueued.add(link)

        if text:
            documents.append(
                SourceDocument(
                    source_id=f"nitt_{stable_id(url)}",
                    source_url=url,
                    title=title,
                    content_type=document_type,
                    text=text,
                    discovered_links=discovered_links,
                )
            )

        time.sleep(delay_seconds)

    return documents


def write_outputs(documents: list[SourceDocument]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sources_path = OUTPUT_DIR / "nit_trichy_sources.json"
    chunks_path = OUTPUT_DIR / "nit_trichy_chunks.jsonl"

    with sources_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(document) for document in documents], f, indent=2, ensure_ascii=False)

    chunk_count = 0
    with chunks_path.open("w", encoding="utf-8") as f:
        for document in documents:
            for index, chunk in enumerate(chunk_text(document.text), start=1):
                chunk_count += 1
                row = {
                    "chunk_id": f"{document.source_id}_chunk_{index:03d}",
                    "source_id": document.source_id,
                    "source_url": document.source_url,
                    "title": document.title,
                    "content_type": document.content_type,
                    "text": chunk,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(documents)} source documents to {sources_path}")
    print(f"Saved {chunk_count} chunks to {chunks_path}")


def main() -> None:
    documents = scrape()
    write_outputs(documents)


if __name__ == "__main__":
    main()
