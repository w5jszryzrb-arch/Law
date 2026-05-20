"""
Shared styles for the NZ Law School Assistant.
Call apply_styles() at the top of every page.
"""
import streamlit as st


_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

/* ── Variables ── */
:root {
    --navy:        #1B2D4F;
    --navy-light:  #253D68;
    --gold:        #C9A84C;
    --gold-light:  #E8D08A;
    --bg:          #F0F2F7;
    --white:       #FFFFFF;
    --text:        #1E293B;
    --muted:       #64748B;
    --border:      #DDE3EE;
    --green:       #059669;
    --amber:       #D97706;
    --red:         #DC2626;
    --radius:      12px;
    --radius-sm:   8px;
    --shadow:      0 1px 3px rgba(27,45,79,.07), 0 4px 14px rgba(27,45,79,.07);
    --shadow-lg:   0 4px 12px rgba(27,45,79,.13), 0 8px 28px rgba(27,45,79,.09);
}

/* ── App shell ── */
.stApp { background: var(--bg) !important; }
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1080px !important;
}

/* ── Typography ── */
html, body, .stApp, p, li, span, label, div {
    font-family: 'Inter', system-ui, sans-serif !important;
    color: var(--text) !important;
}
h1 {
    font-family: 'Crimson Pro', Georgia, serif !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
    letter-spacing: -0.3px !important;
    margin-bottom: .25rem !important;
}
h2 {
    font-family: 'Crimson Pro', Georgia, serif !important;
    font-size: 1.65rem !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
}
h3, h4 {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: var(--navy) !important;
}
.stMarkdown p { line-height: 1.7 !important; }
small, .stCaption, caption { color: var(--muted) !important; font-size: .82rem !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1.25rem 0 !important; }

/* ── Buttons ── */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: .875rem !important;
    padding: .45rem 1.1rem !important;
    transition: all .18s ease !important;
    border: none !important;
    cursor: pointer !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%) !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(27,45,79,.30) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 18px rgba(27,45,79,.40) !important;
}
.stButton > button[kind="primary"]:active { transform: translateY(0) !important; }
.stButton > button[kind="secondary"] {
    background: var(--white) !important;
    color: var(--navy) !important;
    border: 1.5px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--navy) !important;
    background: #F8F9FC !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: var(--white) !important;
    border: 1.5px solid var(--border) !important;
    color: var(--navy) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
}

/* ── Text inputs ── */
.stTextInput > label, .stTextArea > label,
.stSelectbox > label, .stMultiSelect > label,
.stNumberInput > label, .stSlider > label {
    font-weight: 500 !important;
    font-size: .875rem !important;
    color: var(--text) !important;
    margin-bottom: 4px !important;
}
.stTextInput input, .stTextArea textarea {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--white) !important;
    color: var(--text) !important;
    font-size: .9rem !important;
    transition: border-color .15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 3px rgba(27,45,79,.10) !important;
}

/* ── Select / Multiselect ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--white) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--border) !important;
    border-radius: 10px !important;
    padding: 3px !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    padding: 7px 18px !important;
    font-size: .875rem !important;
    font-weight: 500 !important;
    color: var(--muted) !important;
    background: transparent !important;
    border: none !important;
    transition: all .15s !important;
}
.stTabs [aria-selected="true"] {
    background: var(--white) !important;
    color: var(--navy) !important;
    box-shadow: var(--shadow) !important;
}

/* ── Expander ── */
.stExpander {
    background: var(--white) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}
.stExpander summary {
    font-weight: 500 !important;
    font-size: .9rem !important;
    padding: .75rem 1rem !important;
}

/* ── Alert / Info / Success / Warning boxes ── */
.stAlert {
    border-radius: var(--radius) !important;
    border-left-width: 4px !important;
    padding: .75rem 1rem !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: var(--white) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem 1.25rem !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: .8rem !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--border) !important;
    padding: 1rem !important;
    margin-bottom: .75rem !important;
    background: var(--white) !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: #EEF2FF !important;
    border-color: #C7D2FE !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--border) !important;
    background: var(--white) !important;
}

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    border-radius: var(--radius) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--white) !important;
    padding: 1.25rem !important;
    transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--navy) !important;
}

/* ── Form submit button ── */
[data-testid="stForm"] .stButton > button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, var(--navy), var(--navy-light)) !important;
    color: white !important;
}

/* ── Containers with borders ── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--border) !important;
    background: var(--white) !important;
    padding: 1.25rem !important;
    box-shadow: var(--shadow) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, var(--navy) 0%, #142240 100%) !important;
    border-right: none !important;
    box-shadow: 3px 0 20px rgba(0,0,0,.15) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,.92) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #fff !important;
    font-family: 'Crimson Pro', Georgia, serif !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,.15) !important;
}
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,.10) !important;
    border: 1px solid rgba(255,255,255,.20) !important;
    color: #fff !important;
    border-radius: var(--radius-sm) !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: rgba(255,255,255,.40) !important;
}
[data-testid="stSidebar"] .stTextInput input:focus {
    background: rgba(255,255,255,.18) !important;
    border-color: var(--gold) !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stTextInput label {
    color: rgba(255,255,255,.70) !important;
    font-size: .78rem !important;
    text-transform: uppercase !important;
    letter-spacing: .5px !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,.12) !important;
    color: rgba(255,255,255,.92) !important;
    border: 1px solid rgba(255,255,255,.18) !important;
    width: 100% !important;
    text-align: left !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,.22) !important;
    border-color: rgba(255,255,255,.35) !important;
}
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] small {
    color: rgba(255,255,255,.55) !important;
}

/* ── Number input ── */
.stNumberInput input {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--white) !important;
}

/* ── Select slider ── */
.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
    color: var(--navy) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--navy) !important; }

/* ── Progress ── */
.stProgress > div > div { background: var(--navy) !important; }

/* ── Tooltips ── */
.stTooltipIcon { color: var(--muted) !important; }

/* ── Custom helper classes (used via st.markdown) ── */

/* Page header banner */
.law-header {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 60%, #2D5AA0 100%);
    border-radius: var(--radius) !important;
    padding: 1.5rem 1.75rem !important;
    margin-bottom: 1.5rem !important;
    color: white !important;
}
.law-header h1, .law-header h2, .law-header p {
    color: white !important;
    margin: 0 !important;
    padding: 0 !important;
}
.law-header .subtitle { color: rgba(255,255,255,.75) !important; font-size: .9rem !important; margin-top: .4rem !important; }

/* Project card */
.project-card {
    background: var(--white);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 1.1rem 1.25rem;
    box-shadow: var(--shadow);
    transition: box-shadow .2s, border-color .2s, transform .2s;
    cursor: pointer;
    height: 100%;
}
.project-card:hover {
    box-shadow: var(--shadow-lg);
    border-color: var(--navy);
    transform: translateY(-2px);
}
.project-card .subject {
    font-family: 'Crimson Pro', Georgia, serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--navy);
    margin: 0 0 .3rem 0;
}
.project-card .meta {
    font-size: .8rem;
    color: var(--muted);
    margin: 0;
}
.project-card .tools {
    font-size: 1rem;
    margin-top: .5rem;
    letter-spacing: 2px;
}

/* Badge */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: .75rem;
    font-weight: 600;
    line-height: 1.6;
}
.badge-navy  { background: #EEF2FF; color: var(--navy); border: 1px solid #C7D2FE; }
.badge-gold  { background: #FFFBEB; color: #92400E;     border: 1px solid #FDE68A; }
.badge-green { background: #ECFDF5; color: #065F46;     border: 1px solid #A7F3D0; }
.badge-grey  { background: #F1F5F9; color: var(--muted); border: 1px solid var(--border); }

/* Output box (for AI responses) */
.output-box {
    background: var(--white);
    border: 1.5px solid var(--border);
    border-left: 4px solid var(--navy);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 1.25rem 1.5rem;
    margin-top: .75rem;
    box-shadow: var(--shadow);
    line-height: 1.75;
}

/* Tip box */
.tip-box {
    background: #FFFBEB;
    border: 1.5px solid #FDE68A;
    border-left: 4px solid var(--gold);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: .75rem 1rem;
    font-size: .875rem;
    color: #78350F;
    margin: .75rem 0;
}

/* Step indicator */
.step-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 1rem;
}
.step {
    background: var(--border);
    color: var(--muted);
    border-radius: 99px;
    padding: 3px 14px;
    font-size: .78rem;
    font-weight: 600;
}
.step.active {
    background: var(--navy);
    color: white;
}
.step.done {
    background: var(--green);
    color: white;
}
</style>
"""

_DOC_TYPE_COLORS = {
    "case_law":          ("badge-navy",  "⚖️ Case Law"),
    "lecture":           ("badge-grey",  "📖 Lecture"),
    "article":           ("badge-gold",  "📰 Article"),
    "instruction":       ("badge-green", "📋 Instructions"),
    "past_paper":        ("badge-navy",  "📄 Past Paper"),
    "workshop_question": ("badge-gold",  "🔨 Workshop"),
    "statute":           ("badge-grey",  "📜 Statute"),
    "other":             ("badge-grey",  "📎 Other"),
}


def apply_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def doc_badge(doc_type: str) -> str:
    cls, label = _DOC_TYPE_COLORS.get(doc_type, ("badge-grey", doc_type))
    return f'<span class="badge {cls}">{label}</span>'


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="law-header"><h1>{icon} {title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def tip(text: str) -> None:
    st.markdown(f'<div class="tip-box">💡 {text}</div>', unsafe_allow_html=True)
