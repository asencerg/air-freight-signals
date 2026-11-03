"""Build the SZX→ANC case from original official annual BTS exports."""
from pathlib import Path
import hashlib
import json
import sys
import html
import re
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from atlas.analysis import LB_PER_TONNE
from atlas.official import load_official, extract_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/cases/szx-anc'
COMMIT = '52aa3d888dabe6a38e799064dc28627bc0d68f92'


def table(df):
    def fmt(x):
        return f'{x:,.2f}' if isinstance(x, float) else str(x)
    return '| ' + ' | '.join(df.columns) + ' |\n|' + '|'.join(['---']*len(df.columns)) + '|\n' + '\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    frames=[]; provenance=[]; csv_paths=[]
    datasets=load_official(ROOT/'data/official')
    for year,data in sorted(datasets.items()):
        frame=data.rows
        rows=frame[(frame.ORIGIN=='SZX')&(frame.DEST=='ANC')].copy()
        assert not rows.duplicated().any()
        rows['SOURCE_ROW_INDEX']=rows.index
        rows['SOURCE_FILE']=data.metadata['filename']
        frames.append(rows)
        csv_paths.append(str(extract_csv(data.metadata['path'])))
        provenance.append({'year':year,'source_rows':len(rows),'filename':data.metadata['filename'],
                           'sha256':data.sha256,'csv_sha256':data.metadata['csv_sha256']})
    raw=pd.concat(frames,ignore_index=True)
    assert not raw.duplicated().any()
    assert raw[['FREIGHT','DEPARTURES_PERFORMED','UNIQUE_CARRIER','MONTH','CLASS','AIRCRAFT_TYPE']].notna().all().all()
    raw['tonnes']=raw.FREIGHT*0.00045359237  # exact international pound: 0.45359237 kg
    assert (abs(raw.tonnes-raw.FREIGHT/LB_PER_TONNE)<1e-6).all()
    source_out=ROOT/'data/official/derived/szx-anc-source.csv'
    source_out.parent.mkdir(parents=True, exist_ok=True)
    raw.drop(columns='tonnes').to_csv(source_out,index=False)
    annual=raw.groupby('YEAR').agg(pounds=('FREIGHT','sum'),tonnes=('tonnes','sum'),departures=('DEPARTURES_PERFORMED','sum'))
    annual['tonnes_per_departure']=annual.tonnes/annual.departures
    monthly=raw.groupby(['YEAR','MONTH']).agg(tonnes=('tonnes','sum'),departures=('DEPARTURES_PERFORMED','sum'))
    monthly['tonnes_per_departure']=monthly.tonnes/monthly.departures
    carrier=raw.groupby(['YEAR','UNIQUE_CARRIER','UNIQUE_CARRIER_NAME']).agg(tonnes=('tonnes','sum'),departures=('DEPARTURES_PERFORMED','sum')).reset_index()
    carrier['share']=carrier.tonnes/carrier.groupby('YEAR').tonnes.transform('sum')
    hhi=carrier.assign(sq=carrier.share**2*10000).groupby('YEAR').sq.sum()
    cm=raw.groupby(['YEAR','MONTH','UNIQUE_CARRIER']).tonnes.sum()
    mh=(cm/cm.groupby(level=[0,1]).transform('sum')).pow(2).groupby(level=[0,1]).sum()*10000
    monthly['hhi']=mh
    # SQL independent concentration calculation directly from original CSV pounds.
    with duckdb.connect() as db:
        db.read_csv(csv_paths).create_view('official_csv')
        sql=db.execute('''WITH c AS (SELECT YEAR, MONTH, UNIQUE_CARRIER, sum(FREIGHT) AS pounds
          FROM official_csv WHERE ORIGIN='SZX' AND DEST='ANC' GROUP BY ALL),
          s AS (SELECT *, pounds/sum(pounds) OVER(PARTITION BY YEAR,MONTH) AS weight FROM c)
          SELECT YEAR, MONTH, sum(weight*weight)*10000 AS hhi FROM s GROUP BY ALL ORDER BY YEAR,MONTH''').df()
        assert max(abs(sql.hhi.to_numpy()-monthly.hhi.to_numpy()))<1e-8
        direct=db.execute('''WITH c AS (SELECT YEAR,UNIQUE_CARRIER,sum(FREIGHT) AS pounds FROM official_csv
          WHERE ORIGIN='SZX' AND DEST='ANC' GROUP BY ALL), s AS (SELECT *,pounds/sum(pounds) OVER(PARTITION BY YEAR) AS weight FROM c)
          SELECT YEAR,sum(weight*weight)*10000 AS hhi FROM s GROUP BY ALL ORDER BY YEAR''').df()
        assert max(abs(direct.hhi.to_numpy()-hhi.to_numpy()))<1e-8
    annual['hhi']=hhi
    m=monthly.reset_index().pivot(index='MONTH',columns='YEAR')
    mt=pd.DataFrame({'Month':range(1,13),'Tonnes 2024':m.tonnes[2024].values,'Tonnes 2025':m.tonnes[2025].values,
      'Freight change %':((m.tonnes[2025]/m.tonnes[2024]-1)*100).values,
      'Departures 2024':m.departures[2024].values,'Departures 2025':m.departures[2025].values,
      't/dep 2024':m.tonnes_per_departure[2024].values,'t/dep 2025':m.tonnes_per_departure[2025].values,
      'HHI 2024':m.hhi[2024].values,'HHI 2025':m.hhi[2025].values})
    delta=annual.loc[2025,'tonnes']-annual.loc[2024,'tonnes']
    ct=[]
    for code, group in carrier.groupby('UNIQUE_CARRIER'):
        values=group.set_index('YEAR').reindex([2024,2025]).fillna({'tonnes':0,'departures':0,'share':0})
        a,b=values.loc[2024],values.loc[2025]
        ct.append({'Carrier':code,'Name':group.UNIQUE_CARRIER_NAME.iloc[0],'Tonnes 2024':a.tonnes,'Tonnes 2025':b.tonnes,
         'Change tonnes':b.tonnes-a.tonnes,'Share 2024 %':a.share*100,'Share 2025 %':b.share*100,
         'Growth contribution %':(b.tonnes-a.tonnes)/delta*100,'Departures 2024':a.departures,'Departures 2025':b.departures})
    ct=pd.DataFrame(ct).sort_values('Change tonnes',ascending=False)
    def strata(key):
        t=raw.groupby([key,'YEAR']).agg(tonnes=('tonnes','sum'),departures=('DEPARTURES_PERFORMED','sum')).unstack(fill_value=0)
        return pd.DataFrame({key:t.index.astype(str),'Tonnes 2024':t.tonnes[2024].values,'Tonnes 2025':t.tonnes[2025].values,'Departures 2024':t.departures[2024].values,'Departures 2025':t.departures[2025].values})
    aircraft=strata('AIRCRAFT_TYPE'); service=strata('CLASS')
    periods=[]
    for label, months in [('H1',range(1,7)),('H2',range(7,13))]:
        c=raw[raw.MONTH.isin(months)].groupby(['YEAR','UNIQUE_CARRIER']).tonnes.sum()
        concentration=(c/c.groupby(level=0).transform('sum')).pow(2).groupby(level=0).sum()*10000
        periods.append({'Period':label,'HHI 2024':concentration[2024],'HHI 2025':concentration[2025]})
    periods=pd.DataFrame(periods)
    # Standalone charts are self-contained; no CDN required.
    chartdata=monthly.reset_index(); chartdata.YEAR=chartdata.YEAR.astype(str)
    figs=[]
    figs.append(px.line(chartdata,x='MONTH',y='tonnes',color='YEAR',markers=True,title='Matched monthly reported freight · SZX → ANC',labels={'MONTH':'Calendar month','tonnes':'Metric tonnes'}))
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,subplot_titles=['Performed departures','Reported metric tonnes per departure'])
    for year,color in [('2024','#356a91'),('2025','#b75a36')]:
        f=chartdata[chartdata.YEAR==year]
        for i,col in enumerate(['departures','tonnes_per_departure'],1):
            fig.add_trace(go.Scatter(x=f.MONTH,y=f[col],name=year,legendgroup=year,showlegend=i==1,line_color=color,mode='lines+markers'),row=i,col=1)
    fig.update_layout(title='Frequency and freight per departure (not load factor)',height=600);figs.append(fig)
    figs.append(px.bar(ct,x='Carrier',y='Change tonnes',title='Carrier contribution to annual freight change',labels={'Change tonnes':'Change in metric tonnes, 2025 minus 2024'},hover_data=['Name','Growth contribution %']))
    figs.append(px.line(chartdata,x='MONTH',y='hhi',color='YEAR',markers=True,title='Carrier concentration fell in every matched month',labels={'MONTH':'Calendar month','hhi':'HHI (0–10,000)'}))
    for i,fig in enumerate(figs,1):
        fig.update_layout(template='plotly_white',font_family='Arial',margin=dict(l=60,r=30,t=70,b=50))
        fig.write_json(OUT/f'chart-{i}.json')
    annual_table=annual.reset_index().rename(columns={'YEAR':'Year','pounds':'Freight pounds','tonnes':'Metric tonnes','departures':'Departures','tonnes_per_departure':'Tonnes/departure','hhi':'HHI'})
    text=f'''# Shenzhen → Anchorage: growth with broader carrier participation

Research case study · full calendar years 2024 and 2025 · official exports reconciled 2026-11-01.

## Executive summary

Reported freight increased **39.96%**, from **101,320.79 to 141,807.15 metric tonnes** (+40,486.36 tonnes). Departures rose **44.15%**, from **854 to 1,231**, while freight per departure fell **2.90%**, from **118.64 to 115.20 tonnes**. Carrier HHI fell from **5,422.06 to 3,646.06** (−1,776.01 points). UPS increased its freight but its share fell from **69.42% to 53.18%** as other carriers grew faster.

Diversification persists in **all 12 matched months**, including the first quarter before the new positive-freight carriers appear in this extract. FedEx, Polar and Western Global subsequently broadened reported participation. This supports investigating changes in carrier and service mix; it does not identify cargo customers, prove unmet demand, or measure aircraft capacity utilization.

## 1. Source verification and conversion

This case uses only the 52 original 2024 and 74 original 2025 SZX → ANC rows (126 total), selected from the two original official BTS annual ZIP/CSV exports. All 50 source columns are retained in the local source extract, with a zero-based source-file row index added for traceability. The official ZIP and CSV SHA-256 hashes are recorded in the case audit. Historical mirror hashes are retained in mirror-audit.json. The case has no duplicate source rows or missing analytical, aircraft-type or service-class values. All months are present. No rows were dropped or imputed; zero-freight movements remain in departure denominators.

**Conversion:** international pound = 0.45359237 kilograms exactly, hence metric tonnes = FREIGHT × 0.00045359237. Raw annual weights are **223,374,109 lb** and **312,631,252 lb**. The independent multiplication matches the application's division by 2,204.62262185 pounds/tonne to less than 0.000001 tonne per source row. These are metric tonnes, not US short tons. The pound interpretation follows the BTS T-100 FREIGHT field convention; the official CSV itself does not include a unit declaration and the current official field documentation has not been independently verified.

{table(annual_table)}

Source observations: official `T_T100_SEGMENT_ALL_CARRIER_20261101_024444.zip` (2024) and `T_T100_SEGMENT_ALL_CARRIER_20261101_024054.zip` (2025), each containing `T_T100_SEGMENT_ALL_CARRIER.csv`. Reproduction requires the original archives under `data/official/`. Apply `ORIGIN = 'SZX' AND DEST = 'ANC'`. The app offers the official 126-row extract for local inspection when the verified source extract is available; its source filename and zero-based CSV row index identify each observation. See [official reconciliation](../../official-data-reconciliation.md) for the primary-source audit; the historical mirror remains identified in the provenance documentation.

Official reconciliation found no changes to the five briefs' analytical figures or this case's monthly, carrier, type and class totals. One 2024 Atlas source record changed AIRCRAFT_CONFIG from 1 to 2; the official extract retains the corrected value. This does not change the aircraft-type, freight or departure calculations below.

## 2. Equivalent-month trends

Freight increased in 11 of 12 matched months; May was the exception. Comparing the same calendar months reduces seasonal mismatch but is not formal seasonal adjustment. The apparent growth is not confined to a single peak month. All classes and all reporting carriers are included.

{table(mt)}

Charts 1 and 2 show monthly freight, performed departures and freight per departure. The two zero-freight VistaJet departures (February and August 2025) are included: excluding those two only would yield {annual.loc[2025,'tonnes']/1229:.2f} tonnes/departure, versus {annual.loc[2025,'tonnes_per_departure']:.2f} with all observed departures. Neither measure estimates load factor.

## 3. Carriers: volumes, shares and growth contributions

{table(ct)}

Growth contribution = each carrier's absolute tonne change divided by the net segment increase; negative contributions are retained, and contributions sum to 100%. Missing carrier-year combinations below mean no observations in that year's extract, not proof of no actual operation outside this reporting scope. Shares are based on positive freight; a zero-freight carrier has zero share.

**Observed expansion:** UPS increased departures from 580 to 629 and Atlas from 195 to 298; both reported positive freight in every month of both years. AeroLogic contracted from 79 to 54 departures and from 7,164.92 to 5,296.69 tonnes. Its 2024 observations cover April–December; its 2025 observations cover January–March and September–December. This is intermittent participation, not a full-year exit.

**Newly observed positive-freight participation in 2025:** FedEx first appears in April and is present April–December (156 departures); Polar first appears in July and is present July–December (50); Western Global first appears in September and is present September–December (42). They have no rows in the 2024 SZX → ANC extract. Their combined {ct[ct.Carrier.isin(['FX','PO','KD'])]['Tonnes 2025'].sum():,.2f} tonnes account for {ct[ct.Carrier.isin(['FX','PO','KD'])]['Growth contribution %'].sum():.2f}% of net growth. These are first observations within the two-year window, not verified route launch dates.

**Zero-freight movement participation:** VistaJet has two departures, one in February and one in August 2025, with no freight; it is not a freight-market entrant. **No 2024 positive-freight carrier disappears entirely in 2025.** Chart 3 shows absolute changes, avoiding the misleading conclusion that UPS lost volume because its share fell.

## 4. Aircraft and service mix

{table(aircraft)}

Aircraft-type numbers are the exact BTS source codes. The source files contain no aircraft-type descriptions, and an authoritative code lookup has not been verified; model names and payload capacities are deliberately not inferred. Code 821 remains dominant, while code 683 departures increase from 79 to 210 and code 820 appears with 42 departures. Carrier/type contributions show AeroLogic and FedEx on 683, UPS and Atlas on 819/821, Polar on 821, Western Global on 820, and VistaJet on 788. These are aggregated reported type assignments, not tail-level aircraft events.

{table(service)}

Codes G and P carry all freight in this segment; code L contributes only the two zero-freight 2025 departures. Under the conventional T-100 service-class labels, G denotes scheduled all-cargo, P nonscheduled all-cargo, and L nonscheduled passenger/cargo; the original codes are retained and current lookup verification remains outstanding. P freight grew faster than G freight, consistent with a change in reported service mix. This is not evidence about specific charter contracts, customers or capacity utilization.

## 5. Independent HHI and persistence

HHI = 10,000 × sum of squared carrier freight shares. It was recalculated in DuckDB directly from the original official CSV pounds, independently of the Pandas tonne calculation. Both annual values and all 24 monthly values agree within 0.00000001 HHI points. Annual HHI uses annual carrier shares; it is not the mean of monthly HHIs. Zero-freight VistaJet contributes zero.

{table(periods)}

Monthly HHI falls in every matched month (Chart 4). Diversification is therefore not just an annual pooling artifact caused by carriers rotating through different months. It is already visible in January–March, with incumbent share changes; subsequently the newly observed positive-freight carriers add participation. HHI does not consolidate common ownership or commercial control, and it measures reporting-carrier distribution rather than shipper bargaining power.

## 6. Commercial interpretation: observations versus hypotheses

**Observed:** higher segment freight and departures, lower freight per departure, broader positive-freight carrier participation, sustained monthly concentration reduction, and a shift in service/type mix.

**For airport cargo development teams:** prioritize conversations about the operating requirements and continuity of the newly observed services, while maintaining attention to UPS's still-majority share. Test whether ground-handling schedules, transfer processes or facilities are changing in response to the reported mix. The records establish a research priority, not a facility investment requirement.

**For aviation market analysts:** investigate whether the combination of incumbent expansion, new participation and service-class change reflects routing changes, schedule adjustments or broader freight flows. These are hypotheses requiring published schedules, airport statistics and carrier statements. Compare adjacent segments separately before treating this as new shipment demand; Anchorage may be an intermediate stop, and segment totals can count the same shipment on multiple legs.

**Next research steps:** verify current BTS file revisions and aircraft/service code dictionaries; corroborate first-observed carrier months with dated public schedules; compare carrier-level onward routing and other published airport statistics; obtain evidence before attributing any change to particular customers or commodities.

## 7. Methodology and source conditions

Calculations use the original annual BTS exports and exact pound-to-tonne conversion. Monthly reporting is not proof of complete market coverage. Reporting carriers are not consolidated corporate groups; participation changes are not verified first-ever route entry. Aircraft and service codes are retained without inferred payload capacities. No customer, commodity, aircraft utilization or unmet-demand inference is supported.

[Source provenance](../../data-provenance.md) documents the remaining release and redistribution questions. Historical mirror reconciliation supports numerical comparison, not an unconditional license. Source acquisition and unit-dictionary verification have the limits stated in [official reconciliation](../../official-data-reconciliation.md).

## Reproduction and evidence

Run `python scripts/build_szx_case.py` with the project's virtual environment and retained official annual ZIP files. The builder verifies pinned hashes and independently reconciles HHI. The builder writes the row-level extract to `data/official/derived/szx-anc-source.csv`, an ignored path separate from the bundled package. Derived tables and chart JSON are beside this report; `case-study.html` is a self-contained chart-and-table edition for local review. Figures use observed records only. Display rounding does not enter calculations.
'''
    # Check hard-coded executive facts against calculations before emitting the report.
    assert round(annual.loc[2025,'tonnes']/annual.loc[2024,'tonnes']*100-100,2)==39.96
    assert (m.hhi[2025]<m.hhi[2024]).all()
    (OUT/'case-study.md').write_text(text, encoding='utf-8')
    # Render the Markdown through Streamlit's installed Markdown dependency if present; otherwise
    # keep a readable text edition alongside fully interactive charts and HTML evidence tables.
    content='<html><head><meta charset="utf-8"><title>SZX → ANC freight case study</title><style>body{font:16px Arial;max-width:1200px;margin:40px auto;color:#202b35}pre{white-space:pre-wrap;font:inherit;line-height:1.6}table{border-collapse:collapse;font-size:13px}td,th{padding:7px;border-bottom:1px solid #ddd}</style></head><body>'
    content+='<h1>SZX → ANC: freight growth and carrier diversification</h1><p>Independent research · 2024 versus 2025 · genuine BTS-derived observations only</p>'
    for i,fig in enumerate(figs): content+=fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False)
    def inline(value):
        value=html.escape(value)
        value=re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', value)
        value=re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        return re.sub(r'\[([^]]+)\]\((https://[^)]+)\)', r'<a href="\2">\1</a>', value)
    content+='<h2>Complete case study and evidence</h2>'
    for block in text.split('\n\n'):
        if block.startswith('|'):
            lines=block.splitlines()
            content+='<table><thead><tr>'+''.join('<th>'+inline(v.strip())+'</th>' for v in lines[0].strip('|').split('|'))+'</tr></thead><tbody>'
            for line in lines[2:]: content+='<tr>'+''.join('<td>'+inline(v.strip())+'</td>' for v in line.strip('|').split('|'))+'</tr>'
            content+='</tbody></table>'
        elif block.startswith('#'):
            level=len(block)-len(block.lstrip('#'))
            content+=f'<h{level}>'+inline(block.lstrip('# '))+f'</h{level}>'
        else: content+='<p>'+inline(block)+'</p>'
    content+='</body></html>'
    (OUT/'case-study.html').write_text(content, encoding='utf-8')
    for name,frame in [('annual',annual.reset_index()),('monthly',mt),('carriers',ct),('aircraft',aircraft),('service',service),('half-year-hhi',periods)]:frame.to_csv(OUT/f'{name}.csv',index=False)
    audit={'source':'official BTS annual exports','historical_mirror_commit':COMMIT,'source_extract_path':'data/official/derived/szx-anc-source.csv','files':provenance,'rows':len(raw),'monthly_hhi_lower_count':int((m.hhi[2025]<m.hhi[2024]).sum()),'source_extract_sha256':hashlib.sha256(source_out.read_bytes()).hexdigest()}
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2), encoding='utf-8')
    print(annual.to_string()); print(ct.to_string(index=False)); print(periods.to_string(index=False))
    return audit


if __name__=='__main__': build()
