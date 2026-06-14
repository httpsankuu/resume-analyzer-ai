import logging
import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)

# Sentence-transformers has a practical token limit (~512 tokens ≈ 2000 chars).
# Truncating avoids silent truncation deep in the model and speeds up encoding.
_SEMANTIC_CHAR_LIMIT = 2000


class ResumeMatcher:
    """Match resumes against a job description using a composite scoring strategy."""

    def __init__(self, skill_extractor):
        self.extractor = skill_extractor
        self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
        logger.info("Loading sentence-transformer model...")
        self.semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
        # Weights for composite score
        self.w_skill = 0.40
        self.w_tfidf = 0.35
        self.w_semantic = 0.25
        # Cache JD skill extraction so it runs once, not per candidate
        self._all_skills_flat = self.extractor.get_skills_flat_list()
        logger.info("ResumeMatcher ready.")

    def extract_jd_skills(self, jd_text: str) -> list[str]:
        """Extract skills from a job description using the full skills database."""
        jd_extraction = self.extractor.extract(jd_text)
        return jd_extraction["all_skills"]

    def compute_score(
        self,
        resume_text: str,
        jd_text: str,
        resume_skills: list[str],
        jd_skills: list[str],
        precomputed_tfidf: Optional[float] = None,
    ) -> dict:
        """Return composite match score and detailed breakdown.

        Args:
            precomputed_tfidf: If provided (from rank_all), use this value instead
                               of fitting a fresh TF-IDF vectorizer. This ensures
                               all candidates are scored on the same vocabulary.
        """
        # 1. Skill overlap: compare resume skills vs JD skills
        resume_lower = {s.lower() for s in resume_skills}
        jd_lower = {s.lower() for s in jd_skills}

        matched = sorted(s for s in resume_skills if s.lower() in jd_lower)
        missing = sorted(s for s in jd_skills if s.lower() not in resume_lower)

        skill_score = len(matched) / len(jd_skills) if jd_skills else 0.0

        # 2. TF-IDF cosine similarity
        if precomputed_tfidf is not None:
            tfidf_score = precomputed_tfidf
        else:
            # Standalone use: fit on this pair (consistent but isolated)
            try:
                tfidf_matrix = self.tfidf.fit_transform([resume_text, jd_text])
                tfidf_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
            except ValueError:
                tfidf_score = 0.0

        # 3. Semantic similarity — truncate to model's effective token window
        try:
            resume_snippet = resume_text[:_SEMANTIC_CHAR_LIMIT]
            jd_snippet = jd_text[:_SEMANTIC_CHAR_LIMIT]
            emb = self.semantic_model.encode([resume_snippet, jd_snippet], show_progress_bar=False)
            semantic_score = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
        except Exception:
            logger.exception("Semantic similarity computation failed.")
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
        """Score and rank all candidates against a JD.

        TF-IDF is fit once on the full corpus (all resumes + JD) so every
        candidate is compared on the same vocabulary — making scores fair
        and directly comparable to each other.
        """
        # Fit TF-IDF once on all texts for a consistent, shared vocabulary
        all_texts = [c["resume_text"] for c in candidates] + [jd_text]
        precomputed_tfidf_scores: list[float] = []
        try:
            tfidf_matrix = self.tfidf.fit_transform(all_texts)
            jd_vec = tfidf_matrix[-1]  # last entry is the JD
            for i in range(len(candidates)):
                score = float(cosine_similarity(tfidf_matrix[i : i + 1], jd_vec)[0][0])
                precomputed_tfidf_scores.append(score)
        except ValueError:
            logger.warning("TF-IDF vectorization failed; defaulting scores to 0.")
            precomputed_tfidf_scores = [0.0] * len(candidates)

        results = []
        for i, c in enumerate(candidates):
            score = self.compute_score(
                c["resume_text"],
                jd_text,
                c.get("skills", []),
                jd_skills,
                precomputed_tfidf=precomputed_tfidf_scores[i],
            )
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