# Resume Reviewer Pro

AI-powered resume analyzer. Upload your resume, get feedback, and get an improved version.

---

## What It Does

1. **Analyzes your resume** - Checks content, ATS compatibility, impact, and skills
2. **Matches against job description** - Shows what keywords you're missing, what you've got
3. **Rewrites your resume** - Uses AI to improve bullet points and overall quality
4. **Gives detailed feedback** - Tells you exactly what's good and what needs work

The app uses multiple AI agents working together to analyze and improve your resume in real-time.

---

## Installation

### Prerequisites
- Python 3.9 or newer
- Google Gemini API key (get it [here](https://ai.google.dev))

### Setup

1. **Clone and install**
   ```bash
   git clone https://github.com/yourusername/resume-reviewer-pro.git
   cd resume-reviewer-pro
   pip install -r requirements.txt
   ```

2. **Create secrets file**
   ```bash
   mkdir -p .streamlit
   ```
   
   Create `.streamlit/secrets.toml` and add:
   ```toml
   KEY_SID1 = "your_gemini_api_key_here"

   PARSER_MODEL = "your_preferred_model"
   CRITIC_MODEL = "your_preferred_model"
   EDITOR_MODEL = "your_preferred_model"
   ```

3. **Run it**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser**
   ```
   http://localhost:8501
   ```

---

## How to Use

1. Go to the **Home** page
2. Upload your resume (PDF only)
3. (Optional) Paste a job description you're applying for
4. Click "Submit Resume"
5. Wait for analysis to finish
6. Go to **Results** to see scores, feedback, and improvements
7. (Optional) Download the analysis report 

---

## Notes

- Resumes aren't saved anywhere - everything happens in your session
- Minimum resume length: ~100 characters
- If you paste a fake/joke job description, the scores will be low (that's intentional)
- Job descriptions help with matching, but aren't required

---

## Project Structure

```
resume-reviewer-pro/
├── app.py                    # Main app
├── requirements.txt          # Dependencies
├── .streamlit/
│   └── secrets.toml          # Your API key (create this)
├── res/                      # Images and assets
└── src/
    ├── config/               # Settings
    ├── pages/                # Home, Results, About pages
    ├── services/             # PDF, export, AI stuff
    └── analysis/             # Core analysis logic
```

---

## Troubleshooting

**"API key not found"**
- Make sure `.streamlit/secrets.toml` exists and has `KEY_SID1` in it

**"PDF extraction failed"**
- Try a different PDF, make sure it's not encrypted or scanned image

**Session/form resets when switching pages**
- That shouldn't happen with the latest version. If it does, refresh the page

---

## Recent Changes

- Fixed session state (your inputs don't disappear when switching pages)
- Better job description validation (catches fake/nonsense JDs)
- Updated scoring (job match is now more important than resume quality)
- Cleaned up unused code

---

That's it. Pretty straightforward.