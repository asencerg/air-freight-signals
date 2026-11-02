"""Evidence checks against genuine retained observations and the featured case."""
import hashlib
import json
from pathlib import Path
import pandas as pd
import pytest
from atlas.analysis import LB_PER_TONNE

CASE = Path('docs/cases/szx-anc')


def test_case_internal_reconciliation_and_monthly_persistence():
    annual = pd.read_csv(CASE/'annual.csv').set_index('YEAR')
    monthly = pd.read_csv(CASE/'monthly.csv')
    carriers = pd.read_csv(CASE/'carriers.csv')
    for year in [2024, 2025]:
        assert monthly[f'Tonnes {year}'].sum() == pytest.approx(annual.loc[year,'tonnes'])
        assert carriers[f'Tonnes {year}'].sum() == pytest.approx(annual.loc[year,'tonnes'])
        assert (carriers[f'Share {year} %']/100).pow(2).sum()*10000 == pytest.approx(annual.loc[year,'hhi'])
        assert annual.loc[year,'pounds']*.00045359237 == pytest.approx(annual.loc[year,'tonnes'])
        assert annual.loc[year,'pounds']/LB_PER_TONNE == pytest.approx(annual.loc[year,'tonnes'])
    assert carriers['Growth contribution %'].sum() == pytest.approx(100)
    assert (monthly['HHI 2025']<monthly['HHI 2024']).sum()==12
    assert (monthly['Tonnes 2025']>monthly['Tonnes 2024']).sum()==11
    for name in ['aircraft','service']:
        strata=pd.read_csv(CASE/f'{name}.csv')
        assert strata['Tonnes 2025'].sum()==pytest.approx(annual.loc[2025,'tonnes'])
        assert strata['Departures 2025'].sum()==1231


@pytest.mark.skipif(not Path('data/t100_seg_2024.parquet').exists(), reason='Retained genuine source files required')
def test_observations_match_pinned_files_and_entry_claims():
    audit=json.loads((CASE/'mirror-audit.json').read_text())
    rows=[]
    for item in audit['files']:
        path=Path(f"data/t100_seg_{item['year']}.parquet")
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        frame=pd.read_parquet(path)
        segment=frame[(frame.ORIGIN=='SZX')&(frame.DEST=='ANC')]
        assert len(segment)==item['source_rows']
        rows.append(segment)
    raw=pd.concat(rows)
    assert len(raw)==126
    for code, first in [('FX',4),('PO',7),('KD',9)]:
        group=raw[raw.UNIQUE_CARRIER==code]
        assert set(group.YEAR)=={2025}
        assert set(group.MONTH)==set(range(first,13))
        assert group.FREIGHT.sum()>0
    vista=raw[raw.UNIQUE_CARRIER=='VJT']
    assert vista.FREIGHT.sum()==0 and vista.DEPARTURES_PERFORMED.sum()==2
    old=set(raw[(raw.YEAR==2024)&(raw.FREIGHT>0)].UNIQUE_CARRIER)
    new=set(raw[(raw.YEAR==2025)&(raw.FREIGHT>0)].UNIQUE_CARRIER)
    assert old<=new
    source=pd.read_csv('data/validated/szx-anc-source.csv')
    for year, group in source.groupby('YEAR'):
        original=pd.read_parquet(f'data/t100_seg_{year}.parquet').iloc[group.SOURCE_ROW_INDEX]
        assert original.FREIGHT.tolist()==group.FREIGHT.tolist()
        assert original.CLASS.tolist()==group.CLASS.tolist()
        assert original.AIRCRAFT_TYPE.tolist()==group.AIRCRAFT_TYPE.tolist()
    assert hashlib.sha256(Path('data/validated/szx-anc-source.csv').read_bytes()).hexdigest()==audit['source_extract_sha256']
