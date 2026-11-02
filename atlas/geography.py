"""Verified endpoint joins and great-circle geometry; independent of the UI."""
import math
import numpy as np
import pandas as pd


def locate(records, airports):
    reference=airports.copy()
    # Never expand one analytical corridor into multiple rows through an ambiguous code.
    reference=reference[~reference.bts_code.duplicated(keep=False)]
    cols=['bts_code','name','bts_country','country_name','region_name','latitude_deg','longitude_deg','match_status','coordinate_match']
    result=records.copy()
    for end in ['origin','destination']:
        renamed=reference[cols].rename(columns={c:end+'_'+c for c in cols if c!='bts_code'})
        result=result.merge(renamed,left_on=end,right_on='bts_code',how='left',validate='many_to_one').drop(columns='bts_code')
        result[end+'_safe']=(result[end+'_coordinate_match'].eq(True) &
            result[end+'_latitude_deg'].between(-90,90) & result[end+'_longitude_deg'].between(-180,180) &
            result[end+'_match_status'].eq('matched_iata_country'))
        # Unresolved names/countries are not selectable geographic assertions.
        for label in ['name','country_name','region_name']:
            result.loc[~result[end+'_safe'],end+'_'+label]=None
    result['mappable']=result.origin_safe & result.destination_safe
    conflict=(result.origin_match_status.eq('country_conflict')|result.destination_match_status.eq('country_conflict'))
    result['map_status']=np.where(result.mappable,'Mapped',np.where(conflict,'Country conflict','Missing/ambiguous coordinates'))
    return result


def coverage(routes, year):
    """All filtered eligible routes BEFORE top-N; both endpoints required."""
    t,d=f'tonnes_{year}',f'departures_{year}'
    total_t=float(routes[t].sum());total_d=float(routes[d].sum())
    mapped=routes[routes.mappable]
    impacts=routes.groupby('map_status')[[t,d]].sum().rename(columns={t:'tonnes',d:'departures'})
    return dict(corridors=len(routes),mapped_corridors=len(mapped),corridor_pct=100*len(mapped)/len(routes) if len(routes) else None,
        tonnes=total_t,departures=total_d,freight_pct=100*mapped[t].sum()/total_t if total_t else None,
        departures_pct=100*mapped[d].sum()/total_d if total_d else None,
        unmapped_tonnes=float(routes.loc[~routes.mappable,t].sum()),unmapped_departures=float(routes.loc[~routes.mappable,d].sum()),impacts=impacts)


def great_circle(lon1,lat1,lon2,lat2,steps=64):
    """Spherical shortest arc split at ±180°. Coordinates are illustrative, not flight tracks."""
    if not all(math.isfinite(v) for v in [lon1,lat1,lon2,lat2]):raise ValueError('Finite coordinates required')
    if not (-180<=lon1<=180 and -180<=lon2<=180 and -90<=lat1<=90 and -90<=lat2<=90):raise ValueError('Invalid geographic coordinate')
    def xyz(lon,lat):
        x,y=math.radians(lon),math.radians(lat)
        return np.array([math.cos(y)*math.cos(x),math.cos(y)*math.sin(x),math.sin(y)])
    a,b=xyz(lon1,lat1),xyz(lon2,lat2);angle=math.acos(float(np.clip(a@b,-1,1)))
    if angle<1e-10:return [[(lon1,lat1),(lon2,lat2)]]
    if abs(math.pi-angle)<1e-8:raise ValueError('Antipodal endpoints have no unique shortest arc')
    points=[]
    for f in np.linspace(0,1,steps+1):
        v=(math.sin((1-f)*angle)*a+math.sin(f*angle)*b)/math.sin(angle)
        points.append((math.degrees(math.atan2(v[1],v[0])),math.degrees(math.atan2(v[2],math.hypot(v[0],v[1])))))
    parts=[[points[0]]]
    for lon,lat in points[1:]:
        prev_lon,prev_lat=parts[-1][-1]
        if abs(lon-prev_lon)>180:
            unwrapped=lon-360 if lon>prev_lon else lon+360
            edge=-180 if unwrapped<prev_lon else 180
            fraction=(edge-prev_lon)/(unwrapped-prev_lon)
            edge_lat=prev_lat+(lat-prev_lat)*fraction
            parts[-1].append((edge,edge_lat));parts.append([(-edge,edge_lat)])
        parts[-1].append((lon,lat))
    return parts
