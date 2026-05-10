from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import streamlit as st

from src.ui.components.scanner_workspace import render_scanner_workspace


@dataclass(frozen=True)
class ScannerPageView:
    rows: list[Mapping[str, object]]
    narrative: list[str]


def render_scanner_page(view: ScannerPageView) -> None:
    render_scanner_workspace(view.rows)
    st.markdown("#### Scanner Commentary")
    for line in view.narrative:
        st.write(f"- {line}")

