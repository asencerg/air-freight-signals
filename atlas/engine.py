"""Narrow DuckDB queries over the immutable official Parquet package.

No database server, summary download or million-row Pandas load on normal startup.
The legacy engine remains available as the independent regression oracle.
"""
from pathlib import Path
import hashlib
import json
import duckdb
import pandas as pd
from atlas.research import attach_signals

TONNES_PER_POUND = 0.00045359237
ROOT = Path(__file__).resolve().parents[1]


def version_token(directory=None):
    directory = Path(directory or ROOT/'data/processed')
    paths = [directory/name for name in ['manifest.json','segments-v1.parquet','airports-v1.parquet']]
    # Stat changes force a new checked Engine; byte hashes are verified on its construction.
    return tuple((p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in paths)


class Engine:
    def __init__(self, directory=None, rows=None, source=None):
        self.directory=Path(directory or ROOT/'data/processed')
        self.rows=rows
        if rows is None:
            manifest=json.loads((self.directory/'manifest.json').read_text(encoding='utf-8'))
            for name,entry in manifest['files'].items():
                path=self.directory/name
                if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
                    raise ValueError(f'Package checksum mismatch: {name}')
            self.identity=hashlib.sha256((self.directory/'manifest.json').read_bytes()).hexdigest()
            self.source='US DOT BTS T-100 Segment (All Carriers) · official 2024–2025 exports'
            self.airports=pd.read_parquet(self.directory/'airports-v1.parquet')
        else:
            self.identity=source or 'uploaded'
            self.source='User-uploaded BTS reporting data'
            self.airports=pd.DataFrame()

    def connection(self):
        db=duckdb.connect(config={'threads':2,'memory_limit':'512MB'})
        if self.rows is None:
            db.read_parquet(str(self.directory/'segments-v1.parquet')).create_view('segments')
        else:
            db.register('segments',self.rows)
        return db

    @staticmethod
    def months_sql(months):
        months=tuple(sorted(set(int(m) for m in months)))
        if not months or not set(months)<=set(range(1,13)):
            raise ValueError('Choose valid matched months.')
        return months,','.join(map(str,months))

    def carriers(self):
        with self.connection() as db:
            fields=set(db.sql('DESCRIBE segments').df().column_name)
            label='max(UNIQUE_CARRIER_NAME)' if 'UNIQUE_CARRIER_NAME' in fields else 'UNIQUE_CARRIER'
            return db.sql(f'SELECT UNIQUE_CARRIER AS carrier,{label} AS name FROM segments GROUP BY UNIQUE_CARRIER ORDER BY carrier').df()

    def analyze(self, months=tuple(range(1,13)), min_departures=30, min_tonnes=100):
        months,expr=self.months_sql(months)
        with self.connection() as db:
            db.execute(f'''CREATE TEMP TABLE totals AS SELECT ORIGIN origin,DEST destination,YEAR AS "year",
                sum(FREIGHT) freight,sum(DEPARTURES_PERFORMED) departures,count(DISTINCT MONTH) nmonths
                FROM segments WHERE MONTH IN ({expr}) GROUP BY ALL''')
            db.execute('''CREATE TEMP TABLE eligible AS SELECT origin,destination FROM totals
                WHERE year IN (2024,2025) AND nmonths=? AND departures>=? AND departures>0
                AND freight*? >= ? AND freight>0 GROUP BY ALL HAVING count(*)=2''',
                [len(months),min_departures,TONNES_PER_POUND,min_tonnes])
            totals=db.sql('SELECT t.* FROM totals t JOIN eligible USING(origin,destination) WHERE year IN (2024,2025)').df()
            if totals.empty:
                return pd.DataFrame(),pd.DataFrame(columns=['origin','destination','year','carrier','share']),pd.DataFrame()
            carriers=db.sql(f'''SELECT s.ORIGIN origin,s.DEST destination,s.YEAR AS "year",s.UNIQUE_CARRIER carrier,sum(s.FREIGHT) pounds
                FROM segments s JOIN eligible e ON s.ORIGIN=e.origin AND s.DEST=e.destination
                WHERE MONTH IN ({expr}) AND YEAR IN (2024,2025) GROUP BY ALL ORDER BY origin,destination,year,carrier''').df()
            monthly=db.sql(f'''SELECT s.ORIGIN origin,s.DEST destination,s.YEAR AS "year",s.MONTH AS "month",sum(s.FREIGHT) pounds
                FROM segments s JOIN eligible e ON s.ORIGIN=e.origin AND s.DEST=e.destination
                WHERE MONTH IN ({expr}) AND YEAR IN (2024,2025) GROUP BY ALL''').df()
        keys=['origin','destination','year']
        carriers['share']=carriers.pounds/carriers.groupby(keys).pounds.transform('sum')
        carriers['square']=carriers.share**2*10000
        hhi=carriers.groupby(keys).square.sum().rename('hhi')
        top=carriers.loc[carriers.groupby(keys).share.idxmax(),keys+['carrier','share']].rename(columns={'carrier':'top_carrier','share':'top_share'})
        totals['tonnes']=totals.freight*TONNES_PER_POUND
        totals['tonnes_per_departure']=totals.tonnes/totals.departures
        totals=totals.merge(hhi,on=keys).merge(top,on=keys)
        values=['tonnes','departures','tonnes_per_departure','hhi','top_share','top_carrier']
        evidence=totals.pivot(index=['origin','destination'],columns='year',values=values)
        evidence.columns=[f'{k}_{y}' for k,y in evidence.columns]
        evidence=evidence.reset_index().sort_values(['origin','destination']).reset_index(drop=True)
        for col in evidence:
            if col not in ['origin','destination'] and not col.startswith('top_carrier'):
                evidence[col]=pd.to_numeric(evidence[col])
        evidence['months']=','.join(map(str,months))
        for key in ['tonnes','departures','tonnes_per_departure']:
            evidence[key+'_change_pct']=(evidence[key+'_2025']/evidence[key+'_2024']-1)*100
        evidence['hhi_change']=evidence.hhi_2025-evidence.hhi_2024
        m=monthly.pivot(index=['origin','destination','month'],columns='year',values='pounds')
        m['delta']=m[2025]-m[2024]
        c=carriers.pivot(index=['origin','destination','carrier'],columns='year',values='pounds').fillna(0)
        c['delta']=(c[2025]-c[2024])*TONNES_PER_POUND
        out=evidence.assign(market=evidence.origin+' → '+evidence.destination)
        records=attach_signals(out,m,c,months)
        return evidence,carriers[keys+['carrier','share']],records

    def detail(self, origin, destination, months):
        _,expr=self.months_sql(months)
        # Parameterized values; projection/predicate pushdown limits the result to one corridor.
        with self.connection() as db:
            return db.execute(f'SELECT * FROM segments WHERE ORIGIN=? AND DEST=? AND MONTH IN ({expr}) AND YEAR IN (2024,2025)',[origin,destination]).df()
