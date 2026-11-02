# Official BTS validation and mirror reconciliation

Reviewed 1 November 2026. **Primary source: the two official US DOT BTS T-100 Segment (All Carriers) exports.** The AirportData files are historical comparators only. No mirror fallback, imputation or forced reconciliation is used.

## Source identification and preservation

| Year | Archive | Rows | Freight lb | Departures |
|---|---|---|---|---|
| 2024 | T_T100_SEGMENT_ALL_CARRIER_20261101_024444.zip | 549799 | 53150672359 | 10682376 |
| 2025 | T_T100_SEGMENT_ALL_CARRIER_20261101_024054.zip | 571205 | 50777350469 | 10863635 |

Reporting years come from YEAR, not the download timestamp. Both original ZIP filenames and bytes are retained in ignored `data/official/`; SHA-256, member hashes and the exact 50 columns are in [the audit](official-data-audit.json). Each ZIP contains one ordinary comma-separated `T_T100_SEGMENT_ALL_CARRIER.csv`. It is extracted without renaming under an archive-specific directory to avoid filename collision. All three OurAirports CSVs are preserved alongside them.

## Periods, scope and units

| Year | Month | Rows | Freight lb | Departures |
|---|---|---|---|---|
| 2024 | 1 | 45204 | 4004593732 | 812475 |
| 2024 | 2 | 42339 | 3943246432 | 791609 |
| 2024 | 3 | 45200 | 4459793681 | 892887 |
| 2024 | 4 | 43629 | 4278129910 | 879078 |
| 2024 | 5 | 47193 | 4582403972 | 921436 |
| 2024 | 6 | 47638 | 4433545706 | 928941 |
| 2024 | 7 | 47460 | 4440270491 | 959345 |
| 2024 | 8 | 47893 | 4572018011 | 942244 |
| 2024 | 9 | 44755 | 4356682612 | 876601 |
| 2024 | 10 | 44949 | 4756092039 | 913738 |
| 2024 | 11 | 45727 | 4591974017 | 864199 |
| 2024 | 12 | 47812 | 4731921756 | 899823 |
| 2025 | 1 | 45453 | 4060475313 | 834866 |
| 2025 | 2 | 43875 | 3666304395 | 784723 |
| 2025 | 3 | 48154 | 4417112884 | 928957 |
| 2025 | 4 | 45918 | 4339961616 | 907588 |
| 2025 | 5 | 47641 | 4187891021 | 939489 |
| 2025 | 6 | 50111 | 4113398142 | 949721 |
| 2025 | 7 | 49604 | 4376443901 | 985404 |
| 2025 | 8 | 49734 | 4257086954 | 955626 |
| 2025 | 9 | 45152 | 4103783691 | 872206 |
| 2025 | 10 | 47965 | 4462036565 | 932639 |
| 2025 | 11 | 48307 | 4308494318 | 864349 |
| 2025 | 12 | 49291 | 4484361669 | 908067 |

All 12 months occur in each year; YEAR/MONTH/QUARTER agree. Both exports retain all 50 observed fields, service classes F/G/L/P, and multiple carriers and domestic/international source categories. There are no exact duplicate rows, no missing required analytical/identity/aircraft/class fields, no negative/nonfinite freight or departure values, and no positive-freight rows with zero departures. The per-field missing counts and class/data-source counts are in the audit. Missing state metadata is retained and excluded from analytical keys. Exact-record duplicates across years do not occur.

This establishes full calendar-period coverage, not a proof of complete BTS universe coverage: the ZIPs have no download-query/filter manifest. The 2025 full-file match and broad 2024 overlap with the historical all-carrier mirror provide corroboration; no unexpected carrier/class-only restriction is evident. Hidden export filters and reporting revisions cannot be ruled out solely from records.

FREIGHT is interpreted as **pounds under the BTS T-100 field definition**, excluding MAIL. Metric tonnes = pounds × **0.00045359237** (exact international-pound conversion). The existing divisor 2,204.62262185 agrees to sub-microtonne precision per observed row. The CSV and ZIP contain no explicit unit declaration or official data dictionary. Exact 2025 equality and 2024 overlap confirm the same raw scale as the prior files, but do not independently certify that definition. No units are inferred from a timestamp or magnitude, and no payload-utilization inference is made.

## Independent checks and discrepancies

Annual raw-CSV DuckDB sums equal the adapter/Pandas totals exactly. Independent raw-CSV SQL queries reproduce freight (within 0.01 lb), departures (exactly) and HHI (within 0.000001 points) for all **2,892** eligible directed pairs. The application rules produce **5,645** briefs; multiple briefs can describe one pair.

2025: **all 571,205 records match the mirror on all 50 fields**, regardless of row order; zero metric discrepancies.

2024: official has **549,799** rows versus **549,552** in the mirror (+247), **+17,008,789 lb** (about 7,715.06 metric tonnes) and **+10,490 departures**. Canonical all-field comparison finds 1,471 official and 1,224 historical records without exact counterparts. On a unique diagnostic key of year/month/carrier/entity/origin/destination/aircraft type/class (excluding configuration deliberately), there are 1,206 changed matches, 265 official-only keys and 18 mirror-only keys. Changed fields include 330 AIRCRAFT_CONFIG values, 795 carrier-name labels, 68 FREIGHT values and 62 performed-departure values; payload/seats/passengers also change. Full field counts and net carrier deltas are in the audit. Differences are retained, not normalized away.

The pattern is consistent with later corrections, additional submissions and recoding, but **causes are hypotheses**: neither an official revision log nor the mirror generator is available. Aircraft configuration changes can move a record between source-stratum keys; they are not automatically new flights. Carrier-name changes do not create new reporting carriers.

## Five research findings: official recalculation

| Segment | Year | Official tonnes | Mirror tonnes | Tonne difference | Official departures | Departure difference | Official HHI | HHI difference |
|---|---|---|---|---|---|---|---|---|
| HKG → ANC | 2024 | 636,074.30 | 636,074.30 | 0.00 | 6,218.00 | 0.00 | 2,111.24 | 0.00 |
| HKG → ANC | 2025 | 525,517.59 | 525,517.59 | 0.00 | 5,066.00 | 0.00 | 2,344.24 | 0.00 |
| PVG → ANC | 2024 | 288,257.15 | 288,257.15 | 0.00 | 2,691.00 | 0.00 | 1,636.24 | 0.00 |
| PVG → ANC | 2025 | 361,567.55 | 361,567.55 | 0.00 | 3,639.00 | 0.00 | 1,793.46 | 0.00 |
| SZX → ANC | 2024 | 101,320.79 | 101,320.79 | 0.00 | 854.00 | 0.00 | 5,422.06 | 0.00 |
| SZX → ANC | 2025 | 141,807.15 | 141,807.15 | 0.00 | 1,231.00 | 0.00 | 3,646.06 | 0.00 |
| MIA → BOG | 2024 | 114,137.37 | 114,137.37 | 0.00 | 6,970.00 | 0.00 | 1,479.58 | 0.00 |
| MIA → BOG | 2025 | 145,297.40 | 145,297.40 | 0.00 | 7,468.00 | 0.00 | 1,371.72 | 0.00 |
| ANC → MEM | 2024 | 120,381.34 | 120,381.34 | 0.00 | 1,754.00 | 0.00 | 10,000.00 | 0.00 |
| ANC → MEM | 2025 | 88,450.96 | 88,450.96 | 0.00 | 1,416.00 | 0.00 | 9,989.31 | 0.00 |

All five findings' freight, departure, per-departure, share and HHI figures are unchanged. Accordingly no numerical correction to these briefs is warranted. This does not imply all markets are unchanged; annual aggregate discrepancies above remain real. The recalculated full evidence and briefs are stored under ignored `data/official/derived/`.

For SZX → ANC, the same 52 + 74 rows support the case. Monthly, carrier, aircraft-type and service-class totals are unchanged. One 2024 Atlas record changes AIRCRAFT_CONFIG from 1 to 2; its freight/departures/type/class are unchanged. The new extract preserves the official configuration, and the historical extract is retained separately. Independent monthly and annual HHI checks are rerun by the case builder; no synthetic fixture is used as empirical evidence.

## Airport, region and country matching

| Measure | Value |
|---|---|
| reference_rows | 86329 |
| regions | 3987 |
| countries | 249 |
| unique_bts_codes | 2340 |
| endpoint_country_keys | 2340 |
| match_status | {'matched_iata_country': 2020, 'unmatched_iata': 287, 'country_conflict': 33} |
| coordinate_matches | 2020 |
| ambiguous_iata_codes | 0 |
| invalid_reference_coordinates | 0 |
| missing_country_names | 0 |
| inconsistent_regions | 0 |
| origin_rows_with_coordinates | 1102640 |
| dest_rows_with_coordinates | 1103365 |

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

The archives are identified as BTS exports by their acquisition record and schema; their download channel is not independently authenticated. Direct-source possession resolves dependence on third-party Parquet packaging for current calculations, but does not itself establish redistribution rights. The full documented DOT order is now reviewed in the [current rights assessment](data-provenance.md); the BTS restriction page and §298.70 are also reviewed, while current regulatory applicability, completeness/release status and the field dictionary still require verification. OurAirports' previously verified official repository dedication remains applicable to the matching snapshot; mirror licensing is still relevant to historical files only. See data-provenance.md for the policy limitations.

## Executed verification record

On these retained source files, the full suite completed with **24 passed** (no failures or skips). This includes both complete official ZIPs and all three references in Streamlit AppTest, original-column preservation, literal Namibia country-code handling, ambiguity/conflict rejection, mixed-vintage rejection, malformed ZIP rejection, the historical regression suite and official case traceability. A clean source-only copy completed with **14 passed, 10 expected source-dependent skips**; those skips are not real-data validation.

The CLI successfully persisted **1,121,004 official rows** to an ignored DuckDB database. Its annual count/freight/departure totals match the original-export audit. Streamlit started on the local machine and both its root page and health endpoint responded successfully. No public preview or deployment was created. The SZX case's annual/monthly/carrier/type/class tables and all four chart JSON files are byte-identical to the prior validated artifacts; only source attribution, trace metadata and the official row extract changed.

Coordinate coverage is **86.32% of unique BTS codes**, **98.36% of source origin rows**, and **98.43% of source destination rows**. These row percentages are not freight-weighted coverage measures. The 2024 revision is +0.0320% freight and +0.0983% departures relative to the mirror. The five original source files retain the filenames and checksums recorded in the source audit. Git exclusions cover originals, CSV extracts, Parquet, databases, large generated outputs and standalone HTML.
