import streamlit as st
import importlib
import sys
from pathlib import Path

# Ensure the project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

st.set_page_config(page_title="ResRvuPro | Siddharth",
                   page_icon="./res/icon.png",
                   layout="wide")

PAGES ={
    "Home": "src.pages.home",
    "Results": "src.pages.dashboard",
    "About": "src.pages.about",
}


st.sidebar.title("Navigation")

selected_page = st.sidebar.radio(
    "Go to",
    list(PAGES.keys())
)

# Logic for Loading page dynamically
module_name = PAGES[selected_page]
module = importlib.import_module(module_name)

module.render()
