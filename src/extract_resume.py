from pathlib import Path

from pypdf import PdfReader


RESUME_PATH = Path("data/resume/Siddanth_Resume_August_2026.pdf")
OUTPUT_PATH = Path("data/resume_text.txt")


def extract_resume_text(path: Path) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def main():
    text = extract_resume_text(RESUME_PATH)

    OUTPUT_PATH.write_text(text, encoding="utf-8")

    print(f"Extracted resume text saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()