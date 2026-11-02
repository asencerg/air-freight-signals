"""Lazy geographic workflow over the same corridor records used by research."""
import pandas as pd
import streamlit as st
from atlas.geography import locate,coverage
from atlas.presentation import render_detail


def render_explorer(records,airports,engine,months,names,carrier_labels):
    from atlas.maps import route_map
    st.subheader('Cargo Corridor Explorer')
    st.caption('Reported segments, not flight tracks or shipment journeys · eligible matched-period corridors only')
    if airports.empty:
        st.info('Verified endpoint metadata is unavailable for this uploaded dataset. Research remains available; no guessed coordinates are mapped.')
        return
    geo=locate(records,airports)
    controls=st.columns([1,1,1])
    year=controls[0].selectbox('Map reporting year',[2025,2024],key='map_year')
    direction=controls[1].selectbox('Change perspective',['All changes','Growth','Contraction'],key='map_change')
    cap=controls[2].select_slider('Maximum mapped routes',options=[10,25,50,75,100],value=25,key='map_cap')
    with st.expander('Geographic filters'):
        cols=st.columns(2)
        origin=cols[0].selectbox('Origin airport',['All']+sorted(geo.origin.unique()),key='map_origin')
        destination=cols[1].selectbox('Destination airport',['All']+sorted(geo.destination.unique()),key='map_destination')
        countries=sorted(set(geo.origin_country_name.dropna())|set(geo.destination_country_name.dropna()))
        country=cols[0].selectbox('Country (either verified endpoint)',['All']+countries,key='map_country')
        region=cols[1].selectbox('Region (either verified endpoint)',['All']+sorted(set(geo.origin_region_name.dropna())|set(geo.destination_region_name.dropna())),key='map_region')
        minimum=st.number_input('Minimum selected-year freight (metric tonnes)',min_value=0,value=0,key='map_min')
        search=st.text_input('Directional corridor search',key='map_search',placeholder='SZX → ANC').strip().casefold()
    if origin!='All':geo=geo[geo.origin==origin]
    if destination!='All':geo=geo[geo.destination==destination]
    if country!='All':geo=geo[(geo.origin_country_name==country)|(geo.destination_country_name==country)]
    if region!='All':geo=geo[(geo.origin_region_name==region)|(geo.destination_region_name==region)]
    if search:geo=geo[geo.market.str.casefold().str.contains(search,regex=False)]
    if direction=='Growth':geo=geo[geo.absolute_change_tonnes>0]
    if direction=='Contraction':geo=geo[geo.absolute_change_tonnes<0]
    geo=geo[geo[f'tonnes_{year}']>=minimum]
    cov=coverage(geo,year)
    fmt=lambda v:'No denominator' if v is None else f'{v:.2f}%'
    st.caption(f"{year} mapped coverage · {cov['mapped_corridors']:,}/{cov['corridors']:,} eligible corridors · {fmt(cov['freight_pct'])} freight · {fmt(cov['departures_pct'])} departures")
    mapped=geo[geo.mappable].sort_values([f'tonnes_{year}','market'],ascending=[False,True]).head(cap)
    st.caption(f'Map: top {len(mapped)} of {cov["mapped_corridors"]:,} mappable routes by {year} freight. Coverage includes all filtered eligible routes before this cap.')
    if mapped.empty:
        st.info('No safely mappable corridors match these filters. Clear filters or inspect unmapped evidence below.')
    else:
        options=mapped.market.tolist()
        pending=st.session_state.pop('map_pending',None)
        if pending in options:st.session_state['map_selected']=pending
        if st.session_state.get('map_selected') not in options:st.session_state['map_selected']=options[0]
        selected=st.selectbox('Selected directional corridor',options,key='map_selected')
        fig=route_map(mapped,year,selected)
        event=st.plotly_chart(fig,width='stretch',key='corridor_map_'+selected,on_select='rerun',selection_mode='points',config={'scrollZoom':True,'displaylogo':False})
        points=event.selection.points
        if points:
            data=points[-1].get('customdata',[])
            market=data[0] if isinstance(data,list) and data else None
            if market in options and market!=selected:
                st.session_state['last_map_click']=market
                st.session_state['map_pending']=market
                st.rerun()
        st.caption('Plate Carrée projection · great-circle arcs split at ±180° · not actual flown tracks. Width ∝ square root of freight except the fixed-width selected highlight; teal/circle = increase or unchanged, rust/diamond = decline. Route handles are selectable. Selected route arrow points origin → destination. Pan/zoom enabled; double-click resets view.')
        st.caption('Coastline: Natural Earth 1:110m (public domain). Airport references: OurAirports. No remote map tiles or API keys.')
        r=mapped[mapped.market==selected].iloc[0].to_dict()
        render_detail(r,engine,months,names,carrier_labels,key='map')
    with st.expander('Geographic coverage and unresolved endpoints'):
        st.write(f"Reference snapshot: {int(airports.coordinate_match.sum()):,}/{len(airports):,} airport codes matched; {int(airports.match_status.eq('unmatched_iata').sum())} unmatched; {int(airports.match_status.eq('country_conflict').sum())} country conflicts. These code counts do not measure freight coverage.")
        st.write(f"Current selection omits {cov['unmapped_tonnes']:,.0f} tonnes and {cov['unmapped_departures']:,.0f} departures from mapping, not from analysis.")
        st.dataframe(cov['impacts'].round(2),width='stretch')
        missing=geo[~geo.mappable].sort_values(f'tonnes_{year}',ascending=False)
        st.dataframe(missing[['market',f'tonnes_{year}',f'departures_{year}','map_status']].head(15),hide_index=True)
        st.download_button('Export geographic coverage evidence',geo[['market','mappable','map_status',f'tonnes_{year}',f'departures_{year}']].to_csv(index=False).encode('utf-8-sig'),'geographic-coverage.csv','text/csv; charset=utf-8')
