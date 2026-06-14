import json
import logging
import re
from pathlib import Path
from typing import Optional

import spacy
from spacy.matcher import PhraseMatcher


SKILLS_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_db.json"

logger = logging.getLogger(__name__)


class SkillExtractor:
    """Extract skills, education, and experience from resume text using spaCy."""

    def __init__(self):
        logger.info("Loading spaCy model...")
        self.nlp = spacy.load("en_core_web_sm")
        with open(SKILLS_DB_PATH) as f:
            self.skills_db: dict[str, list[str]] = json.load(f)

        # Build PhraseMatcher with all skills from all categories
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.skill_to_category: dict[str, str] = {}

        self._soft_skills_keywords = {s.lower() for s in self.skills_db.get("Soft Skills", [])}
        self._cert_keywords = {s.lower() for s in self.skills_db.get("Certifications", [])}

        for category, skill_list in self.skills_db.items():
            if category == "Soft Skills":
                continue
            for skill in skill_list:
                self.skill_to_category[skill.lower()] = category
                patterns = [self.nlp.make_doc(skill)]
                self.matcher.add(skill, patterns)

        logger.info("SkillExtractor ready. %d categories loaded.", len(self.skills_db))

    def extract(self, text: str) -> dict:
        """Run full extraction pipeline and return structured results."""
        doc = self.nlp(text[:100000])  # cap for performance

        # 1. Match skills from the database
        found_skills: dict[str, set[str]] = {}  # category -> skills
        matches = self.matcher(doc)

        # Track both lowercase key (dedup) and original display case
        seen_lower: set[str] = set()
        seen_display: dict[str, str] = {}  # lower -> display-case

        for match_id, start, end in matches:
            span_text = doc[start:end].text.strip()
            key = span_text.lower()
            if key in seen_lower:
                continue
            seen_lower.add(key)
            seen_display[key] = span_text
            category = self.skill_to_category.get(key, "Other")
            found_skills.setdefault(category, set()).add(span_text)

        # 2. Detect soft skills via word-boundary regex (avoids "go" matching "good")
        text_lower = text.lower()
        found_soft: set[str] = set()
        for s in self._soft_skills_keywords:
            if re.search(r"\b" + re.escape(s) + r"\b", text_lower):
                found_soft.add(s.title())
        if found_soft:
            found_skills["Soft Skills"] = found_soft

        # 3. Detect certifications
        certs_found: set[str] = set()
        for cert in self._cert_keywords:
            if re.search(r"\b" + re.escape(cert) + r"\b", text_lower):
                certs_found.add(cert.title())
        # Regex: "Certified ...", "Certification in ..."
        cert_patterns = re.findall(
            r"(?:Certified|Certification)\s+(?:in\s+)?([A-Za-z\s]+?)(?:,|\.|\\n|$)",
            text, re.IGNORECASE
        )
        for c in cert_patterns:
            c = c.strip()
            if 3 < len(c) < 60:
                certs_found.add(c)

        # 4. Extract education entities via spaCy NER
        education = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "FAC") and any(
                kw in ent.text.lower()
                for kw in ["university", "college", "institute", "school", "academy", "iit", "nit", "mit", "bits"]
            ):
                education.append(ent.text)

        # 5. Years of experience
        experience_years = self._extract_experience_years(text)

        # 6. Contact info
        email = self._extract_email(text)
        phone = self._extract_phone(text)

        # Return all_skills in display-case, sorted case-insensitively
        all_skills_display = sorted(seen_display.values(), key=str.lower)

        return {
            "skills": {cat: sorted(list(s)) for cat, s in found_skills.items()},
            "all_skills": all_skills_display,
            "total_skills_found": len(all_skills_display),
            "education": list(set(education)),
            "experience_years": experience_years,
            "email": email,
            "phone": phone,
        }

    def get_skills_flat_list(self) -> list[str]:
        """Return all skills from the database as a flat lowercase list."""
        result = []
        for skill_list in self.skills_db.values():
            result.extend([s.lower() for s in skill_list])
        return result

    @staticmethod
    def _extract_experience_years(text: str) -> Optional[float]:
        """Heuristic: look for patterns like 'X years of experience'."""
        patterns = [
            r"(\d+[\+]?)\s*(?:\+?\s*)?years?\s*(?:of\s*)?experience",
            r"experience\s*(?:of\s*)?(\d+[\+]?)\s*years?",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).rstrip("+")
                return float(val)
        return None

    @staticmethod
    def _extract_email(text: str) -> Optional[str]:
        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        return m.group(0) if m else None

    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        # Require at least 7 digits to avoid matching plain numbers
        m = re.search(r"\+?\d[\d\s\-()]{7,14}\d", text)
        return m.group(0).strip() if m else None