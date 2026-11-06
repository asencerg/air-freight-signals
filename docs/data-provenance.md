# Data provenance and source conditions

## BTS observations

US Department of Transportation, Bureau of Transportation Statistics, **T-100 Segment (All Carriers)**, table FMG, provides the monthly segment observations for 2024–2025. The package preserves 1,121,004 source records at its declared grain. [Package schema and hashes](processed-data.md) and [original-export reconciliation](official-data-reconciliation.md) document lineage and numerical fidelity. Source archive names and checksums identify the inputs; they do not independently establish download channel, selection parameters or public-release authorization.

Official sources: [table definition](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FMG) · [airline download guide](https://www.bts.gov/airline-data-downloads) · [BTS release restrictions](https://www.bts.gov/topics/airlines-and-airports/restricted-data).

### Record scope

The package contains all 24 reporting months, with no missing endpoint countries and no foreign-to-foreign segments under the recorded BTS country fields, including a territory-inclusive US-point screen. No service-class N/R observations are present. Country conflicts in airport reference data remain explicit; code prefixes and carrier names are not used to infer geographic eligibility. These record checks do not independently establish the original export's public-release authorization.

### Source conditions

BTS applies release restrictions to certain international records. Public redistribution terms for this exact derived bundle have not been established; no CC0 or unrestricted reuse grant is asserted. Numerical reconciliation and elapsed reporting periods do not establish redistribution permission. The package manifest retains this qualification separately from its technical checksums.

## Airport references

**OurAirports**, David Megginson and contributors, supplies airport, region and country reference snapshots. Its pinned [official repository dedication](https://github.com/davidmegginson/ourairports-data/blob/a53a511473382df1da2ba56a229b4b4a3c3904ee/LICENSE) is retained in [OurAirports-Unlicense.txt](licenses/OurAirports-Unlicense.txt). The dedication and no-warranty terms apply to that source, not BTS observations. Reference hashes are in the package manifest. Ambiguous, missing and country-conflicted matches are not silently geocoded.

## Geographic context

**Natural Earth** supplies the locally bundled land and coastline under its documented public-domain statement. [Geographic sources](geographic-sources.md) records the pinned revision, original/output hashes and reproducible transformation. This provides orientation, not flown trajectories or navigational accuracy.

## Code, reports and dependencies

No license has been granted for the author's original code, reports or screenshots. Source attribution does not imply agency or carrier endorsement. Third-party assets and observations retain their separate terms.

Python dependencies retain their upstream licenses: DuckDB and Plotly.py (MIT), pandas (BSD-3-Clause), Streamlit and PyArrow (Apache-2.0, including applicable bundled notices), and pytest (MIT). Installing upstream packages does not grant their licenses to project data or authored material. Distributed wheels, frontend fonts and standalone HTML exports require their own complete notices. The repository does not bundle dependency binaries or standalone Plotly HTML. See [pinned requirements](../requirements.txt).
