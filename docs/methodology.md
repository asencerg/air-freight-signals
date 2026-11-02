# Methodology

Markets are **directed flight segments**, not shipment origin–destination markets. All reported service and aircraft strata are additive; scheduled and nonscheduled activity and passenger-carried freight may coexist. Freight excludes mail. Pounds are converted to metric tonnes using 2,204.62262185 pounds per tonne.

For each directed pair, sum freight and performed departures separately in 2024 and 2025 over the same selected calendar months. Require each month to have at least one observation in each year. Defaults require at least 100 tonnes and 30 departures in **each** comparison period. These are transparent screening rules, not estimates of statistical significance. Low or zero baselines are excluded; market openings and closures with absent periods are therefore outside this version's detection scope.

Full-year comparisons reduce seasonal mismatch. Partial comparisons use identical months, not sequential months; this is seasonal matching, not a fitted seasonal-adjustment model. Revisions, calendar effects, disruptions, changes in reporting scope and missing carriers remain limitations. Full-year availability must be verified with BTS; a row in every month is necessary but does not establish a complete extract.

Freight per departure = total freight / total performed departures, including departures reporting no freight. Percentage change = (2025 / 2024 − 1) × 100. This ratio is not aircraft load factor and does not measure available payload capacity. A change in flight activity is reported alongside, never substituted for freight change.

Carrier shares are each carrier's freight divided by all freight for the pair and period. HHI = sum of squared shares × 10,000 (range approaching zero to 10,000). Top shares use reporting carrier identities, not corporate ownership groups. The carrier filter selects eligible markets with that carrier present; shares and HHI always retain all reporting carriers. Zero-freight carriers have zero freight share.

Rules generate briefs at absolute freight change ≥15%, freight-change minus departure-change ≥15 percentage points in magnitude, absolute HHI change ≥500, or current top-carrier share ≥80%. Ranking uses absolute percentage change, absolute divergence in percentage points, HHI change /100, or top-carrier percentage respectively. The score is an explicit heuristic for review order; scores across types are not comparable statistical effects or confidence levels. No causal or unmet-demand inference is made. Each brief carries figures, periods, limitations, source label and follow-up research suggestions.

Artificial fixtures under tests/ validate arithmetic only and are not accessible through the application. The bundled empirical findings derive from official BTS exports; artificial fixtures remain confined to tests.

## Optimized query and geographic views

The application uses direct DuckDB Parquet aggregates for normal application queries while retaining the original Pandas engine as a regression oracle. All 2,892 default corridor metrics and carrier-share denominators are checked against that oracle. Metric tonnes in the optimized path use the exact pound multiplier 0.00045359237; the original reciprocal-divisor implementation differs only below displayed precision and the documented numeric tolerance. No dataset rows or source hashes change.

Geographic statistics are conditional on the same filtered eligible corridor universe unless explicitly labeled all-source. Both endpoints must be safe; top-N map selection happens after coverage calculations. See [geographic-methodology.md](geographic-methodology.md) for definitions, geometry, omissions and interpretation limits. The [corridor ranking conventions](research-workflow.md) remain research priorities, not statistical significance or verified commercial opportunities.
