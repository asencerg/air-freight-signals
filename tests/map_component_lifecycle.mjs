// Run with Node's built-in assertions; no JavaScript packages are required.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {EventEmitter} from 'node:events';

const source = await readFile(new URL('../atlas/map_component.js', import.meta.url), 'utf8');
const {default: render} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const emitter = new EventEmitter();
const events = [];
const observers = new Set();
let purges = 0;
const plot = {
  dataset: {}, isConnected: true, clientWidth: 800,
  _fullLayout: {width: 800, height: 530, xaxis: {range: [90, 240]}, yaxis: {range: [5, 80]}},
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
const props = epoch => ({parentElement, data: {epoch, figure: {data: [], layout: {}}}, setStateValue: (_key, value) => events.push(value)});
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

// Streamlit invokes render repeatedly but only guarantees cleanup at unmount.
let cleanup;
for (let epoch = 1; epoch <= 30; epoch++) {
  cleanup = render(props(epoch));
  await tick();
  assert.equal(emitter.listenerCount('plotly_click'), 1);
  assert.equal(emitter.listenerCount('plotly_relayout'), 1);
  assert.equal(observers.size, 1);
}
emitter.emit('plotly_click', {points: [{customdata: ['SZX → ANC']}]});
assert.equal(events.length, 1);
assert.equal(events[0].epoch, 30);
assert.deepEqual(events[0].view, {x: [90, 240], y: [5, 80]});
emitter.emit('plotly_click', {points: [{customdata: []}]});
assert.equal(events.length, 1);

// A pending camera notification must not fire from an obsolete render.
emitter.emit('plotly_relayout', {'xaxis.range[0]': 100});
cleanup = render(props(31));
await tick();
await new Promise(resolve => setTimeout(resolve, 220));
assert.equal(events.length, 1);
// A superseded asynchronous render must not attach its listeners later.
render(props(32));
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
assert.equal(purges, 1);
console.log('Component lifecycle: 33 renders, one listener pair, timers canceled, resize and unmount clean.');
