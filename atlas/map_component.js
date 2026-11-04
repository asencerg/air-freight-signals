// Hit-test existing geometry only; land/coastline traces are background context.
export function isEmptyMapPoint(plot, event) {
  if (event.target?.closest?.('.modebar, button, a, .annotation')) return false;
  const layout = plot._fullLayout, box = plot.getBoundingClientRect();
  if (!layout) return false;
  const {l, t, w, h} = layout._size;
  const x = event.clientX - box.left - l, y = event.clientY - box.top - t;
  if (x < 0 || y < 0 || x > w || y > h) return false;
  for (const label of plot.querySelectorAll('.textpoint text, .annotation')) {
    const r = label.getBoundingClientRect();
    if (event.clientX >= r.left - 2 && event.clientX <= r.right + 2 &&
        event.clientY >= r.top - 2 && event.clientY <= r.bottom + 2) return false;
  }
  for (const trace of plot.data) {
    const markers = trace.mode?.includes('markers'), route = trace.meta?.role === 'route';
    if (!markers && !route) continue;
    let previous = null;
    for (let i = 0; i < trace.x.length; i++) {
      if (trace.x[i] == null || trace.y[i] == null) { previous = null; continue; }
      const px = layout.xaxis.l2p(trace.x[i]), py = layout.yaxis.l2p(trace.y[i]);
      if (markers) {
        const size = Array.isArray(trace.marker.size) ? trace.marker.size[i] : trace.marker.size;
        if (Math.hypot(x - px, y - py) <= (size || 13) / 2 + 5) return false;
      }
      if (route && previous) {
        const [ax, ay] = previous, dx = px - ax, dy = py - ay;
        const u = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy || 1)));
        if (Math.hypot(x - ax - u * dx, y - ay - u * dy) <= (trace.line.width || 1) / 2 + 5) return false;
      }
      previous = [px, py];
    }
  }
  return true;
}

export default function(component) {
  const {parentElement, data, setStateValue} = component;
  const plot = parentElement.querySelector('.signals-map');
  // Streamlit calls returned cleanup on unmount, not on every data update.
  plot.signalsCleanup?.();
  let active = true, timer, resizeFrame, gesture, backgroundCleared = false;
  const P = window.Plotly;
  const view = () => ({x: [...plot._fullLayout.xaxis.range], y: [...plot._fullLayout.yaxis.range]});
  const send = (kind, market = null) => {
    if (!active || !plot._fullLayout) return;
    clearTimeout(timer); // Selection/reset already carries the current camera.
    setStateValue('event', {kind, market, view: view(), epoch: data.epoch, nonce: Date.now()});
  };
  const click = event => {
    const market = event.points?.[0]?.customdata?.[0];
    if (typeof market === 'string' && market.includes(' → ')) send('select', market);
  };
  const relayout = event => {
    if (!Object.keys(event).some(k => k.startsWith('xaxis') || k.startsWith('yaxis'))) return;
    clearTimeout(timer); timer = setTimeout(() => send('view'), 180);
  };
  const pointerDown = event => {
    gesture = event.button === 0 && event.isPrimary !== false
      ? {id: event.pointerId, x: event.clientX, y: event.clientY, moved: false} : null;
  };
  const pointerMove = event => {
    if (gesture && event.pointerId === gesture.id &&
        Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) > 5) gesture.moved = true;
  };
  const pointerCancel = () => { gesture = null; };
  const backgroundClick = event => {
    const start = gesture; gesture = null;
    if (!active || plot.dataset.ready !== 'true' || !start || start.moved || event.button !== 0 || plot._dragging ||
        Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return;
    if (!backgroundCleared && data.figure.layout.meta?.highlighted && isEmptyMapPoint(plot, event)) {
      backgroundCleared = true; send('clear');
    }
  };
  const pointerEvents = [['pointerdown', pointerDown], ['pointermove', pointerMove],
    ['pointercancel', pointerCancel], ['click', backgroundClick]];
  for (const [name, listener] of pointerEvents) plot.addEventListener(name, listener);
  plot.dataset.ready = 'false';
  const figure = data.figure;
  figure.layout.height = window.innerWidth < 800 ? 430 : 530;
  P.react(plot, figure.data, figure.layout, {
    responsive: false, scrollZoom: true, displaylogo: false,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'resetScale2d'],
    doubleClick: false
  }).then(() => {
    if (!active) return;
    plot.dataset.renderCount = String(Number(plot.dataset.renderCount || 0) + 1);
    plot.dataset.ready = 'true'; plot.dataset.epoch = String(data.epoch);
    plot.on('plotly_click', click); plot.on('plotly_relayout', relayout);
  }).catch(() => { if (active) plot.textContent = 'The map could not render. Use the corridor list and research evidence below.'; });
  // Own resizing: Plotly's window listener can outlive a Streamlit rerender.
  const observer = new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      if (!active || !plot.isConnected || !plot._fullLayout || !plot.clientWidth) return;
      const width = parentElement.clientWidth;
      const height = window.innerWidth < 800 ? 430 : 530;
      if (width && (plot._fullLayout.width !== width || plot._fullLayout.height !== height)) {
        P.relayout(plot, {width, height});
      }
    });
  });
  observer.observe(parentElement);
  const cleanup = () => {
    if (!active) return;
    active = false; clearTimeout(timer); cancelAnimationFrame(resizeFrame); observer.disconnect();
    for (const [name, listener] of pointerEvents) plot.removeEventListener(name, listener);
    if (plot.removeListener) { plot.removeListener('plotly_click', click); plot.removeListener('plotly_relayout', relayout); }
    if (plot.signalsCleanup === cleanup) delete plot.signalsCleanup;
    queueMicrotask(() => { if (!plot.isConnected) P.purge(plot); });
  };
  plot.signalsCleanup = cleanup;
  return cleanup;
}
