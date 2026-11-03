# Architecture

A single Streamlit application routes four views: Market Overview, Cargo Corridor Explorer, Research Findings and Case Studies. Shared corridor eligibility, signals and rank logic drive overview/research/map evidence; case presentation uses the fixed validated research artifacts. No database server or data download is needed.

## Query path

`atlas.engine.Engine` checks package hashes on construction, retains only the small airport reference table, and opens short-lived DuckDB connections (two threads, 512 MB query memory limit). SQL projects and aggregates the original Parquet by corridor/year, carrier/year and month. Only eligible aggregate results reach Pandas. HHI and top-carrier summaries are vectorized; corridor signals use the existing consolidation logic. Detail queries read just the selected directional pair/months. Original `atlas.analysis.analyze` remains the independent regression oracle and optional reproduction path.

The normal homepage does not call `packaged.load_bundle` or create a million-row DataFrame. Optional uploads use the existing validated adapter and an explicitly in-memory Engine; optional reference enrichment can load source rows only after the user requests it. Direct SQL queries use the 18.91 MB package without additional precomputed freight files.

The DuckDB query path uses pounds × **0.00045359237**. The original analytical oracle retains its rounded reciprocal divisor. Differences are below the regression tolerance (absolute 0.000001 with relative 1e-11 in frame comparison), do not change displayed figures, and are documented numerical representation differences, not source corrections. HHI uses original carrier-pound shares; no intermediate displayed rounding is used.

## Cache boundaries

`atlas.cache` caches the checked Engine as a resource and aggregate results as data. The file-stat/version token changes when manifest or either source file changes; Engine construction rechecks manifest-declared SHA-256 values. Query identity is the manifest hash plus months, departure threshold and tonne threshold. UI search, ranking, pagination, geography and market-presence carrier filters operate on bounded aggregates and do not rerun source aggregation. The map year chooses a column from matched-period results; both years remain available. Resource cache: four entries; research/carrier result caches: sixteen; detail cache: sixty-four. These limits bound growth across filter combinations. Deliberately replacing files while preserving every stat field is outside the supported immutable-package workflow.

## Presentation and geometry

`atlas.research` supplies one record per directional corridor; `atlas.presentation` renders one selected brief and its narrow carrier/month evidence. `atlas.style` and committed `.streamlit/config.toml` define system-font editorial styling. Typography uses system fonts without remote font requests.

`atlas.geography` performs safe endpoint joins and coverage arithmetic independently of UI. `atlas.maps` is imported only on explorer activation and uses local coastline coordinates with great-circle route geometry. Map-selected routes and dropdown selection address the same corridor identity. Current route selection rebuilds a bounded map, so viewport reset on selection is possible. `atlas.explorer` reports top-N and weighted-coverage scope explicitly. Map-only omissions do not affect research totals.

Case Studies imports the case renderer only after navigation. Four validated charts are restyled in memory; the report, underlying case CSV/JSON and original package remain unchanged. Full source narrative and optional local HTML/extract downloads remain accessible without eager homepage rendering.

## Reproducibility

- `python -m pytest -q`: deterministic correctness and lazy-rendering guards.
- `python scripts/audit_geography.py`: both eligible and all-source coverage, from committed files only.
- `python scripts/build_processed.py`: optional original-source package rebuild.
- `python scripts/build_coastline.py`: optional pinned Natural Earth download/verified compact transformation.
