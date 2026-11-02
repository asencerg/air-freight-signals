import json,shutil
from pathlib import Path
import pytest
from atlas.engine import Engine,version_token
from atlas.geography import locate,coverage


def test_version_change_invalidates_identity_and_corruption_is_rejected(tmp_path):
    source=Path('data/processed')
    for name in ['segments-v1.parquet','airports-v1.parquet','manifest.json']:shutil.copy2(source/name,tmp_path/name)
    token=version_token(tmp_path);identity=Engine(tmp_path).identity
    manifest=json.loads((tmp_path/'manifest.json').read_text());manifest['dataset_version']+='-test'
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    assert version_token(tmp_path)!=token and Engine(tmp_path).identity!=identity
    with (tmp_path/'segments-v1.parquet').open('ab') as f:f.write(b'x')
    with pytest.raises(ValueError,match='checksum'):Engine(tmp_path)


def test_global_empty_search_explorer_does_not_raise():
    from streamlit.testing.v1 import AppTest
    a=AppTest.from_file('app.py').run(timeout=30)
    a.text_input(key='search').set_value('no such airport ever').run(timeout=30)
    a.sidebar.radio(key='view').set_value('Cargo Corridor Explorer').run(timeout=30)
    assert not a.exception and any('No safely mappable' in x.value for x in a.info)
