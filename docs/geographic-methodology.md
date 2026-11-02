# Geographic scope and coverage

The map uses the unchanged `airports-v1.parquet` reference snapshot. Its 2,340 distinct BTS codes comprise 2,020 country-checked IATA matches, 287 unmatched codes and 33 country conflicts. A code match rate of 86.32% is **not** a freight coverage estimate. No name similarity, ICAO/local-code substitution or country-conflict override is used. Ambiguous duplicate reference keys are rejected from mapping without expanding analytical rows.

A corridor is mappable only if **both** endpoints have a verified `matched_iata_country` status, true coordinate-match flag and finite, in-range coordinates. Geographic filters use only verified endpoint names/country/region labels. Country conflicts and missing/ambiguous references remain explicit; map exclusions never remove records from research totals.

## Denominators

The explorer operates on the same eligible matched-period corridor universe as research (defaults: every month in both years, at least 100 metric tonnes and 30 departures in each year). Apply shared airport/carrier/signal/search filters and geographic origin/destination/country/region/minimum-volume/change filters **before** computing coverage. A carrier filter selects markets; it does not recalculate a carrier-only HHI or freight denominator. The map's reporting-year selector changes weights and route-size rankings, while growth/contraction always compares the same selected months in 2024 and 2025.

- Freight-weighted coverage = tonnes on fully mappable corridors / tonnes on all filtered eligible corridors in the selected year.
- Departure-weighted coverage uses reported performed departures with the same numerator/denominator scope.
- Corridor coverage = fully mappable directional corridors / all filtered eligible directional corridors.
- Zero denominators display no denominator, not 0% or 100%.
- Top-N is applied only **after** coverage; the map shows the highest-volume mappable subset. Default 25, maximum 100. All selected/unmapped totals remain available below the map and in its export.

For the default 2,892-corridor universe, **2,800 (96.82%)** are mappable. In 2025 this covers **98.6178% of tonnes** and **97.5880% of departures**. Unmapped: **289,205.53 tonnes and 101,950 departures**. In 2024 coverage is **98.5220% / 97.5887%**; unmapped **322,038.52 tonnes and 103,135 departures**.

High-volume 2025 omissions include MIA → SJU (40,791.73 t), SDF → SJU (26,095.41 t), MEM → SJU (21,307.83 t) and MEM → BQN (20,293.75 t), all flagged country conflicts. These are retained flags, not a finding that the airports are unlocatable. Territorial/country coding deserves independent crosswalk review; this implementation does not silently resolve it.

[geographic-coverage.json](validation/geographic-coverage.json) also records **all-source-record** coverage, which has a different denominator: 40,740 observed corridors in 2024 and 41,489 in 2025. Do not interchange those values with the filtered eligible-map percentages. Reproduce both scopes with `python scripts/audit_geography.py`; no originals or network access are needed.

## Geometry and interaction

A local Plotly Cartesian map uses Plate Carrée (longitude/latitude) with spherical great-circle interpolation (64 intervals). Lines are split at ±180°; seam latitude is linearly interpolated between adjacent samples. Reverse routes remain separate identities. Selected-route arrows point toward destination; selection handles lie 40% along each directed arc so reciprocal routes have different handles. Coincident endpoints are supported; exactly antipodal endpoints have no unique shortest arc and are rejected. No original dataset route required an antipodal approximation in the tested map scope.

This is a small-scale geographic comparison, not an equal-area/distance map or actual flown path. High-latitude scale distortion is inherent to Plate Carrée. Line width uses square-root freight scaling, except the fixed selected highlight. Teal circles denote non-negative changes, rust diamonds declines; tooltips give numeric change, volumes, departures and HHI. Directional labels and selected arrows carry meaning independently of color. Pan, wheel zoom and reset controls are supported; selecting a different corridor rebuilds its map and evidence, and may reset viewport state.

## Offline context and attribution

Only locally bundled Natural Earth 1:110m coastlines provide map context; there are no remote tiles, geocoders or API tokens. OurAirports attribution and its preserved Unlicense apply to airport metadata. Natural Earth source and compact output hashes are in [geographic-sources.md](geographic-sources.md). Neither source's dedication is presented as licensing the BTS All Carriers package.
