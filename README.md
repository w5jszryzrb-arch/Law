# NZ Law School Assistant

A personal AI study assistant for NZ law students. Reads case law, drafts essays
in NZ Law Style Guide format, generates exam practice from your own course
materials, and builds advanced notes.

## Run it locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Start the app
python app.py
```

Then open **http://localhost:5000** in your browser.

The first request loads a small local embedding model (~80 MB) from
HuggingFace — this happens once and is cached afterwards.

## Features

- **Projects** — bundle subject, rubric, and saved conversations per course
- **Documents** — upload PDFs / PowerPoints / TXT (lectures, cases, articles,
  past papers, workshop questions, statutes); auto-detection of type
- **Case Analysis** — full IRAC, ratio decidendi extraction, comparison, chat
- **Essay Assistant** — analyse question → plan → draft → critique → chat
  (with optional rubric alignment, NZ Law Style Guide citations)
- **Exam Practice** — strictly course-content only; generate, model answer, mark
  your answer, plus past-paper and workshop-question analysis
- **Notes** — lecture notes, case summary tables, topic overviews, revision notes

## Configuration

Environment variables (in `.env` or shell):

| Variable             | Default       | Purpose                              |
|----------------------|---------------|--------------------------------------|
| `ANTHROPIC_API_KEY`  | *(required)*  | Your Claude API key                  |
| `PORT`               | `5000`        | Port to bind                         |
| `HOST`               | `127.0.0.1`   | Bind address                         |
| `FLASK_DEBUG`        | `0`           | Set to `1` for auto-reload + tracebacks |
| `FLASK_SECRET`       | *(random)*    | Cookie signing key                   |

## Where your data lives

All under `data/` (git-ignored):

- `data/uploads/` — original uploaded files
- `data/chroma_db/` — embedded vector store
- `data/projects.db` — SQLite database of projects and saved conversations

Delete the `data/` folder to fully reset the app.
