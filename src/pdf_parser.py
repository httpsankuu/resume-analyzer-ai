import logging
from typing import BinaryIO, Union

import pdfplumber


logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_source: Union[bytes, BinaryIO]) -> str:
    """Extract and return clean text from a PDF file.

    Args:
        file_source: Either raw bytes or a file-like object (BinaryIO / BytesIO).

    Returns:
        Extracted text as a single string.

    Raises:
        ValueError: If the PDF cannot be parsed or contains no extractable text.
    """
    text_parts: list[str] = []

    try:
        with pdfplumber.open(file_source) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
    except Exception as e:
        logger.exception("PDF parsing failed.")
        raise ValueError(f"Failed to parse PDF: {e}") from e

    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        raise ValueError(
            "No extractable text found in the PDF. "
            "The file may be image-only or empty."
        )

    return full_text


def extract_name_from_text(text: str) -> str | None:
    """Heuristic: return the first non-empty line that looks like a name."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Skip lines that are clearly not names (emails, phones, URLs)
    skip_keywords = ["@", "http", "www.", "+", "summary", "objective", "resume"]
    for line in lines[:8]:
        if len(line.split()) <= 5 and not any(k in line.lower() for k in skip_keywords):
            # Reasonable name: 1-4 words, each capitalized
            words = line.split()
            if 1 <= len(words) <= 4 and all(w[0].isupper() or not w[0].isalpha() for w in words):
                return line
    # Fallback: use the filename-derived name from outside
    return None