import os
from pathlib import Path

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8000
TOP_K_RETRIEVAL = 6
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
EXPORT_DIR = DATA_DIR / "exports"

for d in (UPLOAD_DIR, CHROMA_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

COLLECTIONS = {
    "case_law": "case_law",
    "lecture": "lecture",
    "article": "article",
    "instruction": "instruction",
    "past_paper": "past_paper",
    "workshop_question": "workshop_question",
    "statute": "statute",
    "other": "other",
}

DOC_TYPE_LABELS = {
    "case_law": "Case Law",
    "lecture": "Lecture Material",
    "article": "Legal Scholar / Article",
    "instruction": "Assignment / Instructions",
    "past_paper": "Past Exam Paper",
    "workshop_question": "Workshop / Tutorial Questions",
    "statute": "Statute / Legislation",
    "other": "Other",
}

NZ_COURT_HIERARCHY = [
    "New Zealand Supreme Court [NZSC]",
    "New Zealand Court of Appeal [NZCA]",
    "New Zealand High Court [NZHC]",
    "New Zealand District Court",
    "Privy Council (pre-2004, persuasive)",
    "UK Supreme Court / House of Lords (persuasive)",
    "Australian High Court (persuasive)",
]

NZ_STYLE_GUIDE_RULES = """
## New Zealand Law Style Guide (3rd ed, 2018) — Citation Rules

**Case citations:**
- NZ Supreme Court:    [year] NZSC n          e.g. [2024] NZSC 12
- NZ Court of Appeal:  [year] NZCA n          e.g. [2023] NZCA 45
- NZ High Court:       [year] NZHC n          e.g. [2022] NZHC 200
- NZ Law Reports:      Name [year] vol NZLR page (court)  e.g. Smith v Jones [2020] 2 NZLR 100 (SC)
- UK Supreme Court:    [year] UKSC n
- Short form:          Name, above n X, at [para]

**Statute citations:**
- Act Name year, s section  e.g. Contract and Commercial Law Act 2017, s 7
- Pinpoint: s 7(1)(a)

**Footnoting:**
- Superscript numbers in body text after punctuation
- Case names italicised in body text, not in footnotes
- Pinpoint to paragraph: at [23]; to page: at 105

**Essay structure:**
- Formal academic prose throughout (no bullet points in essay body)
- Binding NZ authority first, then persuasive (UK/AU), then academic commentary
- Acknowledge unsettled law and competing interpretations
- Conclusion must directly resolve the issue posed
"""
