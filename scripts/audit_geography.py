"""Reproduce coverage from committed package only; no raw downloads required."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas.engine import Engine,TONNES_PER_POUND
from atlas.geography import locate,coverage


def report():
    engine=Engine();_,_,records=engine.analyze();geo=locate(records,engine.airports)
    output={'scope':'Full-year eligible directional corridors: every month, >=100 tonnes and >=30 departures in each year; both safe endpoints needed for mapping. Top-N not applied.',
      'airport_codes':len(engine.airports),'matched_codes':int(engine.airports.coordinate_match.sum()),'statuses':engine.airports.match_status.value_counts().to_dict(),'eligible':{},'all_source_records':{}}
    for year in [2024,2025]:
        item=coverage(geo,year);item['impacts']=item['impacts'].reset_index().to_dict('records')
        item['highest_unmapped']=geo[~geo.mappable].sort_values(f'tonnes_{year}',ascending=False)[['market',f'tonnes_{year}',f'departures_{year}','map_status']].head(15).to_dict('records')
        output['eligible'][str(year)]=item
        with engine.connection() as db:
            raw=db.execute('SELECT ORIGIN origin,DEST destination,sum(FREIGHT) pounds,sum(DEPARTURES_PERFORMED) departures FROM segments WHERE YEAR=? GROUP BY ALL',[year]).df()
        raw[f'tonnes_{year}']=raw.pounds*TONNES_PER_POUND;raw[f'departures_{year}']=raw.departures
        all_cov=coverage(locate(raw,engine.airports),year);all_cov['impacts']=all_cov['impacts'].reset_index().to_dict('records')
        output['all_source_records'][str(year)]=all_cov
    return output

if __name__=='__main__':
    data=report();out=Path('docs/validation/geographic-coverage.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,indent=2),encoding='utf-8');print(out)
