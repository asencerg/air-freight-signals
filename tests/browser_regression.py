"""Optional end-to-end checks against a locally running, bundled-data application."""
import argparse
import csv
import io
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


class Explorer:
    def __init__(self, page):
        self.page = page
        self.plot = page.locator('.signals-map')
        self.timings = []

    def state(self):
        return self.plot.evaluate('''e => ({
            x: e._fullLayout.xaxis.range, y: e._fullLayout.yaxis.range,
            count: Number(e.dataset.renderCount), meta: e.layout.meta,
            routes: e.data.filter(t => t.meta?.role === 'route').map(t => ({
                market: t.meta.market, opacity: t.opacity})),
            click: e._ev.listeners('plotly_click').length,
            relayout: e._ev.listeners('plotly_relayout').length
        })''')

    def ready(self, before):
        started = time.perf_counter()
        self.page.wait_for_function('''n => {
            const e = document.querySelector('.signals-map');
            return e?.dataset.ready === 'true' && Number(e.dataset.renderCount) > n;
        }''', arg=before['count'], timeout=60000)
        # Catch delayed duplicate events after the bridge's 180 ms debounce.
        self.page.wait_for_timeout(450)
        self.timings.append(time.perf_counter() - started)
        assert self.state()['click'] == self.state()['relayout'] == 1

    def choose(self, label, value):
        control = self.page.get_by_role('combobox', name=re.compile(re.escape(label) + '$'))
        if control.get_attribute('aria-label').startswith('Selected ' + value + '. '):
            return
        before = self.state()
        control.fill(value)
        self.page.get_by_role('option', name=value, exact=True).click()
        self.ready(before)

    def same_camera(self, before):
        after = self.state()
        assert (before['x'], before['y']) == (after['x'], after['y']), (before, after)

    def selected(self, market, highlighted=True):
        state = self.state()
        assert state['meta'] == {'selected': market, 'highlighted': market if highlighted else None}
        assert all(t['opacity'] == (1 if t['market'] == market else .55)
                   if highlighted else t['opacity'] == .7 for t in state['routes'])
        control = self.page.get_by_role('combobox', name=re.compile('Selected directional corridor$'))
        assert market in control.get_attribute('aria-label')
        origin, destination = market.split(' → ')
        self.page.get_by_role('heading', name=re.compile(origin + '.*→.*' + destination)).wait_for()

    def point(self, longitude, latitude):
        self.plot.scroll_into_view_if_needed()
        box = self.plot.bounding_box()
        x, y = self.plot.evaluate('''(e, p) => [
            e._fullLayout.xaxis.l2p(p[0]) + e._fullLayout._size.l,
            e._fullLayout.yaxis.l2p(p[1]) + e._fullLayout._size.t
        ]''', [longitude, latitude])
        assert 0 < x < box['width'] and 0 < y < box['height']
        return box['x'] + x, box['y'] + y

    def clear(self, longitude, latitude):
        before = self.state()
        self.page.mouse.click(*self.point(longitude, latitude))
        self.ready(before)
        self.same_camera(before)
        self.selected(before['meta']['selected'], highlighted=False)

    def handle(self, market):
        """Read handle geometry, then select with a real mouse event, not Plotly.emit."""
        before = self.state()
        self.plot.scroll_into_view_if_needed()
        box = self.plot.bounding_box()
        target = self.plot.evaluate('''(e, market) => {
            const t = e.data.find(t => t.customdata && t.mode === 'markers');
            return t.customdata.map((v, i) => ({market: v[0],
                x: e._fullLayout.xaxis.l2p(t.x[i]) + e._fullLayout._size.l,
                y: e._fullLayout.yaxis.l2p(t.y[i]) + e._fullLayout._size.t
            })).find(p => p.market === market && p.x > 25 && p.x < e.clientWidth - 25
                && p.y > 25 && p.y < e.clientHeight - 25);
        }''', market)
        assert target, f'No visible directional handle: {market}'
        self.page.mouse.click(box['x'] + target['x'], box['y'] + target['y'])
        self.ready(before)
        self.same_camera(before)
        self.selected(market)

    def button(self, label):
        before = self.state()
        self.page.get_by_role('button', name=label, exact=True).click()
        self.ready(before)


def download(page, label, output, filename):
    with page.expect_download() as event:
        page.get_by_text(label, exact=True).click()
    path = output / filename
    event.value.save_as(path)
    assert path.stat().st_size > 0
    return path.read_text(encoding='utf-8-sig')


def run(page, output):
    page.get_by_text('Market developments', exact=True).wait_for(timeout=120000)
    page.get_by_text('Cargo Corridor Explorer', exact=True).first.click()
    page.locator('.signals-map[data-ready=true]').wait_for(timeout=120000)
    explorer = Explorer(page)
    explorer.choose('Selected directional corridor', 'HKG → ANC')
    explorer.choose('Geographic focus', 'North Pacific')
    explorer.selected('HKG → ANC')

    before = explorer.state()
    page.mouse.move(*explorer.point(200, 15))
    page.mouse.wheel(0, -400)
    explorer.ready(before)
    assert explorer.state()['x'] != before['x']
    before = explorer.state()
    x, y = explorer.point(200, 15)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 24, y - 8, steps=8)
    page.mouse.up()
    explorer.ready(before)
    assert explorer.state()['x'] != before['x']
    explorer.clear(200, 15)
    before = explorer.state()
    page.mouse.click(*explorer.point(200, 15))
    page.wait_for_timeout(800)
    assert explorer.state()['count'] == before['count']
    for market in ['ANC → HKG', 'HKG → ANC']:
        explorer.handle(market)
        explorer.clear(200, 15)
        explorer.handle(market)

    explorer.button('Fit corridor')
    explorer.selected('HKG → ANC')
    explorer.button('Reset view')
    assert explorer.state()['x'] == [-180, 180]
    explorer.clear(-30, -40)
    modes = ['Freight change · tonnes', 'Freight change · %', 'Carrier HHI change',
             'Departures', 'Freight volume']
    for highlighted in [False, True]:
        if highlighted:
            explorer.choose('Selected directional corridor', 'ANC → HKG')
        for mode in modes:
            before = explorer.state()
            explorer.choose('Map encoding', mode)
            explorer.same_camera(before)
            explorer.selected('ANC → HKG' if highlighted else 'HKG → ANC', highlighted)

    for label, extent in [('North America', [-170, -50]), ('Europe', [-25, 45]),
                          ('Latin America', [-120, -30]), ('North Pacific', [90, 240])]:
        explorer.choose('Geographic focus', label)
        assert explorer.state()['x'] == extent
    page.get_by_text('Geographic filters', exact=True).click()
    before = explorer.state()
    explorer.choose('Airport hub (filters corridors)', 'ANC')
    explorer.same_camera(before)
    for direction in ['Outbound', 'Inbound', 'Both directions']:
        before = explorer.state()
        page.get_by_text(direction, exact=True).click()
        explorer.ready(before)
        explorer.same_camera(before)
        for route in explorer.state()['routes']:
            origin, destination = route['market'].split(' → ')
            assert (origin == 'ANC' if direction == 'Outbound' else destination == 'ANC'
                    if direction == 'Inbound' else 'ANC' in (origin, destination))
    explorer.choose('Airport hub (filters corridors)', 'All')
    page.get_by_text('Geographic filters', exact=True).click()
    explorer.choose('Selected directional corridor', 'HKG → ANC')
    before = explorer.state()
    explorer.choose('Map reporting year', '2024')
    explorer.same_camera(before)
    explorer.choose('Map reporting year', '2025')

    for width in [1440, 760, 390]:
        before = explorer.state()
        page.set_viewport_size({'width': width, 'height': 1200 if width == 1440 else 900})
        explorer.plot.scroll_into_view_if_needed()
        page.wait_for_timeout(700)
        explorer.same_camera(before)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
        page.mouse.move(5, 5)
        page.screenshot(path=str(output / f'explorer-{width}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1200})
    assert 'HKG' in download(page, 'Download selected brief', output, 'selected.md')
    monthly = download(page, 'Download monthly evidence CSV', output, 'monthly.csv')
    assert len(list(csv.DictReader(io.StringIO(monthly)))) == 24
    page.get_by_text('Geographic coverage and unresolved endpoints', exact=True).click()
    coverage = download(page, 'Export geographic coverage evidence', output, 'coverage.csv')
    assert len(list(csv.DictReader(io.StringIO(coverage)))) == 2892

    before = explorer.state()
    page.wait_for_timeout(3000)
    assert explorer.state()['count'] == before['count'], 'Idle map repeatedly rerendered'
    cdp = page.context.new_cdp_session(page)

    def listeners(expression):
        return cdp.send('Runtime.evaluate', {'expression': expression,
                        'includeCommandLineAPI': True, 'returnByValue': True})['result']['value']

    owned = "['pointerdown','pointermove','pointercancel','click']"
    assert listeners(f"{owned}.every(k => getEventListeners(document.querySelector('.signals-map'))[k]?.length === 1)")
    explorer.plot.evaluate('e => window.retiredMap = e')
    page.get_by_text('Market Overview', exact=True).first.click()
    page.get_by_text('Market developments', exact=True).wait_for()
    page.wait_for_timeout(500)
    assert listeners(f"!retiredMap.isConnected && !retiredMap._ev && {owned}.every(k => !getEventListeners(retiredMap)[k]?.length)")

    page.get_by_text('Research Findings', exact=True).first.click()
    page.get_by_text('Market developments', exact=True).wait_for()
    search = page.get_by_role('textbox', name='Search airport code, name or directional corridor')
    search.fill('SZX')
    search.press('Enter')
    page.get_by_text('Export research and underlying analytical signals', exact=True).click()
    page.get_by_text('Prepare exports', exact=True).click()
    page.get_by_text('Export findings CSV', exact=True).wait_for()
    for label, filename in [('Export findings CSV', 'findings.csv'),
                            ('Export findings Markdown', 'findings.md'),
                            ('Export original analytical signals CSV', 'signals.csv')]:
        assert 'SZX' in download(page, label, output, filename)
    page.get_by_text('Case Studies', exact=True).first.click()
    page.get_by_text('Carrier composition', exact=True).wait_for()
    case = download(page, 'Download case study (Markdown)', output, 'case.md')
    assert '101,320' in case and 'records source-file hashes' in case
    assert not page.locator('[data-testid="stException"]').count()
    return {'workspaces': 4, 'downloads': 7, 'viewport_widths': [1440, 760, 390],
            'reciprocal_mouse_selection': True, 'listener_cleanup': True,
            'wait_to_ready_seconds': explorer.timings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8501')
    parser.add_argument('--browser-executable', help='Optional installed Chromium path')
    parser.add_argument('--output-dir', type=Path, help='Screenshots and downloads; default: new temporary directory')
    args = parser.parse_args()
    address = urlsplit(args.url)
    if address.hostname not in {'localhost', '127.0.0.1', '::1'}:
        parser.error('Use a locally running application')
    output = args.output_dir or Path(tempfile.mkdtemp(prefix='air-freight-browser-'))
    output.mkdir(parents=True, exist_ok=True)
    errors, external = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser_executable)
        page = browser.new_page(viewport={'width': 1440, 'height': 1200})
        page.set_default_timeout(60000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        page.on('request', lambda request: external.append(request.url)
                if urlsplit(request.url).netloc not in {'', address.netloc} else None)
        try:
            page.goto(args.url)
            result = run(page, output)
            assert not errors and not external, {'errors': errors, 'external': external}
            result.update(console_errors=errors, external_requests=external)
            (output / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        except Exception:
            page.screenshot(path=str(output / 'failure.png'))
            raise
        finally:
            browser.close()
    print(f'Browser evidence: {output}')


if __name__ == '__main__':
    main()
