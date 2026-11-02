import pandas as pd
import pytest
from tests.fixtures import generate
from atlas.ingest import BTSCSV
from atlas.analysis import analyze, findings, markdown


def test_expected_growth_concentration_and_shares():
    data = BTSCSV().read(generate().to_csv(index=False).encode())
    evidence, shares = analyze(data.rows)
    r = evidence.iloc[0]
    assert r.tonnes_change_pct == pytest.approx(45)
    assert r.departures_change_pct == 0
    assert r.tonnes_per_departure_change_pct == pytest.approx(45)
    assert r.hhi_2024 == pytest.approx(5000)
    assert r.hhi_2025 == pytest.approx(8200)
    assert r.top_share_2025 == pytest.approx(.9)
    assert shares.groupby(['origin', 'destination', 'year']).share.sum().eq(1).all()
    briefs = findings(evidence, synthetic=True)
    assert 'SYNTHETIC' in markdown(briefs)
    assert '45.0%' in markdown(briefs)
    assert len(briefs) > 0


def test_missing_month_excluded_and_matched_partial_period_allowed():
    frame = generate()
    frame = frame[~((frame.YEAR == 2025) & (frame.MONTH == 12))]
    assert analyze(frame)[0].empty
    assert len(analyze(frame, months=[1, 2, 3])[0]) == 2


def test_thresholds_zero_and_direction():
    frame = generate()
    assert analyze(frame, min_tonnes=1000000)[0].empty
    assert analyze(frame.assign(FREIGHT=0))[0].empty
    reverse = frame.copy().rename(columns={'ORIGIN': 'DEST', 'DEST': 'ORIGIN'})
    assert len(analyze(pd.concat([frame, reverse]))[0]) == 4


@pytest.mark.parametrize('column,value', [('FREIGHT', -1), ('FREIGHT', float('inf')), ('MONTH', 13), ('YEAR', 2026), ('DEPARTURES_PERFORMED', 1.5), ('ORIGIN', '')])
def test_invalid_data_rejected(column, value):
    frame = generate()
    frame[column] = frame[column].astype(object)
    frame.loc[0, column] = value
    with pytest.raises(ValueError):
        BTSCSV().read(frame.to_csv(index=False).encode())


def test_duplicates_and_zero_departures_rejected():
    frame = generate()
    with pytest.raises(ValueError):
        BTSCSV().read(pd.concat([frame, frame]).to_csv(index=False).encode())
    frame.loc[0, 'DEPARTURES_PERFORMED'] = 0
    with pytest.raises(ValueError):
        BTSCSV().read(frame.to_csv(index=False).encode())


def test_streamlit_requires_real_upload(monkeypatch):
    from atlas import packaged
    monkeypatch.setattr(packaged, "available", lambda: False)
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('app.py').run(timeout=30)
    assert not app.exception
    assert any('Upload' in message.value for message in app.info)
    assert not app.get('plotly_chart')
    app.sidebar.radio(key='view').set_value('Case Studies').run()
    assert any(e.label.startswith('Featured research') for e in app.expander)
    assert len(app.get('plotly_chart')) == 4
