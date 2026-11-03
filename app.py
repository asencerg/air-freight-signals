from pathlib import Path
import calendar
import math
import pandas as pd
import streamlit as st
from atlas.ingest import read_dataset, combine_datasets, airport_names
from atlas.reference import reference_metadata, match_airports
from atlas.analysis import findings, LIMITATIONS
from atlas.research import RANKINGS, rank_corridors, airport_labels, briefs_markdown, month_label
from atlas.engine import Engine, version_token
from atlas.cache import checked_engine, research as cached_research, carrier_names as cached_carriers
from atlas.presentation import render_detail
from atlas.style import apply_style
from atlas import packaged

st.set_page_config(page_title='Air Freight Signals',layout='wide')
apply_style()
st.title('Air Freight Signals')
st.caption('Evidence of change across aviation freight corridors.')
st.caption('AVIATION RESEARCH / 2024–2025 · Reported directional segments, not global shipment flows')
view=st.sidebar.radio('Explore',['Market Overview','Cargo Corridor Explorer','Research Findings','Case Studies'],key='view')
if st.session_state.get('map_workspace')!=view:
    st.session_state['map_mount']=st.session_state.get('map_mount',0)+1
    st.session_state['map_workspace']=view
if view=='Case Studies':
    from atlas.case_study import render_featured_case
    render_featured_case()
    st.stop()

period=st.sidebar.selectbox('Matched reporting period',['Full year','Q1 · Jan–Mar','Q2 · Apr–Jun','Q3 · Jul–Sep','Q4 · Oct–Dec','Custom months'],key='period')
periods={'Full year':list(range(1,13)),'Q1 · Jan–Mar':[1,2,3],'Q2 · Apr–Jun':[4,5,6],'Q3 · Jul–Sep':[7,8,9],'Q4 · Oct–Dec':[10,11,12]}
with st.sidebar.expander('Advanced data controls'):
    uploads=st.file_uploader('Optional BTS files (replace bundled data)',type=['zip','csv','parquet'],accept_multiple_files=True)
    custom=st.multiselect('Custom matched months',range(1,13),default=list(range(1,13)),format_func=lambda m:calendar.month_abbr[m],key='months') if period=='Custom months' else None
    minimum=st.number_input('Minimum tonnes per pair in each period',min_value=1,value=100)
    minimum_departures=st.number_input('Minimum departures in each period',min_value=1,value=30)
months=custom if period=='Custom months' else periods[period]
if not months:
    st.info('Select at least one matched calendar month.');st.stop()
try:
    if uploads:
        uploaded=combine_datasets([read_dataset(u.getvalue(),u.name) for u in uploads])
        engine=Engine(rows=uploaded.rows,source=uploaded.sha256)
    elif packaged.available():
        engine=checked_engine(version_token())
    else:
        st.info('Upload official BTS files under Advanced data controls; the processed bundle is absent from this checkout. The fixed case remains available under Case Studies.');st.stop()
except (ValueError,OSError,pd.errors.ParserError,UnicodeDecodeError) as exc:
    st.error(f'Cannot load research data: {exc}');st.stop()
names=airport_labels(engine.airports)
labels=cached_carriers(engine.identity,engine)
carrier_labels=dict(zip(labels.carrier,labels.name))
with st.spinner('Comparing official reporting periods…'):
    evidence,shares,universe=cached_research(engine.identity,tuple(sorted(months)),minimum_departures,minimum,engine)
st.caption(('Loaded official 2024–2025 BTS research data automatically.' if not uploads else 'Using uploaded reporting data.')+' Metric tonnes · '+month_label(months)+' in each year')
if universe.empty:
    st.info('No corridors meet the matched-month and minimum-volume requirements.');st.stop()
query=st.sidebar.text_input('Search airport code, name or directional corridor',key='search',placeholder='SZX, Anchorage or SZX → ANC').strip().casefold()
airport = st.sidebar.selectbox('Airport (either end)', ['All'] + sorted(set(universe.origin) | set(universe.destination)), key='airport', format_func=lambda c: f'{c} · {names[c]}' if c in names else c)
carrier_codes = sorted(carrier_labels)
carrier = st.sidebar.selectbox('Carrier present in market', ['All'] + carrier_codes, key='carrier', format_func=lambda c: f'{c} · {carrier_labels[c]}' if c in carrier_labels else c)
signal_options = sorted({v for s in universe.signals for v in s.split('; ') if v})
signal = st.sidebar.selectbox('Analytical signal', ['All'] + signal_options, key='signal')
filtered = universe.copy()
if airport != 'All': filtered = filtered[(filtered.origin == airport) | (filtered.destination == airport)]
if carrier != 'All':
    pairs = shares[shares.carrier == carrier][['origin','destination']].drop_duplicates()
    filtered = filtered.merge(pairs, on=['origin','destination'])
if signal != 'All': filtered = filtered[filtered.signals.map(lambda s: signal in s.split('; '))]
if query:
    searchable = filtered.market + ' ' + filtered.origin.map(names).fillna('') + ' ' + filtered.destination.map(names).fillna('')
    filtered = filtered[searchable.str.casefold().str.contains(query, regex=False)]

def reset_filters():
    for key in ['airport','carrier','signal']:st.session_state[key]='All'
    st.session_state['search']=''
    st.session_state['period']='Full year'
    for key in ['map_origin','map_destination','map_country','map_region']:st.session_state[key]='All'
    st.session_state['map_search']=''
    st.session_state['map_min']=0
    st.session_state['map_hub']='All'
    st.session_state['map_hub_direction']='Both directions'
    st.session_state['map_change']='All changes'
st.sidebar.button('Reset filters',on_click=reset_filters)
with st.sidebar.expander('Sources and methodology'):
    st.caption(engine.source)
    st.caption('Freight pounds × 0.00045359237 = metric tonnes. Mail excluded. Carrier filters select markets, not HHI denominators. At least every selected month must be reported in both years.')
    st.caption(LIMITATIONS)
    st.caption('Independent analysis; no DOT endorsement. Source-specific data terms: docs/data-provenance.md.')
    st.caption('Dataset SHA-256: '+engine.identity)
    st.markdown('[Research methodology](https://github.com/asencerg/air-freight-signals/blob/main/docs/methodology.md)')
with st.sidebar.expander('Optional reference enrichment'):
    if st.checkbox('Load reference controls'):
        reference=st.file_uploader('OurAirports airports.csv',type='csv')
        regions=st.file_uploader('OurAirports regions.csv',type='csv')
        countries=st.file_uploader('OurAirports countries.csv',type='csv')
        try:
            if reference and regions and countries:
                metadata=reference_metadata(reference.getvalue(),regions.getvalue(),countries.getvalue())
                # Explicit upload-only path; normal startup never materializes source rows.
                source_rows=engine.rows if engine.rows is not None else packaged.load_bundle()[0].rows
                st.dataframe(match_airports(source_rows,metadata),hide_index=True)
                st.caption('Unique IATA and country agreement only; conflicts remain unmapped.')
            elif reference:
                st.dataframe(pd.DataFrame(airport_names(reference.getvalue()).items(),columns=['Code','Name']))
        except (ValueError,pd.errors.ParserError,UnicodeDecodeError) as exc:
            st.error(f'Cannot enrich references: {exc}')
if view=='Cargo Corridor Explorer':
    from atlas.explorer import render_explorer
    render_explorer(filtered,engine.airports,engine,months,names,carrier_labels)
    st.stop()
if view=='Research Findings':
    st.subheader('Research Findings')
    st.caption('One primary record per directional corridor; inspect secondary signals within the evidence.')

if view=='Market Overview':
    cols=st.columns(3)
    total24=float(filtered.tonnes_2024.sum());total25=float(filtered.tonnes_2025.sum())
    cols[0].metric('2025 reported segment tonnes',f'{total25:,.0f}',f'{(total25/total24-1)*100:+.1f}%' if total24 else None)
    cols[1].metric('Absolute freight change',f'{total25-total24:+,.0f} t')
    cols[2].metric('Eligible directional corridors',f'{len(filtered):,}')
    st.caption('Totals cover the filtered eligible corridor scope, not all source records or unique shipments. A consignment may be reported on successive segments.')
st.subheader('Market developments')
growth = rank_corridors(filtered, 'Freight growth')
contraction = rank_corridors(filtered, 'Freight contraction')
if not growth.empty and not contraction.empty:
    g, c = growth.iloc[0], contraction.iloc[0]
    st.write(f"Largest absolute increase: **{g.market}**, +{g.absolute_change_tonnes:,.0f} tonnes; largest decline: **{c.market}**, {c.absolute_change_tonnes:,.0f} tonnes. These are reported segment changes, not estimates of customer demand.")

controls = st.columns([1, 2])
category = controls[0].selectbox('Research question', RANKINGS, key='category')
controls[1].caption('Search and market filters are in the sidebar. Full eligible universe removes editorial size screens.')
ranked = rank_corridors(filtered, category)
page_size = 15
pages = max(1, math.ceil(len(ranked) / page_size))
# Reset pagination when the filtered universe or ranking changes.
page_key = (category, query, airport, carrier, signal, tuple(months), minimum, minimum_departures)
page = st.selectbox('Results page', list(range(1, pages + 1)), key='page_' + repr(page_key))
shown = ranked.iloc[(page-1)*page_size:page*page_size]
st.caption(f'{len(ranked):,} corridors match this view · page {page} of {pages} · showing {len(shown)}. Select Full eligible universe to remove editorial screens.')
if shown.empty:
    st.info('No corridors match this view. Try Full eligible universe or broaden the filters.')
else:
    table = pd.DataFrame({
        'Corridor': shown.market,
        'Research issue': shown.primary_issue,
        'Change (tonnes)': shown.absolute_change_tonnes.map(lambda v: f'{v:+,.0f}'),
        '2024 tonnes': shown.tonnes_2024.map(lambda v: f'{v:,.0f}'),
        '2025 tonnes': shown.tonnes_2025.map(lambda v: f'{v:,.0f}'),
        'Months in same direction': shown.same_direction_months.astype(str) + '/' + shown.compared_months.astype(str),
        'Change (%)': shown.tonnes_change_pct.map(lambda v: f'{v:+.1f}%'),
        'HHI change': shown.hhi_change.map(lambda v: f'{v:+,.0f}'),
        'Leading carrier change': shown.leading_carrier + ' · ' + shown.leading_carrier_change_tonnes.map(lambda v: f'{v:+,.0f} t'),
    })
    st.dataframe(table, hide_index=True, width='stretch', height=390)

with st.expander('Why these corridors rank highly'):
    st.caption('Carrier filters select markets; all-carrier HHI and shares are preserved. Overview totals use the filtered eligible universe.')
    if category == 'Full eligible universe':
        st.caption('Every eligible corridor, ordered by absolute tonne change; no editorial size screen. A → B and B → A remain separate.')
    else:
        st.caption('Editorial screen: ≥1,000 tonnes in each period; growth/decline also requires ≥500 tonnes absolute change. Carrier structure uses ≥500 HHI change or newly/absent positive-freight carriers. These are review thresholds, not statistical significance.')
        st.caption('Order: ' + ('smaller of the two market sizes, then directional monthly persistence, then absolute tonne change.' if category == 'Carrier structure' else 'absolute tonne change, then directional monthly persistence, then smaller market size.') + ' No weighted score.')


selected=st.selectbox('Open corridor evidence',['Choose a corridor']+shown.market.tolist(),key=f'detail_{page}_{category}')
if selected!='Choose a corridor' and selected in set(shown.market):
    render_detail(shown[shown.market==selected].iloc[0].to_dict(),engine,months,names,carrier_labels)
with st.expander('Export research and underlying analytical signals'):
    st.caption('Exports cover all matching eligible corridors before editorial ranking screens and pagination. Clear filters for the full universe. Signal rows remain separate only in the signal export.')
    if st.checkbox('Prepare exports', key='exports'):
        exported = filtered.assign(source=engine.source, dataset_sha256=engine.identity)
        st.download_button('Export findings CSV', exported.to_csv(index=False).encode('utf-8-sig'), 'corridors.csv', 'text/csv; charset=utf-8')
        st.download_button('Export findings Markdown', briefs_markdown(filtered,names,engine.source).encode('utf-8'), 'corridors.md', 'text/markdown; charset=utf-8')
        signals = findings(filtered).assign(source=engine.source, dataset_sha256=engine.identity)
        st.download_button('Export original analytical signals CSV', signals.to_csv(index=False).encode('utf-8-sig'), 'signals.csv', 'text/csv; charset=utf-8')
st.caption('Independent research observations, not commercial opportunity forecasts. Source details and limitations: Sources and methodology in the sidebar.')
