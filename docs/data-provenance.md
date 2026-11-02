# Data provenance and source conditions

## BTS observations

US Department of Transportation, Bureau of Transportation Statistics, **T-100 Segment (All Carriers)**, table FMG, provides the monthly segment observations for 2024–2025. The package preserves 1,121,004 source records at its declared grain. [Package schema and hashes](processed-data.md) and [original-export reconciliation](official-data-reconciliation.md) document lineage and numerical fidelity. Source archive names and checksums identify the inputs; they do not independently establish download channel, selection parameters or public-release authorization.

[DOT Order 1351.34, Data Management Policy](https://www.transportation.gov/sites/dot.gov/files/2023-04/Policy%20-%20Data%20Management%20-%201351.34.pdf), approved 13 July 2017, supports public reuse subject to confidentiality and other legal safeguards. Sections 34.4.26–27 distinguish federal works, international licensing and acquired data. Section 34.3 footnote 5 addresses BTS's distinct implementation role. Carrier-submitted observations are not automatically federal-authored works. The dated documentary edition does not establish current supersession status or a dataset-specific worldwide license.

[BTS Restricted Data](https://www.bts.gov/topics/airlines-and-airports/restricted-data) describes six-month international release restrictions and a three-year restriction for US-carrier foreign-to-foreign records. [14 CFR §298.70](https://www.law.cornell.edu/cfr/text/14/298.70) additionally conditions international disclosure on the Department's determination that the database is complete, excludes military service categories, and addresses segments with no US points. The definition includes states, DC, Puerto Rico, the Virgin Islands and US territories or possessions. Its applicability alongside [Part 241](https://www.ecfr.gov/current/title-14/chapter-II/subchapter-A/part-241) and [Part 217](https://www.ecfr.gov/current/title-14/chapter-II/subchapter-A/part-217) must be evaluated for the complete All Carriers population.

The documented evidence comprises the BTS page dated 4 December 2024 and the Cornell regulatory reproduction recorded 2 November 2026; current official text, source-category dictionary and exact export release status remain to be confirmed. See the [official table](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FMG) and [download guide](https://www.bts.gov/airline-data-downloads).

The package has no missing endpoint countries and no no-US-point segments on its recorded BTS country fields, including a territory-inclusive screen. There are no service-class N/R observations. All 24 reporting months pass the minimum six-month calendar screen as of 3 November 2026, including December 2025 (threshold 30 June 2026). These are record-screening results, not independent confirmation of DOT completeness determinations or acquisition authorization. Country conflicts in reference data remain explicit; code prefixes and carrier names are not used to infer eligibility.

**Public redistribution of the full BTS-derived bundle remains unresolved.** Confirmation is needed of the exact FMG export's public-release status and applicable downstream, international and third-party conditions. No CC0 designation or unconditional reuse grant is asserted. Compression, aggregation and screenshots do not automatically remove confidentiality restrictions. A separate NTAD domestic aggregate's licensing metadata does not license this All Carriers package. No restricted record is affirmatively identified by the present screen; absence of such a record is not legal clearance.

## Airport references

**OurAirports**, David Megginson and contributors, supplies airport, region and country reference snapshots. Its pinned [official repository dedication](https://github.com/davidmegginson/ourairports-data/blob/a53a511473382df1da2ba56a229b4b4a3c3904ee/LICENSE) is retained in [OurAirports-Unlicense.txt](licenses/OurAirports-Unlicense.txt). The dedication and no-warranty terms apply to that source, not BTS observations. Reference hashes are in the package manifest. Ambiguous, missing and country-conflicted matches are not silently geocoded.

## Geographic context

**Natural Earth** supplies the locally bundled coastline under its documented public-domain statement. [Geographic sources](geographic-sources.md) records the pinned revision, original/output hashes and reproducible transformation. This provides orientation, not flown trajectories or navigational accuracy.

## Code, reports and dependencies

No license has been granted for the author's original code, reports or screenshots. Source attribution does not imply agency or carrier endorsement. Third-party assets and observations retain their separate terms.

Python dependencies retain their upstream licenses: DuckDB and Plotly.py (MIT), pandas (BSD-3-Clause), Streamlit and PyArrow (Apache-2.0, including applicable bundled notices), and pytest (MIT). Installing upstream packages does not grant their licenses to project data or authored material. Distributed wheels, frontend fonts and standalone HTML exports require their own complete notices. The repository does not bundle dependency binaries or standalone Plotly HTML. See [pinned requirements](../requirements.txt).
