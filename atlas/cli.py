"""Validate and aggregate a local export into a local DuckDB database."""
import argparse
from pathlib import Path
import duckdb
import pandas as pd
import hashlib
from atlas.ingest import read_dataset, combine_datasets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path, nargs='+')
    parser.add_argument('--synthetic', action='store_true', help='Label demonstration input explicitly')
    parser.add_argument('--database', type=Path, default=Path('data/research.duckdb'))
    args = parser.parse_args()
    inputs = [read_dataset(path.read_bytes(), path.name) for path in args.csv]
    dataset = combine_datasets(inputs)
    if args.synthetic:
        dataset.source = 'SYNTHETIC DEMONSTRATION — not empirical evidence'
    args.database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(args.database)) as connection:
        connection.register('validated', dataset.rows)
        connection.execute('CREATE OR REPLACE TABLE segments AS SELECT * FROM validated')
        connection.execute('CREATE OR REPLACE TABLE provenance (sha256 VARCHAR, source VARCHAR)')
        connection.execute('INSERT INTO provenance VALUES (?, ?)', [dataset.sha256, dataset.source])
    print(f'Validated {len(dataset.rows)} carrier/month/segment rows. SHA-256: {dataset.sha256}')


if __name__ == '__main__':
    main()
