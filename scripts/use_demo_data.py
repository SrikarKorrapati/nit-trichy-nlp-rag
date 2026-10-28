"""Install the small public example only when no application corpus exists."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CORPUS_FILES = ("nit_trichy_chunks.jsonl", "nit_trichy_cp_course_details.json", "nit_trichy_cp_course_detail_chunks.jsonl")

def main():
    if any((DATA / name).exists() for name in CORPUS_FILES):
        print("Using existing local corpus; no files changed.")
        return
    DATA.mkdir(exist_ok=True)
    source = ROOT / "examples/nit_trichy_cp_course_details.json"
    shutil.copyfile(source, DATA / source.name)
    print("Installed the two-course example dataset. See examples/README.md for sources.")

if __name__ == "__main__":
    main()
