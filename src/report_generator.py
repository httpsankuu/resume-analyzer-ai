import io
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF


class ReportGenerator:
    """Generate PDF (per candidate) and CSV (bulk ranking) reports."""

    @staticmethod
    def generate_pdf(candidate_name: str, score: dict, skills: list[str], jd_title: str = "Job Description") -> bytes:
        """Return a PDF report as bytes for a single candidate."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)

        # ── Header ──
        pdf.set_fill_color(234, 88, 12)
        pdf.rect(0, 0, 210, 45, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_y(12)
        pdf.cell(0, 14, "Resume Analysis Report", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(12)

                # ── Candidate & Score ──
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Candidate: {candidate_name}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 8, f"Job Description: {jd_title}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # Big score box
        overall = score.get("overall_match", 0)
        pdf.set_fill_color(248, 249, 250)
        pdf.set_draw_color(234, 88, 12)
        pdf.rect(15, pdf.get_y(), 180, 32, "DF")
        pdf.set_xy(15, pdf.get_y() + 4)
        pdf.set_text_color(234, 88, 12)
        pdf.set_font("Helvetica", "B", 28)
        pdf.cell(180, 12, f"{overall}%", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(15, pdf.get_y() + 1)
        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(180, 8, score.get("label", ""), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(pdf.get_y() + 10)

        # ── Score Breakdown ──
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Score Breakdown", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(230, 230, 230)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)

        breakdowns = [
            ("Skill Overlap (40% weight)", score.get("skill_score", 0)),
            ("TF-IDF Similarity (35% weight)", score.get("tfidf_score", 0)),
            ("Semantic Similarity (25% weight)", score.get("semantic_score", 0)),
        ]
        for label, val in breakdowns:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(80, 8, label)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.cell(30, 8, f"{val}%", align="R")
            # Progress bar
            bar_x = 130
            bar_w = 55
            bar_y = pdf.get_y() + 1.5
            bar_h = 5
            pdf.set_fill_color(230, 230, 230)
            pdf.rect(bar_x, bar_y, bar_w, bar_h, "F")
            fill_w = min(bar_w * val / 100, bar_w)
            pdf.set_fill_color(234, 88, 12)
            pdf.rect(bar_x, bar_y, fill_w, bar_h, "F")
            pdf.ln(10)

        pdf.ln(4)

        # ── Matched Skills ──
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Matched Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)
        matched = score.get("matched_skills", [])
        if matched:
            pdf.set_font("Helvetica", "", 10)
            chunks = [", ".join(matched[i:i+4]) for i in range(0, len(matched), 4)]
            for chunk in chunks:
                pdf.set_text_color(40, 140, 40)
                pdf.cell(0, 7, f"  +  {chunk}", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_text_color(150, 150, 150)
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 7, "  No specific skills matched.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # ── Missing Skills ──
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Missing Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)
        missing = score.get("missing_skills", [])
        if missing:
            pdf.set_font("Helvetica", "", 10)
            chunks = [", ".join(missing[i:i+4]) for i in range(0, len(missing), 4)]
            for chunk in chunks:
                pdf.set_text_color(200, 50, 50)
                pdf.cell(0, 7, f"  -  {chunk}", new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_text_color(150, 150, 150)
            pdf.set_font("Helvetica", "I", 10)
            pdf.cell(0, 7, "  No skills missing - excellent!", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # ── Recommendations ──
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Recommendations", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)
        recs = ReportGenerator._generate_recommendations(score, skills)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        for i, rec in enumerate(recs, 1):
            pdf.cell(0, 7, f"  {i}. {rec}", new_x="LMARGIN", new_y="NEXT")

        # Output to bytes
        return pdf.output()

    @staticmethod
    def generate_csv(results: list[dict]) -> bytes:
        """Return a CSV file as bytes with all candidates ranked."""
        rows = []
        for r in results:
            s = r.get("score", {})
            rows.append({
                "Rank": r.get("rank", 0),
                "Candidate": r.get("name", "Unknown"),
                "Match %": s.get("overall_match", 0),
                "Label": s.get("label", ""),
                "Skills Matched": s.get("matched_count", 0),
                "Skills Missing": s.get("missing_count", 0),
                "Skill Score": s.get("skill_score", 0),
                "TF-IDF Score": s.get("tfidf_score", 0),
                "Semantic Score": s.get("semantic_score", 0),
                "Matched Skills": ", ".join(s.get("matched_skills", [])),
                "Missing Skills": ", ".join(s.get("missing_skills", [])),
            })
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return buf.getvalue()

    @staticmethod
    def _generate_recommendations(score: dict, skills: list[str]) -> list[str]:
        recs = []
        overall = score.get("overall_match", 0)
        missing = score.get("missing_skills", [])

        if overall >= 80:
            recs.append("Candidate is an excellent match. Fast-track to interview.")
        elif overall >= 65:
            recs.append("Strong candidate - recommend advancing to technical screening.")
        elif overall >= 50:
            recs.append("Decent match but gaps exist. Consider a screening call to assess depth.")
        else:
            recs.append("Significant skill gaps. Not recommended unless pool is limited.")

        if missing:
            top_missing = missing[:5]
            recs.append(f"Key skills to develop: {', '.join(top_missing)}.")

        if score.get("skill_score", 0) < 40:
            recs.append("Core technical skill overlap is low - verify experience level.")
        if score.get("semantic_score", 0) > score.get("skill_score", 0) + 20:
            recs.append("Resume phrasing aligns well with the JD but concrete skill matches are weaker - probe deeper in interview.")

        return recs
