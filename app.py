from __future__ import annotations

import pandas as pd
import streamlit as st

from nitt_rag.engine import NITTAssistant
from nitt_rag.data import DATA_DIR


st.set_page_config(
    page_title="NIT Trichy Academic RAG Assistant",
    page_icon="N",
    layout="wide",
)


@st.cache_resource(show_spinner="Building classical NLP index...")
def load_assistant(data_version: tuple) -> NITTAssistant:
    return NITTAssistant()


data_version = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(DATA_DIR.glob("*.json*")))
assistant = load_assistant(data_version)

st.title("NIT Trichy Academic RAG Assistant")
st.caption("Classical NLP project using TF-IDF, BM25, cosine similarity, Naive Bayes, TextRank, and rule-based extraction.")

left, right = st.columns([0.68, 0.32])

with right:
    st.metric("Indexed chunks", len(assistant.chunks))
    st.write("Try:")
    st.code(
        "What is the course plan for AR507?\n"
        "Show courses related to Natural Language Processing.\n"
        "What is the syllabus for Data Structures?\n"
        "What fees information is available for B.Tech 2026?",
        language="text",
    )

with left:
    query = st.text_input("Ask a question", value="What is the course plan for AR507?")
    top_k = st.slider("Retrieved chunks", min_value=3, max_value=12, value=6)

    if query:
        response = assistant.ask(query, top_k=top_k)

        st.subheader("Answer")
        st.markdown(response.answer)

        c1, c2 = st.columns(2)
        c1.metric("Question type", response.category)
        c2.metric("Classifier confidence", f"{response.category_confidence:.2f}")

        st.subheader("Extracted Entities")
        entity_rows = [
            {"entity_type": key, "values": ", ".join(values)}
            for key, values in response.entities.items()
            if values
        ]
        if entity_rows:
            st.dataframe(pd.DataFrame(entity_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No rule-based entities found.")

        st.subheader("Retrieved Evidence")
        for index, result in enumerate(response.results, start=1):
            chunk = result.chunk
            with st.expander(f"{index}. {chunk.title} | score {result.score:.3f}", expanded=index <= 2):
                st.write(chunk.text[:1800])
                st.caption(chunk.source_url)

        st.subheader("Sources")
        st.dataframe(pd.DataFrame(response.sources), use_container_width=True, hide_index=True)
