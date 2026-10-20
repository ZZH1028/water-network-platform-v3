"""Public hosting entry point. Select this file in Streamlit Community Cloud."""
from pathlib import Path
import runpy

from core.cloud import apply_cloud_settings

apply_cloud_settings()

import streamlit as st
from scripts.setup_scene_assets import install_assets


@st.cache_resource(show_spinner="正在准备三维引擎…")
def prepare_scene_assets() -> None:
    install_assets()


prepare_scene_assets()
runpy.run_path(str(Path(__file__).resolve().with_name("app.py")), run_name="__main__")

