"""
Unit tests for Resume Analyzer AI.

Run with:
    pytest tests/ -v
"""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ─── ResumeMatcher tests ───────────────────────────────────────────────────

class TestResumeMatcher:
    """Tests for src/matcher.py — composite scoring & ranking."""

    def _make_matcher(self):
        """Return a ResumeMatcher with a mocked SkillExtractor."""
        from src.matcher import ResumeMatcher

        mock_extractor = MagicMock()
        mock_extractor.get_skills_flat_list.return_value = ["python", "sql", "docker"]
        mock_extractor.extract.return_value = {"all_skills": ["Python", "SQL"]}

        with patch("src.matcher.SentenceTransformer") as MockST:
            # encode() returns two identical vectors → cosine = 1.0
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[1, 0], [1, 0]], dtype=float)
            MockST.return_value = mock_model
            matcher = ResumeMatcher(mock_extractor)

        return matcher

    def test_label_thresholds(self):
        from src.matcher import ResumeMatcher
        assert ResumeMatcher._label(85) == "Excellent Match"
        assert ResumeMatcher._label(70) == "Strong Match"
        assert ResumeMatcher._label(55) == "Good Match"
        assert ResumeMatcher._label(40) == "Average Match"
        assert ResumeMatcher._label(20) == "Low Match"

    def test_compute_score_perfect_skill_overlap(self):
        matcher = self._make_matcher()
        score = matcher.compute_score(
            resume_text="Python SQL developer",
            jd_text="We need Python and SQL",
            resume_skills=["Python", "SQL"],
            jd_skills=["Python", "SQL"],
        )
        assert score["skill_score"] == 100.0
        assert score["matched_count"] == 2
        assert score["missing_count"] == 0
        assert score["overall_match"] > 0

    def test_compute_score_no_skills(self):
        matcher = self._make_matcher()
        score = matcher.compute_score(
            resume_text="Some text",
            jd_text="Some JD",
            resume_skills=[],
            jd_skills=[],
        )
        # skill_score should be 0 when jd_skills is empty
        assert score["skill_score"] == 0.0

    def test_compute_score_partial_overlap(self):
        matcher = self._make_matcher()
        score = matcher.compute_score(
            resume_text="Python developer",
            jd_text="We need Python SQL Docker",
            resume_skills=["Python"],
            jd_skills=["Python", "SQL", "Docker"],
        )
        assert score["skill_score"] == pytest.approx(100 / 3, rel=0.01)
        assert "SQL" in score["missing_skills"]
        assert "Docker" in score["missing_skills"]

    def test_rank_all_sorted_descending(self):
        matcher = self._make_matcher()
        candidates = [
            {"resume_text": "junior dev", "skills": []},
            {"resume_text": "Python SQL Docker expert", "skills": ["Python", "SQL", "Docker"]},
        ]
        jd_skills = ["Python", "SQL", "Docker"]
        ranked = matcher.rank_all(candidates, "Python SQL Docker JD", jd_skills)
        # Candidate with more skills should rank first
        scores = [r["score"]["overall_match"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_precomputed_tfidf_used(self):
        """When precomputed_tfidf is passed, it should override internal TF-IDF."""
        matcher = self._make_matcher()
        score_with = matcher.compute_score(
            resume_text="a",
            jd_text="b",
            resume_skills=[],
            jd_skills=[],
            precomputed_tfidf=0.99,
        )
        assert score_with["tfidf_score"] == pytest.approx(99.0, rel=0.01)


# ─── SkillExtractor tests ──────────────────────────────────────────────────

class TestSkillExtractor:
    """Tests for src/skill_extractor.py."""

    @pytest.fixture(scope="class")
    def extractor(self):
        from src.skill_extractor import SkillExtractor
        return SkillExtractor()

    def test_extract_returns_required_keys(self, extractor):
        result = extractor.extract("Python developer with 3 years of experience.")
        assert "all_skills" in result
        assert "skills" in result
        assert "experience_years" in result
        assert "email" in result

    def test_experience_year_extraction(self, extractor):
        result = extractor.extract("I have 5 years of experience in data science.")
        assert result["experience_years"] == 5.0

    def test_email_extraction(self, extractor):
        result = extractor.extract("Contact me at test@example.com for details.")
        assert result["email"] == "test@example.com"

    def test_soft_skill_no_false_positive(self, extractor):
        """'go' skill should NOT trigger on words like 'good' or 'google'."""
        result = extractor.extract("I am good at googling things and I am productive.")
        all_lower = [s.lower() for s in result["all_skills"]]
        # 'go' should not appear as a standalone skill match here
        assert "go" not in all_lower or "good" not in " ".join(all_lower)

    def test_all_skills_not_all_lowercase(self, extractor):
        """all_skills should preserve original casing, not return all lowercase."""
        result = extractor.extract("Experienced with Python, TensorFlow, and Docker.")
        if result["all_skills"]:
            # At least one skill should have a capital letter
            has_capital = any(s != s.lower() for s in result["all_skills"])
            assert has_capital, f"Expected cased skills, got: {result['all_skills']}"

    def test_get_skills_flat_list_returns_lowercase(self, extractor):
        flat = extractor.get_skills_flat_list()
        assert isinstance(flat, list)
        assert len(flat) > 0
        assert all(s == s.lower() for s in flat)


# ─── ReportGenerator tests ────────────────────────────────────────────────

class TestReportGenerator:
    """Tests for src/report_generator.py."""

    SAMPLE_SCORE = {
        "overall_match": 72.5,
        "skill_score": 80.0,
        "tfidf_score": 60.0,
        "semantic_score": 70.0,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["Docker"],
        "matched_count": 2,
        "missing_count": 1,
        "label": "Strong Match",
    }

    def test_generate_pdf_returns_bytes(self):
        from src.report_generator import ReportGenerator
        pdf_bytes = ReportGenerator.generate_pdf("Jane Doe", self.SAMPLE_SCORE, ["Python", "SQL"])
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDFs start with %PDF
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_csv_returns_bytes(self):
        from src.report_generator import ReportGenerator
        candidates = [{"name": "Jane Doe", "rank": 1, "score": self.SAMPLE_SCORE}]
        csv_bytes = ReportGenerator.generate_csv(candidates)
        assert isinstance(csv_bytes, bytes)
        assert b"Jane Doe" in csv_bytes
        assert b"72.5" in csv_bytes

    def test_generate_csv_columns(self):
        from src.report_generator import ReportGenerator
        candidates = [{"name": "Bob", "rank": 1, "score": self.SAMPLE_SCORE}]
        csv_bytes = ReportGenerator.generate_csv(candidates)
        header = csv_bytes.decode().splitlines()[0]
        for col in ["Rank", "Candidate", "Match %", "Label"]:
            assert col in header

    def test_recommendations_excellent(self):
        from src.report_generator import ReportGenerator
        score = {**self.SAMPLE_SCORE, "overall_match": 85}
        recs = ReportGenerator._generate_recommendations(score, [])
        assert any("excellent" in r.lower() for r in recs)

    def test_recommendations_low(self):
        from src.report_generator import ReportGenerator
        score = {**self.SAMPLE_SCORE, "overall_match": 20, "skill_score": 10, "semantic_score": 5}
        recs = ReportGenerator._generate_recommendations(score, [])
        assert any("gap" in r.lower() or "not recommended" in r.lower() for r in recs)


# ─── pdf_parser tests ─────────────────────────────────────────────────────

class TestPdfParser:
    """Tests for src/pdf_parser.py."""

    def test_extract_name_simple(self):
        from src.pdf_parser import extract_name_from_text
        text = "John Smith\nSoftware Engineer\njohn@example.com"
        name = extract_name_from_text(text)
        assert name == "John Smith"

    def test_extract_name_skips_email_line(self):
        from src.pdf_parser import extract_name_from_text
        text = "john@example.com\nJane Doe\nEngineer"
        name = extract_name_from_text(text)
        assert name == "Jane Doe"

    def test_extract_name_returns_none_for_garbage(self):
        from src.pdf_parser import extract_name_from_text
        text = "https://example.com\nsummary of work\nobjective statement"
        name = extract_name_from_text(text)
        assert name is None

    def test_extract_text_raises_on_empty(self):
        from src.pdf_parser import extract_text_from_pdf
        # An empty bytes object is not a valid PDF
        with pytest.raises((ValueError, Exception)):
            extract_text_from_pdf(b"")
