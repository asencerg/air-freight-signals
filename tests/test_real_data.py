"""Local integration tests use genuine downloaded files; CI skips when absent."""
from pathlib import Path
import io
import pandas as pd
import pytest
from atlas.ingest import read_dataset

DATA = Path('data/t100_seg_2024.parquet')
pytestmark = pytest.mark.skipif(not DATA.exists(), reason='Genuine mirror files not downloaded')


def test_parquet_preserves_source_and_csv_equivalence():
    source = pd.read_parquet(DATA).head(1000)
    buffer = io.BytesIO()
    source.to_parquet(buffer, index=False)
    result = read_dataset(buffer.getvalue(), DATA.name)
    pd.testing.assert_frame_equal(source, result.rows)
    csv = read_dataset(source.to_csv(index=False).encode(), 'export.csv')
    assert csv.rows.FREIGHT.sum() == result.rows.FREIGHT.sum()
    assert csv.rows.CLASS.tolist() == source.CLASS.tolist()
    assert csv.rows.UNIQUE_CARRIER.tolist() == source.UNIQUE_CARRIER.tolist()


def test_app_with_real_annual_uploads(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    uploads = []
    for year in [2024, 2025]:
        content = io.BytesIO(Path(f'data/t100_seg_{year}.parquet').read_bytes())
        content.name = f't100_seg_{year}.parquet'
        uploads.append(content)
    def uploader(label, *args, **kwargs):
        return uploads if kwargs.get('accept_multiple_files') else None
    monkeypatch.setattr(st.sidebar, 'file_uploader', uploader)
    monkeypatch.setattr(st, 'file_uploader', uploader)
    app = AppTest.from_file('app.py').run(timeout=120)
    assert not app.exception
    assert len(app.dataframe[0].value)==15
    choice=app.selectbox(key='detail_1_Freight growth').options[1]
    app.selectbox(key='detail_1_Freight growth').select(choice).run(timeout=120)
    assert not app.exception
    assert len(app.dataframe)>=3
    assert len(app.get('plotly_chart'))==1
