import { createBaseView } from './base3d.js';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

let api = null;
let state = {};
let cfg = {};
let meta = {};
let S = {};
let forced = false;
let lastInfo = '';
const t = (k, v = {}) => (S[k] ?? k).replace(/\{(\w+)\}/g, (_, n) => v[n]);
const pct = lvl => Math.round((lvl || 0) * 100 / 8);

function openTab(name) {
  $$('#tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  $$('.page').forEach(p => p.classList.toggle('active', p.dataset.page === name));
}
$$('#tabs button').forEach(b => b.addEventListener('click', () => openTab(b.dataset.tab)));

let toastTimer;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}

function paintRange(el) {
  const p = (el.value - el.min) / (el.max - el.min) * 100;
  el.style.setProperty('--p', p + '%');
}

function bindDevice() {
  $$('[data-set]').forEach(el => {
    const name = el.dataset.set;
    if (el.classList.contains('seg')) {
      $$('button', el).forEach(b => b.addEventListener('click', () => {
        const v = +b.dataset.v;
        $$('button', el).forEach(x => x.classList.toggle('on', x === b));
        state[name] = v;
        api.set(name, v);
        if (name === 'anc') render();
      }));
    } else if (el.type === 'range') {
      el.addEventListener('input', () => { paintRange(el); const o = $(`[data-out="${name}"]`); if (o) o.value = el.value; el.dataset.busy = 1; });
      el.addEventListener('change', () => { delete el.dataset.busy; state[name] = +el.value; api.set(name, +el.value); });
    } else if (el.tagName === 'SELECT') {
      el.addEventListener('change', () => { state[name] = +el.value; api.set(name, +el.value); });
    }
  });
}

function bindConfig() {
  $$('[data-cfg]').forEach(el => {
    const key = el.dataset.cfg;
    if (el.classList.contains('seg')) {
      $$('button', el).forEach(b => b.addEventListener('click', () => setCfg(key, b.dataset.v)));
    } else if (el.type === 'checkbox') {
      el.addEventListener('change', () => setCfg(key, el.checked));
    } else if (el.type === 'range') {
      el.addEventListener('input', () => { paintRange(el); renderIdle(+el.value); });
      el.addEventListener('change', () => setCfg(key, +el.value));
    } else if (el.tagName === 'SELECT') {
      el.addEventListener('change', () => setCfg(key, +el.value));
    }
  });
}

function setCfg(key, value) {
  cfg[key] = value;
  api.setCfg(key, JSON.stringify(value));
  renderConfig();
}

function renderIdle(v) {
  $('#idle-out').value = v === 0 ? t('idle_never') : `${v} min`;
}

function setTile(id, { value, unit = true, fill = 0, badge = '', cls = {} }) {
  const t = $(id);
  $('.val', t).textContent = value;
  const small = $('.tile-val small', t);
  if (small) small.style.display = unit ? '' : 'none';
  $('.meter i', t).style.width = `${Math.max(0, Math.min(100, fill))}%`;
  $('.badge', t).textContent = badge;
  for (const [k, v] of Object.entries(cls)) t.classList.toggle(k, !!v);
}

function render() {
  const s = state;
  const conn = $('#conn');
  const online = s.headset === 'online' || s.headset === 'charging';
  conn.className = 'chip ' + (s.connected ? 'ok' : 'off');
  $('.label', conn).textContent = t(!s.connected ? 'base_missing'
    : s.headset === 'charging' ? 'headset_charging'
    : online ? 'headset_on' : 'headset_off');

  const hsOn = !!(s.connected && online);
  setTile('#t-headset', {
    value: hsOn ? pct(s.battery) : '—', unit: hsOn, fill: hsOn ? pct(s.battery) : 0,
    badge: s.headset === 'charging' ? t('charging') : hsOn ? '' : t('off'),
    cls: { low: hsOn && s.battery <= 2, charging: s.headset === 'charging', dim: !hsOn },
  });
  setTile('#t-spare', {
    value: s.connected ? pct(s.spare_battery) : '—', unit: !!s.connected, fill: s.connected ? pct(s.spare_battery) : 0,
    badge: s.connected && s.spare_battery === 8 ? t('full') : s.connected ? t('charging') : '',
    cls: { low: s.connected && s.spare_battery <= 2, dim: !s.connected },
  });
  setTile('#t-vol', {
    value: s.volume ?? '—', unit: s.volume != null, fill: s.volume ?? 0,
    badge: t('dial'), cls: { dim: !s.connected },
  });
  setTile('#t-mic', {
    value: !hsOn ? '—' : s.mic_muted ? t('muted') : t('active'), unit: false,
    fill: hsOn && !s.mic_muted ? (s.mic_volume ?? 0) * 10 : 0,
    badge: hsOn ? t('mic_badge', { v: s.mic_volume ?? '—' }) : '',
    cls: { muted: hsOn && s.mic_muted, dim: !hsOn },
  });
  if (s.volume != null) view.setVolume(s.volume);

  $$('[data-set]').forEach(el => {
    const name = el.dataset.set;
    if (!(name in s)) return;
    if (el.classList.contains('seg')) {
      $$('button', el).forEach(b => b.classList.toggle('on', +b.dataset.v === s[name]));
    } else if (el.type === 'range') {
      if (el.dataset.busy) return;
      el.value = s[name];
      paintRange(el);
      const o = $(`[data-out="${name}"]`); if (o) o.value = s[name];
    } else if (el.tagName === 'SELECT') {
      el.value = s[name];
    }
  });
  $('[data-set="transparency"]').disabled = s.anc !== 1;
  $('#transp-note').textContent = t(s.anc === 1 ? 'transp_active' : 'transp_note');
  $('#bt-status').textContent = t(s.bt_connected ? 'connected' : 'not_connected');

  if (s.eq && !eqDrag) { eqGains = s.eq.slice(); drawEq(); }
  renderEqChips();
}

function renderConfig() {
  $$('[data-cfg]').forEach(el => {
    const key = el.dataset.cfg;
    if (!(key in cfg)) return;
    if (el.classList.contains('seg')) {
      $$('button', el).forEach(b => b.classList.toggle('on', b.dataset.v === String(cfg[key])));
    } else if (el.type === 'checkbox') {
      el.checked = !!cfg[key];
    } else if (el.type === 'range') {
      el.value = cfg[key]; paintRange(el);
    } else if (el.tagName === 'SELECT') {
      el.value = cfg[key];
    }
  });
  renderIdle(cfg.idle_minutes);
  $('#language').value = cfg.language;
  $('#page-pick').style.display = cfg.screen_mode === 'custom' ? '' : 'none';
  $$('input.hotkey').forEach(el => { if (document.activeElement !== el) el.value = (cfg.hotkeys || {})[el.dataset.hk] || '—'; });
  renderEqChips();
  renderRules();
}

const FREQS = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
const FLAB = ['32', '64', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'];
const BASE_PRESETS = ['Flat', 'Bass Boost', 'Focus', 'Smiley'];
const EQ = { x0: 26, x1: 386, y0: 16, y1: 196 };
let eqGains = new Array(10).fill(0);
let eqDrag = null;
const ex = i => EQ.x0 + (EQ.x1 - EQ.x0) * i / 9;
const ey = g => EQ.y0 + (EQ.y1 - EQ.y0) * (10 - g) / 20;

function smoothPath(pts) {
  // courbe monotone (Catmull-Rom -> Bezier)
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`;
  }
  return d;
}

function drawEq() {
  const svg = $('#eq');
  const pts = eqGains.map((g, i) => [ex(i), ey(g)]);
  const curve = smoothPath(pts);
  let h = '';
  for (const g of [-10, -5, 5, 10]) h += `<line class="grid" x1="${EQ.x0}" x2="${EQ.x1}" y1="${ey(g)}" y2="${ey(g)}"/>`;
  for (let i = 0; i < 10; i++) h += `<line class="grid" x1="${ex(i)}" x2="${ex(i)}" y1="${EQ.y0}" y2="${EQ.y1}"/>`;
  h += `<line class="zero" x1="${EQ.x0}" x2="${EQ.x1}" y1="${ey(0)}" y2="${ey(0)}"/>`;
  h += `<text x="10" y="${ey(10) + 4}">+10</text><text x="10" y="${ey(0) + 4}">0</text><text x="10" y="${ey(-10) + 4}">−10</text>`;
  h += `<path class="area" d="${curve} L${EQ.x1},${EQ.y1} L${EQ.x0},${EQ.y1} Z"/>`;
  h += `<path class="curve" d="${curve}"/>`;
  eqGains.forEach((g, i) => {
    h += `<circle class="knob${eqDrag === i ? ' drag' : ''}" data-i="${i}" cx="${ex(i)}" cy="${ey(g)}" r="6"/>`;
    h += `<text x="${ex(i)}" y="222">${FLAB[i]}</text>`;
    if (eqDrag === i) h += `<text class="val" x="${ex(i)}" y="${ey(g) - 14}">${g > 0 ? '+' : ''}${g}</text>`;
  });
  svg.innerHTML = h;
}

let eqSendTimer;
function sendEq() {
  clearTimeout(eqSendTimer);
  eqSendTimer = setTimeout(() => api.setEq(JSON.stringify(eqGains)), 120);
}

(function bindEq() {
  const svg = $('#eq');
  const toY = e => {
    const r = svg.getBoundingClientRect();
    const y = (e.clientY - r.top) * 230 / r.height;
    const g = 10 - (y - EQ.y0) / (EQ.y1 - EQ.y0) * 20;
    return Math.max(-10, Math.min(10, Math.round(g * 2) / 2));
  };
  const nearest = e => {
    const r = svg.getBoundingClientRect();
    const x = (e.clientX - r.left) * 400 / r.width;
    let best = 0;
    for (let i = 1; i < 10; i++) if (Math.abs(ex(i) - x) < Math.abs(ex(best) - x)) best = i;
    return best;
  };
  svg.addEventListener('pointerdown', e => {
    eqDrag = nearest(e);
    svg.setPointerCapture(e.pointerId);
    eqGains[eqDrag] = toY(e);
    drawEq(); sendEq();
  });
  svg.addEventListener('pointermove', e => {
    if (eqDrag === null) return;
    const g = toY(e);
    if (g !== eqGains[eqDrag]) { eqGains[eqDrag] = g; drawEq(); sendEq(); }
  });
  const end = () => { if (eqDrag !== null) { eqDrag = null; drawEq(); state.eq_preset = 4; renderEqChips(); } };
  svg.addEventListener('pointerup', end);
  svg.addEventListener('pointercancel', end);
  svg.addEventListener('dblclick', e => { const i = nearest(e); eqGains[i] = 0; drawEq(); sendEq(); });
  $('#eq-flat').addEventListener('click', () => { eqGains = new Array(10).fill(0); drawEq(); sendEq(); });
  $('#eq-save').addEventListener('click', () => {
    const name = $('#eq-name').value.trim();
    if (!name) { $('#eq-name').focus(); return; }
    const presets = { ...(cfg.eq_presets || {}), [name]: eqGains.slice() };
    setCfg('eq_presets', presets);
    $('#eq-name').value = '';
    toast(t('curve_saved', { name }));
  });
})();

function sameCurve(a, b) { return a && b && a.every((v, i) => Math.abs(v - b[i]) < 0.01); }

function renderEqChips() {
  const base = $('#eq-base');
  base.innerHTML = '';
  [...BASE_PRESETS, t('custom')].forEach((n, i) => {
    const b = document.createElement('button');
    b.textContent = n;
    b.classList.toggle('on', state.eq_preset === i);
    b.onclick = () => { state.eq_preset = i; api.set('eq_preset', i); renderEqChips(); if (i === 4) api.refresh(); };
    base.appendChild(b);
  });
  const user = $('#eq-user');
  user.innerHTML = '';
  const presets = cfg.eq_presets || {};
  const names = Object.keys(presets).sort();
  if (!names.length) user.innerHTML = `<span class="empty">${t('eq_none')}</span>`;
  names.forEach(n => {
    const b = document.createElement('button');
    b.innerHTML = `<span></span><span class="x" title="${t('delete')}">×</span>`;
    b.firstChild.textContent = n;
    b.classList.toggle('on', state.eq_preset === 4 && sameCurve(presets[n], eqGains));
    b.onclick = e => {
      if (e.target.classList.contains('x')) {
        const p = { ...presets }; delete p[n]; setCfg('eq_presets', p); return;
      }
      eqGains = presets[n].slice(); drawEq(); api.setEq(JSON.stringify(eqGains));
      state.eq_preset = 4; renderEqChips();
    };
    user.appendChild(b);
  });
}

$('#force-black').addEventListener('click', () => api.toggleBlack());
$('#hero-black').addEventListener('click', () => api.toggleBlack());
function renderForced(on) {
  forced = on;
  const b = $('#force-black');
  b.classList.toggle('on', on);
  b.textContent = t(on ? 'screen_on' : 'screen_off_now');
  $('#hero-black').textContent = t(on ? 'screen_on' : 'screen_off');
  $('#hero-black').classList.toggle('on', on);
}

// rendu facon dalle OLED : 128x64 pixels agrandis x8, pixels eteints a peine visibles, legere lueur
const PX = 8;
const oled = document.createElement('canvas');
oled.width = 1024; oled.height = 512;
const octx = oled.getContext('2d');
const dots = document.createElement('canvas');
dots.width = 1024; dots.height = 512;
(() => {
  const d = dots.getContext('2d');
  d.fillStyle = '#000'; d.fillRect(0, 0, 1024, 512);
  d.fillStyle = '#0b0c0f';
  for (let y = 0; y < 64; y++) for (let x = 0; x < 128; x++) d.fillRect(x * PX + 1, y * PX + 1, PX - 2, PX - 2);
})();
const layer = document.createElement('canvas');
layer.width = 1024; layer.height = 512;
const lctx = layer.getContext('2d');
const view = createBaseView($('#view'), oled);
function onFrame(b64, info) {
  const bin = atob(b64);
  lctx.clearRect(0, 0, 1024, 512);
  lctx.fillStyle = '#eef2fb';
  for (let y = 0; y < 64; y++) for (let xb = 0; xb < 16; xb++) {
    const v = bin.charCodeAt(y * 16 + xb);
    if (!v) continue;
    for (let bit = 0; bit < 8; bit++) if (v & (0x80 >> bit)) lctx.fillRect((xb * 8 + bit) * PX + 1, y * PX + 1, PX - 2, PX - 2);
  }
  octx.drawImage(dots, 0, 0);
  octx.globalCompositeOperation = 'lighter';
  octx.globalAlpha = 0.4;
  octx.filter = 'blur(8px)';
  octx.drawImage(layer, 0, 0);
  octx.filter = 'none';
  octx.globalAlpha = 1;
  octx.globalCompositeOperation = 'source-over';
  octx.drawImage(layer, 0, 0);
  view.update();
  lastInfo = info;
  $('#hero-info').textContent = info ? t('info_' + info) : '';
}

function eqTargets() {
  const targets = BASE_PRESETS.map((n, i) => [`base:${i}`, `Base · ${n}`]);
  Object.keys(cfg.eq_presets || {}).sort().forEach(n => targets.push([`user:${n}`, n]));
  return targets;
}
function targetLabel(v) { return (eqTargets().find(t => t[0] === v) || [v, v])[1]; }

function renderRules() {
  const box = $('#rules');
  box.innerHTML = '';
  (cfg.eq_rules || []).forEach((r, i) => {
    const row = document.createElement('div');
    row.className = 'rule';
    row.innerHTML = `<span class="exe"></span><span class="arrow">→</span><span class="tgt"></span><button class="del" title="${t('delete')}">×</button>`;
    $('.exe', row).textContent = r.exe;
    $('.tgt', row).textContent = targetLabel(r.eq);
    $('.del', row).onclick = () => setCfg('eq_rules', cfg.eq_rules.filter((_, j) => j !== i));
    box.appendChild(row);
  });
  if (!(cfg.eq_rules || []).length) box.innerHTML = `<p class="note">${t('rules_none')}</p>`;
  const sel = $('#rule-eq');
  const cur = sel.value;
  sel.innerHTML = eqTargets().map(([v, l]) => `<option value="${v}">${l}</option>`).join('');
  if (cur) sel.value = cur;
}

async function refreshApps() {
  const apps = JSON.parse(await api.runningApps());
  $('#rule-app').innerHTML = apps.map(a => `<option>${a}</option>`).join('');
}
$('#rule-app').addEventListener('focus', refreshApps);
$('#rule-add').addEventListener('click', () => {
  const exe = $('#rule-app').value, eq = $('#rule-eq').value;
  if (!exe || !eq) return;
  const rules = (cfg.eq_rules || []).filter(r => r.exe !== exe);
  rules.push({ exe, eq });
  setCfg('eq_rules', rules);
  toast(`${exe} → ${targetLabel(eq)}`);
});

// raccourcis : capture de la combinaison
$$('input.hotkey').forEach(el => {
  el.addEventListener('focus', () => { el.value = t('hk_press'); });
  el.addEventListener('blur', () => renderConfig());
  el.addEventListener('keydown', e => {
    e.preventDefault();
    if (e.key === 'Escape') { el.blur(); return; }
    const hk = { ...(cfg.hotkeys || {}) };
    if (e.key === 'Backspace' || e.key === 'Delete') { hk[el.dataset.hk] = ''; setCfg('hotkeys', hk); el.blur(); return; }
    if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return;
    let key = e.code.startsWith('Key') ? e.code.slice(3) : e.code.startsWith('Digit') ? e.code.slice(5) : /^F\d+$/.test(e.key) ? e.key : null;
    if (!key) return;
    const parts = [];
    if (e.ctrlKey) parts.push('Ctrl');
    if (e.altKey) parts.push('Alt');
    if (e.shiftKey) parts.push('Shift');
    if (!parts.length && !/^F\d+$/.test(key)) { el.value = t('hk_mod'); return; }
    hk[el.dataset.hk] = [...parts, key].join('+');
    setCfg('hotkeys', hk);
    el.blur();
  });
});

$('#autostart').addEventListener('change', e => api.setAutostart(e.target.checked));
$('#language').addEventListener('change', async e => {
  setCfg('language', e.target.value);
  meta = JSON.parse(await api.getMeta());
  await loadStrings();
});

async function loadStrings() {
  S = JSON.parse(await api.getStrings());
  document.documentElement.lang = S.lang;
  $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  $$('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
  $$('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  if (meta.gg) renderGG(meta.gg);
  $('#fw').textContent = meta.firmware ? t('firmware', { v: meta.firmware }) : '';
  $('#hero-info').textContent = lastInfo ? t('info_' + lastInfo) : t('screen_title');
  renderForced(forced);
  renderConfig();
  render();
}
$('#gg-toggle').addEventListener('click', async () => {
  const res = JSON.parse(await api.toggleGG());
  renderGG(res);
  toast(res.message);
});
function renderGG(g) {
  $('#gg-status').textContent = g.status;
  $('#gg-toggle').textContent = g.button;
}

$('#titlebar').addEventListener('mousedown', e => { if (!e.target.closest('button') && e.button === 0) api.startDrag(); });
$('#titlebar').addEventListener('dblclick', e => e.preventDefault());
$('#btn-min').addEventListener('click', () => api.minimize());
$('#btn-close').addEventListener('click', () => api.hide());
document.addEventListener('click', e => {
  const a = e.target.closest('a[href]');
  if (a) { e.preventDefault(); api.openUrl(a.href); }
});

new QWebChannel(qt.webChannelTransport, async channel => {
  api = channel.objects.api;
  bindDevice();
  bindConfig();
  cfg = JSON.parse(await api.getConfig());
  meta = JSON.parse(await api.getMeta());
  state = JSON.parse(await api.getState());
  $('#autostart').checked = meta.autostart;
  $('#version').textContent = meta.version;
  $('#hk-card').hidden = !meta.hotkeys;
  $('#gg-card').hidden = !meta.gg;
  $('#page-music').hidden = !meta.media;
  $('#rules').closest('.card').hidden = meta.platform === 'linux';
    forced = meta.forced_black;
  await loadStrings();
  refreshApps();

  api.stateChanged.connect(json => { state = JSON.parse(json); render(); });
  api.configChanged.connect(json => { cfg = JSON.parse(json); renderConfig(); });
  api.frame.connect(onFrame);
  api.resendFrame();
  api.forcedBlack.connect(renderForced);
  api.notify.connect(toast);
});
