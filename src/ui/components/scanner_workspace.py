from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd
import streamlit as st


def render_scanner_workspace(rows: Iterable[Mapping[str, object]]) -> None:
    st.markdown("### Scanner Workspace")
    dataframe = pd.DataFrame(list(rows))
    if dataframe.empty:
        st.info("No ranked candidates yet.")
        return
    st.dataframe(dataframe, use_container_width=True, hide_index=True)

