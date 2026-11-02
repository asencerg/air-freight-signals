"""Integration checks use only the supplied genuine BTS and OurAirports records."""
from pathlib import Path
import io
import json
import zipfile
import pandas as pd
import pytest
from atlas.official import load_official
from atlas.ingest import read_dataset, combine_datasets, BTSOfficialZIP
from atlas.reference import reference_metadata, match_airports

BASE = Path('data/official')
AVAILABLE = len(list(BASE.glob('T_T100_SEGMENT_ALL_CARRIER_*.zip'))) == 2
pytestmark = pytest.mark.skipif(not AVAILABLE, reason='Supplied official BTS uploads unavailable')


@pytest.fixture(scope='module')
def datasets():
    return load_official(BASE)


@pytest.fixture(scope='module')
def reference():
    return reference_metadata(*[(BASE/name).read_bytes() for name in ['airports.csv','regions.csv','countries.csv']])


def test_official_periods_counts_units_and_identifiers(datasets):
    for year, count, pounds in [(2024,549799,53150672359),(2025,571205,50777350469)]:
        data=datasets[year];frame=data.rows
        assert len(frame)==count
        assert set(frame.MONTH)==set(range(1,13))
        assert set(frame.YEAR)=={year}
        assert frame.FREIGHT.sum()==pounds
        assert 'AIRCRAFT_CONFIG' in frame and 'CLASS' in frame
        assert frame.UNIQUE_CARRIER_ENTITY.str.startswith('0').any()
        assert not frame.duplicated().any()
        szx=frame[(frame.ORIGIN=='SZX')&(frame.DEST=='ANC')]
        assert szx.FREIGHT.sum()*.00045359237 == pytest.approx({2024:101320.79149794833,2025:141807.150531}[year])
    assert datasets[2024].metadata['filename'].endswith('024444.zip')
    assert datasets[2025].metadata['filename'].endswith('024054.zip')


def test_official_source_preservation_and_reconciliation(datasets):
    for year,data in datasets.items():
        path=BASE/data.metadata['filename']
        with zipfile.ZipFile(path) as archive:
            raw=pd.read_csv(archive.open(archive.namelist()[0]),keep_default_na=False,
                            dtype={'UNIQUE_CARRIER_ENTITY':str},low_memory=False)
        for col in ['FREIGHT','DEPARTURES_PERFORMED','AIRCRAFT_TYPE','AIRCRAFT_CONFIG','CLASS','UNIQUE_CARRIER_ENTITY','ORIGIN','DEST']:
            assert raw[col].tolist()==data.rows[col].tolist()
    current=pd.read_csv('docs/official-five-reconciliation.csv')
    assert (current[['Tonne difference','Departure difference','HHI difference']]==0).all().all()
    audit=json.loads(Path('docs/official-data-audit.json').read_text())
    assert audit['reconciliation']['2024']['freight_lb_delta']==17008789
    assert audit['reconciliation']['2025']['official_rows_different']==0


def test_reject_mixed_vintages_duplicates_and_bad_zip(datasets):
    current=datasets[2024]
    historic=type(current)(current.rows.copy(),'old','historical Parquet')
    with pytest.raises(ValueError,match='mix official'):
        combine_datasets([current,historic])
    with pytest.raises(ValueError,match='Overlapping'):
        combine_datasets([current,current])
    with pytest.raises(ValueError,match='Invalid or corrupt'):
        BTSOfficialZIP().read(b'not a zip')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('a.csv','YEAR\n2024');z.writestr('b.csv','YEAR\n2025')
    with pytest.raises(ValueError,match='exactly one'):
        BTSOfficialZIP().read(buffer.getvalue())


def test_reference_country_codes_and_no_identifier_fallback(datasets,reference):
    namibia=reference[reference.iso_country=='NA']
    assert len(namibia)>0 and namibia.country_name.eq('Namibia').all()
    assert reference.region_consistent.all()
    rows=pd.concat([x.rows for x in datasets.values()],ignore_index=True)
    mapped=match_airports(rows,reference)
    assert len(mapped)==2340
    assert mapped.coordinate_match.sum()==2020
    conflicts=mapped[mapped.match_status=='country_conflict']
    assert len(conflicts)==33
    assert conflicts[['latitude_deg','longitude_deg']].isna().all().all()
    assert mapped[mapped.bts_code=='PTL'].match_status.eq('country_conflict').all()
    assert mapped[mapped.bts_code.isin(['SZX','ANC'])].coordinate_match.all()


def test_ambiguous_iata_not_joined(datasets,reference):
    szx=reference[reference.iata_code=='SZX'].copy()
    # Deliberately mark a real reference as ambiguous to verify fail-closed matching.
    altered=reference.copy();altered.loc[altered.iata_code=='SZX','iata_ambiguous']=True
    segment=datasets[2025].rows.query("ORIGIN == 'SZX' and DEST == 'ANC'")
    result=match_airports(segment,altered)
    assert result[result.bts_code=='SZX'].match_status.eq('ambiguous_iata').all()
    assert not result[result.bts_code=='SZX'].coordinate_match.any()


def test_official_case_source_trace(datasets):
    audit=json.loads(Path('docs/cases/szx-anc/audit.json').read_text())
    assert audit['source']=='official BTS annual exports'
    extract=pd.read_csv(audit['source_extract_path'])
    assert len(extract)==126
    for year,group in extract.groupby('YEAR'):
        original=datasets[year].rows.iloc[group.SOURCE_ROW_INDEX]
        for col in ['FREIGHT','DEPARTURES_PERFORMED','CLASS','AIRCRAFT_TYPE','AIRCRAFT_CONFIG']:
            assert original[col].tolist()==group[col].tolist()


def test_app_with_official_zips_and_all_reference_files(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    uploads=[]
    for path in sorted(BASE.glob('T_T100_SEGMENT_ALL_CARRIER_*.zip')):
        file=io.BytesIO(path.read_bytes());file.name=path.name;uploads.append(file)
    def uploader(label,*args,**kwargs):
        if kwargs.get('accept_multiple_files'):
            return uploads
        for name in ['airports.csv','regions.csv','countries.csv']:
            if name in label:
                return io.BytesIO((BASE/name).read_bytes())
        return None
    monkeypatch.setattr(st.sidebar,'file_uploader',uploader)
    monkeypatch.setattr(st,'file_uploader',uploader)
    app=AppTest.from_file('app.py').run(timeout=180)
    assert not app.exception
    assert not app.error
    assert len(app.dataframe[0].value)==15
    next(c for c in app.checkbox if c.label=='Load reference controls').check().run(timeout=180)
    assert not app.exception
    assert len(app.dataframe)>=1
    assert any('Unique IATA and country' in item.value for item in app.caption)
