from __future__ import annotations

import re


DEPARTMENTS = [
    "Architecture",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Applications",
    "Computer Science and Engineering",
    "Electrical and Electronics Engineering",
    "Electronics and Communication Engineering",
    "Instrumentation and Control Engineering",
    "Management Studies",
    "Mathematics",
    "Mechanical Engineering",
    "Metallurgical and Materials Engineering",
    "Physics",
    "Production Engineering",
    "Chemistry",
    "Humanities and Social Sciences",
]

PROGRAMS = [
    "B.Tech.",
    "M.Tech.",
    "B.Arch.",
    "M.Arch.",
    "MCA",
    "MBA",
    "M.Sc.",
    "M.A",
    "M. Plan.",
    "B.Sc.B.Ed.",
    "Ph.D.",
    "M.S.",
]


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def extract_entities(text: str) -> dict[str, list[str]]:
    course_codes = re.findall(r"\b[A-Z]{2,5}\s?\d{2,4}[A-Z]?(?:\([^)]+\))?\b", text)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)", text)
    sessions = re.findall(r"\b(?:Jan|January|July)\s?20\d{2}\b", text, flags=re.IGNORECASE)
    years = re.findall(r"\b20\d{2}(?:-\d{2,4})?\b", text)
    credits = re.findall(r"\b\d+(?:\.\d+)?\s*(?:credits?|credit)\b", text, flags=re.IGNORECASE)
    urls = re.findall(r"https?://[^\s|)]+", text)

    lower = text.lower()
    departments = [department for department in DEPARTMENTS if department.lower() in lower]
    programs = [program for program in PROGRAMS if program.lower() in lower]

    return {
        "course_codes": unique(course_codes),
        "emails": unique(emails),
        "phone_numbers": unique([re.sub(r"\s+", "", phone) for phone in phones]),
        "sessions": unique(sessions),
        "years": unique(years),
        "credits": unique(credits),
        "departments": unique(departments),
        "programs": unique(programs),
        "urls": unique(urls),
    }
