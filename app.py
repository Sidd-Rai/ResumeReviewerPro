# Imports section
import streamlit as st
import importlib

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
