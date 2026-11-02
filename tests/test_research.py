import pandas as pd
import pytest
from atlas.analysis import analyze, findings
from atlas.ingest import BTSCSV
from atlas.research import corridor_records, rank_corridors, briefs_markdown
from tests.fixtures import generate


def test_corridor_consolidation_preserves_direction_and_signals():
    rows = BTSCSV().read(generate().to_csv(index=False).encode()).rows
    reverse = rows.rename(columns={'ORIGIN':'DEST','DEST':'ORIGIN'})
    rows = pd.concat([rows, reverse],ignore_index=True)
    evidence, _ = analyze(rows)
    records = corridor_records(evidence, rows, list(range(1,13)))
    assert len(records)==len(evidence)==4
    assert records.market.is_unique
    for signal in findings(evidence).itertuples():
        assert signal.finding_type in records.set_index('market').loc[signal.market,'signals']
    pd.testing.assert_frame_equal(evidence, records[evidence.columns])
    assert records.same_direction_months.eq(12).all()
    assert '### Next investigation' in briefs_markdown(records)
    assert 'Metric tonnes / departure' in briefs_markdown(records)


def test_ranking_uses_tonnes_not_percent_and_separates_questions():
    records = pd.DataFrame([
        dict(market='A → B',absolute_change_tonnes=600,magnitude_tonnes=600,comparison_size_tonnes=1000,same_direction_months=12,hhi_change=0,newly_observed='',no_longer_observed=''),
        dict(market='B → A',absolute_change_tonnes=2000,magnitude_tonnes=2000,comparison_size_tonnes=5000,same_direction_months=6,hhi_change=-600,newly_observed='X',no_longer_observed=''),
        dict(market='C → D',absolute_change_tonnes=900,magnitude_tonnes=900,comparison_size_tonnes=100,same_direction_months=12,hhi_change=0,newly_observed='',no_longer_observed=''),
        dict(market='D → C',absolute_change_tonnes=-1000,magnitude_tonnes=1000,comparison_size_tonnes=2000,same_direction_months=10,hhi_change=800,newly_observed='',no_longer_observed='Y'),
    ])
    assert rank_corridors(records).market.tolist()==['B → A','A → B']
    assert rank_corridors(records,'Freight contraction').market.tolist()==['D → C']
    assert rank_corridors(records,'Carrier structure').market.tolist()==['B → A','D → C']
    assert len(rank_corridors(records,'Full eligible universe'))==4


def test_missing_month_is_not_imputed_and_new_carrier_is_window_relative():
    rows = BTSCSV().read(generate().to_csv(index=False).encode()).rows
    rows.loc[(rows.YEAR==2025)&(rows.UNIQUE_CARRIER=='DEMO2'),'UNIQUE_CARRIER']='NEW'
    evidence,_=analyze(rows)
    records=corridor_records(evidence,rows,list(range(1,13)))
    assert records.newly_observed.str.contains('NEW').any()
    assert records.no_longer_observed.str.contains('DEMO2').any()
    incomplete=rows[~((rows.YEAR==2025)&(rows.MONTH==12))]
    assert corridor_records(analyze(incomplete)[0],incomplete,list(range(1,13))).empty


def test_real_case_carrier_contributions_and_persistence():
    from atlas.packaged import load_bundle
    rows=load_bundle()[0].rows
    rows=rows[(rows.ORIGIN=='SZX')&(rows.DEST=='ANC')]
    evidence,shares=analyze(rows)
    r=corridor_records(evidence,rows,list(range(1,13))).iloc[0]
    assert r.same_direction_months==11
    assert r.absolute_change_tonnes==pytest.approx(40486.359033,abs=.001)
    assert r.hhi_2025==pytest.approx(3646.0565536)
    assert set(r.newly_observed.split(', '))=={'FX','PO','KD'}
    assert shares.groupby('year').share.sum().to_numpy()==pytest.approx([1,1])
