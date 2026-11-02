"""Versioned local analytical bundle: no network and no raw-source fallback."""
from pathlib import Path
import hashlib
import json
import pandas as pd
from atlas.ingest import Dataset

DIRECTORY = Path(__file__).resolve().parents[1] / 'data/processed'


def available():
    return (DIRECTORY/'manifest.json').is_file()


def fingerprint():
    return hashlib.sha256((DIRECTORY/'manifest.json').read_bytes()).hexdigest()


def load_bundle():
    manifest=json.loads((DIRECTORY/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1:
        raise ValueError('Unsupported bundled dataset schema version.')
    tables={}
    for name in ['segments-v1.parquet','airports-v1.parquet']:
        path=DIRECTORY/name
        info=manifest['files'][name]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError(f'Bundled file checksum mismatch: {name}')
        tables[name]=pd.read_parquet(path)
        if len(tables[name])!=info['rows']:
            raise ValueError(f'Bundled file row count mismatch: {name}')
    rows=tables['segments-v1.parquet']
    if int(rows.SOURCE_RECORD_COUNT.sum())!=manifest['source_records']:
        raise ValueError('Bundled source-record accounting does not reconcile.')
    source='US DOT BTS T-100 Segment (All Carriers), processed official 2024–2025 exports; '+manifest['dataset_version']
    dataset=Dataset(rows, fingerprint(), source, metadata=manifest)
    return dataset,tables['airports-v1.parquet']
