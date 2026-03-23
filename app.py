"""
Streamlit UI
"""

import streamlit as st
from src.rag import RegIQ

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RegIQ - BNR Regulatory Intelligence",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Global */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 780px; }

  /* Header */
  .regiq-header {
    border-bottom: 2px solid #1a3a5c;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
  }
  .regiq-logo {
    font-size: 1.6rem;
    font-weight: 600;
    color: #1a3a5c;
    letter-spacing: -0.5px;
  }
  .regiq-sub {
    font-size: 0.82rem;
    color: #6b7280;
    margin-top: 0.15rem;
  }

  /* Answer card */
  .answer-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #1a3a5c;
    border-radius: 6px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #1e293b;
  }

  /* Source chip */
  .source-chip {
    display: inline-block;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    padding: 0.2rem 0.6rem;
    font-size: 0.75rem;
    color: #1e40af;
    margin: 0.2rem 0.2rem 0.2rem 0;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }

  /* Example queries */
  .example-label {
    font-size: 0.75rem;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
  }

  /* Input */
  .stTextInput > div > div > input {
    border-radius: 6px;
    border: 1.5px solid #cbd5e1;
    font-size: 0.95rem;
    padding: 0.65rem 1rem;
  }
  .stTextInput > div > div > input:focus {
    border-color: #1a3a5c;
    box-shadow: 0 0 0 3px rgba(26,58,92,0.08);
  }

  /* Button */
  .stButton > button {
    background: #1a3a5c;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.6rem 1.4rem;
    font-size: 0.9rem;
    font-weight: 500;
    transition: background 0.15s;
  }
  .stButton > button:hover { background: #152d47; }

  /* Divider */
  hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.5rem 0; }

  /* Warning banner */
  .disclaimer {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #f1f5f9;
  }
</style>
""", unsafe_allow_html=True)

# ─── Init RAG ─────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def load_regiq():
    return RegIQ(model="gpt-4o-mini", top_k=6)


# ─── Session state ────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    # list of {"q": ..., "a": ..., "sources": [...]}
    st.session_state.history = []

if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ─── Example queries ──────────────────────────────────────────────────────────
EXAMPLES = [
    "What templates must banks submit daily?",
    "Penalty for late data submission",
    "Recovery plan governance requirements",
    "Monthly reporting deadlines",
    "What data do microfinance institutions report?",
    "Capital adequacy recovery triggers",
    "Electronic data warehouse submission times",
    "Who reviews the bank recovery plan?",
]

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="regiq-header">
  <div class="regiq-logo">⚖️ RegIQ</div>
  <div class="regiq-sub">Central Bank Regulatory Intelligence · National Bank of Rwanda</div>
</div>
""", unsafe_allow_html=True)

# ─── System status ────────────────────────────────────────────────────────────
rag = load_regiq()

if not rag.is_ready:
    st.error(
        "**Vector store not found.** "
        "Run `python -m src.ingest` after placing PDFs in `data/directives/`.",
        icon="⚠️"
    )
    st.stop()

# ─── Example query buttons ────────────────────────────────────────────────────
st.markdown('<div class="example-label">Try asking</div>',
            unsafe_allow_html=True)

cols = st.columns(4)
clicked_example = None
for i, example in enumerate(EXAMPLES):
    with cols[i % 4]:
        if st.button(example, key=f"ex_{i}", use_container_width=True,
                     help=example):
            clicked_example = example

st.markdown("<hr>", unsafe_allow_html=True)

# ─── Query input ──────────────────────────────────────────────────────────────
with st.form(key="query_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query = st.text_input(
            label="question",
            placeholder="Ask any compliance question - e.g. 'fraud transaction reporting frequency'",
            label_visibility="collapsed",
            key=f"query_input_{st.session_state.input_key}",
            value=clicked_example or "",
        )
    with col_btn:
        submitted = st.form_submit_button("Ask", use_container_width=True)

# ─── Handle query ─────────────────────────────────────────────────────────────
active_query = (clicked_example or query) if (
    submitted or clicked_example) else None

if active_query and active_query.strip():
    q = active_query.strip()

    with st.spinner(""):
        result = rag.ask(q)

    # Store in history
    st.session_state.history.insert(0, {
        "q":       q,
        "a":       result["answer"],
        "sources": result["sources"],
    })
    st.session_state.input_key += 1

# ─── Render history ───────────────────────────────────────────────────────────
for i, item in enumerate(st.session_state.history):
    # Question
    st.markdown(
        f"<div style='font-size:0.85rem;color:#64748b;margin-bottom:0.3rem;"
        f"font-weight:500;'>Q - {item['q']}</div>",
        unsafe_allow_html=True
    )

    # Answer
    st.markdown(
        f"<div class='answer-card'>{item['a']}</div>",
        unsafe_allow_html=True
    )

    # Sources
    if item["sources"]:
        with st.expander(f"Sources ({len(item['sources'])} references)", expanded=False):
            for src in item["sources"]:
                st.markdown(
                    f"<span class='source-chip'>{src['citation']}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='font-size:0.78rem;color:#6b7280;"
                    f"margin:0.3rem 0 0.8rem 0.2rem;line-height:1.5;'>"
                    f"{src['preview']}</div>",
                    unsafe_allow_html=True
                )

    if i < len(st.session_state.history) - 1:
        st.markdown("<hr>", unsafe_allow_html=True)

# ─── Empty state ──────────────────────────────────────────────────────────────
if not st.session_state.history:
    st.markdown("""
    <div style='text-align:center;padding:3rem 0;color:#94a3b8;'>
      <div style='font-size:2.5rem;margin-bottom:0.8rem;'>⚖️</div>
      <div style='font-size:1rem;font-weight:500;color:#64748b;'>
        Ask any question about BNR directives
      </div>
      <div style='font-size:0.82rem;margin-top:0.4rem;'>
        Submission templates · Deadlines · Penalties · Recovery planning · Governance
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**RegIQ** - BNR Directives")
    st.markdown("---")

    try:
        stats = rag.get_stats()
        st.metric("Chunks indexed", stats["total_chunks"])
    except Exception:
        pass

    st.markdown("**Corpus**")
    st.markdown("""
    - National Bank of Rwanda
    - 26 Directives
    - English / French
    - Updated: 2018–2022
    """)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem;color:#9ca3af;'>
    RegIQ provides regulatory information only.
    Always verify with BNR for official guidance.
    </div>
    """, unsafe_allow_html=True)

# ─── Disclaimer ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
RegIQ provides regulatory information for reference purposes only.
For official compliance guidance, consult BNR directly at <strong>bnr.rw</strong>.
</div>
""", unsafe_allow_html=True)
