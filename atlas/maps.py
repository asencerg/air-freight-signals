"""Offline geographic figures, with display encodings separate from analysis."""
import json,math
from functools import lru_cache
from pathlib import Path
import plotly.graph_objects as go
from atlas.map_view import FOCUS,route_arc,route_handles,metric,encoding


@lru_cache(maxsize=2)
def background(name):
    return json.loads((Path(__file__).resolve().parents[1]/'assets'/name).read_text(encoding='utf-8'))


def route_map(routes,year,selected=None,mode='Freight volume',view=None,revision=0,emphasized=True):
    view=view or {'x':list(FOCUS['World'][0]),'y':list(FOCUS['World'][1])}
    fig=go.Figure()
    # Three adjacent worlds support continuous Pacific focus without moving observations.
    for name,color,width,fill in [('land-110m.json','#e8e9df',0,'toself'),('coastlines-110m.json','#a4b4b7',.65,None)]:
        xs,ys=[],[]
        for shift in [-360,0,360]:
            for line in background(name):
                xs.extend([p[0]+shift for p in line]+[None]);ys.extend([p[1] for p in line]+[None])
        fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',fill=fill,fillcolor=color,line=dict(color=color,width=width),hoverinfo='skip',showlegend=False))
    rows=routes.to_dict('records');values=[metric(r,year,mode) for r in rows]
    maximum=max([abs(v) for v in values if v is not None and math.isfinite(v)]+[1])
    pairs={(r['origin'],r['destination']) for r in rows};handles=[];positions=route_handles(rows)
    # Draw selection last so its halo and endpoints remain visible above crossing corridors.
    rows.sort(key=lambda r:r['market']==selected)
    for r in rows:
        points=route_arc(r);value=metric(r,year,mode);color,width,label=encoding(value,mode,maximum);chosen=r['market']==selected;active=emphasized and chosen
        reciprocal=(r['destination'],r['origin']) in pairs
        pct=r.get('tonnes_change_pct');pct_text=f'{pct:+.1f}%' if pct is not None and math.isfinite(pct) else 'undefined'
        text=(f"<b>{r['market']}</b><br>{year}: {r[f'tonnes_{year}']:,.0f} metric tonnes · {r[f'departures_{year}']:,.0f} departures"
              f"<br>Freight change: {r['absolute_change_tonnes']:+,.0f} t ({pct_text})<br>HHI change: {r['hhi_change']:+,.0f} points")
        if mode=='Freight change · %' and value is None:text+='<br>Percentage encoding suppressed: baseline below 1,000 t'
        if reciprocal:text+='<br>Reciprocal pair: use the directional handles or corridor list'
        x,y=[],[]
        for shift in [-360,0,360]:
            x.extend([p[0]+shift for p in points]+[None]);y.extend([p[1] for p in points]+[None])
        if active:
            fig.add_trace(go.Scatter(x=x,y=y,mode='lines',line=dict(color='#ffffff',width=width+5),hoverinfo='skip',showlegend=False))
        # Lines provide context; only explicit directional handles receive pointer hits.
        # Nearby parallel and reciprocal lines must not steal another route's handle.
        fig.add_trace(go.Scatter(x=x,y=y,mode='lines',line=dict(color=color,width=width+(.8 if active else 0)),
            opacity=1 if active else .55 if emphasized and selected else .7,
            meta={'role':'route','market':r['market']},hoverinfo='skip',showlegend=False))
        handle=positions[r['market']]
        for shift in [-360,0,360]:handles.append((handle[0]+shift,handle[1],text,r['market'],color,active))
        if chosen:
            for shift in [-360,0,360]:
                i=max(1,len(points)//2)
                fig.add_annotation(x=points[i][0]+shift,y=points[i][1],ax=points[i-2][0]+shift,ay=points[i-2][1],xref='x',yref='y',axref='x',ayref='y',showarrow=True,arrowhead=3,arrowsize=1.6,arrowwidth=2,arrowcolor='#203e55',text='')
                fig.add_trace(go.Scatter(x=[points[0][0]+shift,points[-1][0]+shift],y=[points[0][1],points[-1][1]],mode='markers+text',
                    marker=dict(size=[11,13],color=['#ffffff','#203e55'],line=dict(color='#203e55',width=2),symbol=['circle','diamond']),
                    text=[r['origin']+' · origin',r['destination']+' · destination'],textposition=['bottom right' if points[0][0]+shift<sum(view['x'])/2 else 'bottom left',
                                  'top right' if points[-1][0]+shift<sum(view['x'])/2 else 'top left'],
                    textfont=dict(size=12,color='#203e55'),hoverinfo='skip',showlegend=False))
    fig.add_trace(go.Scatter(x=[h[0] for h in handles],y=[h[1] for h in handles],text=[h[2] for h in handles],customdata=[[h[3]] for h in handles],mode='markers',zorder=10,
        marker=dict(size=[16 if h[5] else 13 for h in handles],color=[h[4] for h in handles],line=dict(color='white',width=1.5),symbol='circle'),
        hovertemplate='%{text}<extra></extra>',showlegend=False))
    tickvals=list(range(-540,541,30));ticktext=[f'{abs((x+180)%360-180)}°'+('W' if (x+180)%360-180<0 else 'E' if (x+180)%360-180>0 else '') for x in tickvals]
    fig.update_layout(height=530,margin=dict(l=36,r=12,t=12,b=26),paper_bgcolor='#f7f6f2',plot_bgcolor='#eaf2f4',font=dict(family='Arial',color='#243b4b'),
        meta={'selected':selected,'highlighted':selected if emphasized else None},
        dragmode='pan',clickmode='event',hovermode='closest',hoverdistance=14,uirevision=f'view-{revision}',
        xaxis=dict(range=view['x'],minallowed=-540,maxallowed=540,title=None,showgrid=True,gridcolor='#d8e3e5',tickvals=tickvals,ticktext=ticktext,tickfont=dict(size=10),zeroline=False,showline=False),
        yaxis=dict(range=view['y'],minallowed=-90,maxallowed=90,title=None,showgrid=True,gridcolor='#d8e3e5',dtick=30,ticksuffix='°',tickfont=dict(size=10),zeroline=False,showline=False))
    return fig
