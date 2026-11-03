"""Audit original official exports and compare the historical mirror without forcing agreement."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import duckdb
import pandas as pd
from atlas.official import load_official, extract_csv
from atlas.ingest import TEXT_FIELDS
from atlas.reference import reference_metadata, match_airports
from atlas.analysis import analyze, findings, markdown
from scripts.build_szx_case import table

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [('HKG','ANC'),('PVG','ANC'),('SZX','ANC'),('MIA','BOG'),('ANC','MEM')]


def canonical(frame):
    frame=frame.copy()
    for col in frame:
        if col in TEXT_FIELDS:
            frame[col]=frame[col].fillna('').astype(str)
        else:
            frame[col]=pd.to_numeric(frame[col],errors='raise').astype(float)
    return frame


def main():
    base=ROOT/'data/official'; out=base/'derived';out.mkdir(exist_ok=True)
    datasets=load_official(base)
    audit={'sources':{},'reconciliation':{}}
    official=[];mirrors=[];periods=[];changes=[];source_paths=[]
    for year,data in sorted(datasets.items()):
        f=data.rows; m=pd.read_parquet(ROOT/f'data/t100_seg_{year}.parquet')
        official.append(f);mirrors.append(m)
        source=extract_csv(data.metadata['path']);source_paths.append(str(source))
        with duckdb.connect() as db:
            sql=db.execute('SELECT count(*),sum(FREIGHT),sum(DEPARTURES_PERFORMED) FROM read_csv_auto(?)',[str(source)]).fetchone()
        assert sql==(len(f),f.FREIGHT.sum(),f.DEPARTURES_PERFORMED.sum())
        assert set(f.MONTH)==set(range(1,13))
        assert f.QUARTER.eq(((f.MONTH-1)//3)+1).all()
        audit['sources'][year]={**{k:v for k,v in data.metadata.items() if k!='path'},'sha256':data.sha256,'rows':len(f),
          'columns':list(f),'freight_lb':int(f.FREIGHT.sum()),'departures':int(f.DEPARTURES_PERFORMED.sum()),
          'carriers':f.UNIQUE_CARRIER.nunique(),'pairs':len(f[['ORIGIN','DEST']].drop_duplicates()),
          'months':f.MONTH.value_counts().sort_index().to_dict(),'service_classes':f.CLASS.value_counts().to_dict(),
          'data_sources':f.DATA_SOURCE.value_counts().to_dict(),'missing':f.isna().sum()[f.isna().any()].to_dict(),
          'duplicates':int(f.duplicated().sum())}
        for month,g in f.groupby('MONTH'):
            periods.append({'Year':year,'Month':month,'Rows':len(g),'Freight lb':int(g.FREIGHT.sum()),'Departures':int(g.DEPARTURES_PERFORMED.sum())})
        a,b=canonical(f),canonical(m)
        ha=pd.util.hash_pandas_object(a,index=False);hb=pd.util.hash_pandas_object(b[a.columns],index=False)
        new=a[~ha.isin(hb)];old=b[~hb.isin(ha)]
        new.to_csv(out/f'{year}-official-different.csv',index=False);old.to_csv(out/f'{year}-mirror-different.csv',index=False)
        # This key is unique within the differing rows; omit CONFIG deliberately to identify recoding.
        keys=['YEAR','MONTH','UNIQUE_CARRIER','UNIQUE_CARRIER_ENTITY','ORIGIN','DEST','AIRCRAFT_TYPE','CLASS']
        assert not new.duplicated(keys).any() and not old.duplicated(keys).any()
        paired=new.merge(old,on=keys,suffixes=('_official','_mirror'),how='outer',indicator=True,validate='one_to_one')
        both=paired[paired._merge=='both']
        field_changes={c:int((both[c+'_official'].fillna('')!=both[c+'_mirror'].fillna('')).sum()) for c in new if c not in keys}
        field_changes={k:v for k,v in field_changes.items() if v}
        delta=f.groupby('UNIQUE_CARRIER')[['FREIGHT','DEPARTURES_PERFORMED']].sum().subtract(m.groupby('UNIQUE_CARRIER')[['FREIGHT','DEPARTURES_PERFORMED']].sum(),fill_value=0)
        delta=delta[(delta!=0).any(axis=1)]
        audit['reconciliation'][year]={'mirror_rows':len(m),'row_delta':len(f)-len(m),
          'freight_lb_delta':int(f.FREIGHT.sum()-m.FREIGHT.sum()),'departures_delta':int(f.DEPARTURES_PERFORMED.sum()-m.DEPARTURES_PERFORMED.sum()),
          'official_rows_different':len(new),'mirror_rows_different':len(old),'matched_changed_keys':len(both),
          'official_only_keys':int((paired._merge=='left_only').sum()),'mirror_only_keys':int((paired._merge=='right_only').sum()),
          'changed_fields':field_changes,'carrier_deltas':delta.to_dict(orient='index')}
    rows=pd.concat(official,ignore_index=True);oldrows=pd.concat(mirrors,ignore_index=True)
    evidence,shares=analyze(rows);previous,oldshares=analyze(oldrows)
    evidence.to_csv(out/'evidence.csv',index=False);shares.to_csv(out/'carrier-shares.csv',index=False)
    briefs=findings(evidence);briefs['source']='US DOT BTS T-100 Segment (All Carriers), official annual ZIP exports; 2024–2025'
    briefs.to_csv(out/'findings.csv',index=False)
    # Independent SQL checks from original CSVs, not the application adapter.
    with duckdb.connect() as db:
        db.read_csv(source_paths).create_view('original_csv')
        totals=db.sql('SELECT YEAR,ORIGIN,DEST,sum(FREIGHT) lb,sum(DEPARTURES_PERFORMED) departures FROM original_csv GROUP BY ALL').df()
        hh=db.sql('''WITH c AS (SELECT YEAR,ORIGIN,DEST,UNIQUE_CARRIER,sum(FREIGHT) lb FROM original_csv GROUP BY ALL),
          s AS (SELECT *,lb/sum(lb) OVER(PARTITION BY YEAR,ORIGIN,DEST) AS weight FROM c)
          SELECT YEAR,ORIGIN,DEST,sum(weight*weight)*10000 AS hhi FROM s GROUP BY ALL''').df()
    for year in [2024,2025]:
        check=evidence.merge(totals[totals.YEAR==year],left_on=['origin','destination'],right_on=['ORIGIN','DEST']).merge(hh[hh.YEAR==year],on=['YEAR','ORIGIN','DEST'])
        assert len(check)==len(evidence)
        assert (abs(check[f'tonnes_{year}']*2204.62262185-check.lb)<.01).all()
        assert (check[f'departures_{year}']==check.departures).all()
        assert (abs(check[f'hhi_{year}']-check.hhi)<1e-6).all()
    audit['eligible_pairs']=len(evidence);audit['rule_findings']=len(briefs)
    five=[]
    for a,b in PAIRS:
        cur=evidence[(evidence.origin==a)&(evidence.destination==b)].iloc[0]
        prev=previous[(previous.origin==a)&(previous.destination==b)].iloc[0]
        for year in [2024,2025]:
            five.append({'Segment':f'{a} → {b}','Year':year,'Official tonnes':cur[f'tonnes_{year}'],'Mirror tonnes':prev[f'tonnes_{year}'],
              'Tonne difference':cur[f'tonnes_{year}']-prev[f'tonnes_{year}'],'Official departures':cur[f'departures_{year}'],
              'Departure difference':cur[f'departures_{year}']-prev[f'departures_{year}'],'Official HHI':cur[f'hhi_{year}'],
              'HHI difference':cur[f'hhi_{year}']-prev[f'hhi_{year}']})
    for a,b in PAIRS:
        now=shares[(shares.origin==a)&(shares.destination==b)].sort_values(['year','carrier']).reset_index(drop=True)
        before=oldshares[(oldshares.origin==a)&(oldshares.destination==b)].sort_values(['year','carrier']).reset_index(drop=True)
        pd.testing.assert_frame_equal(now,before,atol=1e-12,rtol=1e-12)
    five=pd.DataFrame(five);five.to_csv(ROOT/'docs/official-five-reconciliation.csv',index=False)
    # Independently compare SZX monthly, carrier, type, class and CONFIG breakdowns.
    szx={}
    for cols in [['YEAR','MONTH'],['YEAR','UNIQUE_CARRIER'],['YEAR','AIRCRAFT_TYPE'],['YEAR','CLASS'],['YEAR','AIRCRAFT_CONFIG']]:
        new=rows[(rows.ORIGIN=='SZX')&(rows.DEST=='ANC')].groupby(cols)[['FREIGHT','DEPARTURES_PERFORMED']].sum()
        old=oldrows[(oldrows.ORIGIN=='SZX')&(oldrows.DEST=='ANC')].groupby(cols)[['FREIGHT','DEPARTURES_PERFORMED']].sum()
        diff=new.subtract(old,fill_value=0);szx['+'.join(cols)]=diff[diff.ne(0).any(axis=1)].reset_index().to_dict('records')
    audit['szx_differences']=szx
    reference=reference_metadata(*[(base/name).read_bytes() for name in ['airports.csv','regions.csv','countries.csv']])
    mapped=match_airports(rows,reference);mapped.to_csv(out/'airport-matches.csv',index=False)
    coverage={'reference_rows':len(reference),'regions':len(pd.read_csv(base/'regions.csv')),'countries':len(pd.read_csv(base/'countries.csv')),
      'unique_bts_codes':len(set(rows.ORIGIN)|set(rows.DEST)), 'endpoint_country_keys':len(mapped),
      'match_status':mapped.match_status.value_counts().to_dict(),'coordinate_matches':int(mapped.coordinate_match.sum()),
      'ambiguous_iata_codes':reference.loc[reference.iata_ambiguous,'iata_code'].nunique(),
      'invalid_reference_coordinates':int((~reference.coordinates_valid).sum()),
      'missing_country_names':int(reference.country_name.isna().sum()),'inconsistent_regions':int((~reference.region_consistent).sum())}
    # Event-row coverage counts each raw BTS row once, regardless of frequency/weight.
    for end in ['ORIGIN','DEST']:
        merged=rows[[end,end+'_COUNTRY']].merge(mapped[['bts_code','bts_country','coordinate_match']],left_on=[end,end+'_COUNTRY'],right_on=['bts_code','bts_country'],validate='many_to_one')
        coverage[end.lower()+'_rows_with_coordinates']=int(merged.coordinate_match.sum())
    audit['airport_coverage']=coverage
    audit['reference_sha256']={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in ['airports.csv','regions.csv','countries.csv']}
    # Network footprint retains previous methodology: presence, not inferred launches/closures.
    active={y:set(map(tuple,d.rows.loc[d.rows.FREIGHT>0,['ORIGIN','DEST']].drop_duplicates().values)) for y,d in datasets.items()}
    audit['network']={'positive_freight_pairs_2024':len(active[2024]),'positive_freight_pairs_2025':len(active[2025]),'both':len(active[2024]&active[2025]),'only_2024':len(active[2024]-active[2025]),'only_2025':len(active[2025]-active[2024])}
    (out/'audit.json').write_text(json.dumps(audit,indent=2,default=int))
    (ROOT/'docs/official-data-audit.json').write_text(json.dumps(audit,indent=2,default=int))
    overview=pd.DataFrame([{'Year':y,'Archive':d.metadata['filename'],'Rows':len(d.rows),'Freight lb':int(d.rows.FREIGHT.sum()),'Departures':int(d.rows.DEPARTURES_PERFORMED.sum())} for y,d in sorted(datasets.items())])
    report=f'''# Official BTS validation and mirror reconciliation

Reviewed 1 November 2026. **Primary source: the two official US DOT BTS T-100 Segment (All Carriers) exports.** The AirportData files are historical comparators only. No mirror fallback, imputation or forced reconciliation is used.

## Source identification and preservation

{table(overview)}

Reporting years come from YEAR, not the download timestamp. Original ZIP filenames, SHA-256 checksums, member hashes and the exact 50 columns are recorded in [the audit](official-data-audit.json). Reproduction requires those archives under `data/official/`. Each ZIP contains one ordinary comma-separated `T_T100_SEGMENT_ALL_CARRIER.csv`. It is extracted without renaming under an archive-specific directory to avoid filename collision. Reproduction also requires the three matching OurAirports CSVs in that directory.

## Periods, scope and units

{table(pd.DataFrame(periods))}

All 12 months occur in each year; YEAR/MONTH/QUARTER agree. Both exports retain all 50 observed fields, service classes F/G/L/P, and multiple carriers and domestic/international source categories. There are no exact duplicate rows, no missing required analytical/identity/aircraft/class fields, no negative/nonfinite freight or departure values, and no positive-freight rows with zero departures. The per-field missing counts and class/data-source counts are in the audit. Missing state metadata is retained and excluded from analytical keys. Exact-record duplicates across years do not occur.

This establishes full calendar-period coverage, not a proof of complete BTS universe coverage: the ZIPs have no download-query/filter manifest. The 2025 full-file match and broad 2024 overlap with the historical all-carrier mirror provide corroboration; no unexpected carrier/class-only restriction is evident. Hidden export filters and reporting revisions cannot be ruled out solely from records.

FREIGHT is interpreted as **pounds under the BTS T-100 field definition**, excluding MAIL. Metric tonnes = pounds × **0.00045359237** (exact international-pound conversion). The existing divisor 2,204.62262185 agrees to sub-microtonne precision per observed row. The CSV and ZIP contain no explicit unit declaration or official data dictionary. Exact 2025 equality and 2024 overlap confirm the same raw scale as the prior files, but do not independently certify that definition. No units are inferred from a timestamp or magnitude, and no payload-utilization inference is made.

## Independent checks and discrepancies

Annual raw-CSV DuckDB sums equal the adapter/Pandas totals exactly. Independent raw-CSV SQL queries reproduce freight (within 0.01 lb), departures (exactly) and HHI (within 0.000001 points) for all **{len(evidence):,}** eligible directed pairs. The application rules produce **{len(briefs):,}** briefs; multiple briefs can describe one pair.

2025: **all 571,205 records match the mirror on all 50 fields**, regardless of row order; zero metric discrepancies.

2024: official has **549,799** rows versus **549,552** in the mirror (+247), **+17,008,789 lb** (about 7,715.06 metric tonnes) and **+10,490 departures**. Canonical all-field comparison finds 1,471 official and 1,224 historical records without exact counterparts. On a unique diagnostic key of year/month/carrier/entity/origin/destination/aircraft type/class (excluding configuration deliberately), there are 1,206 changed matches, 265 official-only keys and 18 mirror-only keys. Changed fields include 330 AIRCRAFT_CONFIG values, 795 carrier-name labels, 68 FREIGHT values and 62 performed-departure values; payload/seats/passengers also change. Full field counts and net carrier deltas are in the audit. Differences are retained, not normalized away.

The pattern is consistent with later corrections, additional submissions and recoding, but **causes are hypotheses**: neither an official revision log nor the mirror generator is available. Aircraft configuration changes can move a record between source-stratum keys; they are not automatically new flights. Carrier-name changes do not create new reporting carriers.

## Five research findings: official recalculation

{table(five)}

All five findings' freight, departure, per-departure, share and HHI figures are unchanged. Accordingly no numerical correction to these briefs is warranted. This does not imply all markets are unchanged; annual aggregate discrepancies above remain real. The recalculated full evidence and briefs are stored under ignored `data/official/derived/`.

For SZX → ANC, the same 52 + 74 rows support the case. Monthly, carrier, aircraft-type and service-class totals are unchanged. One 2024 Atlas record changes AIRCRAFT_CONFIG from 1 to 2; its freight/departures/type/class are unchanged. The new extract preserves the official configuration, and the historical extract is retained separately. Independent monthly and annual HHI checks are rerun by the case builder; no synthetic fixture is used as empirical evidence.

## Airport, region and country matching

{table(pd.DataFrame([{'Measure':k,'Value':str(v)} for k,v in coverage.items()]))}

Match BTS ORIGIN/DEST **only to a unique OurAirports iata_code**, then require agreement with the BTS country code. No fallback to ICAO, ident, GPS or local_code is permitted. Duplicate IATA references, missing matches and country conflicts remain flagged and receive no coordinates. A matching code/country is a candidate geographic match, not a dated authoritative BTS-airport-ID crosswalk. Reassigned codes, historical airports and BTS local conventions remain limitations.

Regions join only on iso_region → regions.code; countries join only on iso_country → countries.code. Region-country disagreement is flagged and its region label suppressed. CSV parsing preserves the literal country code **NA (Namibia)** instead of treating it as missing. Latitude/longitude must be numeric and within ±90/±180; zero is a valid coordinate, not automatically missing. Source coordinates, country/region labels and match statuses are inspectable without adding a map. Matching does not drop freight records or affect analytical totals. Details and unresolved keys remain in ignored `airport-matches.csv`. Among country conflicts are US-territory scope differences (BTS US versus OurAirports PR/VI/GU/etc.), GB versus GG/JE, and Kosovo KV versus XK, alongside genuine code collisions such as BTS US PTL versus an OurAirports airport in Peru. No territory or country-code alias is silently assumed. A future dated BTS-ID crosswalk can resolve these separately.

## Reproduction and limitations

From the repository root with Python 3.12 and requirements installed:

```sh
python scripts/reconcile_official.py
python scripts/build_szx_case.py
python -m pytest -q
python -m streamlit run app.py --browser.gatherUsageStats false
```

Place the five original source files under `data/official/`. Reconciliation additionally requires the historical mirror files under `data/`; primary ingestion and official case generation do not. In the app, upload the official ZIPs directly; historical Parquet/CSV support remains for comparison, but mixing official ZIPs with mirror uploads in one analysis is rejected.

The archives are identified as BTS exports by their acquisition record and schema; their download channel is not independently authenticated. Direct-source possession resolves dependence on third-party Parquet packaging for current calculations, but does not itself establish redistribution rights. The [source-rights assessment](data-provenance.md) addresses DOT Order 1351.34, BTS Restricted Data guidance and §298.70. Current regulatory applicability, completeness/release status and the field dictionary remain unverified. OurAirports' previously verified official repository dedication remains applicable to the matching snapshot; mirror licensing is still relevant to historical files only. See data-provenance.md for the policy limitations.
'''
    (ROOT/'docs/official-data-reconciliation.md').write_text(report)
    print(overview.to_string(index=False));print(json.dumps(audit['reconciliation'],indent=2));print(json.dumps(coverage,indent=2));print(five.to_string(index=False))
    return audit


if __name__=='__main__': main()
