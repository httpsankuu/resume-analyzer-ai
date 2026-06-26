import io
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from src.pdf_parser import extract_text_from_pdf, extract_name_from_text
from src.skill_extractor import SkillExtractor
from src.matcher import ResumeMatcher
from src.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Analyzer AI", version="2.0.0")

# ── CORS — allow local Next.js dev + Vercel deploys ──
# Note: allow_origin_regex uses regex patterns — no need to list every Vercel URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load NLP models once at startup ──
logger.info("Loading NLP models...")
extractor = SkillExtractor()
matcher = ResumeMatcher(extractor)
gen = ReportGenerator()
logger.info("Models ready.")


# ── Schemas ──
class PDFReportRequest(BaseModel):
    candidate_name: str
    score: dict
    skills: list[str] = []


class CSVReportRequest(BaseModel):
    results: list[dict]


# ── Health check ──
@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


# ── Main analysis endpoint ──
@app.post("/api/analyze")
async def analyze(
    jd_text: str = Form(default=""),
    jd_file: Optional[UploadFile] = File(default=None),
    resumes: list[UploadFile] = File(...),
):
    """
    Accepts a job description (text or file) and one or more resume PDFs.
    Returns a ranked list of candidates with composite match scores.
    """
    # ── Parse JD ──
    if jd_file and jd_file.filename:
        content = await jd_file.read()
        try:
            if jd_file.filename.endswith(".pdf"):
                jd_text = extract_text_from_pdf(io.BytesIO(content))
            else:
                jd_text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse JD file: {e}")

    if not jd_text.strip():
        raise HTTPException(status_code=400, detail="No job description provided.")

    # ── Parse resumes ──
    candidates = []
    errors = []
    for file in resumes:
        file_bytes = await file.read()
        try:
            resume_text = extract_text_from_pdf(io.BytesIO(file_bytes))
            name = extract_name_from_text(resume_text) or Path(file.filename).stem
            skills_data = extractor.extract(resume_text)
            candidates.append({
                "name": name,
                "filename": file.filename,
                "resume_text": resume_text,
                "skills": skills_data["all_skills"],
                "skills_detail": skills_data,
            })
        except Exception as e:
            logger.warning("Skipping %s: %s", file.filename, e)
            errors.append({"filename": file.filename, "error": str(e)})

    if not candidates:
        raise HTTPException(status_code=400, detail="No valid resumes could be parsed.")

    # ── Score & rank ──
    jd_skills = matcher.extract_jd_skills(jd_text)
    ranked = matcher.rank_all(candidates, jd_text, jd_skills)

    response_ranked = []
    for i, r in enumerate(ranked):
        response_ranked.append({
            "rank": i + 1,
            "name": r["name"],
            "filename": r["filename"],
            "skills": r["skills"],
            "skills_detail": {
                k: v for k, v in r["skills_detail"].items() if k != "skills"
            },
            "score": r["score"],
        })

    return {
        "ranked": response_ranked,
        "jd_skills": jd_skills,
        "total_candidates": len(response_ranked),
        "errors": errors,
    }


# ── PDF report ──
@app.post("/api/report/pdf")
def generate_pdf(req: PDFReportRequest):
    try:
        pdf_bytes = gen.generate_pdf(req.candidate_name, req.score, req.skills, jd_title="Uploaded JD")
        safe_name = req.candidate_name.replace(" ", "_")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report_{safe_name}.pdf"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


# ── CSV report ──
@app.post("/api/report/csv")
def generate_csv(req: CSVReportRequest):
    try:
        csv_bytes = gen.generate_csv(req.results)
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="results.csv"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV generation failed: {e}")
