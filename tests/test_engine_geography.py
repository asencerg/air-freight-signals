import hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from atlas.engine import Engine,version_token,TONNES_PER_POUND
from atlas.geography import locate,coverage,great_circle
from atlas.analysis import analyze


@pytest.fixture(scope='module')
def queried():
    engine=Engine();return engine,engine.analyze()


def test_sql_full_universe_matches_legacy_and_all_carrier_denominators(queried):
    engine,(e,s,r)=queried
    rows=pd.read_parquet(engine.directory/'segments-v1.parquet')
    expected,shares=analyze(rows)
    assert len(e)==len(r)==2892 and r.market.is_unique
    pd.testing.assert_frame_equal(e[expected.columns],expected,check_dtype=False,atol=1e-6,rtol=1e-11)
    keys=['origin','destination','year','carrier']
    pd.testing.assert_frame_equal(s.sort_values(keys).reset_index(drop=True)[shares.columns],shares.sort_values(keys).reset_index(drop=True),check_dtype=False,atol=1e-12)
    assert s.groupby(['origin','destination','year']).share.sum().to_numpy()==pytest.approx(np.ones(5784))
    assert int(rows.SOURCE_RECORD_COUNT.sum())==1121004
    for name,item in json.loads((engine.directory/'manifest.json').read_text())['files'].items():
        assert hashlib.sha256((engine.directory/name).read_bytes()).hexdigest()==item['sha256']
        assert (engine.directory/name).stat().st_size==item['bytes']
    assert sum(p.stat().st_size for p in engine.directory.glob('*.parquet'))<50_000_000


def test_sql_partial_period_and_thresholds(queried):
    engine,_=queried
    rows=engine.detail('SZX','ANC',[1,2,3]);expected,_=analyze(rows,[1,2,3])
    e,_,_=engine.analyze([1,2,3]);actual=e[(e.origin=='SZX')&(e.destination=='ANC')]
    assert actual.iloc[0].tonnes_2025==pytest.approx(expected.iloc[0].tonnes_2025)
    assert actual.iloc[0].months=='1,2,3'
    assert engine.analyze([1],min_tonnes=1e12)[0].empty
    with pytest.raises(ValueError):engine.analyze([])


def test_geographic_denominators_and_conflicts(queried):
    engine,(_,_,r)=queried;g=locate(r,engine.airports);c=coverage(g,2025)
    assert len(g)==2892 and g.market.is_unique
    assert c['mapped_corridors']==2800
    assert c['freight_pct']==pytest.approx(98.6178039849428)
    assert c['departures_pct']==pytest.approx(97.58802867300412)
    assert c['unmapped_tonnes']==pytest.approx(289205.52872914)
    assert c['impacts'].tonnes.sum()==pytest.approx(c['tonnes'])
    assert (g.loc[g.market=='MIA → SJU','map_status']=='Country conflict').all()
    sub=g[g.origin=='SZX'];sc=coverage(sub,2025)
    assert sc['corridors']==len(sub) and sc['tonnes']==pytest.approx(sub.tonnes_2025.sum())
    assert coverage(g.iloc[:0],2025)['freight_pct'] is None
    for pair in ['SZX → ANC','HKG → ANC','PVG → ANC','MIA → BOG','ANC → MEM']:
        assert g.loc[g.market==pair,'mappable'].item()
    assert g[g.market=='SZX → ANC'].origin_longitude_deg.item()==pytest.approx(113.803262)


def test_ambiguous_reference_does_not_duplicate_or_force_coordinates(queried):
    engine,(_,_,r)=queried
    duplicate=pd.concat([engine.airports,engine.airports[engine.airports.bts_code=='SZX']])
    g=locate(r,duplicate)
    assert len(g)==len(r) and not g[g.origin=='SZX'].mappable.any()
    invalid=engine.airports.copy();invalid.loc[invalid.bts_code=='ANC','latitude_deg']=999
    assert not locate(r,invalid).query("destination=='ANC'").mappable.any()


@pytest.mark.parametrize('endpoints',[(113.803262,22.639474,-149.992561,61.179004),(113.914862,22.311840,-149.992561,61.179004),(121.805,31.1434,-149.992561,61.179004),(-80.289751,25.796011,-74.1469,4.70159),(-149.992561,61.179004,-89.97634,35.043845),(179,10,-179,10)])
def test_great_circle_and_dateline(endpoints):
    parts=great_circle(*endpoints)
    assert parts[0][0]==pytest.approx(endpoints[:2]);assert parts[-1][-1]==pytest.approx(endpoints[2:])
    for part in parts:
        assert all(abs(b[0]-a[0])<=180 for a,b in zip(part,part[1:]))
        assert all(-180<=x<=180 and -90<=y<=90 for x,y in part)
    if endpoints[0]>0 and endpoints[2]<0:assert len(parts)==2
    rev=great_circle(*endpoints[2:],*endpoints[:2]);assert rev[0][0]==pytest.approx(endpoints[2:])
    # Every original interior slerp point lies on the plane through both endpoint vectors.
    def xyz(lon,lat):
        lon,lat=map(math.radians,[lon,lat]);return np.array([math.cos(lat)*math.cos(lon),math.cos(lat)*math.sin(lon),math.sin(lat)])
    normal=np.cross(xyz(*endpoints[:2]),xyz(*endpoints[2:]))
    for part in parts:
        for x,y in part:
            if abs(abs(x)-180)>1e-8:assert abs(xyz(x,y)@normal)<1e-10


def test_geometry_invalid_and_zero_distance():
    assert len(great_circle(1,1,1,1)[0])==2
    with pytest.raises(ValueError):great_circle(0,0,180,0)
    with pytest.raises(ValueError):great_circle(0,100,30,10)


def test_cache_keys_cover_version_and_filters():
    from atlas.cache import research
    research.clear()
    class Counter:
        calls=0
        def analyze(self,*args):self.calls+=1;return args
    obj=Counter()
    research('v1',(1,2),30,100,obj);research('v1',(1,2),30,100,obj)
    assert obj.calls==1
    for args in [('v2',(1,2),30,100),('v2',(1,),30,100),('v2',(1,),31,100),('v2',(1,),31,101)]:research(*args,obj)
    assert obj.calls==5
    research.clear()


def test_home_is_bounded_and_does_not_load_full_pandas_or_maps(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from atlas import packaged
    from atlas import maps,case_study
    def forbidden(*args,**kwargs):raise AssertionError('Eager heavy view or full dataset load')
    monkeypatch.setattr(packaged,'load_bundle',forbidden)
    monkeypatch.setattr(maps,'route_map',forbidden)
    monkeypatch.setattr(case_study,'render_featured_case',forbidden)
    a=AppTest.from_file('app.py').run(timeout=30)
    assert not a.exception
    assert len(a.dataframe[0].value)==15
    assert not a.get('plotly_chart')
    assert len(list(a))<100


def test_geographic_navigation_filter_reset_and_empty_state():
    from streamlit.testing.v1 import AppTest
    a=AppTest.from_file('app.py').run(timeout=30)
    a.sidebar.radio(key='view').set_value('Cargo Corridor Explorer').run(timeout=30)
    assert not a.exception and len(a.get('plotly_chart'))==2
    a.selectbox(key='map_origin').select('SZX').run(timeout=30)
    assert 'SZX → ANC' in a.selectbox(key='map_selected').options
    a.selectbox(key='map_selected').select('SZX → ANC').run(timeout=30)
    assert not a.exception
    a.text_input(key='map_search').set_value('NO SUCH ROUTE').run(timeout=30)
    assert any('No safely mappable' in i.value for i in a.info)
    next(b for b in a.button if b.label=='Reset filters').click().run(timeout=30)
    assert a.selectbox(key='map_origin').value=='All'
    assert not a.exception
