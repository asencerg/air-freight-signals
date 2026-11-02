"""The bundled application must run with the standalone HTML omitted."""
from pathlib import Path
import shutil
import pytest
from streamlit.testing.v1 import AppTest
from atlas import case_study


@pytest.mark.parametrize('html_present', [False, True])
def test_featured_case_optional_html(tmp_path, monkeypatch, html_present):
    from atlas import packaged
    monkeypatch.setattr(packaged, 'available', lambda: False)
    case = tmp_path / 'case'
    case.mkdir()
    for source in case_study.CASE.iterdir():
        if source.suffix != '.html':
            shutil.copy2(source, case / source.name)
    if html_present:
        (case / 'case-study.html').write_text('<html><body>Local export test</body></html>')
    monkeypatch.setattr(case_study, 'CASE', case)
    app = AppTest.from_file(str(Path('app.py').resolve())).run(timeout=30)
    app.sidebar.radio(key='view').set_value('Case Studies').run()
    assert not app.exception
    labels = [button.label for button in app.get('download_button')]
    assert ('Download case study with charts (HTML)' in labels) == html_present
    assert 'Download case study (Markdown)' in labels
    assert len(app.get('plotly_chart')) == 4
