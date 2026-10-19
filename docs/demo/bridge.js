// Remplace le QWebChannel de l'application : la demo du site tourne avec Pyodide et une base simulee.
(() => {
  const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
  const handlers = {};
  const signal = name => ({ connect: fn => (handlers[name] ||= []).push(fn) });
  globalThis.npEmit = (name, ...args) => (handlers[name] || []).forEach(fn => fn(...args));
  const lang = new URLSearchParams(location.search).get('lang');
  globalThis.npLang = ['en', 'fr'].includes(lang) ? lang : 'auto';

  const load = src => new Promise((ok, fail) => {
    const s = document.createElement('script');
    s.src = src;
    s.onload = ok;
    s.onerror = fail;
    document.head.append(s);
  });

  window.qt = { webChannelTransport: null };
  window.QWebChannel = function (_, ready) {
    (async () => {
      await load(PYODIDE + 'pyodide.js');
      const py = await loadPyodide({ indexURL: PYODIDE });
      await py.loadPackage('pillow');
      py.unpackArchive(await (await fetch('novapanel.zip')).arrayBuffer(), 'zip');
      py.runPython(await (await fetch('demo.py')).text());
      const pyApi = py.globals.get('api');

      const api = {};
      for (const n of ['getState', 'getConfig', 'getStrings', 'getMeta', 'set', 'setEq', 'setCfg', 'refresh',
        'toggleBlack', 'setAutostart', 'toggleGG', 'runningApps']) api[n] = (...a) => pyApi[n](...a);
      for (const n of ['stateChanged', 'configChanged', 'frame', 'forcedBlack', 'notify', 'updateAvailable']) api[n] = signal(n);
      let last = '';
      Object.assign(api, {
        resendFrame: () => { last = ''; },
        openUrl: url => { if (url.startsWith('https://')) window.open(url, '_blank', 'noopener'); },
        startDrag() {}, minimize() {}, hide() {},
      });

      const t0 = performance.now();
      setInterval(() => {
        const f = pyApi.frame((performance.now() - t0) / 1000);
        if (f !== last) { last = f; npEmit('frame', ...JSON.parse(f)); }
      }, 100);

      const wheel = e => { e.preventDefault(); pyApi.nudgeVolume(e.deltaY < 0 ? 2 : -2); };
      document.getElementById('view').addEventListener('wheel', wheel, { passive: false });
      document.getElementById('t-vol').addEventListener('wheel', wheel, { passive: false });
      document.getElementById('t-mic').addEventListener('click', () => pyApi.toggleMute());
      ready({ objects: { api } });
      window.frameElement?.dispatchEvent(new Event('demoready'));
    })().catch(e => { console.error(e); window.frameElement?.dispatchEvent(new Event('demofailed')); });
  };
})();
