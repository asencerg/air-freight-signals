"""Lazy geographic workflow over the same corridor records used by research."""
import pandas as pd
import streamlit as st
from atlas.geography import locate,coverage
from atlas.presentation import render_detail


def render_explorer(records,airports,engine,months,names,carrier_labels):
    from atlas.maps import route_map
    from atlas.map_component import render_map
    from atlas.map_view import FOCUS, MODES, LEGENDS, fit_corridor, valid_view
    st.subheader('Cargo Corridor Explorer')
    st.caption('Reported segments, not flight tracks or shipment journeys · eligible matched-period corridors only')
    if airports.empty:
        st.info('Verified endpoint metadata is unavailable for this uploaded dataset. Research remains available; no guessed coordinates are mapped.')
        return
    geo=locate(records,airports)
    controls=st.columns([1,2,1])
    year=controls[0].selectbox('Map reporting year',[2025,2024],key='map_year')
    mode=controls[1].selectbox('Map encoding',MODES,key='map_mode')
    cap=controls[2].select_slider('Maximum mapped routes',options=[10,25,50,75,100],value=25,key='map_cap')
    with st.expander('Geographic filters'):
        direction=st.selectbox('Change perspective',['All changes','Growth','Contraction'],key='map_change')
        hub=st.selectbox('Airport hub (filters corridors)',['All']+sorted(set(geo.origin)|set(geo.destination)),key='map_hub')
        hub_direction=st.radio('Hub direction',['Both directions','Outbound','Inbound'],horizontal=True,key='map_hub_direction')
        cols=st.columns(2)
        origin=cols[0].selectbox('Origin airport',['All']+sorted(geo.origin.unique()),key='map_origin')
        destination=cols[1].selectbox('Destination airport',['All']+sorted(geo.destination.unique()),key='map_destination')
        countries=sorted(set(geo.origin_country_name.dropna())|set(geo.destination_country_name.dropna()))
        country=cols[0].selectbox('Country (either verified endpoint)',['All']+countries,key='map_country')
        region=cols[1].selectbox('Region (either verified endpoint)',['All']+sorted(set(geo.origin_region_name.dropna())|set(geo.destination_region_name.dropna())),key='map_region')
        minimum=st.number_input('Minimum selected-year freight (metric tonnes)',min_value=0,key='map_min')
        search=st.text_input('Directional corridor search',key='map_search',placeholder='SZX → ANC').strip().casefold()
    if origin!='All':geo=geo[geo.origin==origin]
    if destination!='All':geo=geo[geo.destination==destination]
    if country!='All':geo=geo[(geo.origin_country_name==country)|(geo.destination_country_name==country)]
    if region!='All':geo=geo[(geo.origin_region_name==region)|(geo.destination_region_name==region)]
    if search:geo=geo[geo.market.str.casefold().str.contains(search,regex=False)]
    if direction=='Growth':geo=geo[geo.absolute_change_tonnes>0]
    if direction=='Contraction':geo=geo[geo.absolute_change_tonnes<0]
    geo=geo[geo[f'tonnes_{year}']>=minimum]
    # Reserve a stable map position when the hub summary appears or clears.
    hub_summary=st.empty()
    if hub!='All':
        mask=(geo.origin==hub)|(geo.destination==hub)
        if hub_direction=='Outbound':mask=geo.origin==hub
        if hub_direction=='Inbound':mask=geo.destination==hub
        geo=geo[mask]
        hub_summary.caption(f'{hub} · {hub_direction.lower()} · {len(geo):,} eligible directional corridors · {geo[f"tonnes_{year}"].sum():,.0f} metric tonnes · {geo[f"departures_{year}"].sum():,.0f} performed departures ({year}). This filters the analytical population; no global-network claim.')
    cov=coverage(geo,year)
    fmt=lambda v:'No denominator' if v is None else f'{v:.2f}%'
    st.caption(f"{year} mapped coverage · {cov['mapped_corridors']:,}/{cov['corridors']:,} eligible corridors · {fmt(cov['freight_pct'])} freight · {fmt(cov['departures_pct'])} departures")
    mapped=geo[geo.mappable].sort_values([f'tonnes_{year}','market'],ascending=[False,True]).head(cap)
    st.caption(f'Top {len(mapped)} routes by {year} freight · coverage measured before the display cap.')
    if mapped.empty:
        st.session_state['map_was_empty']=True
        st.info('No safely mappable corridors match these filters. Clear filters or inspect unmapped evidence below.')
    else:
        if st.session_state.pop('map_was_empty',False):
            st.session_state['map_mount']=st.session_state.get('map_mount',0)+1
        options=mapped.market.tolist()
        # Explicitly synchronize recreated controls with their retained Python values.
        current=st.session_state.get('map_selected')
        st.session_state['map_selected']=current if current in options else options[0]
        if 'map_highlight' not in st.session_state or current not in options:
            st.session_state['map_highlight']=st.session_state['map_selected']
        def highlight_selection():
            st.session_state['map_highlight']=st.session_state['map_selected']
        nav=st.columns([3,2,1,1],vertical_alignment='bottom')
        selected=nav[0].selectbox('Selected directional corridor',options,key='map_selected',on_change=highlight_selection,help='Search by airport code. Direction matters: A → B is separate from B → A. List contains the displayed top-N routes.')
        st.session_state['map_focus']=st.session_state.get('map_focus',st.session_state.get('map_applied_focus','World'))
        focus=nav[1].selectbox('Geographic focus',list(FOCUS),key='map_focus',format_func=lambda name: 'North Pacific' if name=='East Asia / North Pacific' else name,help='Moves the camera only; does not filter corridors or change coverage. North Pacific covers East Asia and the northern Pacific Ocean.')
        if st.session_state.get('map_applied_focus')!=focus:
            st.session_state['map_view']={'x':list(FOCUS[focus][0]),'y':list(FOCUS[focus][1])}
            st.session_state['map_epoch']=st.session_state.get('map_epoch',0)+1
            st.session_state['map_applied_focus']=focus
        if nav[2].button('Fit corridor',help='Includes every point of the selected great-circle arc, including its dateline crossing.'):
            st.session_state['map_view']=fit_corridor(mapped[mapped.market==selected].iloc[0].to_dict())
            st.session_state['map_epoch']=st.session_state.get('map_epoch',0)+1
        def reset_view():
            st.session_state['map_view']={'x':list(FOCUS['World'][0]),'y':list(FOCUS['World'][1])}
            st.session_state['map_epoch']=st.session_state.get('map_epoch',0)+1
            st.session_state['map_focus']='World'
            st.session_state['map_applied_focus']='World'
        nav[3].button('Reset view',on_click=reset_view)
        # Explicit mount generations avoid reusing a removed component's frontend data.
        canvas_key=f"corridor_canvas_{st.session_state.get('map_mount',0)}"
        def on_map_event():
            event=st.session_state.get(canvas_key,{}).get('event')
            if not event or event.get('epoch')!=st.session_state.get('map_epoch',0):return
            if valid_view(event.get('view')):st.session_state['map_view']=event['view']
            if event.get('kind')=='select' and event.get('market') in options:
                st.session_state['map_selected']=event['market']
                st.session_state['map_highlight']=event['market']
            elif event.get('kind')=='clear':
                st.session_state['map_highlight']=None
        fig=route_map(mapped,year,selected,mode,st.session_state.get('map_view'),st.session_state.get('map_epoch',0),emphasized=st.session_state.get('map_highlight')==selected)
        render_map(fig,st.session_state.get('map_epoch',0),on_map_event,key=canvas_key)
        st.caption(LEGENDS[mode])
        st.caption('Hollow circle = origin · filled diamond = destination · arrow = direction. Click a large directional handle or use the searchable corridor list; route lines do not intercept selections. Click empty map space to clear emphasis while keeping the research selection. Pan / wheel zoom; focus controls move the view only.')
        st.caption('Plate Carrée · great-circle context, not flown tracks. Coastline and land: Natural Earth 1:110m (public domain). Airport references: OurAirports. No remote tiles or API keys.')
        r=mapped[mapped.market==selected].iloc[0].to_dict()
        render_detail(r,engine,months,names,carrier_labels,key='map')
    with st.expander('Geographic coverage and unresolved endpoints'):
        st.write(f"Reference snapshot: {int(airports.coordinate_match.sum()):,}/{len(airports):,} airport codes matched; {int(airports.match_status.eq('unmatched_iata').sum())} unmatched; {int(airports.match_status.eq('country_conflict').sum())} country conflicts. These code counts do not measure freight coverage.")
        st.write(f"Current selection omits {cov['unmapped_tonnes']:,.0f} tonnes and {cov['unmapped_departures']:,.0f} departures from mapping, not from analysis.")
        st.dataframe(cov['impacts'].round(2),width='stretch')
        missing=geo[~geo.mappable].sort_values(f'tonnes_{year}',ascending=False)
        st.dataframe(missing[['market',f'tonnes_{year}',f'departures_{year}','map_status']].head(15),hide_index=True)
        st.download_button('Export geographic coverage evidence',geo[['market','mappable','map_status',f'tonnes_{year}',f'departures_{year}']].to_csv(index=False).encode('utf-8-sig'),'geographic-coverage.csv','text/csv; charset=utf-8')
