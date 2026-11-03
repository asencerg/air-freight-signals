"""Geographic view extents and display encodings; never analytical filters."""
import math
from functools import lru_cache
from atlas.geography import great_circle

FOCUS = {
    'World': ((-180, 180), (-65, 85)),
    'North America': ((-170, -50), (5, 80)),
    'Europe': ((-25, 45), (30, 72)),
    'East Asia / North Pacific': ((90, 240), (5, 80)),
    'Latin America': ((-120, -30), (-60, 35)),
}
MODES = ('Freight volume', 'Freight change · tonnes', 'Freight change · %', 'Carrier HHI change', 'Departures')
LEGENDS = {
    'Freight volume': 'Selected-year metric tonnes · teal · width 1–6 px, square-root scaled within the displayed routes.',
    'Freight change · tonnes': '2025 − 2024 metric tonnes · teal increase / rust decrease / gray unchanged · width 1–6 px by absolute change.',
    'Freight change · %': '2025 versus 2024 freight · teal increase / rust decrease / gray unchanged · width 1–6 px, capped at 100%. Baselines below 1,000 tonnes are gray and unscaled.',
    'Carrier HHI change': '2025 − 2024 HHI points · purple higher concentration / teal lower / gray unchanged · width 1–6 px, capped at 2,500 points. Lower HHI does not establish greater competition.',
    'Departures': 'Selected-year performed departures · blue · width 1–6 px, square-root scaled within the displayed routes. Not aircraft capacity.',
}
NEUTRAL='#87939a'


def longitude(value):
    """Canonical longitude in [-180, 180); valid for wrapped Pacific views."""
    if not math.isfinite(value): raise ValueError('Finite longitude required')
    return (value+180)%360-180


@lru_cache(maxsize=4096)
def arc(lon1,lat1,lon2,lat2):
    """Unwrap the existing split great circle without changing its spherical path."""
    points=[]
    for part in great_circle(lon1,lat1,lon2,lat2):
        for x,y in part:
            if points: x=points[-1][0]+longitude(x-points[-1][0])
            if not points or abs(x-points[-1][0])+abs(y-points[-1][1])>1e-9:points.append((x,y))
    return tuple(points)


def route_arc(row):
    return arc(*(float(row[end+'_'+coord+'_deg']) for end in ['origin','destination'] for coord in ['longitude','latitude']))


def route_handles(rows):
    """Spread handles along real arcs so nearby parallel routes remain distinguishable.

    Stable market ordering keeps positions independent of the selected route or mode.
    The searchable list remains available for crowded views at small display sizes.
    """
    placed={}
    for row in sorted(rows,key=lambda r:r['market']):
        points=route_arc(row)
        candidates=[points[int((len(points)-1)*f)] for f in (.38,.28,.48,.18,.58,.68,.78,.88,.08)]
        def clearance(point):
            return min((math.hypot(longitude(point[0]-p[0]),point[1]-p[1]) for p in placed.values()),default=math.inf)
        handle=next((p for p in candidates if clearance(p)>=5),None)
        placed[row['market']]=handle if handle is not None else max(candidates,key=clearance)
    return placed


def fit_corridor(row):
    pts=route_arc(row);xs,ys=zip(*pts)
    dx=max(5,(max(xs)-min(xs))*.12);dy=max(4,(max(ys)-min(ys))*.18)
    return {'x':[min(xs)-dx,max(xs)+dx], 'y':[max(-90,min(ys)-dy),min(90,max(ys)+dy)]}


def valid_view(view):
    try:
        x,y=view['x'],view['y']
        return (len(x)==len(y)==2 and all(math.isfinite(float(v)) for v in [*x,*y])
                and -540<=x[0]<x[1]<=540 and .01<x[1]-x[0]<=720
                and -90<=y[0]<y[1]<=90 and y[1]-y[0]>.01)
    except (TypeError,KeyError,ValueError):return False


def metric(row,year,mode):
    if mode=='Freight volume':return row.get(f'tonnes_{year}')
    if mode=='Departures':return row.get(f'departures_{year}')
    if mode=='Carrier HHI change':return row.get('hhi_change')
    if mode=='Freight change · %':
        base=row.get('tonnes_2024',0)
        if base is None or not math.isfinite(base) or base<1000:return None
        return 100*(row['tonnes_2025']/base-1)
    return row.get('absolute_change_tonnes')


def encoding(value,mode,maximum):
    if value is None or not math.isfinite(value):return NEUTRAL,1.0,'Not scaled / undefined'
    if mode=='Freight volume':color='#28757a'
    elif mode=='Departures':color='#386f9c'
    elif value==0:color=NEUTRAL
    elif mode=='Carrier HHI change':color='#82639e' if value>0 else '#168577'
    else:color='#168577' if value>0 else '#b55c43'
    limit=100 if mode=='Freight change · %' else 2500 if mode=='Carrier HHI change' else max(maximum,1)
    return color,1+5*math.sqrt(min(abs(value)/limit,1)),f'{value:,.1f}'
