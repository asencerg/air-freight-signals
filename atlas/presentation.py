"""Shared, bounded research evidence and editorial chart styling."""
import pandas as pd
import streamlit as st
from atlas.engine import TONNES_PER_POUND
from atlas.research import research_brief, evidence_table, briefs_markdown, month_label

COLORS=['#223b53','#397d80','#ad7951','#829191','#96564f','#6b7283']


def style_figure(fig):
    fig.update_layout(template='plotly_white',paper_bgcolor='#f7f6f2',plot_bgcolor='#f7f6f2',font=dict(family='Arial',size=12,color='#29343e'),colorway=COLORS,margin=dict(l=15,r=15,t=45,b=25),legend=dict(orientation='h',y=-.2))
    return fig


@st.cache_data(show_spinner=False,max_entries=64)
def detail_rows(identity,origin,destination,months,_engine):
    return _engine.detail(origin,destination,months)


def render_detail(r,engine,months,names,carrier_labels,key='research'):
    import plotly.express as px
    brief=research_brief(r,names)
    st.subheader(brief['title'])
    st.caption('Analytical observation · '+month_label(months)+' in each year · direction preserved')
    st.markdown('**Observation**');st.write(brief['observation'])
    st.markdown('**Evidence**');st.dataframe(evidence_table(r),hide_index=True,width='stretch')
    st.write(f"Departures {r['departures_change_pct']:+.1f}% · tonnes per departure {r['tonnes_per_departure_change_pct']:+.1f}% · {r['same_direction_months']}/{r['compared_months']} months in the annual-change direction.")
    st.caption('Secondary signals: '+(r['signals'] or 'No rule threshold crossed'))
    rows=detail_rows(engine.identity,r['origin'],r['destination'],tuple(months),engine)
    monthly=rows.groupby(['YEAR','MONTH'],as_index=False)[['FREIGHT','DEPARTURES_PERFORMED']].sum()
    monthly['Metric tonnes']=monthly.FREIGHT*TONNES_PER_POUND;monthly['Year']=monthly.YEAR.astype(str)
    fig=px.line(monthly,x='MONTH',y='Metric tonnes',color='Year',markers=True,color_discrete_sequence=COLORS,labels={'MONTH':'Reporting month'})
    st.plotly_chart(style_figure(fig),width='stretch',key=key+'_monthly')
    table=rows.groupby(['UNIQUE_CARRIER','YEAR']).FREIGHT.sum().unstack('YEAR').reindex(columns=[2024,2025]).fillna(0)*TONNES_PER_POUND
    table.columns=['2024 tonnes','2025 tonnes'];table['Change (tonnes)']=table['2025 tonnes']-table['2024 tonnes']
    for year in [2024,2025]:table[f'{year} share (%)']=table[f'{year} tonnes']/r[f'tonnes_{year}']*100
    table['Net change contribution (%)']=table['Change (tonnes)']/r['absolute_change_tonnes']*100 if r['absolute_change_tonnes'] else float('nan')
    counts=[int((table[f'{y} tonnes']>0).sum()) for y in [2024,2025]]
    st.caption(f'Positive-freight carriers: {counts[0]} → {counts[1]}. Shares and HHI include every reporting carrier; zero-freight shares are zero.')
    table.index=[f'{c} · {carrier_labels.get(c,c)}' for c in table.index]
    st.dataframe(table.round(2),width='stretch')
    st.caption('Contributions may be negative or exceed 100% when carrier changes offset; undefined for zero net change.')
    st.write('Newly positive freight: '+(r['newly_observed'] or 'None')+'. No longer positive: '+(r['no_longer_observed'] or 'None')+'. These are reporting-window observations, not verified launches or exits.')
    st.markdown('**Interpretation**');st.write(brief['interpretation'])
    st.markdown('**Next investigation**');st.write(brief['next_investigation'])
    st.markdown('**Limitations**');st.caption(brief['limitations'])
    data=briefs_markdown(pd.DataFrame([r]),names,engine.source)+'\n\nDataset SHA-256: '+engine.identity
    st.download_button('Download selected brief',data.encode('utf-8'),'corridor.md','text/markdown; charset=utf-8',key=key+'_brief')
    st.download_button('Download monthly evidence CSV',monthly.to_csv(index=False).encode('utf-8-sig'),'monthly-evidence.csv','text/csv; charset=utf-8',key=key+'_csv')
