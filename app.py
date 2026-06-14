import io
import logging
from pathlib import Path

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from src.pdf_parser import extract_text_from_pdf, extract_name_from_text
from src.skill_extractor import SkillExtractor
from src.matcher import ResumeMatcher
from src.report_generator import ReportGenerator

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Page config ──
st.set_page_config(
    page_title="Resume Analyzer AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: transparent; }
  .main-header { font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 0; }
  .main-header span { color: #ea580c; }
  .sub-header { color: var(--text-color); opacity: 0.7; font-size: 1rem; margin-bottom: 1.5rem; }
  .metric-card {
    background: var(--secondary-background-color); border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06); border: 1px solid var(--border-color);
    text-align: center;
  }
  .metric-value { font-size: 2rem; font-weight: 800; color: #ea580c; }
  .metric-label { font-size: .75rem; color: var(--text-color); opacity: 0.6; text-transform: uppercase; letter-spacing: .08em; margin-top: 4px; }
  .candidate-row {
    background: var(--secondary-background-color); border-radius: 10px; padding: 16px 20px; margin-bottom: 10px;
    border: 1px solid var(--border-color); display: flex; align-items: center;
    justify-content: space-between; transition: box-shadow .2s;
  }
  .candidate-row:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
  div[data-testid="stExpander"] { background: var(--secondary-background-color) !important; border-radius: 12px !important; border: 1px solid var(--border-color) !important; }
  .skill-tag {
    display: inline-block; padding: 4px 10px; border-radius: 100px;
    font-size: .75rem; font-weight: 600; margin: 2px;
  }
  .skill-matched { background: #ecfdf5; color: #166534; }
  .skill-missing { background: #fef2f2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

# ── Model caching — loaded once, reused across all reruns ──
@st.cache_resource(show_spinner="Loading NLP models (first run only)...")
def load_models():
    """Load and cache SkillExtractor and ResumeMatcher.

    Decorated with @st.cache_resource so these heavy models are initialised
    exactly once per app lifecycle, not on every button click.
    """
    extractor = SkillExtractor()
    matcher = ResumeMatcher(extractor)
    return extractor, matcher

# ── Session state init ──
if "results" not in st.session_state:
    st.session_state.results = None
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

# ── Header ──
st.markdown('<p class="main-header">Resume <span>Analyzer</span> AI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload resumes, paste a job description, and get AI-powered match scores in seconds.</p>', unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/resume.png", width=58)
    st.markdown("### How it works")
    st.markdown("""
    1. **Enter a job description** below (paste or upload)
    2. **Upload multiple resume PDFs**
    3. Click **Analyze Resumes**
    4. View rankings, download **PDF/CSV reports**
    """)
    st.divider()
    st.markdown("#### About")
    st.markdown("Built with `spaCy`, `scikit-learn`, and `sentence-transformers`. Composite scoring across skill overlap, TF-IDF, and semantic similarity.")
    st.caption("© 2026 Ankit Kumar Singh")

# ── Layout: two columns for input ──
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### 📋 Job Description")
    jd_input_method = st.radio("Input method:", ["Paste Text", "Upload File"], horizontal=True, label_visibility="collapsed")

    if jd_input_method == "Paste Text":
        jd_text = st.text_area(
            "Paste the job description here",
            height=220,
            placeholder="Paste the full job description including required skills, qualifications, responsibilities...",
            label_visibility="collapsed",
            key="jd_text_area",
        )
    else:
        jd_file = st.file_uploader("Upload JD file", type=["txt", "pdf"], key="jd_file")
        jd_text = ""
        if jd_file is not None:
            if jd_file.name.endswith(".pdf"):
                try:
                    jd_text = extract_text_from_pdf(jd_file.read())
                except Exception as e:
                    st.error(f"Failed to parse JD PDF: {e}")
            else:
                jd_text = jd_file.read().decode("utf-8", errors="ignore")
            if jd_text:
                st.success(f"Loaded: {jd_file.name} ({len(jd_text)} chars)")
                with st.expander("Preview JD text"):
                    st.text(jd_text[:800])

with col2:
    st.markdown("### 📂 Upload Resumes")
    resume_files = st.file_uploader(
        "Upload one or more resume PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="resume_files",
    )
    if resume_files:
        st.info(f"{len(resume_files)} resume(s) uploaded")
        names = [f.name for f in resume_files]
        st.markdown("  \n".join([f"• `{n}`" for n in names]))

# ── Analyze button ──
st.divider()
analyze_cols = st.columns([2, 1, 2])
with analyze_cols[1]:
    analyze_btn = st.button(
        "🔍 Analyze Resumes",
        type="primary",
        use_container_width=True,
        disabled=not (jd_text.strip() and resume_files),
    )

# ── Processing ──
if analyze_btn and jd_text.strip() and resume_files:
    st.session_state.jd_text = jd_text.strip()
    with st.status("Analyzing resumes...", expanded=True) as status:
        st.write("Loading NLP models...")
        # Retrieve cached models — no re-loading cost on subsequent runs
        extractor, matcher = load_models()

        st.write(f"Processing {len(resume_files)} resume(s)...")
        candidates = []
        progress_bar = st.progress(0)

        for i, file in enumerate(resume_files):
            status_msg = f"Parsing {file.name}..."
            st.write(status_msg)

            try:
                file_bytes = file.read()
                resume_text = extract_text_from_pdf(io.BytesIO(file_bytes))
                name = extract_name_from_text(resume_text) or Path(file.name).stem
                skills_data = extractor.extract(resume_text)

                candidates.append({
                    "name": name,
                    "filename": file.name,
                    "resume_text": resume_text,
                    "skills": skills_data["all_skills"],
                    "skills_detail": skills_data,
                    "original_file_bytes": file_bytes,
                })
            except Exception as e:
                st.error(f"Error processing {file.name}: {e}")
            progress_bar.progress((i + 1) / len(resume_files))

        st.write("Extracting required skills from job description...")
        jd_skills = matcher.extract_jd_skills(jd_text)

        if not jd_skills:
            st.warning(
                "⚠️ No recognised skills were found in the job description. "
                "Skill Overlap score will be 0 for all candidates. "
                "Try including more explicit skill names (e.g. Python, SQL, React)."
            )
        else:
            st.write(f"Found {len(jd_skills)} skills in JD: {', '.join(jd_skills[:15])}{'...' if len(jd_skills) > 15 else ''}")

        st.write("Computing match scores...")
        ranked = matcher.rank_all(candidates, jd_text, jd_skills)

        # Add ranks
        for i, r in enumerate(ranked):
            r["rank"] = i + 1

        st.session_state.results = {
            "ranked": ranked,
            "jd_text": jd_text,
            "jd_skills": jd_skills,
            "total_candidates": len(ranked),
        }

        status.update(label=f"Analysis complete! {len(ranked)} resumes scored.", state="complete")

# ── Results ──
if st.session_state.results:
    results = st.session_state.results
    ranked = results["ranked"]

    st.divider()
    st.markdown("### 🏆 Results")

    # ── JD Skills extracted ──
    jd_skills = results.get("jd_skills", [])
    if jd_skills:
        st.markdown("**Skills required by Job Description:**  \n" + " ".join(
            [f'<span class="skill-tag skill-missing">{s}</span>' for s in jd_skills]
        ), unsafe_allow_html=True)
        st.markdown("")

    # ── Summary metrics ──
    m1, m2, m3, m4 = st.columns(4)
    scores = [r["score"]["overall_match"] for r in ranked]
    with m1:
        st.markdown('<div class="metric-card"><div class="metric-value">' + str(len(ranked)) + '</div><div class="metric-label">Candidates</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{max(scores):.1f}%</div><div class="metric-label">Top Match</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{sum(scores)/len(scores):.1f}%</div><div class="metric-label">Avg Match</div></div>', unsafe_allow_html=True)
    with m4:
        strong = sum(1 for s in scores if s >= 65)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{strong}</div><div class="metric-label">Strong (65%+)</div></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Bar chart ──
    fig, ax = plt.subplots(figsize=(8, max(2, len(ranked) * 0.5)))
    names = [r["name"][:25] for r in reversed(ranked)]
    vals = [r["score"]["overall_match"] for r in reversed(ranked)]
    colors = ["#ea580c" if v >= 65 else "#fb923c" if v >= 50 else "#fed7aa" for v in vals]
    ax.barh(names, vals, color=colors, height=0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Match %")
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9, fontweight="bold", color="#555")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="y", labelsize=9)
    fig.tight_layout()
    st.pyplot(fig)

    st.markdown("")

    # ── Leaderboard ──
    st.markdown("#### Leaderboard")
    leaderboard_data = []
    for r in ranked:
        s = r["score"]
        leaderboard_data.append({
            "Rank": r["rank"],
            "Candidate": r["name"],
            "Match": f"{s['overall_match']}%",
            "Label": s["label"],
            "Skills Found": f"{s['matched_count']} / {s['matched_count'] + s['missing_count']}",
        })
    lb_df = pd.DataFrame(leaderboard_data)

    st.dataframe(
        lb_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Match": st.column_config.TextColumn(width="small"),
        },
    )

    # ── Candidate details ──
    st.markdown("")
    st.markdown("#### Candidate Details")

    # ReportGenerator is stateless — instantiate once outside the loop
    gen = ReportGenerator()

    for r in ranked:
        s = r["score"]
        emoji = "🟢" if s["overall_match"] >= 65 else "🟡" if s["overall_match"] >= 50 else "🔴"
        label = f"{emoji} #{r['rank']} — {r['name']} — **{s['overall_match']}%** ({s['label']})"

        with st.expander(label):
            det_col1, det_col2 = st.columns([1, 1])

            with det_col1:
                st.markdown("**Score Breakdown**")
                st.markdown(f"- Skill Overlap (40%): `{s['skill_score']}%`")
                st.markdown(f"- TF-IDF Similarity (35%): `{s['tfidf_score']}%`")
                st.markdown(f"- Semantic Similarity (25%): `{s['semantic_score']}%`")

                sd = r.get("skills_detail", {})
                if sd.get("education"):
                    st.markdown("**Education Detected**")
                    for edu in sd["education"]:
                        st.markdown(f"- {edu}")
                if sd.get("experience_years"):
                    st.markdown(f"**Experience**: ~{sd['experience_years']} years")
                if sd.get("email"):
                    st.markdown(f"**Email**: {sd['email']}")

            with det_col2:
                st.markdown("**Matched Skills**")
                if s["matched_skills"]:
                    tags = " ".join([f'<span class="skill-tag skill-matched">{sk}</span>' for sk in s["matched_skills"]])
                    st.markdown(tags, unsafe_allow_html=True)
                else:
                    st.caption("None matched")

                st.markdown("**Missing Skills**")
                if s["missing_skills"]:
                    tags = " ".join([f'<span class="skill-tag skill-missing">{sk}</span>' for sk in s["missing_skills"]])
                    st.markdown(tags, unsafe_allow_html=True)
                else:
                    st.caption("None missing — all required skills present!")

            # ── Download buttons per candidate ──
            dl_col1, dl_col2 = st.columns(2)
            with dl_col1:
                try:
                    pdf_bytes = gen.generate_pdf(r["name"], s, r.get("skills", []), jd_title="Uploaded JD")
                    st.download_button(
                        label=f"📥 Download PDF Report — {r['name']}",
                        data=pdf_bytes,
                        file_name=f"report_{r['name'].replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{r['rank']}",
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

            with dl_col2:
                csv_bytes = gen.generate_csv([r])
                st.download_button(
                    label=f"📥 Download CSV — {r['name']}",
                    data=csv_bytes,
                    file_name=f"report_{r['name'].replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"csv_{r['rank']}",
                )

    # ── Bulk CSV download ──
    st.divider()
    try:
        all_csv = gen.generate_csv(ranked)
        st.download_button(
            label="📊 Download All Results (CSV)",
            data=all_csv,
            file_name="all_candidates_ranking.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Bulk CSV generation failed: {e}")

# ── Empty state ──
else:
    st.divider()
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: var(--text-color); opacity: 0.5;">
      <div style="font-size: 3rem; margin-bottom: 12px;">📄</div>
      <h3 style="color: var(--text-color); opacity: 0.8; margin-bottom: 8px;">Ready to analyze resumes</h3>
      <p>Enter a job description, upload resume PDFs, and click <strong>Analyze Resumes</strong> to get started.</p>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ──
st.divider()
st.caption("Built with ❤️ by Ankit Kumar Singh | © 2026 | Resume Analyzer AI")
