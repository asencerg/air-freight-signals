"""Local-only Plate Carrée map. Imported only on explorer/case activation."""
import json,math
from pathlib import Path
import plotly.graph_objects as go
from atlas.geography import great_circle


def route_map(routes,year,selected=None):
    fig=go.Figure()
    coast=json.loads((Path(__file__).resolve().parents[1]/'assets/coastlines-110m.json').read_text(encoding='utf-8'))
    xs,ys=[],[]
    for line in coast:
        for i,(x,y) in enumerate(line):
            if i and abs(x-line[i-1][0])>180:xs.append(None);ys.append(None)
            xs.append(x);ys.append(y)
        xs.append(None);ys.append(None)
    fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines',line=dict(color='#b5bbb5',width=.6),hoverinfo='skip',showlegend=False))
    max_t=max(float(routes[f'tonnes_{year}'].max()),1) if len(routes) else 1
    centers={'Increase / unchanged':([],[],[],[]),'Decrease':([],[],[],[])}
    for r in routes.to_dict('records'):
        parts=great_circle(r['origin_longitude_deg'],r['origin_latitude_deg'],r['destination_longitude_deg'],r['destination_latitude_deg'])
        x,y=[],[]
        for part in parts:
            x += [v[0] for v in part]+[None];y += [v[1] for v in part]+[None]
        kind='Increase / unchanged' if r['absolute_change_tonnes']>=0 else 'Decrease'
        color='#285f65' if kind=='Increase / unchanged' else '#a55444'
        active=r['market']==selected
        text=f"{r['market']}<br>{year}: {r[f'tonnes_{year}']:,.0f} metric tonnes<br>{r[f'departures_{year}']:,.0f} departures<br>Change: {r['absolute_change_tonnes']:+,.0f} tonnes ({r['tonnes_change_pct']:+.1f}%)<br>HHI change: {r['hhi_change']:+,.0f}"
        fig.add_trace(go.Scatter(x=x,y=y,mode='lines+markers',customdata=[[r['market']] for _ in x],marker=dict(size=1,opacity=0),line=dict(color='#192e45' if active else color,width=(3 if active else .6+2*math.sqrt(r[f'tonnes_{year}']/max_t))),opacity=1 if active else .55,hoverinfo='skip',showlegend=False))
        # A handle 40% along the directed arc separates reciprocal-route selection points.
        cx,cy,ct,cd=centers[kind];points=[point for part in parts for point in part];handle=points[int((len(points)-1)*.4)]
        cx.append(handle[0]);cy.append(handle[1]);ct.append(text);cd.append([r['market']])
        if active:
            part=max(parts,key=len);i=max(1,len(part)//2)
            fig.add_annotation(x=part[i][0],y=part[i][1],ax=part[i-1][0],ay=part[i-1][1],xref='x',yref='y',axref='x',ayref='y',showarrow=True,arrowhead=3,arrowsize=1.7,arrowwidth=2,arrowcolor='#192e45',text='')
            fig.add_trace(go.Scatter(x=[r['origin_longitude_deg'],r['destination_longitude_deg']],y=[r['origin_latitude_deg'],r['destination_latitude_deg']],mode='markers+text',marker=dict(size=9,color='#192e45',symbol=['circle','diamond']),text=[r['origin'],r['destination']],textposition=['bottom center','top center'],showlegend=False,hoverinfo='text'))
    for kind,(x,y,text,data) in centers.items():
        fig.add_trace(go.Scatter(x=x,y=y,text=text,customdata=data,mode='markers',name=kind+' · route handle',marker=dict(size=7,color='#285f65' if kind=='Increase / unchanged' else '#a55444',symbol='circle' if kind=='Increase / unchanged' else 'diamond'),hovertemplate='%{text}<extra></extra>'))
    fig.update_layout(height=485,margin=dict(l=0,r=0,t=5,b=5),paper_bgcolor='#f7f6f2',plot_bgcolor='#f1f2ee',font=dict(family='Arial',color='#24303a'),legend=dict(orientation='h',y=1.04,x=0),dragmode='pan',clickmode='event+select',uirevision='atlas-world',xaxis=dict(range=[-180,180],title=None,showgrid=True,gridcolor='#e0e2dc',dtick=60,zeroline=False),yaxis=dict(range=[-60,85],title=None,showgrid=True,gridcolor='#e0e2dc',dtick=30,zeroline=False))
    return fig
