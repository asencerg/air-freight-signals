# Processed data: official BTS 2024–2025

The package preserves the official exports at the declared grain. The [current redistribution assessment](data-provenance.md) separates DOT policy evidence from BTS release rules and the records present. Public redistribution conditions remain unresolved; no worldwide public-domain or CC0 designation is asserted.

## Files and scope

| File | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `data/processed/segments-v1.parquet` | 1,121,004 | 18,799,202 | `6e5114157edb6fa6b02d367272a60f48afbd8408962bbb9789445aa66e7c10aa` |
| `data/processed/airports-v1.parquet` | 2,340 | 107,357 | `26e18c362e886742c34b54c496345d9f308037f3debe85c64164e436cd545b45` |

The two Parquet files total **18,906,559 bytes (18.91 MB)**, plus a small JSON manifest. Compression is Zstandard level 12 with Parquet dictionary encoding. No Git LFS, API, key, network request, paid service or database server is needed to read them.

The segment table retains all reporting months, directions, carrier/entity IDs, airline ID, carrier name, service class, aircraft group/type/configuration, source category, distance, airport IDs and country codes. It stores FREIGHT, performed/scheduled departures, MAIL, PAYLOAD, SEATS and PASSENGERS as exact signed 64-bit integer sums, plus SOURCE_RECORD_COUNT. Selected dimension columns use checked compact unsigned integers; string IDs retain leading zeros. Numeric aircraft-code padding is normalized (042 → 42), not reinterpreted as a different aircraft type.

**Declared grain:** `YEAR, MONTH, ORIGIN, DEST, ORIGIN_AIRPORT_ID, DEST_AIRPORT_ID, ORIGIN_COUNTRY, DEST_COUNTRY, UNIQUE_CARRIER, AIRLINE_ID, UNIQUE_CARRIER_ENTITY, UNIQUE_CARRIER_NAME, REGION, CLASS, AIRCRAFT_GROUP, AIRCRAFT_TYPE, AIRCRAFT_CONFIG, DATA_SOURCE, DISTANCE`.

The grouping keys happen to be unique for all 1,121,004 records in this source vintage, so this version performs a lossless column projection and type/compression optimization at the retained grain rather than reducing row count. No records are sampled or excluded, including records with zero freight or zero departures. This is a full-scope processed derivative, not a small sample. It is not the original ZIP/CSV or a mirror download.

Omitted fields: `AIR_TIME, CARRIER, CARRIER_GROUP, CARRIER_GROUP_NEW, CARRIER_NAME, DEST_AIRPORT_SEQ_ID, DEST_CITY_MARKET_ID, DEST_CITY_NAME, DEST_COUNTRY_NAME, DEST_STATE_ABR, DEST_STATE_FIPS, DEST_STATE_NM, DEST_WAC, DISTANCE_GROUP, ORIGIN_AIRPORT_SEQ_ID, ORIGIN_CITY_MARKET_ID, ORIGIN_CITY_NAME, ORIGIN_COUNTRY_NAME, ORIGIN_STATE_ABR, ORIGIN_STATE_FIPS, ORIGIN_STATE_NM, ORIGIN_WAC, QUARTER, RAMP_TO_RAMP`. They are unused descriptive geography/version fields, alternate carrier labels/groups, redundant quarter/distance bands and time measures. They are not required for current freight, frequency, carrier-share/HHI, directional/monthly/yearly, service-class or aircraft-type analyses. Quarter is recoverable from month. Tail-level events, original-row traceability and flight-time analysis are not claimed; unchanged original exports remain local for rebuilding and independent source audit.

The airport table has one row per BTS code/country key and retains explicit IATA match status, reference names/regions/countries and coordinates only for the 2,020 safe matches. The 287 unmatched and 33 conflicting keys remain present with null coordinates. No ICAO/local-code fallback or geographic inference is added. Coordinates are candidates validated by unique IATA/country agreement, not a historical BTS-ID crosswalk. These references support the current geographic explorer.

## Provenance and exact conversion

This derivative is built **exclusively from the official US DOT BTS T-100 Segment (All Carriers) ZIP exports** and the official OurAirports reference snapshots. It contains no AirportData mirror records, mirror-derived calculated tables, synthetic observations, raw-source extracts or third-party JavaScript. The original dataset remains separate from the historical mirror described in data-provenance.md.

Source receipt date is 2026-11-01. The original download date/time was not independently captured; filenames contain 20261101 but are not proof of the actual download event. Reporting periods are taken from YEAR and MONTH, not timestamps. Original filenames, record counts, ZIP/CSV SHA-256 values, reference-file checksums, processed checksums and schema are recorded in `data/processed/manifest.json`.

FREIGHT remains integer **pounds** under the BTS T-100 field convention. Metric tonnes = pounds × **0.00045359237**. The established analytical code's divisor 2,204.62262185 is retained to avoid changing validated figures. Neither source CSV nor ZIP embeds a unit declaration; current policy/dictionary verification remains incomplete. Freight per departure is not load factor, and segments are not shipment origins/destinations.

## Reconciliation

The builder compares serialized Parquet against the original CSVs through an independent DuckDB grouping and bidirectional EXCEPT ALL at the complete declared grain: **zero differences**. Pandas checks also match every retained measure at annual, monthly, directional-pair, carrier/month, service-class and aircraft/type/configuration grains. SOURCE_RECORD_COUNT sums to 549,799 (2024) and 571,205 (2025).

Annual freight pounds remain **53,150,672,359** and **50,777,350,469**; performed departures remain **10,682,376** and **10,863,635**. All 2,892 eligible pair results match analysis of the official rows, and independent raw-CSV HHI agrees within 0.000001 points. Exact carrier freight groups reproduce carrier shares. The five research findings and SZX–ANC annual/monthly figures are regression-tested from the package, not replaced by hardcoded narratives. No scope exclusion or unexplained metric discrepancy remains.

## Source conditions

See [data provenance](data-provenance.md) for separately scoped BTS, OurAirports and code rights. The manifest records unresolved public redistribution; it is not a license. Original source archives and extracts remain separate from the bundled package.

## Reproduction and startup

With original official exports and references in `data/official/`:

```sh
python scripts/build_processed.py
python -m pytest -q
python -m streamlit run app.py --browser.gatherUsageStats false
```

The builder needs the official originals and OurAirports files, not the historical mirror or cached reconciliation outputs. End users of this bundle need only requirements.txt and the committed bundle. The app automatically discovers the manifest, checks file hashes and source-row accounting, computes findings, shows existing filters/evidence/case and supports exports. Optional uploads replace the bundle for that session; no upload is requested when the bundle exists. No synthetic fallback is present.

`tests/test_packaged.py` contains mandatory no-raw-data checks and fails rather than skips if the bundle is missing. Existing rebuild/integration tests in test_official/test_real_data may skip when original files are absent. All bundled-app tests must pass in a fresh clone.
