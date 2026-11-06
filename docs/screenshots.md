# Application screenshots

The README images are Chromium captures of the working Air Freight Signals application at 1440 × 1200, using the bundled 2024–2025 observations and full-year filters. No interface or observations were synthesized. The images contain no browser chrome or personal filesystem paths.

- **Cargo Corridor Explorer — 6 November 2026:** top 25 routes, 2025 Freight volume encoding, North Pacific focus and HKG → ANC selected. The white halo and stronger route emphasis distinguish the directional selection from surrounding corridors. Land and coastlines are locally bundled Natural Earth assets; airport references come from OurAirports.
- **Supporting views — 3 November 2026:** Market Overview, Research Findings and the Shenzhen → Anchorage case. These captures retain their original analytical scope.

To reproduce, install the requirements, run `python -m streamlit run app.py --browser.gatherUsageStats false`, open localhost:8501, select a workspace and wait for tables and charts to settle. For the explorer, choose HKG → ANC and North Pacific, keeping the default 25-route cap. The application uses the committed system-font theme. [Browser regression checks](browser-testing.md) provide optional capture and interaction tooling; browser automation is not a runtime dependency.
