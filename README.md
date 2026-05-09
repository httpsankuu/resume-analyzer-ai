# Resume Analyzer AI
An intelligent resume screening tool that parses PDFs, extracts key skills and experience using NLP, and ranks candidates against job descriptions with a composite match score.

## Features
- **PDF Parsing** — Extracts text from multi-page resume PDFs using `pdfplumber`
- **Skill Extraction** — 200+ skill taxonomy with `spaCy` PhraseMatcher for fast, accurate skill detection
- **Multi-Strategy Scoring** — Composite match % combining:
  - Skill Overlap (40%) — Jaccard similarity between JD and resume skills
  - TF-IDF Cosine Similarity (35%) — Keyword/ngram vector matching
  - Semantic Similarity (25%) — Contextual matching via `sentence-transformers`
- **Bulk Processing** — Upload multiple resumes and rank them all at once
- **Downloadable Reports** — Individual PDF reports per candidate + bulk CSV export
- **Interactive UI** — Built with Streamlit, featuring leaderboard, charts, and expandable details

---

## 🐳 Docker (Easiest Way — No Setup Needed!)

> No Python, no venv, no pip install — just Docker!

```bash
# Clone the repo
git clone https://github.com/httpsankuu/resume-analyzer-ai.git
cd resume-analyzer-ai

# Build the Docker image
docker build -t resume-analyzer-ai .

# Run the container
docker run -p 8501:8501 resume-analyzer-ai
```

Then open your browser and go to:
```
http://localhost:8501
```

---

## Installation (Manual Setup)

```bash
# Clone the repo
git clone https://github.com/httpsankuu/resume-analyzer-ai.git
cd resume-analyzer-ai

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

## Usage
```bash
streamlit run app.py
```

Then:
1. Paste a job description (or upload a .txt/.pdf file)
2. Upload one or more resume PDFs
3. Click **Analyze Resumes**
4. Explore the ranked leaderboard and download reports

## Project Structure
```
resume-analyzer-ai/
├── app.py                    # Streamlit UI
├── requirements.txt          # Dependencies
├── Dockerfile                # Docker configuration
├── src/
│   ├── pdf_parser.py         # PDF text extraction
│   ├── skill_extractor.py    # spaCy skill extraction
│   ├── matcher.py            # Composite scoring engine
│   └── report_generator.py   # PDF & CSV export
└── data/
    ├── skills_db.json        # 200+ skill taxonomy
    └── sample_jd.txt         # Sample job description
```

## Tech Stack
- **NLP**: spaCy, scikit-learn, sentence-transformers
- **PDF**: pdfplumber
- **Reports**: fpdf2, pandas
- **UI**: Streamlit, matplotlib
- **Deployment**: Docker

## Author
**Ankit Kumar Singh** — AI Engineer
- GitHub: [httpsankuu](https://github.com/httpsankuu)
- LinkedIn: [Ankit Kumar Singh](https://www.linkedin.com/in/ankit-kumar-singh-24681b36b/)
- Email: ankitkumar143563@gmail.com
