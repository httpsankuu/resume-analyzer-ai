import pdfplumber
from typing import Optional


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract and return clean text from a PDF file's bytes."""
    text_parts: list[str] = []

    try:
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")

    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        raise ValueError(
            "No extractable text found in the PDF. "
            "The file may be image-only or empty."
        )

    return full_text


def extract_name_from_text(text: str) -> Optional[str]:
    """Heuristic: return the first non-empty line that looks like a name."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Skip lines that are clearly not names (emails, phones, URLs)
    skip_keywords = ["@", "http", "www.", "+", "summary", "objective", "resume"]
    for line in lines[:8]:
        if len(line.split()) <= 5 and not any(k in line.lower() for k in skip_keywords):
            # Reasonable name: 2-4 words, each capitalized
            words = line.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() or not w[0].isalpha() for w in words):
                return line
    # Fallback: use the filename-derived name from outside
    return None