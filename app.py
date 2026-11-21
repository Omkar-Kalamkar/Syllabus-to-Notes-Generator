"""Streamlit frontend for the Syllabus-to-Notes Generator."""

from __future__ import annotations

import re

import streamlit as st

import docx_generator
import generator


st.set_page_config(
    page_title="Syllabus-to-Notes Generator",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


DEFAULT_STATE = {
    "syllabus_text": "",
    "subject_name": "",
    "notes_length": "Medium",
    "generated_notes": "",
    "error_message": "",
}


def initialize_state() -> None:
    """Set safe default values for all widgets and generated output."""
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_app() -> None:
    """Clear all user input and generated notes."""
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value


def make_download_filename(subject_name: str) -> str:
    """Create a clean file name from the optional subject name."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", subject_name.strip())
    cleaned = cleaned.strip("_") or "syllabus"
    return f"{cleaned}_study_notes.docx"


initialize_state()

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        .main-header {
            background: linear-gradient(135deg, #1f4e79 0%, #2e75b6 55%, #5b9bd5 100%);
            color: #ffffff;
            padding: 1.6rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 20px rgba(31, 78, 121, 0.18);
        }
        .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
        .main-header p { margin: 0.45rem 0 0; font-size: 1rem; opacity: 0.94; }
        .stTextArea textarea { font-family: Consolas, "Courier New", monospace; font-size: 0.9rem; }
        .stButton > button { border-radius: 10px; font-weight: 600; }
        .stDownloadButton > button { border-radius: 10px; font-weight: 600; }
        .note-output {
            background: #f7f9fc;
            border: 1px solid #dce5f0;
            border-radius: 12px;
            padding: 1rem;
        }
        .sidebar-note {
            background: #eef4fb;
            border-radius: 10px;
            padding: 0.75rem;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-header">
        <h1>Syllabus-to-Notes Generator</h1>
        <p>
            Paste a university syllabus and generate short, simple, unit-wise study notes
            with Google Gemini.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Quick Guide")
    st.markdown(
        """
        1. Paste syllabus text.
        2. Choose Short, Medium, or Detailed.
        3. Click **Generate Notes**.
        4. Download the Word file.
        """
    )
    st.markdown("---")
    config_issue = generator.get_configuration_issue()
    if config_issue is None:
        st.success("Gemini API key: configured")
    else:
        st.warning(config_issue.message)
    st.markdown(
        f'<div class="sidebar-note">Set {generator.API_KEY_ENV_VAR} in your .env file, '
        "then restart Streamlit. The key is never displayed in this app.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption(f"Model: {generator.get_model_name()}")

input_column, output_column = st.columns([1, 1], gap="large")

with input_column:
    with st.container(border=True):
        st.subheader("Syllabus Details")

        subject_name = st.text_input(
            "Subject name (optional)",
            key="subject_name",
            placeholder="Example: Data Structures",
        )

        syllabus_text = st.text_area(
            "Paste syllabus here",
            key="syllabus_text",
            height=300,
            placeholder=(
                "Unit I: Introduction to Data Structures\n"
                "- Arrays, linked lists, stacks and queues\n"
                "Unit II: Trees and Graphs\n"
                "- Binary trees, traversal, graph representation"
            ),
            help="Copy the syllabus text directly from the university website.",
        )

        notes_length = st.selectbox(
            "Notes length",
            options=["Short", "Medium", "Detailed"],
            key="notes_length",
            index=1,
        )

        if syllabus_text.strip():
            analysis = generator.analyze_syllabus(syllabus_text)
            if analysis["has_clear_units"]:
                st.caption(
                    f"Detected {analysis['unit_count']} unit/module heading(s). "
                    "The original order will be preserved."
                )
            else:
                st.caption(
                    "No clear unit headings detected. Gemini will organize the given "
                    "topics without inventing units."
                )

        generate_clicked = st.button(
            "Generate Notes",
            type="primary",
            use_container_width=True,
        )
        st.button(
            "Clear / Reset",
            on_click=reset_app,
            use_container_width=True,
        )

with output_column:
    with st.container(border=True):
        st.subheader("Generated Notes")

        if generate_clicked:
            st.session_state["error_message"] = ""
            st.session_state["generated_notes"] = ""
            if not st.session_state["syllabus_text"].strip():
                st.session_state["error_message"] = (
                    "Please paste a syllabus before generating notes."
                )
            else:
                config_issue = generator.get_configuration_issue()
                if config_issue is not None:
                    st.session_state["error_message"] = config_issue.message
                else:
                    with st.spinner("Generating unit-wise notes with Gemini..."):
                        try:
                            st.session_state["generated_notes"] = generator.generate_notes(
                                st.session_state["syllabus_text"],
                                st.session_state["subject_name"],
                                st.session_state["notes_length"],
                            )
                        except generator.SyllabusNotesError as exc:
                            st.session_state["error_message"] = str(exc)
                        except Exception:
                            st.session_state["error_message"] = (
                                "Something unexpected happened while generating notes. "
                                "Please try again."
                            )
            st.rerun()

        if st.session_state["error_message"]:
            st.error(st.session_state["error_message"])

        if st.session_state["generated_notes"]:
            st.success("Notes generated successfully.")
            st.markdown("---")
            st.markdown(st.session_state["generated_notes"])

            with st.expander("View raw Markdown"):
                st.code(st.session_state["generated_notes"], language="markdown")

            st.markdown("---")
            try:
                docx_bytes = docx_generator.create_docx_bytes(
                    st.session_state["generated_notes"],
                    st.session_state["subject_name"],
                )
                st.download_button(
                    label="Download Notes as Word (.docx)",
                    data=docx_bytes,
                    file_name=make_download_filename(st.session_state["subject_name"]),
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "wordprocessingml.document"
                    ),
                    type="primary",
                    use_container_width=True,
                )
            except docx_generator.DocxGenerationError as exc:
                st.error(str(exc))
        else:
            st.info("Your generated notes will appear here after you click Generate Notes.")

st.markdown("---")
st.caption(
    "Designed for quick university revision. Always verify generated notes against "
    "your official syllabus and textbooks before exams."
)
