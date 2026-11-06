# Shenzhen → Anchorage: growth with broader carrier participation

Research case study · full calendar years 2024 and 2025 · official exports reconciled 2026-11-01.

## Executive summary

Reported freight increased **39.96%**, from **101,320.79 to 141,807.15 metric tonnes** (+40,486.36 tonnes). Departures rose **44.15%**, from **854 to 1,231**, while freight per departure fell **2.90%**, from **118.64 to 115.20 tonnes**. Carrier HHI fell from **5,422.06 to 3,646.06** (−1,776.01 points). UPS increased its freight but its share fell from **69.42% to 53.18%** as other carriers grew faster.

Diversification persists in **all 12 matched months**, including the first quarter before the new positive-freight carriers appear in this extract. FedEx, Polar and Western Global subsequently broadened reported participation. This supports investigating changes in carrier and service mix; it does not identify cargo customers, prove unmet demand, or measure aircraft capacity utilization.

## 1. Source verification and conversion

This case uses only the 52 original 2024 and 74 original 2025 SZX → ANC rows (126 total), selected from the two original official BTS annual ZIP/CSV exports. All 50 source columns are retained in the local source extract, with a zero-based source-file row index added for traceability. The official ZIP and CSV SHA-256 hashes are recorded in the case audit. Historical mirror hashes are retained in mirror-audit.json. The case has no duplicate source rows or missing analytical, aircraft-type or service-class values. All months are present. No rows were dropped or imputed; zero-freight movements remain in departure denominators.

**Conversion:** international pound = 0.45359237 kilograms exactly, hence metric tonnes = FREIGHT × 0.00045359237. Raw annual weights are **223,374,109 lb** and **312,631,252 lb**. The independent multiplication matches the application's division by 2,204.62262185 pounds/tonne to less than 0.000001 tonne per source row. These are metric tonnes, not US short tons. The pound interpretation follows the BTS T-100 FREIGHT field convention; the official CSV itself does not include a unit declaration and the current official field documentation has not been independently verified.

| Year | Freight pounds | Metric tonnes | Departures | Tonnes/departure | HHI |
|---|---|---|---|---|---|
| 2024 | 223,374,109.00 | 101,320.79 | 854.00 | 118.64 | 5,422.06 |
| 2025 | 312,631,252.00 | 141,807.15 | 1,231.00 | 115.20 | 3,646.06 |

Source observations: official `T_T100_SEGMENT_ALL_CARRIER_20261101_024444.zip` (2024) and `T_T100_SEGMENT_ALL_CARRIER_20261101_024054.zip` (2025), each containing `T_T100_SEGMENT_ALL_CARRIER.csv`. Reproduction requires the original archives under `data/official/`. Apply `ORIGIN = 'SZX' AND DEST = 'ANC'`. The app offers the official 126-row extract for local inspection when the verified source extract is available; its source filename and zero-based CSV row index identify each observation. See [official reconciliation](../../official-data-reconciliation.md) for the primary-source audit; the historical mirror remains identified in the provenance documentation.

Official reconciliation found no changes to the five briefs' analytical figures or this case's monthly, carrier, type and class totals. One 2024 Atlas source record changed AIRCRAFT_CONFIG from 1 to 2; the official extract retains the corrected value. This does not change the aircraft-type, freight or departure calculations below.

## 2. Equivalent-month trends

Freight increased in 11 of 12 matched months; May was the exception. Comparing the same calendar months reduces seasonal mismatch but is not formal seasonal adjustment. The apparent growth is not confined to a single peak month. All classes and all reporting carriers are included.

| Month | Tonnes 2024 | Tonnes 2025 | Freight change % | Departures 2024 | Departures 2025 | t/dep 2024 | t/dep 2025 | HHI 2024 | HHI 2025 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 5,743.56 | 11,042.90 | 92.27 | 47.00 | 94.00 | 122.20 | 117.48 | 7,299.73 | 4,199.30 |
| 2 | 3,371.45 | 6,706.85 | 98.93 | 29.00 | 56.00 | 116.26 | 119.77 | 7,142.26 | 4,590.80 |
| 3 | 6,576.38 | 10,372.33 | 57.72 | 53.00 | 84.00 | 124.08 | 123.48 | 7,255.83 | 5,024.41 |
| 4 | 7,688.25 | 11,223.72 | 45.99 | 64.00 | 97.00 | 120.13 | 115.71 | 6,096.23 | 4,568.64 |
| 5 | 8,917.92 | 8,653.22 | -2.97 | 72.00 | 82.00 | 123.86 | 105.53 | 5,282.24 | 4,005.83 |
| 6 | 9,159.62 | 10,624.71 | 16.00 | 76.00 | 93.00 | 120.52 | 114.24 | 5,229.02 | 4,223.84 |
| 7 | 9,811.49 | 11,902.35 | 21.31 | 81.00 | 104.00 | 121.13 | 114.45 | 5,457.22 | 3,721.21 |
| 8 | 8,924.62 | 12,074.07 | 35.29 | 75.00 | 107.00 | 118.99 | 112.84 | 5,786.29 | 3,664.80 |
| 9 | 8,804.75 | 12,979.38 | 47.41 | 74.00 | 115.00 | 118.98 | 112.86 | 5,686.66 | 3,867.73 |
| 10 | 9,441.54 | 16,282.88 | 72.46 | 80.00 | 141.00 | 118.02 | 115.48 | 5,547.98 | 3,211.53 |
| 11 | 12,110.79 | 15,308.41 | 26.40 | 107.00 | 131.00 | 113.18 | 116.86 | 4,407.95 | 2,885.84 |
| 12 | 10,770.42 | 14,636.32 | 35.89 | 96.00 | 127.00 | 112.19 | 115.25 | 4,179.52 | 3,053.50 |

Charts 1 and 2 show monthly freight, performed departures and freight per departure. The two zero-freight VistaJet departures (February and August 2025) are included: excluding those two only would yield 115.38 tonnes/departure, versus 115.20 with all observed departures. Neither measure estimates load factor.

## 3. Carriers: volumes, shares and growth contributions

| Carrier | Name | Tonnes 2024 | Tonnes 2025 | Change tonnes | Share 2024 % | Share 2025 % | Growth contribution % | Departures 2024 | Departures 2025 |
|---|---|---|---|---|---|---|---|---|---|
| 5Y | Atlas Air Inc. | 23,815.98 | 37,209.73 | 13,393.74 | 23.51 | 26.24 | 33.08 | 195.00 | 298.00 |
| FX | Federal Express Corporation | 0.00 | 13,164.58 | 13,164.58 | 0.00 | 9.28 | 32.52 | 0.00 | 156.00 |
| PO | Polar Air Cargo Airways | 0.00 | 6,352.02 | 6,352.02 | 0.00 | 4.48 | 15.69 | 0.00 | 50.00 |
| 5X | United Parcel Service | 70,339.89 | 75,409.15 | 5,069.26 | 69.42 | 53.18 | 12.52 | 580.00 | 629.00 |
| KD | Western Global | 0.00 | 4,374.99 | 4,374.99 | 0.00 | 3.09 | 10.81 | 0.00 | 42.00 |
| VJT | VistaJet Limited | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 2.00 |
| 3S | AeroLogic GmbH | 7,164.92 | 5,296.69 | -1,868.23 | 7.07 | 3.74 | -4.61 | 79.00 | 54.00 |

Growth contribution = each carrier's absolute tonne change divided by the net segment increase; negative contributions are retained, and contributions sum to 100%. Missing carrier-year combinations below mean no observations in that year's extract, not proof of no actual operation outside this reporting scope. Shares are based on positive freight; a zero-freight carrier has zero share.

**Observed expansion:** UPS increased departures from 580 to 629 and Atlas from 195 to 298; both reported positive freight in every month of both years. AeroLogic contracted from 79 to 54 departures and from 7,164.92 to 5,296.69 tonnes. Its 2024 observations cover April–December; its 2025 observations cover January–March and September–December. This is intermittent participation, not a full-year exit.

**Newly observed positive-freight participation in 2025:** FedEx first appears in April and is present April–December (156 departures); Polar first appears in July and is present July–December (50); Western Global first appears in September and is present September–December (42). They have no rows in the 2024 SZX → ANC extract. Their combined 23,891.59 tonnes account for 59.01% of net growth. These are first observations within the two-year window, not verified route launch dates.

**Zero-freight movement participation:** VistaJet has two departures, one in February and one in August 2025, with no freight; it is not a freight-market entrant. **No 2024 positive-freight carrier disappears entirely in 2025.** Chart 3 shows absolute changes, avoiding the misleading conclusion that UPS lost volume because its share fell.

## 4. Aircraft and service mix

| AIRCRAFT_TYPE | Tonnes 2024 | Tonnes 2025 | Departures 2024 | Departures 2025 |
|---|---|---|---|---|
| 683 | 7,164.92 | 18,461.27 | 79.00 | 210.00 |
| 788 | 0.00 | 0.00 | 0.00 | 2.00 |
| 819 | 12,495.03 | 13,735.63 | 120.00 | 133.00 |
| 820 | 0.00 | 4,374.99 | 0.00 | 42.00 |
| 821 | 81,660.84 | 105,235.26 | 655.00 | 844.00 |

Aircraft-type numbers are the exact BTS source codes. The source files contain no aircraft-type descriptions, and an authoritative code lookup has not been verified; model names and payload capacities are deliberately not inferred. Code 821 remains dominant, while code 683 departures increase from 79 to 210 and code 820 appears with 42 departures. Carrier/type contributions show AeroLogic and FedEx on 683, UPS and Atlas on 819/821, Polar on 821, Western Global on 820, and VistaJet on 788. These are aggregated reported type assignments, not tail-level aircraft events.

| CLASS | Tonnes 2024 | Tonnes 2025 | Departures 2024 | Departures 2025 |
|---|---|---|---|---|
| G | 77,504.81 | 93,870.42 | 659.00 | 839.00 |
| L | 0.00 | 0.00 | 0.00 | 2.00 |
| P | 23,815.98 | 47,936.74 | 195.00 | 390.00 |

Codes G and P carry all freight in this segment; code L contributes only the two zero-freight 2025 departures. Under the conventional T-100 service-class labels, G denotes scheduled all-cargo, P nonscheduled all-cargo, and L nonscheduled passenger/cargo; the original codes are retained and current lookup verification remains outstanding. P freight grew faster than G freight, consistent with a change in reported service mix. This is not evidence about specific charter contracts, customers or capacity utilization.

## 5. Independent HHI and persistence

HHI = 10,000 × sum of squared carrier freight shares. It was recalculated in DuckDB directly from the original official CSV pounds, independently of the Pandas tonne calculation. Both annual values and all 24 monthly values agree within 0.00000001 HHI points. Annual HHI uses annual carrier shares; it is not the mean of monthly HHIs. Zero-freight VistaJet contributes zero.

| Period | HHI 2024 | HHI 2025 |
|---|---|---|
| H1 | 6,069.35 | 4,290.09 |
| H2 | 5,027.51 | 3,295.66 |

Monthly HHI falls in every matched month (Chart 4). Diversification is therefore not just an annual pooling artifact caused by carriers rotating through different months. It is already visible in January–March, with incumbent share changes; subsequently the newly observed positive-freight carriers add participation. HHI does not consolidate common ownership or commercial control, and it measures reporting-carrier distribution rather than shipper bargaining power.

## 6. Commercial interpretation: observations versus hypotheses

**Observed:** higher segment freight and departures, lower freight per departure, broader positive-freight carrier participation, sustained monthly concentration reduction, and a shift in service/type mix.

**For airport cargo development teams:** prioritize conversations about the operating requirements and continuity of the newly observed services, while maintaining attention to UPS's still-majority share. Test whether ground-handling schedules, transfer processes or facilities are changing in response to the reported mix. The records establish a research priority, not a facility investment requirement.

**For aviation market analysts:** investigate whether the combination of incumbent expansion, new participation and service-class change reflects routing changes, schedule adjustments or broader freight flows. These are hypotheses requiring published schedules, airport statistics and carrier statements. Compare adjacent segments separately before treating this as new shipment demand; Anchorage may be an intermediate stop, and segment totals can count the same shipment on multiple legs.

**Next research steps:** verify current BTS file revisions and aircraft/service code dictionaries; corroborate first-observed carrier months with dated public schedules; compare carrier-level onward routing and other published airport statistics; obtain evidence before attributing any change to particular customers or commodities.

## 7. Methodology and source conditions

Calculations use the original annual BTS exports and exact pound-to-tonne conversion. Monthly reporting is not proof of complete market coverage. Reporting carriers are not consolidated corporate groups; participation changes are not verified first-ever route entry. Aircraft and service codes are retained without inferred payload capacities. No customer, commodity, aircraft utilization or unmet-demand inference is supported.

[Source provenance](../../data-provenance.md) documents attribution and source-specific conditions. [Official reconciliation](../../official-data-reconciliation.md) records the input hashes, historical mirror comparison and acquisition and unit-dictionary limitations.

## Reproduction and evidence

Run `python scripts/build_szx_case.py` with the project's virtual environment and retained official annual ZIP files. The builder records source-file hashes and independently reconciles HHI. The builder writes the row-level extract to `data/official/derived/szx-anc-source.csv`, an ignored path separate from the bundled package. Derived tables and chart JSON are beside this report; `case-study.html` is a self-contained chart-and-table edition for local review. Figures use observed records only. Display rounding does not enter calculations.
