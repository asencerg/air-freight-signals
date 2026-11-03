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

## Geometry, camera and interaction

The offline map uses Plate Carrée (longitude/latitude), with the existing spherical great-circle interpolation (64 intervals). Geometry is unwrapped continuously across the dateline and repeated in adjacent longitude windows. This keeps trans-Pacific arcs continuous in an East Asia / North Pacific view without changing endpoint coordinates or the underlying observations. World views clip arcs at the visible map boundary. Reciprocal routes remain distinct directional records.

Plate Carrée preserves readable longitude/latitude navigation but exaggerates high-latitude area; it is not an equal-area or distance-preserving map. A cylindrical equal-area comparison compresses the northern corridors central to this reporting population, so the default retains Plate Carrée with explicit projection context. Neither representation is a flight track.

Camera controls provide World, North America, Europe, East Asia / North Pacific and Latin America. Fit corridor bounds **all sampled arc points**, with padding, rather than just the endpoints. Reset view returns to the default world extent. These controls do not change analytical filters, route eligibility or coverage denominators. Regional views may omit routes outside their visible bounds; the displayed route list still identifies the full bounded selection.

Pan/zoom extents and exact selected corridor identity are returned through Streamlit's built-in component API. The bridge uses the installed Plotly JavaScript locally, with no CDN, new package dependency or vendored bundle. View extents are validated and retained in session state through route, mode and filter reruns. Focus/Fit/Reset explicitly replace the view. A browser reload or new session starts at the default extent; this is not a persistent saved-map feature.

Selected corridors have a white halo, a direction arrow and labeled endpoints: hollow circle for origin, filled diamond for destination. Large handles sit along the real directed arcs, normally at 38% of their length. Nearby handles are spread across alternative sampled arc points to distinguish parallel and reciprocal routes. Placement uses stable corridor ordering and does not change when selection or encoding changes. Route lines are noninteractive context so nearby parallel or reciprocal paths cannot intercept handle selections. Use the large handles or searchable corridor list; densely overlapping handles may still require the list. Unmapped endpoints are never guessed.

## Map encodings

Routes remain ranked by the selected year's freight for the display cap; switching encoding does not silently select a new analytical population. Widths are bounded to 1–6 pixels, with a selected-route outline added separately.

| Mode | Measurement | Color and width |
|---|---|---|
| Freight volume | Selected-year metric tonnes | Teal; square-root width relative to the largest displayed value |
| Freight change · tonnes | 2025 minus 2024 metric tonnes | Teal increase, rust decrease, gray unchanged; width by absolute change |
| Freight change · % | Percentage relative to 2024 freight | Same diverging colors; width capped at 100%; baselines below 1,000 tonnes are neutral and unscaled |
| Carrier HHI change | 2025 minus 2024 HHI points | Purple higher concentration, teal lower, gray unchanged; width capped at 2,500 points |
| Departures | Selected-year performed departures | Blue; square-root width relative to the largest displayed value |

Undefined or nonfinite values are neutral and unscaled. Suppressing percentage *encoding* does not remove the record or alter eligibility. Tooltips retain the factual values and indicate suppressed baselines. Lower HHI is not automatically greater competition; reporting carriers need not represent independent ownership. Departures do not measure capacity or aircraft utilization.

## Airport hub scope

The optional Airport hub filter selects eligible corridors connected to an airport, with Both directions, Outbound or Inbound controls. Counts, selected-year freight and departures describe that filtered reporting population before the map cap. Coverage and exports use the same denominator. No global network-centrality or market-dominance claim is inferred. Hub selection does not force coordinates for unresolved airports.

## Offline geographic context

Local Natural Earth 1:110m land fill and coastlines provide visual orientation. Generalized land polygons omit interior holes at this scale; the map is not suitable for navigation or boundary interpretation. OurAirports references retain country/coordinate validation and their separate Unlicense. [Geographic sources](geographic-sources.md) records source revisions, hashes and transformations. These source dedications do not license the BTS All Carriers package.
