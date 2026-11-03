export default function(component) {
  const {parentElement, data, setStateValue} = component;
  const plot = parentElement.querySelector('.signals-map');
  // Streamlit calls returned cleanup on unmount, not on every data update.
  plot.signalsCleanup?.();
  let active = true, timer, resizeFrame;
  const P = window.Plotly;
  const view = () => ({x: [...plot._fullLayout.xaxis.range], y: [...plot._fullLayout.yaxis.range]});
  const send = (kind, market = null) => {
    if (!active || !plot._fullLayout) return;
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
    if (plot.removeListener) { plot.removeListener('plotly_click', click); plot.removeListener('plotly_relayout', relayout); }
    if (plot.signalsCleanup === cleanup) delete plot.signalsCleanup;
    queueMicrotask(() => { if (!plot.isConnected) P.purge(plot); });
  };
  plot.signalsCleanup = cleanup;
  return cleanup;
}
