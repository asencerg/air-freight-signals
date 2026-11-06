# Browser regression checks

The optional Chromium harness exercises the running application with the committed BTS package. It is separate from the normal pytest suite and adds no production dependency.

Using the virtual environment's Python, install the browser tooling once:

```sh
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
```

On Linux, Chromium also needs system libraries; Playwright documents these through `python -m playwright install --with-deps chromium`. Installing system packages may require administrator privileges. An existing compatible Chromium installation can instead be selected with `--browser-executable`.

Start the application in one terminal:

```sh
python -m streamlit run app.py --browser.gatherUsageStats false
```

In a second terminal, from the repository root:

```sh
python tests/browser_regression.py
```

Use `--url http://localhost:8502` for another local port. Screenshots, downloads and timing results go to a new operating-system temporary directory; `--output-dir` selects another location. Keep generated evidence outside the repository. The harness uses an isolated browser context and the default bundled-data filters, not a user's existing browser session. It neither rebuilds datasets nor updates reference screenshots.

## Coverage

Checks include four-workspace navigation; searchable corridor selection; actual mouse clicks on both HKG → ANC and ANC → HKG handles; pan/zoom and camera persistence; background-click clearing without analytical deselection; all five map encodings; regional focus, Fit corridor and Reset view; airport-hub directions; seven research downloads; desktop/tablet/phone widths; duplicate listener detection, unmount cleanup and idle rerun detection. Console errors and external requests fail the run. Wait-to-ready timings include event debounce and rendering, not just query execution.

The harness reads Plotly's trace geometry to locate real mouse targets and inspects the bridge's render counter and listeners. Changes to these interfaces or the pinned Streamlit/Plotly versions require reviewing these assertions. `python -m pytest -q` also runs the component lifecycle checks when Node is installed.

## Visual review

Inspect the three captured explorer images for destination-label clipping, control overlap, legible units and selected-route contrast. Review other workspaces at phone width, where evidence tables may scroll internally. At the 100-route cap, inspect crowded Anchorage handles and Pacific/dateline continuity. Confirm the map-mode legend describes the visible metric. These visual judgments complement the automated assertions; a passing run alone is not visual approval.
