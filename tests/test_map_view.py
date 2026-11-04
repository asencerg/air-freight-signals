"""Display geometry, focus, encoding and state contracts independent of source facts."""
import math
import pytest
from atlas.map_view import longitude,arc,route_handles,fit_corridor,valid_view,FOCUS,MODES,LEGENDS,metric,encoding
from atlas.maps import route_map
from atlas.engine import Engine
from atlas.geography import locate,coverage


@pytest.fixture(scope='module')
def routes():
 e=Engine();return locate(e.analyze()[2],e.airports)


@pytest.mark.parametrize('value,expected',[(180,-180),(540,-180),(-181,179),(210,-150),(0,0)])
def test_longitude(value,expected):assert longitude(value)==expected


def test_fit_contains_entire_pacific_arc_and_reverse(routes):
 for pair in ['SZX → ANC','ANC → SZX']:
  row=routes[routes.market==pair].iloc[0].to_dict();pts=arc(row['origin_longitude_deg'],row['origin_latitude_deg'],row['destination_longitude_deg'],row['destination_latitude_deg']);v=fit_corridor(row)
  assert valid_view(v) and v['x'][1]-v['x'][0]<150
  assert all(v['x'][0]<=x<=v['x'][1] and v['y'][0]<=y<=v['y'][1] for x,y in pts)
  assert all(abs(a[0]-b[0])<=180 for a,b in zip(pts,pts[1:]))
 assert arc(179,10,-179,10)[-1][0]==pytest.approx(181)


def test_focus_extents_and_invalid_client_state():
 for x,y in FOCUS.values():assert valid_view({'x':x,'y':y})
 assert FOCUS['East Asia / North Pacific'][0][1]>180
 for v in [None,{}, {'x':[0,float('nan')],'y':[0,1]},{'x':[3,2],'y':[0,1]},{'x':[0,1],'y':[-91,1]}]:assert not valid_view(v)


def test_units_hhi_and_percentage_guards():
 r={'tonnes_2024':2000,'tonnes_2025':3000,'departures_2025':123,'hhi_change':-500,'absolute_change_tonnes':1000}
 assert metric(r,2025,'Freight volume')==3000
 assert metric(r,2025,'Departures')==123
 assert metric(r,2025,'Freight change · tonnes')==1000
 assert metric(r,2025,'Carrier HHI change')==-500
 assert metric(r,2025,'Freight change · %')==50
 for baseline in [0,999,None,float('nan')]:assert metric(dict(r,tonnes_2024=baseline),2025,'Freight change · %') is None
 for value in [None,float('nan'),float('inf')]:assert encoding(value,'Freight change · %',100)[1]==1
 assert encoding(-500,'Carrier HHI change',500)[0]!=encoding(500,'Carrier HHI change',500)[0]
 assert encoding(0,'Carrier HHI change',500)[0]!=encoding(500,'Carrier HHI change',500)[0]
 assert encoding(10000,'Freight change · %',100)[1]==6
 assert set(MODES)==set(LEGENDS)


def test_map_bound_identity_encodings_and_unchanged_coverage(routes):
 safe=routes[routes.mappable].sort_values('tonnes_2025',ascending=False).head(100)
 original=routes.copy(deep=True);before=coverage(routes,2025)
 for mode in MODES:
  fig=route_map(safe,2025,safe.iloc[0].market,mode)
  assert len(fig.data)<110
  assert fig.layout.xaxis.range==(-180,180)
  handles=fig.data[-1]
  assert len(handles.x)==300 and all(v[0] in set(safe.market) for v in handles.customdata)
  assert max(handles.marker.size)==16
 assert routes.equals(original) and coverage(routes,2025)['tonnes']==before['tonnes']
 pair=routes[routes.market.isin(['SZX → ANC','ANC → SZX'])]
 fig=route_map(pair,2025,'SZX → ANC')
 h=fig.data[-1];coords={m[0]:(x,y) for m,x,y in zip(h.customdata,h.x,h.y)}
 assert coords['SZX → ANC']!=coords['ANC → SZX']
 # Context lines cannot intercept directional handles, including nearby parallel routes.
 assert all(t.hoverinfo=='skip' for t in fig.data[:-1])
 assert fig.data[-1].zorder>0


def test_handles_separate_nearby_parallel_routes_and_are_order_independent(routes):
 rows=routes[routes.mappable].sort_values('tonnes_2025',ascending=False).head(25).to_dict('records')
 handles=route_handles(rows)
 assert handles==route_handles(list(reversed(rows)))
 a,b=handles['HKG → ANC'],handles['SZX → ANC']
 assert math.hypot(longitude(a[0]-b[0]),a[1]-b[1])>=5
 for row in rows:
  assert handles[row['market']] in arc(row['origin_longitude_deg'],row['origin_latitude_deg'],row['destination_longitude_deg'],row['destination_latitude_deg'])


def test_emphasis_only_changes_route_hierarchy_and_preserves_selection(routes):
 safe=routes[routes.mappable].sort_values('tonnes_2025',ascending=False).head(100)
 selected='HKG → ANC'
 for mode in MODES:
  highlighted=route_map(safe,2025,selected,mode,emphasized=True)
  normal=route_map(safe,2025,selected,mode,emphasized=False)
  def lines(fig):return {t.meta['market']:t for t in fig.data if t.meta and t.meta.get('role')=='route'}
  h,n=lines(highlighted),lines(normal)
  assert set(h)==set(n)==set(safe.market)
  assert h[selected].opacity==1
  assert all(t.opacity==.55 for key,t in h.items() if key!=selected)
  assert all(t.opacity==.7 for t in n.values())
  for market in h:
   assert h[market].line.color==n[market].line.color
   if market!=selected:assert h[market].line.width==n[market].line.width
   assert h[market].x==n[market].x and h[market].y==n[market].y
  assert highlighted.layout.meta['highlighted']==selected and normal.layout.meta['highlighted'] is None
  assert normal.layout.meta['selected']==selected
  assert normal.layout.annotations==highlighted.layout.annotations
  assert [t.to_json() for t in normal.data if t.mode=='markers+text']==[t.to_json() for t in highlighted.data if t.mode=='markers+text']
  assert normal.data[-1].x==highlighted.data[-1].x and normal.data[-1].y==highlighted.data[-1].y
  assert len(highlighted.data)==len(normal.data)+1  # Existing halo only; no duplicated route network.
