# Resume Analyzer AI

**Live Demo:** [https://resumeanalyzer-10.vercel.app/](https://resumeanalyzer-10.vercel.app/)

An intelligent, full-stack resume screening tool that parses PDFs, extracts skills and experience using NLP, and ranks candidates against job descriptions with a composite match score.

## Architecture

This project has been restructured into a modern **Next.js + FastAPI** architecture:

| Layer | Technology | Directory |
|-------|-----------|-----------|
| **Frontend** | Next.js 16 (React 19, TypeScript) | `frontend/` |
| **Backend API** | FastAPI (Python) | `backend/` |
| **Core NLP Engine** | spaCy, scikit-learn, sentence-transformers | `src/` |

---

## Features

- **PDF Parsing** — Extracts text from multi-page resume PDFs using `pdfplumber`
- **Skill Extraction** — 200+ skill taxonomy with `spaCy` PhraseMatcher for fast, accurate skill detection
- **Multi-Strategy Scoring** — Composite match % combining:
  - **Skill Overlap (40%)** — Jaccard similarity between JD and resume skills
  - **TF-IDF Cosine Similarity (35%)** — Keyword/ngram vector matching (fit once across all candidates for fair comparison)
  - **Semantic Similarity (25%)** — Contextual matching via `sentence-transformers` (all-MiniLM-L6-v2)
- **Bulk Processing** — Upload multiple resumes and rank them all at once
- **Downloadable Reports** — Individual PDF reports per candidate + bulk CSV export
- **Modern Dark-Theme UI** — Built with Next.js, featuring bar chart visualization, leaderboard, accordion-style candidate details, drag & drop file upload
- **RESTful API** — Clean FastAPI backend with `/api/analyze`, `/api/report/pdf`, `/api/report/csv` endpoints

---

## Getting Started

### Prerequisites

- **Python 3.10+** with `pip`
- **Node.js 18+** with `npm` (or `pnpm` / `yarn`)

### 1. Backend Setup

```bash
# Clone the repo
git clone https://github.com/httpsankuu/resume-analyzer-ai.git
cd resume-analyzer-ai

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r backend/requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` (Swagger docs at `/docs`).

### 2. Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
# Copy the env example and adjust if needed (defaults to localhost:8000)
# echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 3. Open the App

Navigate to [http://localhost:3000](http://localhost:3000) and you'll see the Resume Analyzer AI interface. From there:

1. Paste a job description (or upload a `.txt` / `.pdf` file)
2. Upload one or more resume PDFs (drag & drop supported)
3. Click **Analyze Resumes**
4. Explore the ranked leaderboard, chart, and accordion-style candidate details
5. Download individual PDF/CSV reports or bulk CSV export

---

## Project Structure

```
resume-analyzer-ai/
├── README.md
├── backend/
│   ├── main.py                # FastAPI server (endpoints, CORS, models)
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── package.json           # Next.js dependencies
│   ├── tsconfig.json          # TypeScript config
│   ├── next.config.ts         # Next.js configuration
│   ├── eslint.config.mjs      # ESLint config
│   └── app/
│       ├── globals.css        # Global styles (dark theme)
│       ├── layout.tsx         # Root layout & metadata
│       └── page.tsx           # Main page (UI + state logic)
├── src/
│   ├── __init__.py
│   ├── pdf_parser.py          # PDF text extraction + name heuristic
│   ├── skill_extractor.py     # spaCy skill/education/experience extraction
│   ├── matcher.py             # Composite scoring engine (skill, TF-IDF, semantic)
│   └── report_generator.py    # PDF (fpdf2) & CSV (pandas) report generation
├── data/
│   ├── skills_db.json         # 200+ skill taxonomy (8 categories)
│   └── sample_jd.txt          # Sample Senior ML Engineer job description
└── tests/
    └── test_all.py            # Comprehensive pytest suite
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — returns `{"status": "ok", "version": "2.0.0"}` |
| `POST` | `/api/analyze` | Upload resumes + JD (text or file) → ranked candidates with scores |
| `POST` | `/api/report/pdf` | Generate a PDF report for a single candidate |
| `POST` | `/api/report/csv` | Generate a CSV report for one or all candidates |

### `/api/analyze` Request (multipart/form-data)

- `jd_text` (optional) — Job description as plain text
- `jd_file` (optional) — Job description as .txt or .pdf file
- `resumes` — One or more .pdf resume files

### `/api/analyze` Response

```json
{
  "ranked": [
    {
      "rank": 1,
      "name": "Jane Doe",
      "filename": "resume.pdf",
      "skills": ["Python", "SQL", "Docker"],
      "skills_detail": {
        "education": ["MIT"],
        "experience_years": 5.0,
        "email": "jane@example.com",
        "phone": null
      },
      "score": {
        "overall_match": 78.2,
        "skill_score": 100.0,
        "tfidf_score": 65.4,
        "semantic_score": 82.1,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["Docker", "Kubernetes"],
        "matched_count": 2,
        "missing_count": 2,
        "label": "Strong Match"
      }
    }
  ],
  "jd_skills": ["Python", "SQL", "Docker", "Kubernetes"],
  "total_candidates": 1,
  "errors": []
}
```

---

## Scoring Methodology

The composite match score combines three independent signals:

| Component | Weight | Method |
|-----------|--------|--------|
| **Skill Overlap** | 40% | Jaccard similarity between JD skills and resume skills (case-insensitive) |
| **TF-IDF Similarity** | 35% | Cosine similarity of TF-IDF vectors (fit once across all candidates + JD for fair comparison) |
| **Semantic Similarity** | 25% | Cosine similarity of sentence-transformer embeddings (all-MiniLM-L6-v2) |

**Labels:**
- ≥80% → Excellent Match
- ≥65% → Strong Match
- ≥50% → Good Match
- ≥35% → Average Match
- <35% → Low Match

---

## Running Tests

```bash
# From the project root
pytest tests/ -v
```

The test suite covers:
- Score computation (perfect, partial, and zero overlap scenarios)
- Ranking order correctness
- Precomputed TF-IDF usage
- Skill extraction keys, experience years, email extraction
- Soft skill false-positive prevention
- PDF report generation (validates %PDF header)
- CSV report generation (columns and content)
- Recommendation logic for excellent and low matches
- Name extraction heuristics

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **NLP** | spaCy, scikit-learn, sentence-transformers |
| **PDF** | pdfplumber |
| **Reports** | fpdf2 (PDF), pandas (CSV) |
| **Backend** | FastAPI, uvicorn, python-multipart, pydantic |
| **Frontend** | Next.js 16, React 19, TypeScript |
| **Testing** | pytest |

---

## Author

**Ankit Kumar Singh** — AI Engineer

- GitHub: [httpsankuu](https://github.com/httpsankuu)
- LinkedIn: [Ankit Kumar Singh](https://www.linkedin.com/in/ankit-kumar-singh-24681b36b/)
- Email: ankitkumar143563@gmail.com

---

Built with ❤️ by Ankit Kumar Singh | © 2026 Resume Analyzer AI
