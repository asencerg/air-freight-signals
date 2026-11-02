"""Strict CSV adapters. No movement source may supply freight weights implicitly."""
from dataclasses import dataclass, field
from typing import Protocol
import hashlib
import io
import zipfile

import pandas as pd

FIELDS = ['YEAR', 'MONTH', 'ORIGIN', 'DEST', 'UNIQUE_CARRIER', 'FREIGHT', 'DEPARTURES_PERFORMED']


@dataclass
class Dataset:
    rows: pd.DataFrame
    sha256: str
    source: str
    metadata: dict = field(default_factory=dict)


class Provider(Protocol):
    def read(self, content: bytes) -> Dataset: ...


# String identifiers must preserve leading zeros and literal country code NA.
TEXT_FIELDS = ['UNIQUE_CARRIER', 'UNIQUE_CARRIER_NAME', 'UNIQUE_CARRIER_ENTITY',
               'REGION', 'CARRIER', 'CARRIER_NAME', 'ORIGIN', 'ORIGIN_CITY_NAME',
               'ORIGIN_STATE_ABR', 'ORIGIN_STATE_NM', 'ORIGIN_COUNTRY', 'ORIGIN_COUNTRY_NAME',
               'DEST', 'DEST_CITY_NAME', 'DEST_STATE_ABR', 'DEST_STATE_NM', 'DEST_COUNTRY',
               'DEST_COUNTRY_NAME', 'CLASS', 'DATA_SOURCE']


def csv_frame(content):
    raw = pd.read_csv(io.BytesIO(content), dtype={c: str for c in TEXT_FIELDS},
                      keep_default_na=False, low_memory=False)
    # Empty cells are missing; literal identifiers such as NA remain intact.
    return raw.replace('', pd.NA)


class BTSOfficialZIP:
    def read(self, content: bytes) -> Dataset:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = [i for i in archive.infolist() if i.filename.lower().endswith('.csv')]
                if len(members) != 1:
                    raise ValueError('Expected exactly one BTS CSV member in the ZIP.')
                member = members[0]
                if member.file_size > 1024 * 1024 * 1024:
                    raise ValueError('BTS CSV exceeds the 1 GiB ingestion limit.')
                csv_content = archive.read(member)  # CRC verified; no filesystem extraction
        except zipfile.BadZipFile as exc:
            raise ValueError('Invalid or corrupt BTS ZIP archive.') from exc
        raw = csv_frame(csv_content)
        required = {'CLASS', 'AIRCRAFT_TYPE', 'AIRCRAFT_CONFIG', 'AIRLINE_ID',
                    'UNIQUE_CARRIER_ENTITY', 'ORIGIN_AIRPORT_ID', 'DEST_AIRPORT_ID'}
        missing = required - set(raw)
        if missing:
            raise ValueError('Official export lacks source strata: ' + ', '.join(sorted(missing)))
        if raw[list(required)].isna().any().any():
            raise ValueError('Official export has missing identity or source-stratum fields.')
        result = validate(raw, content, 'US DOT BTS T-100 Segment official export (local input)')
        result.metadata = {'archive_member': member.filename,
                           'csv_sha256': hashlib.sha256(csv_content).hexdigest(),
                           'freight_unit': 'pounds (BTS FREIGHT convention; no unit metadata in CSV)'}
        return result


class BTSCSV:
    def read(self, content: bytes) -> Dataset:
        raw = csv_frame(content)
        return validate(raw, content, "BTS T-100 CSV (local input)")


class BTSParquet:
    def read(self, content: bytes) -> Dataset:
        raw = pd.read_parquet(io.BytesIO(content))
        if "CLASS" not in raw:
            raise ValueError("T-100 Parquet requires CLASS to preserve service scope.")
        return validate(raw, content, "BTS-derived T-100 Parquet (local mirror input)")


def validate(raw, content, source):
    raw.columns = raw.columns.str.strip().str.upper()
    if raw.columns.duplicated().any():
        raise ValueError('Duplicate column names are not supported.')
    missing = sorted(set(FIELDS) - set(raw.columns))
    if missing:
        raise ValueError('Missing BTS fields: ' + ', '.join(missing))
    raw = raw.drop(columns=[c for c in raw if c.startswith('UNNAMED:')])
    if raw.empty:
        raise ValueError('The CSV contains no observations.')
    if raw.duplicated().any():
        raise ValueError('Exact duplicate records found. Upload a single, non-overlapping export.')
    frame = raw.copy()
    for col in ['YEAR', 'MONTH', 'FREIGHT', 'DEPARTURES_PERFORMED']:
        frame[col] = pd.to_numeric(frame[col], errors='raise')
        if frame[col].isna().any() or not frame[col].map(lambda x: float('-inf') < x < float('inf')).all() or (frame[col] < 0).any():
            raise ValueError(f'{col} must contain finite, nonnegative values.')
    for col in ['YEAR', 'MONTH', 'DEPARTURES_PERFORMED']:
        if (frame[col] % 1 != 0).any():
            raise ValueError(f'{col} must contain whole numbers.')
    if not frame.YEAR.isin([2024, 2025]).all() or not frame.MONTH.between(1, 12).all():
        raise ValueError('Expected years 2024/2025 and months 1–12.')
    for col in ['ORIGIN', 'DEST', 'UNIQUE_CARRIER']:
        frame[col] = frame[col].str.strip().str.upper()
        if frame[col].isna().any() or frame[col].eq('').any():
            raise ValueError(f'{col} contains missing identifiers.')
    if ((frame.FREIGHT > 0) & (frame.DEPARTURES_PERFORMED == 0)).any():
        raise ValueError('Positive freight with zero performed departures needs source review.')
    # Preserve all source strata, IDs and CLASS. Analysis performs its own sums.
    return Dataset(frame, hashlib.sha256(content).hexdigest(), source)

def read_dataset(content: bytes, filename: str) -> Dataset:
    adapter = BTSOfficialZIP() if filename.lower().endswith('.zip') else BTSParquet() if filename.lower().endswith('.parquet') else BTSCSV()
    return adapter.read(content)


def airport_names(content: bytes) -> dict:
    frame = pd.read_csv(io.BytesIO(content), dtype=str)
    if not {'iata_code', 'name'} <= set(frame):
        raise ValueError('OurAirports CSV requires iata_code and name.')
    frame = frame.dropna(subset=['iata_code', 'name'])
    # Ambiguous matches are deliberately left unenriched.
    frame = frame[~frame.iata_code.duplicated(keep=False)]
    return dict(zip(frame.iata_code, frame.name))


def combine_datasets(inputs):
    """Avoid silently adding different vintages of the same observations."""
    official = [bool(item.metadata.get('archive_member')) for item in inputs]
    if any(official) and not all(official):
        raise ValueError('Do not mix official ZIP exports with historical CSV/Parquet sources in one analysis.')
    if not inputs:
        raise ValueError('No datasets supplied.')
    if any(set(item.rows.columns) != set(inputs[0].rows.columns) for item in inputs):
        raise ValueError('Input files must have identical source column sets.')
    rows = pd.concat([item.rows for item in inputs], ignore_index=True)
    if rows.duplicated().any():
        raise ValueError('Overlapping records across input files.')
    return Dataset(rows, hashlib.sha256(''.join(item.sha256 for item in inputs).encode()).hexdigest(),
                   '; '.join(sorted(set(item.source for item in inputs))))
