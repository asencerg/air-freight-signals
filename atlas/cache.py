"""Versioned analytical caches. UI-only filters never rerun the source aggregation."""
import streamlit as st
from atlas.engine import Engine


@st.cache_resource(show_spinner=False,max_entries=4)
def checked_engine(token):
    return Engine()


@st.cache_data(show_spinner=False,max_entries=16)
def research(identity,months,min_departures,min_tonnes,_engine):
    return _engine.analyze(months,min_departures,min_tonnes)


@st.cache_data(show_spinner=False,max_entries=16)
def carrier_names(identity,_engine):
    return _engine.carriers()
