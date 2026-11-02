"""Small system-font editorial layer; no remote fonts or assets."""
import streamlit as st


def apply_style():
    st.markdown('''<style>
    :root {font-variant-numeric:tabular-nums;}
    .stMainBlockContainer {padding-top:1.4rem;max-width:1500px;}
    h1 {font-size:2rem!important;font-weight:650!important;letter-spacing:-.045em;color:#223b53;}
    h2,h3 {color:#223b53;letter-spacing:-.02em;}
    h2 {font-size:1.5rem!important;} h3 {font-size:1.15rem!important;}
    [data-testid=stMetricValue] {font-size:1.7rem;font-variant-numeric:tabular-nums;}
    [data-testid=stMarkdownContainer] p {max-width:85ch;line-height:1.55;}
    [data-testid=stSidebar] {border-right:1px solid #d8ddd6;}
    [data-testid=stExpander] {border-radius:2px;box-shadow:none;}
    .stButton button,.stDownloadButton button {border-radius:2px;}
    [data-testid=stDataFrame] {border-top:2px solid #223b53;}
    @media(max-width:800px){.stMainBlockContainer{padding:1rem;}h1{font-size:1.65rem!important;}}
    </style>''',unsafe_allow_html=True)
