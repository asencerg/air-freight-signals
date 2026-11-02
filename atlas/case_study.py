"""Display the fixed, reviewed real-data case without changing upload analysis."""
from pathlib import Path
import hashlib
import json
import plotly.io as pio
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'docs/cases/szx-anc'


def render_featured_case():
    report = CASE / 'case-study.md'
    if not report.exists():
        return
    import pandas as pd
    from atlas.presentation import style_figure, COLORS
    text=report.read_text(encoding='utf-8')
    annual=pd.read_csv(CASE/'annual.csv').set_index('YEAR')
    sections={part.split('\n',1)[0]:part.split('\n',1)[1] for part in text.split('\n## ')[1:]}
    st.subheader('Shenzhen → Anchorage')
    st.caption('CASE STUDY / Growth with broader reporting-carrier participation · full calendar years 2024–2025')
    st.write('Freight grew while carrier concentration fell in every comparable month. The evidence supports investigation of the changing service mix, not conclusions about cargo customers or unmet demand.')
    cols=st.columns(3)
    cols[0].metric('2025 freight',f"{annual.loc[2025,'tonnes']:,.0f} t",f"{(annual.loc[2025,'tonnes']/annual.loc[2024,'tonnes']-1)*100:+.2f}%")
    cols[1].metric('2025 departures',f"{annual.loc[2025,'departures']:,.0f}",f"{(annual.loc[2025,'departures']/annual.loc[2024,'departures']-1)*100:+.2f}%")
    cols[2].metric('Carrier HHI',f"{annual.loc[2025,'hhi']:,.0f}",f"{annual.loc[2025,'hhi']-annual.loc[2024,'hhi']:+,.0f}",delta_color='off')
    st.subheader('Market evolution')
    table=annual[['tonnes','departures','tonnes_per_departure','hhi']].rename(columns={'tonnes':'Freight (metric tonnes)','departures':'Departures','tonnes_per_departure':'Tonnes / departure','hhi':'HHI'})
    st.dataframe(table.round(2),width='stretch')
    def chart(number):
        fig=pio.from_json((CASE/f'chart-{number}.json').read_text(encoding='utf-8'))
        for i,trace in enumerate(fig.data):
            label=str(trace.name or '')
            color=COLORS[0] if '2024' in label else COLORS[1] if '2025' in label else COLORS[i%len(COLORS)]
            if hasattr(trace,'line'):trace.line.color=color
            if hasattr(trace,'marker'):trace.marker.color=color
        st.plotly_chart(style_figure(fig),width='stretch',key=f'szx-chart-{number}')
    cols=st.columns(2)
    with cols[0]:chart(1)
    with cols[1]:chart(2)
    st.subheader('Carrier composition')
    st.caption('UPS increased absolute freight but its share declined. Newly observed FedEx, Polar and Western Global freight accounts for about 59% of net growth; these are not verified first-ever route entry dates.')
    st.dataframe(pd.read_csv(CASE/'carriers.csv').round(2),hide_index=True,width='stretch')
    chart(3)
    st.subheader('Monthly consistency')
    st.write('Freight increased in 11 of 12 matched months. HHI was lower in all 12; diversification is not confined to a short annual pooling effect.')
    chart(4)
    st.subheader('Interpretation and next investigation')
    st.markdown(sections['6. Commercial interpretation: observations versus hypotheses'])
    with st.expander('Featured research · Full methodology, limitations and source narrative'):
        st.markdown(text)
    st.caption('Sources: official BTS T-100 All Carriers exports. Freight pounds × 0.00045359237 = metric tonnes; mail excluded. Fixed case independent of current filters. No capacity utilization, customers or contracts inferred.')
    html_report = CASE / 'case-study.html'
    if html_report.exists():
        st.download_button('Download case study with charts (HTML)', html_report.read_bytes(), 'szx-anc-case-study.html', 'text/html')
    st.download_button('Download case study (Markdown)', report.read_text(encoding='utf-8'), 'szx-anc-case-study.md', 'text/markdown')
    audit = json.loads((CASE / 'audit.json').read_text(encoding='utf-8'))
    source = ROOT / audit.get('source_extract_path', 'data/validated/szx-anc-source.csv')
    if source.exists() and hashlib.sha256(source.read_bytes()).hexdigest() == audit['source_extract_sha256']:
        st.download_button('Inspect underlying source observations (126 rows, CSV)', source.read_bytes(), 'szx-anc-source.csv', 'text/csv')
    else:
        st.caption('Local observation extract unavailable or changed. Use the pinned source-file links in the case or regenerate it from the retained annual files.')
