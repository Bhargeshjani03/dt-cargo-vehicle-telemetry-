"""Render the team walkthrough stored in docs/ as a page in the app."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


WALKTHROUGH_PATH = Path(__file__).resolve().parents[2] / "docs" / "PROJECT_WALKTHROUGH.md"
GITHUB_BLOB_ROOT = "https://github.com/Bhargeshjani03/dt-cargo-vehicle-telemetry-/blob/divy"


def render_project_walkthrough() -> None:
    """Open the shared Markdown guide inside the Streamlit website."""
    if not WALKTHROUGH_PATH.is_file():
        st.error("The project walkthrough file is missing from docs/.")
        return

    markdown = WALKTHROUGH_PATH.read_text(encoding="utf-8")
    for local_path in ("src", "notebooks"):
        markdown = markdown.replace(
            f"](../{local_path}/",
            f"]({GITHUB_BLOB_ROOT}/{local_path}/",
        )
    markdown = markdown.replace("](../README.md)", f"]({GITHUB_BLOB_ROOT}/README.md)")
    st.markdown(markdown, unsafe_allow_html=False)
