"""Mandatory bundled-app acceptance checks; no source ZIPs, mirror or API required.

Missing/corrupt packaged files fail these tests rather than silently skipping them.
Raw rebuild integration checks remain separately in test_official/test_real_data.
"""
import io
import json
from pathlib import Path
import pandas as pd
import pytest
from atlas import packaged
from atlas.analysis import analyze, findings, markdown


@pytest.fixture(scope='module')
def bundle():
    return packaged.load_bundle()


def test_packaged_totals_scope_and_coordinates(bundle):
    data,airports=bundle
    manifest=data.metadata
    assert manifest['source_records']==1121004
    assert manifest['reporting_years']==[2024,2025]
    expected={2024:(53150672359,10682376,549799),2025:(50777350469,10863635,571205)}
    for year,group in data.rows.groupby('YEAR'):
        assert set(group.MONTH)==set(range(1,13))
        assert (group.FREIGHT.sum(),group.DEPARTURES_PERFORMED.sum(),group.SOURCE_RECORD_COUNT.sum())==expected[year]
    assert set(['CLASS','AIRCRAFT_TYPE','AIRCRAFT_CONFIG','UNIQUE_CARRIER_ENTITY'])<=set(data.rows)
    assert len(airports)==2340 and airports.coordinate_match.sum()==2020
    assert airports.loc[~airports.coordinate_match,['latitude_deg','longitude_deg']].isna().all().all()
    assert manifest['validation']['independent_raw_csv_group_difference_count']==0
    assert sum(item['bytes'] for item in manifest['files'].values())<50_000_000


def test_five_findings_hhi_months_and_exports(bundle):
    rows=bundle[0].rows
    pairs=pd.read_csv('docs/official-five-reconciliation.csv')
    targets=set(tuple(p.split(' → ')) for p in pairs.Segment.unique())
    subset=rows[[pair in targets for pair in zip(rows.ORIGIN,rows.DEST)]]
    evidence,shares=analyze(subset)
    assert len(evidence)==5
    for expected in pairs.to_dict('records'):
        a,b=expected['Segment'].split(' → ');y=expected['Year']
        r=evidence[(evidence.origin==a)&(evidence.destination==b)].iloc[0]
        assert r[f'tonnes_{y}']==pytest.approx(expected['Official tonnes'])
        assert r[f'departures_{y}']==expected['Official departures']
        assert r[f'hhi_{y}']==pytest.approx(expected['Official HHI'])
    s=rows[(rows.ORIGIN=='SZX')&(rows.DEST=='ANC')]
    c=s[s.YEAR==2025].groupby('UNIQUE_CARRIER').FREIGHT.sum()
    assert ((c/c.sum())**2).sum()*10000==pytest.approx(3646.0565536)
    expected_months=pd.read_csv('docs/cases/szx-anc/monthly.csv').set_index('Month')
    for year in [2024,2025]:
        monthly=s[s.YEAR==year].groupby('MONTH')[['FREIGHT','DEPARTURES_PERFORMED']].sum()
        assert monthly.FREIGHT.to_numpy()*.00045359237==pytest.approx(expected_months[f'Tonnes {year}'].to_numpy())
        assert monthly.DEPARTURES_PERFORMED.tolist()==expected_months[f'Departures {year}'].tolist()
    q1,_=analyze(s,months=[1,2,3])
    assert q1.iloc[0].tonnes_2025==pytest.approx(expected_months.loc[[1,2,3],'Tonnes 2025'].sum())
    briefs=findings(evidence);briefs['source']=bundle[0].source
    exported=pd.read_csv(io.StringIO(briefs.to_csv(index=False)))
    assert len(exported)==len(briefs) and 'SZX → ANC' in markdown(briefs)
    assert not briefs.source.str.contains('SYNTHETIC').any()


def test_default_app_filtering_and_downloads():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file('app.py').run(timeout=180)
    assert not app.exception and not app.error
    assert any('Loaded official' in item.value for item in app.caption)
    assert len(app.dataframe[0].value)==15
    assert app.dataframe[0].value.Corridor.is_unique
    assert not app.get('plotly_chart')
    assert not any(e.label.startswith('Featured research') for e in app.expander)
    assert len(app.expander)<=5
    first_page=set(app.dataframe[0].value.Corridor)
    next(widget for widget in app.selectbox if widget.label=='Results page').select(2).run(timeout=180)
    assert len(app.dataframe[0].value)==15
    assert first_page.isdisjoint(set(app.dataframe[0].value.Corridor))
    app.selectbox(key='category').select('Full eligible universe')
    app.sidebar.selectbox(key='airport').select('SZX').run(timeout=180)
    markets=app.dataframe[0].value.Corridor
    assert markets.str.contains('SZX').all()
    app.selectbox(key='detail_1_Full eligible universe').select('SZX → ANC').run(timeout=180)
    metrics=app.dataframe[1].value.set_index('Metric')
    assert metrics.loc['Carrier HHI','2025']=='3,646'
    app.sidebar.selectbox(key='carrier').select('5X').run(timeout=180)
    app.selectbox(key='detail_1_Full eligible universe').select('SZX → ANC').run(timeout=180)
    metrics=app.dataframe[1].value.set_index('Metric')
    assert metrics.loc['Carrier HHI','2025']=='3,646'
    app.checkbox(key='exports').check().run(timeout=180)
    labels=[x.label for x in app.get('download_button')]
    assert 'Export findings CSV' in labels and 'Export findings Markdown' in labels
    app.sidebar.radio(key='view').set_value('Case Studies').run(timeout=30)
    assert len(app.get('plotly_chart'))==4
    assert not app.exception
