"""Load official annual archives; never silently fall back to mirrors."""
from pathlib import Path
import pandas as pd
from atlas.ingest import read_dataset


def load_official(directory):
    datasets = {}
    for path in sorted(Path(directory).glob('T_T100_SEGMENT_ALL_CARRIER_*.zip')):
        data = read_dataset(path.read_bytes(), path.name)
        years = data.rows.YEAR.unique()
        if len(years) != 1:
            raise ValueError(f'{path.name}: expected one reporting year per annual export.')
        year = int(years[0])
        if year in datasets:
            raise ValueError(f'Multiple annual files for {year}; review overlap rather than combine.')
        if set(data.rows.MONTH) != set(range(1, 13)):
            raise ValueError(f'{path.name}: missing reporting months.')
        data.metadata.update(filename=path.name, path=str(path), year=year)
        datasets[year] = data
    if set(datasets) != {2024, 2025}:
        raise ValueError('Both complete 2024 and 2025 official annual ZIP exports are required; no mirror fallback.')
    return datasets


def official_rows(directory):
    return pd.concat([d.rows for _, d in sorted(load_official(directory).items())], ignore_index=True)


def extract_csv(path):
    """Preserve each archive member under its archive stem; never collide filenames."""
    import zipfile
    import hashlib
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        members = [i for i in archive.infolist() if i.filename.lower().endswith('.csv')]
        if len(members) != 1 or Path(members[0].filename).name != members[0].filename:
            raise ValueError('Expected one flat CSV member in the official archive.')
        content = archive.read(members[0])
    target = path.parent / 'extracted' / path.stem / members[0].filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(content).digest():
        raise ValueError(f'Existing original extract differs: {target}')
    if not target.exists():
        target.write_bytes(content)
    return target
