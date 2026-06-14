# Resume Reviewer Pro

An AI-powered resume analyzer. Just upload your resume, and it'll give you scores and suggestions to make it better.

You can try the live demo right here:

```text
https://siddharths-resume-reviewer-pro.streamlit.app/

```

*Note: I used the Gemini free tier keys for the live demo, so you might see a "This model is currently unavailable due to heavy demand" message if you try using it during busy times. Also, if you see a "Streamlit app is sleeping" message, just hit the "Wake the app" button. Streamlit puts apps to sleep if nobody has used them for a little while.*

---

## What It Does

1. **Analyzes your resume** - Checks the content, ATS compatibility, impact, and your skills.
2. **Matches against job descriptions** - Shows you exactly what keywords you're missing and what you've already got.
3. **Suggests improvements** - Uses AI to suggest better bullet points and improve the overall quality of the resume.
4. **Gives detailed feedback** - Tells you what's good, what needs work, and what immediate steps you can take to get better results.

Basically, the app uses a few AI agents working together to analyze and fix up your resume in real-time.

After the initial check, the app sends your data to three different AI models to parse, edit, and critique the resume. I made this configurable, so you can just pick whichever models you think work best for each specific task.

---

## Installation

### Prerequisites

* Python 3.12
* A Google Gemini API key (you can grab one [here](https://aistudio.google.com/api-keys))

### Setup

1. **Clone and install**

   ```bash
   cd YOUR_FOLDER
   git clone https://github.com/Sidd-Rai/ResumeReviewerPro
   pip install -r requirements.txt

   ```
2. **Create your secrets file**
   ```bash
   mkdir -p .streamlit
   ```

   Create a `.streamlit/secrets.toml` file and add your keys:

   ```toml
   KEY_SID1 = "your_gemini_api_key_here"

   PARSER_MODEL = "your_preferred_model"
   CRITIC_MODEL = "your_preferred_model"
   EDITOR_MODEL = "your_preferred_model"

   ```

   Here is an example of how that should look:

   ```toml
   KEY_SID1 = "your_gemini_api_key_here"

   PARSER_MODEL = "gemini-3.1-flash-lite"
   CRITIC_MODEL = "gemini-3.5-flash"
   EDITOR_MODEL = "gemini-3.1-flash-lite"


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

1. Go to the **Home** page.
2. Upload your resume (PDFs only).
3. (Optional) Paste in the description of a job you're applying for.
4. Click "Submit Resume".
5. Wait a bit for the analysis to finish.
6. Go to the **Results** page to see your scores, feedback, and suggested improvements.
7. (Optional) Download the analysis report if you want to keep it.

---

## Notes

* I don't save your resumes anywhere. Everything happens locally in your session.
* Make sure your resume is at least ~100 characters long.
* If you paste a fake or joke job description, your scores are going to be low (I did that on purpose).
* You don't *have* to use a job description, but it helps a lot with the matching.

---

## Project Structure

```text
resume-reviewer-pro/
├── app.py                    # Main app
├── requirements.txt          # Dependencies
├── .streamlit/
│   └── secrets.toml          # Your API key goes here
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

* Make sure you actually created the `.streamlit/secrets.toml` file and put `KEY_SID1` inside it.

**"PDF extraction failed"**

* Try a different PDF. Just make sure it isn't encrypted or just a scanned image of a document.

**Session/form resets when switching pages**

* That shouldn't happen anymore with the latest version. But if it does, just give the page a refresh.

---

## Recent Changes

* Fixed the session state so your inputs don't just disappear when you switch pages.
* Added better job description validation (it catches fake or nonsense JDs now).
* Updated the scoring system (matching the job is now weighed heavier than general resume quality).
* Cleaned up some old, unused code.

---

## Known Issues and Improvements

* When using free tier keys, some models might not be available due to heavy demand, and the app will throw an error message mentioning the same.
* The API call chain can be further optimized to rely on even fewer API calls.

---

## License & Contributing

This project is open source under the MIT License. Feel free to fork it, play around with the code, or submit a PR if you have ideas for improvements!

That's it. Pretty straightforward.