import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class ResumeMatcher:
    """Match resumes against a job description using a composite scoring strategy."""

    def __init__(self, skill_extractor):
        self.extractor = skill_extractor
        self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
        self.semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
        # Weights for composite score
        self.w_skill = 0.40
        self.w_tfidf = 0.35
        self.w_semantic = 0.25
        # Cache JD skill extraction so it runs once, not per candidate
        self._all_skills_flat = self.extractor.get_skills_flat_list()

    def extract_jd_skills(self, jd_text: str) -> list[str]:
        """Extract skills from a job description using the full skills database."""
        jd_extraction = self.extractor.extract(jd_text)
        return jd_extraction["all_skills"]

    def compute_score(self, resume_text: str, jd_text: str, resume_skills: list[str], jd_skills: list[str]) -> dict:
        """Return composite match score and detailed breakdown."""
        # 1. Skill overlap: compare resume skills vs JD skills (both extracted independently)
        resume_lower = {s.lower() for s in resume_skills}
        jd_lower = {s.lower() for s in jd_skills}

        matched = sorted(s for s in resume_skills if s.lower() in jd_lower)
        missing = sorted(s for s in jd_skills if s.lower() not in resume_lower)

        skill_score = len(matched) / len(jd_skills) if jd_skills else 0.0

        # 2. TF-IDF cosine similarity
        try:
            tfidf_matrix = self.tfidf.fit_transform([resume_text, jd_text])
            tfidf_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        except ValueError:
            tfidf_score = 0.0

        # 3. Semantic similarity
        try:
            emb = self.semantic_model.encode([resume_text, jd_text], show_progress_bar=False)
            semantic_score = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
        except Exception:
            semantic_score = 0.0

        # Composite
        composite = (
            self.w_skill * skill_score
            + self.w_tfidf * tfidf_score
            + self.w_semantic * semantic_score
        )
        composite_pct = round(min(composite, 1.0) * 100, 1)

        return {
            "overall_match": composite_pct,
            "skill_score": round(skill_score * 100, 1),
            "tfidf_score": round(tfidf_score * 100, 1),
            "semantic_score": round(semantic_score * 100, 1),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing),
            "matched_count": len(matched),
            "missing_count": len(missing),
            "label": self._label(composite_pct),
        }

    def rank_all(self, candidates: list[dict], jd_text: str, jd_skills: list[str]) -> list[dict]:
        """Score and rank all candidates against a JD. Returns sorted list."""
        results = []
        for c in candidates:
            score = self.compute_score(c["resume_text"], jd_text, c.get("skills", []), jd_skills)
            results.append({**c, "score": score})
        results.sort(key=lambda r: r["score"]["overall_match"], reverse=True)
        return results

    @staticmethod
    def _label(pct: float) -> str:
        if pct >= 80:
            return "Excellent Match"
        if pct >= 65:
            return "Strong Match"
        if pct >= 50:
            return "Good Match"
        if pct >= 35:
            return "Average Match"
        return "Low Match"