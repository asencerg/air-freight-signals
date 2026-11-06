# Sources and ingestion

The application loads the bundled Parquet package automatically. Official BTS ZIP uploads are optional and replace it for the session. Original archives are required only for source-level rebuilding. The manifest identifies `T_T100_SEGMENT_ALL_CARRIER_20261101_024444.zip` as 2024 and `T_T100_SEGMENT_ALL_CARRIER_20261101_024054.zip` as 2025, using `YEAR` within the records. Preserve original filenames under `data/official/`. Run `python scripts/reconcile_official.py` for the official-versus-historical audit, and `python scripts/build_szx_case.py` to rebuild the case exclusively from official exports. Official ZIP ingestion retains all 50 original fields; the bundled projection is described in [processed data](processed-data.md). See [official reconciliation](official-data-reconciliation.md).

OurAirports enrichment accepts the airport, region and country CSVs: airport iata_code matches are unique and country-checked; region and country labels join explicitly by ISO codes. No coordinate-based or ICAO/local-code fallback occurs.

The mirror is a historical comparator, not a dependency of official-source ingestion.

## BTS source and export requirements

Source: US Department of Transportation, Bureau of Transportation Statistics, https://www.transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EEE .

The current BTS download form, schema, publication completeness for 2025 and any supported automated endpoint have not been independently verified. No unofficial download endpoint is assumed. The following is the intended manual export procedure; confirm the labels and units on the actual BTS page before treating an upload as research evidence.

1. Open the database link and select **T-100 Segment (All Carriers)**, then its download/export option. Do not select T-100 Market or a domestic-only subset.
2. Select reporting year **2024** and all months; repeat for **2025**. Retain all carriers, airports and service classes for consistent scope. If the interface exports one month at a time, download each required month.
3. Include these fields: `YEAR`, `MONTH`, `ORIGIN`, `DEST`, `UNIQUE_CARRIER`, `FREIGHT`, `DEPARTURES_PERFORMED`. Keep aircraft/service identifiers when available so distinct strata remain identifiable. Check the BTS field definitions: this adapter expects freight in **pounds**, excluding mail, and performed departures as a count. Do not upload tonne-denominated or precomputed rate columns under those names.
4. Download CSV (unzip locally if necessary), keep it under ignored `data/`, and upload the non-overlapping files together in the app. File column sets must match. Do not include a total file alongside its component months.
5. Confirm all selected months are published and the extract covers all carriers in each market. Save the download date, source selection and any revision notice alongside the local dataset. The app and CLI identify combined inputs by hashing the ordered sequence of their individual SHA-256 digests. Each individual digest identifies the original input bytes. These hashes identify input content, not source authenticity.

The application fails on missing required fields, invalid periods, missing identifiers, nonfinite/negative quantities, fractional departure counts, exact duplicate records, and positive freight with zero departures. Distinct aircraft/service strata are summed by carrier, directed segment and month. Exact duplicates are rejected for review rather than silently deleted. Missing records cannot reliably be distinguished from zero activity or incomplete exports, so no missing month is imputed. Carrier-level omissions within a present month cannot be detected automatically.

## OurAirports reference enrichment

Reference: https://ourairports.com/data/ . Download `airports.csv` and upload in the optional enrichment section. Expected fields are `iata_code` and `name`; duplicate IATA matches are omitted. The current website schema requires verification before ingestion. Airport names do not change grouping or calculations. Codes can be reassigned over time, and BTS identifiers do not always correspond to current IATA codes; inspect unmatched and historical airports before external publication.

## Verified annual Parquet mirror (2026-11-01)

The historical comparison uses annual files from `Unison-Consulting-Inc/AirportData` at commit `52aa3d888dabe6a38e799064dc28627bc0d68f92`:

- https://github.com/Unison-Consulting-Inc/AirportData/blob/52aa3d888dabe6a38e799064dc28627bc0d68f92/t100_seg/t100_seg_2024.parquet
- https://github.com/Unison-Consulting-Inc/AirportData/blob/52aa3d888dabe6a38e799064dc28627bc0d68f92/t100_seg/t100_seg_2025.parquet

Use **Download raw file**, save under ignored `data/`, and upload both files together. The app accepts these Parquet files directly. Source names `YEAR`, `MONTH`, `ORIGIN`, `DEST`, `UNIQUE_CARRIER`, `FREIGHT`, `DEPARTURES_PERFORMED` map identically to the internal schema. `CLASS`, aircraft strata, airline IDs, carrier names and all other source columns are retained. No direction reversal or conversion occurs during ingestion; freight remains pounds, with metric-tonne conversion only in analysis. CSV ingestion also preserves extra columns, including service strata.

The mirror README attributes these files to BTS T-100 Segment (All Carriers), form `FMG`, and `t100_download.py`; that generator is not in this repository, so its transformations cannot be independently audited here. The freight-pound interpretation follows the BTS T-100 field convention, not Parquet unit metadata; the files contain no unit metadata. This is a genuine third-party BTS-derived extract, not a direct certified BTS download. Its manifest's latest 2025 record count matches the file; no 2024 manifest entry was found.

No LICENSE/COPYING/terms file or explicit reuse grant was found in the AirportData tree or documentation. Public GitHub availability is not itself a redistribution license. Mirror-specific reuse terms remain unconfirmed. The historical mirror files are excluded from the bundled package. Seek mirror-owner confirmation before redistributing their files.

OurAirports data was obtained from its official GitHub repository, `davidmegginson/ourairports-data`; inspected commit `a53a511473382df1da2ba56a229b4b4a3c3904ee`. Its LICENSE is the Unlicense, a public-domain dedication with no warranty. IATA-name joins are reference enrichment only.

For reproducibility and archive prerequisites, see [official reconciliation](official-data-reconciliation.md) and [package rebuilding](processed-data.md). Historical mirrors are not needed for startup.
