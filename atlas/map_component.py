"""Local Plotly bridge: explicit viewport events survive figure changes and reruns."""
import json
from pathlib import Path
import streamlit as st
from streamlit.components.v2 import component


@st.cache_resource(show_spinner=False)
def _component():
    from plotly.offline import get_plotlyjs
    # Use the installed Plotly bundle and its notices, not a CDN or vendored copy.
    js=get_plotlyjs()+'\n'+(Path(__file__).with_name('map_component.js')).read_text(encoding='utf-8')
    return component('signals_corridor_map',html='<div class="signals-map" aria-label="Interactive directional freight corridor map"></div>',js=js)


def render_map(fig,epoch,on_event,*,key):
    return _component()(key=key,data={'figure':json.loads(fig.to_json()),'epoch':epoch},
                        on_event_change=on_event,isolate_styles=False,height='content')
