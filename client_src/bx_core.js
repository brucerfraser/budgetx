/* bx_core.js v1 — Budget X canon client plumbing (Round 02, Builder D)
   history:
   v1 — initial: token helpers, api(), signOut(), fmtR(), toast/inline-error helper.
   No browser dialogs — no alert, confirm or prompt — anywhere in this file, this round or ever. */

var BX_TOKEN_KEY = 'bx_token';
var BX_EXPIRES_KEY = 'bx_expires';
var BX_LOGIN_PATH = '/_/api/x';
var BX_API_PREFIX = '/_/api';

/* ---------- routing helper ----------
   Every client page (x, d-dash, m-dash) is served from the SAME path, /_/api/x,
   distinguished only by the ?slug= query string — so "am I already on the login
   page" has to be decided from the slug, never from location.pathname. */
function bxCurrentSlug() {
  try {
    var sp = new URLSearchParams(location.search);
    return sp.get('slug') || 'x';
  } catch (e) { return 'x'; }
}

/* ---------- token helpers over localStorage ---------- */
function bxGetToken() {
  try { return localStorage.getItem(BX_TOKEN_KEY); } catch (e) { return null; }
}
function bxGetExpires() {
  try { return localStorage.getItem(BX_EXPIRES_KEY); } catch (e) { return null; }
}
function bxSetSession(token, expiresIso) {
  try {
    localStorage.setItem(BX_TOKEN_KEY, token);
    localStorage.setItem(BX_EXPIRES_KEY, expiresIso || '');
  } catch (e) { /* storage unavailable — nothing to do */ }
}
function bxClearSession() {
  try {
    localStorage.removeItem(BX_TOKEN_KEY);
    localStorage.removeItem(BX_EXPIRES_KEY);
  } catch (e) { /* storage unavailable — nothing to do */ }
}

/* ---------- api(path, opts) ----------
   Prefixes /_/api, sends Authorization: Bearer <token> from localStorage.bx_token,
   sets Content-Type: application/json, and on any 401 clears bx_token + bx_expires
   and navigates to /_/api/x (skipped only when already there, to avoid a reload loop
   on the login page's own stored-token probe). */
async function api(path, opts) {
  opts = opts || {};
  var url = BX_API_PREFIX + (path.charAt(0) === '/' ? path : '/' + path);
  var headers = {};
  for (var k in (opts.headers || {})) { headers[k] = opts.headers[k]; }
  if (!headers['Content-Type']) { headers['Content-Type'] = 'application/json'; }
  var token = bxGetToken();
  if (token) { headers['Authorization'] = 'Bearer ' + token; }

  var fetchOpts = {
    method: opts.method || 'GET',
    headers: headers
  };
  if (opts.body !== undefined) { fetchOpts.body = opts.body; }

  var res, text, data;
  try {
    res = await fetch(url, fetchOpts);
  } catch (err) {
    return { ok: false, status: 0, data: null };
  }
  try { text = await res.text(); } catch (e) { text = ''; }
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }

  if (res.status === 401) {
    bxClearSession();
    if (bxCurrentSlug() !== 'x') {
      location.href = BX_LOGIN_PATH;
    }
  }
  return { ok: res.ok, status: res.status, data: data };
}

/* ---------- signOut() ---------- */
async function signOut() {
  try { await api('/auth/logout', { method: 'POST' }); } catch (e) { /* best effort */ }
  bxClearSession();
  location.href = BX_LOGIN_PATH;
}

/* ---------- fmtR(n) — R1,234.56 / (R1,234.56) for negatives ---------- */
function fmtR(n) {
  var num = Number(n);
  if (!isFinite(num)) { num = 0; }
  var neg = num < 0;
  var abs = Math.abs(num);
  var fixed = abs.toFixed(2);
  var parts = fixed.split('.');
  var intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  var out = 'R' + intPart + '.' + parts[1];
  return neg ? '(' + out + ')' : out;
}

/* ---------- toast / inline-error helper ---------- */
function bxToast(msg, opts) {
  opts = opts || {};
  var el = document.getElementById('bx-toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'bx-toast';
    el.className = 'bx-toast';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('bx-toast--show');
  if (el._bxTimer) { clearTimeout(el._bxTimer); }
  el._bxTimer = setTimeout(function () {
    el.classList.remove('bx-toast--show');
  }, opts.duration || 3000);
}

function bxInlineError(target, msg) {
  var el = (typeof target === 'string') ? document.getElementById(target) : target;
  if (!el) { return; }
  el.textContent = msg || '';
}
