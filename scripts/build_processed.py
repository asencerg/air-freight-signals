"""Build a compact, lossless-at-declared-grain package from official exports.

Source-specific redistribution conditions are documented in data-provenance.md.
This script writes local data; it does not stage or publish anything.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import duckdb
import pandas as pd
from atlas.official import load_official, extract_csv
from atlas.reference import reference_metadata, match_airports
from atlas.analysis import analyze

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/processed'
DIMENSIONS = ['YEAR','MONTH','ORIGIN','DEST','ORIGIN_AIRPORT_ID','DEST_AIRPORT_ID',
    'ORIGIN_COUNTRY','DEST_COUNTRY','UNIQUE_CARRIER','AIRLINE_ID','UNIQUE_CARRIER_ENTITY',
    'UNIQUE_CARRIER_NAME','REGION','CLASS','AIRCRAFT_GROUP','AIRCRAFT_TYPE','AIRCRAFT_CONFIG',
    'DATA_SOURCE','DISTANCE']
MEASURES = ['FREIGHT','DEPARTURES_PERFORMED','DEPARTURES_SCHEDULED','MAIL','PAYLOAD','SEATS','PASSENGERS']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_table(frame, filename):
    frame.to_parquet(OUT/filename,index=False,compression='zstd',compression_level=12)
    return {'rows':len(frame),'bytes':(OUT/filename).stat().st_size,'sha256':sha(OUT/filename),
            'columns':{k:str(v) for k,v in frame.dtypes.items()}}


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    datasets=load_official(ROOT/'data/official')
    raw=pd.concat([d.rows for _,d in sorted(datasets.items())],ignore_index=True)
    # Preserve integer pounds/counts exactly. Fail rather than round source measures.
    for col in MEASURES:
        assert raw[col].notna().all() and raw[col].ge(0).all()
        assert (raw[col]%1==0).all(), f'Fractional source {col}; revise representation rather than round.'
        raw[col]=raw[col].astype('int64')
    grouped=raw.groupby(DIMENSIONS,dropna=False,observed=True,sort=True)
    segments=grouped[MEASURES].sum().join(grouped.size().rename('SOURCE_RECORD_COUNT')).reset_index()
    for col in ['YEAR','AIRCRAFT_GROUP','AIRCRAFT_TYPE','AIRCRAFT_CONFIG']:
        segments[col]=segments[col].astype('uint16')
    segments['MONTH']=segments.MONTH.astype('uint8')
    for col in ['ORIGIN_AIRPORT_ID','DEST_AIRPORT_ID','AIRLINE_ID','SOURCE_RECORD_COUNT']:
        assert segments[col].between(0,2**32-1).all()
        segments[col]=segments[col].astype('uint32')
    segment_file=write_table(segments,'segments-v1.parquet')
    # Reference join statuses/coordinates are prepared once, without dropping any segment.
    reference=reference_metadata(*[(ROOT/'data/official'/name).read_bytes() for name in ['airports.csv','regions.csv','countries.csv']])
    airports=match_airports(raw,reference)
    fields=['bts_code','bts_country','ident','iata_code','name','iso_country','iso_region',
            'country_name','region_name','type','latitude_deg','longitude_deg','match_status','coordinate_match']
    airports=airports[fields].sort_values(['bts_code','bts_country']).reset_index(drop=True)
    airport_file=write_table(airports,'airports-v1.parquet')
    # Verify serialized output, independently of the dataframe written above.
    packaged=pd.read_parquet(OUT/'segments-v1.parquet')
    assert packaged.SOURCE_RECORD_COUNT.sum()==len(raw)
    checks={}
    axes=[['YEAR'],['YEAR','MONTH'],['YEAR','ORIGIN','DEST'],['YEAR','MONTH','ORIGIN','DEST'],
          ['YEAR','MONTH','ORIGIN','DEST','UNIQUE_CARRIER'],['YEAR','CLASS'],
          ['YEAR','MONTH','ORIGIN','DEST','UNIQUE_CARRIER','CLASS','AIRCRAFT_TYPE','AIRCRAFT_CONFIG']]
    for axis in axes:
        left=raw.groupby(axis,dropna=False)[MEASURES].sum().sort_index()
        right=packaged.groupby(axis,dropna=False)[MEASURES].sum().sort_index()
        pd.testing.assert_frame_equal(left,right,check_dtype=False,check_index_type=False)
        checks['+'.join(axis)]={'groups':len(left),'all_measures_exact':True}
    # Independent DuckDB rollup from the original CSV bytes, comparing complete declared grain.
    csv_paths=[str(extract_csv(d.metadata['path'])) for _,d in sorted(datasets.items())]
    keys=', '.join('"'+key+'"' for key in DIMENSIONS)
    sums=', '.join('sum("'+col+'") AS "'+col+'"' for col in MEASURES)
    with duckdb.connect() as db:
        db.read_csv(csv_paths, dtype={'AIRCRAFT_TYPE':'INTEGER'}).create_view('original')
        db.read_parquet(str(OUT/'segments-v1.parquet')).create_view('packaged')
        expected=f'SELECT {keys}, {sums}, count(*) AS SOURCE_RECORD_COUNT FROM original GROUP BY ALL'
        actual=f'SELECT {keys}, '+', '.join('"'+col+'"' for col in MEASURES)+', SOURCE_RECORD_COUNT FROM packaged'
        differences=db.sql(f'SELECT count(*) FROM (({expected} EXCEPT ALL {actual}) UNION ALL ({actual} EXCEPT ALL {expected}))').fetchone()[0]
        assert differences==0
        # Carrier shares/HHI independent SQL from original rows, compared to app output.
        sql_hhi=db.sql('''WITH c AS (SELECT YEAR,ORIGIN,DEST,UNIQUE_CARRIER,sum(FREIGHT) AS lb
          FROM original GROUP BY ALL), s AS (SELECT *,lb/sum(lb) OVER(PARTITION BY YEAR,ORIGIN,DEST) AS share FROM c)
          SELECT YEAR,ORIGIN,DEST,sum(share*share)*10000 AS hhi FROM s GROUP BY ALL''').df()
    evidence,shares=analyze(packaged)
    official_evidence,_=analyze(raw)
    pd.testing.assert_frame_equal(evidence,official_evidence,check_dtype=False,atol=1e-8,rtol=1e-12)
    for year in [2024,2025]:
        joined=evidence.merge(sql_hhi[sql_hhi.YEAR==year],left_on=['origin','destination'],right_on=['ORIGIN','DEST'])
        assert len(joined)==len(evidence) and (abs(joined[f'hhi_{year}']-joined.hhi)<1e-6).all()
    checks.update(independent_raw_csv_group_difference_count=0,eligible_pairs=len(evidence),all_application_evidence_reconciled=True,
                  all_carrier_shares_reproduced_by_exact_carrier_freight_groups=True)
    # Recheck all case measures using packaged rows; no raw-row lineage is bundled.
    case=packaged[(packaged.ORIGIN=='SZX')&(packaged.DEST=='ANC')]
    for year,group in case.groupby('YEAR'):
        expected=pd.read_csv(ROOT/'docs/cases/szx-anc/annual.csv').set_index('YEAR').loc[year]
        assert group.FREIGHT.sum()==expected.pounds
        assert group.DEPARTURES_PERFORMED.sum()==expected.departures
    annual=packaged.groupby('YEAR')[MEASURES+['SOURCE_RECORD_COUNT']].sum().reset_index().to_dict('records')
    sources=[{'filename':d.metadata['filename'],'year':year,'rows':len(d.rows),'zip_sha256':d.sha256,
              'csv_sha256':d.metadata['csv_sha256']} for year,d in sorted(datasets.items())]
    manifest={'schema_version':1,'dataset_version':'bts-2024-2025-official-20261101-v1',
      'publisher':'US DOT Bureau of Transportation Statistics', 'source_dataset':'T-100 Segment (All Carriers)',
      'source_receipt_date':'2026-11-01','original_download_date':'Not independently recorded; export filenames contain 20261101.',
      'reporting_years':[2024,2025],'months_per_year':list(range(1,13)),'source_records':len(raw),
      'sources':sources,'grain':DIMENSIONS,'measures':MEASURES,'freight_unit':'pounds',
      'metric_tonnes_per_pound':0.00045359237,'aggregation':'Sum integer measures at declared grain; count every original row, including zero freight/departures. No scope exclusions. Aircraft type is a numeric BTS code: CSV padding such as 042 normalizes to 42; carrier/entity strings keep leading zeros.',
      'not_retained':sorted(set(raw.columns)-set(DIMENSIONS)-set(MEASURES)),
      'not_retained_rationale':'Unused descriptive geography/version IDs and time fields are not needed for current freight, frequency, concentration, aircraft/class or coordinate analyses. The projection does not modify the original input files.',
      'files':{'segments-v1.parquet':segment_file,'airports-v1.parquet':airport_file},'annual_totals':annual,'validation':checks,
      'reference_sources':{name:sha(ROOT/'data/official'/name) for name in ['airports.csv','regions.csv','countries.csv']},
      'coordinate_coverage':{'matched':int(airports.coordinate_match.sum()),'total':len(airports),'statuses':airports.match_status.value_counts().to_dict()},
      'redistribution':{'status': 'unresolved', 'hold': True, 'reason': 'Public redistribution requires confirmation of exact T-100 export release status and applicable downstream terms. Elapsed embargo periods alone do not establish redistribution rights. See docs/data-provenance.md.', 'assessment': 'docs/data-provenance.md', 'ourairports_notice': 'docs/licenses/OurAirports-Unlicense.txt'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'files':manifest['files'],'annual_totals':annual,'validation':checks},indent=2))
    return manifest


if __name__=='__main__': build()
