// Run with Node's built-in assertions; no JavaScript packages are required.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {EventEmitter} from 'node:events';

const source = await readFile(new URL('../atlas/map_component.js', import.meta.url), 'utf8');
const {default: render, isEmptyMapPoint} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const emitter = new EventEmitter();
const dom = new EventEmitter();
const events = [];
const observers = new Set();
let purges = 0;
const plot = {
  dataset: {}, isConnected: true, clientWidth: 800,
  _fullLayout: {width: 800, height: 530, _size: {l: 0, t: 0, w: 800, h: 530},
    xaxis: {range: [90, 240], l2p: x => x}, yaxis: {range: [5, 80], l2p: y => y}},
  data: [{mode: 'markers', x: [100], y: [100], marker: {size: [16]}},
    {mode: 'lines', meta: {role: 'route'}, x: [10, 200, null, 700], y: [10, 10, null, 500], line: {width: 6}}],
  getBoundingClientRect: () => ({left: 0, top: 0}),
  querySelectorAll: () => [],
  addEventListener: (...args) => dom.on(...args),
  removeEventListener: (...args) => dom.removeListener(...args),
  on: (...args) => emitter.on(...args),
  removeListener: (...args) => emitter.removeListener(...args),
};
const parentElement = {clientWidth: 800, querySelector: () => plot};
globalThis.window = {innerWidth: 1000, Plotly: {
  react: async () => {},
  relayout: async (_plot, values) => Object.assign(plot._fullLayout, values),
  purge: () => {purges++;},
}};
globalThis.ResizeObserver = class {
  constructor(callback) {this.callback = callback;}
  observe() {observers.add(this);}
  disconnect() {observers.delete(this);}
};
globalThis.requestAnimationFrame = callback => setTimeout(callback, 0);
globalThis.cancelAnimationFrame = clearTimeout;
const props = epoch => ({parentElement, data: {epoch, figure: {data: [], layout: {meta: {highlighted: "SZX → ANC"}}}}, setStateValue: (_key, value) => events.push(value)});
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

// Streamlit invokes render repeatedly but only guarantees cleanup at unmount.
let cleanup;
for (let epoch = 1; epoch <= 30; epoch++) {
  cleanup = render(props(epoch));
  await tick();
  assert.equal(emitter.listenerCount('plotly_click'), 1);
  assert.equal(emitter.listenerCount('plotly_relayout'), 1);
  assert.equal(observers.size, 1);
  for (const type of ['pointerdown','pointermove','pointercancel','click']) assert.equal(dom.listenerCount(type), 1);
}
emitter.emit('plotly_click', {points: [{customdata: ['SZX → ANC']}]});
assert.equal(events.length, 1);
assert.equal(events[0].epoch, 30);
assert.deepEqual(events[0].view, {x: [90, 240], y: [5, 80]});
emitter.emit('plotly_click', {points: [{customdata: []}]});
assert.equal(events.length, 1);


const pointer = (x, y, extra = {}) => ({clientX: x, clientY: y, button: 0, pointerId: 1, isPrimary: true,
  target: {closest: () => null}, ...extra});
assert.equal(isEmptyMapPoint(plot, pointer(300, 300)), true);
assert.equal(isEmptyMapPoint(plot, pointer(-1, 100)), false);
assert.equal(isEmptyMapPoint(plot, pointer(100, 100)), false);
assert.equal(isEmptyMapPoint(plot, pointer(150, 10)), false);
assert.equal(isEmptyMapPoint(plot, pointer(300, 300, {target: {closest: () => ({})}})), false);
// Handle selection must not be followed by a background reset.
dom.emit('pointerdown', pointer(100, 100));
dom.emit('click', pointer(100, 100));
assert.equal(events.length, 1);
// Panning, including a drag returning to its start, is not an empty-space click.
dom.emit('pointerdown', pointer(300, 300));
dom.emit('pointermove', pointer(330, 300));
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 1);
dom.emit('pointerdown', pointer(300, 300));
dom.emit('pointercancel');
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 1);
// One genuine blank-space click emits only clear and preserves the current view.
dom.emit('pointerdown', pointer(300, 300));
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 2);
assert.equal(events[1].kind, 'clear');
assert.deepEqual(events[1].view, events[0].view);
dom.emit('pointerdown', pointer(300, 300));
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 2); // No duplicate clear before the next data render.
events.pop();

// A pending camera notification must not fire from an obsolete render.
emitter.emit('plotly_relayout', {'xaxis.range[0]': 100});
const cleared = props(31); cleared.data.figure.layout.meta.highlighted = null;
cleanup = render(cleared);
await tick();
await new Promise(resolve => setTimeout(resolve, 220));
dom.emit('pointerdown', pointer(300, 300));
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 1);
// A superseded asynchronous render must not attach its listeners later.
render(props(32));
dom.emit('pointerdown', pointer(300, 300));
dom.emit('click', pointer(300, 300));
assert.equal(events.length, 1); // Ignore input until the incoming figure is ready.
cleanup = render(props(33));
await tick();
assert.equal(emitter.listenerCount('plotly_click'), 1);
assert.equal(observers.size, 1);
window.innerWidth = 760;
[...observers][0].callback();
await tick();
assert.equal(plot._fullLayout.height, 430);
plot.isConnected = false;
cleanup();
cleanup(); // cleanup is idempotent
await tick();
assert.equal(emitter.listenerCount('plotly_click'), 0);
assert.equal(emitter.listenerCount('plotly_relayout'), 0);
assert.equal(observers.size, 0);
for (const type of ['pointerdown','pointermove','pointercancel','click']) assert.equal(dom.listenerCount(type), 0);
assert.equal(purges, 1);
console.log('Component lifecycle: 33 renders, one listener pair, timers canceled, resize and unmount clean.');
