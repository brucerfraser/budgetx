/* bx_core.js v2 — Budget X canon client plumbing
   history:
   v1 — initial: token helpers, api(), signOut(), fmtR(), toast/inline-error helper.
   v2 — Round 03, Builder D: bxWrite() (optimistic write, serialised per key), bxSheet()
        (bottom sheet / centred modal from one call, focus-trapped), bxConfirm() (styled
        two-button confirm — the reason nothing in this app ever needs window.confirm),
        bxToastAction() (a toast carrying an action button, used for "Archived. Undo").
        bxFmtCents is NOT redeclared here — see the note above the deprecated fmtR() for why.
        fmtR() is now explicitly marked deprecated; it is still callable (removing it would
        break nothing this round writes, but a later round reaching for the wrong formatter
        is exactly how every figure ends up rendered 100x too small) and this file calls it
        from nowhere.
   No browser dialogs — no alert, confirm or prompt — anywhere in this file, this round or ever. */

var BX_TOKEN_KEY = 'bx_token';
var BX_EXPIRES_KEY = 'bx_expires';
var BX_LOGIN_PATH = '/_/api/x';
var BX_API_PREFIX = '/_/api';

/* ---------- routing helper ----------
   Every client page (x, d-dash, m-dash, d-trans, m-trans) is served from the SAME path,
   /_/api/x, distinguished only by the ?slug= query string — so "am I already on the login
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

/* ---------- fmtR(n) — DEPRECATED, not deleted ----------
   Takes RANDS, not cents. This app moves integer cents everywhere now (spec_03 §0.1); a
   later round reaching for fmtR() on a cents value would render every figure 100x too
   small. It stays callable only so nothing that already depends on it (nothing does, in
   this round — AC-7.6 greps all five served pages and expects zero call sites outside this
   canon block) breaks outright. Use bxFmtCents() for every new figure. */
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

/* ---------- bxFmtCents(n) — thin re-export of bx_calc.js's formatter ----------
   bx_calc.js is embedded immediately BEFORE this block in every page's marker sandwich
   (spec_03: "bx_calc.js FIRST, because bx_core.js's bxFmtCents delegates to it") and it
   already declares a global `function bxFmtCents(cents)`. Deliberately NOT re-declared as
   `function bxFmtCents(...)` here: both blocks share one <script> scope, and a second
   top-level function declaration with the SAME name hoists over the first before any code
   runs — there is no execution-time moment at which this file could still read bx_calc.js's
   original function via that name, so redeclaring it would either shadow it with a
   half-implementation or (if it tried to call "itself" by name) recurse forever. Instead:
   bx_calc.js's global is the live implementation, unmodified, and this is a documented,
   defensive no-op unless something is badly wrong (bx_calc.js missing from the page). */
if (typeof bxFmtCents === 'undefined') {
  window.bxFmtCents = function bxFmtCents(n) {
    throw new Error('bxFmtCents: bx_calc.js was not embedded before bx_core.js on this page');
  };
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
  el.innerHTML = '';
  var msgEl = document.createElement('span');
  msgEl.className = 'bx-toast__msg';
  msgEl.textContent = msg;
  el.appendChild(msgEl);
  el.classList.add('bx-toast--show');
  if (el._bxTimer) { clearTimeout(el._bxTimer); }
  el._bxTimer = setTimeout(function () {
    el.classList.remove('bx-toast--show');
  }, opts.duration || 3000);
}

/* ---------- bxToastAction(msg, opts) ----------
   A toast carrying an action button — "Archived. Undo" for 10 seconds. Same #bx-toast
   element as bxToast() (only one toast is ever shown at a time on this app), rebuilt each
   call so an action button never lingers into a later plain toast.
   opts: { label: 'Undo', onAction: fn(), duration: 10000 } */
function bxToastAction(msg, opts) {
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
  el.innerHTML = '';
  var msgEl = document.createElement('span');
  msgEl.className = 'bx-toast__msg';
  msgEl.textContent = msg;
  el.appendChild(msgEl);

  if (opts.label && typeof opts.onAction === 'function') {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bx-toast__action';
    btn.textContent = opts.label;
    btn.addEventListener('click', function () {
      el.classList.remove('bx-toast--show');
      if (el._bxTimer) { clearTimeout(el._bxTimer); }
      opts.onAction();
    });
    el.appendChild(btn);
  }

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

/* ---------- bxWrite(path, body, opts) — the optimistic write helper ----------
   Applies the change to the local model and repaints IMMEDIATELY (opts.apply runs
   synchronously, before any network activity), fires the POST in the background, and on
   any non-2xx or network failure rolls the local model back (opts.rollback) and raises a
   toast naming what did not save. Never blocks a repaint on the network — the 1-second
   rule applied to writes.

   Writes sharing the same opts.key are serialised: each call's request is chained after
   the previous one's for that key, so a fast double-tap edits the model twice (both
   applies run instantly, as they should) but the two requests still reach the server in
   order rather than racing — the second can never land before the first and be
   overwritten by it arriving late.

   opts: { key: string, apply: fn(), rollback: fn(), describe: string }
   returns Promise<{ok, status, data}> */
var _bxWriteQueues = {};
async function bxWrite(path, body, opts) {
  opts = opts || {};
  if (typeof opts.apply === 'function') {
    opts.apply();
  }
  var key = opts.key || path;
  var prevTail = _bxWriteQueues[key] || Promise.resolve();
  var describe = opts.describe || 'Change';

  var tail = prevTail.then(function () {
    return api(path, { method: 'POST', body: JSON.stringify(body) }).then(function (res) {
      if (!res.ok) {
        if (typeof opts.rollback === 'function') { opts.rollback(); }
        bxToast(describe + ' did not save');
      }
      return res;
    }, function () {
      if (typeof opts.rollback === 'function') { opts.rollback(); }
      bxToast(describe + ' did not save');
      return { ok: false, status: 0, data: null };
    });
  });

  /* Keep the queue alive for the NEXT same-key write regardless of this one's outcome —
     a failed write must not jam the queue for whatever the user tries next. */
  _bxWriteQueues[key] = tail.then(function (r) { return r; }, function () {
    return { ok: false, status: 0, data: null };
  });

  return tail;
}

/* ---------- bxSheet(opts) — bottom sheet (mobile) / centred modal (desktop) ----------
   One call renders either shape depending on the same breakpoint the rest of the app
   redirects on (max-width: 998px). Focus is trapped inside the sheet, Escape and a
   backdrop click both close it, and focus returns to opts.invoker (or whatever had focus
   when bxSheet was called) on close.

   opts: { kind: 'edit'|'confirm'|'picker', title, bodyEl|bodyHTML,
           actions: [{label, onClick, primary}], onClose, invoker }
   The root element carries data-sheet and data-kind="<kind>".
   returns { close() } */
function bxSheet(opts) {
  opts = opts || {};
  var invoker = opts.invoker || document.activeElement;
  var mobile = window.matchMedia('(max-width: 998px)').matches;

  var backdrop = document.createElement('div');
  backdrop.className = 'bx-sheet-backdrop';

  var sheet = document.createElement('div');
  sheet.className = 'bx-sheet ' + (mobile ? 'bx-sheet--bottom' : 'bx-sheet--modal');
  sheet.setAttribute('data-sheet', '');
  sheet.setAttribute('data-kind', opts.kind || 'edit');
  sheet.setAttribute('role', 'dialog');
  sheet.setAttribute('aria-modal', 'true');
  sheet.tabIndex = -1;

  if (opts.title) {
    var titleEl = document.createElement('div');
    titleEl.className = 'bx-sheet__title';
    titleEl.textContent = opts.title;
    sheet.appendChild(titleEl);
  }

  var bodyWrap = document.createElement('div');
  bodyWrap.className = 'bx-sheet__body';
  if (opts.bodyEl) {
    bodyWrap.appendChild(opts.bodyEl);
  } else if (opts.bodyHTML) {
    bodyWrap.innerHTML = opts.bodyHTML;
  }
  sheet.appendChild(bodyWrap);

  var actionsWrap = document.createElement('div');
  actionsWrap.className = 'bx-sheet__actions';
  (opts.actions || []).forEach(function (a) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bx-btn' + (a.primary ? '' : ' bx-btn--ghost');
    btn.textContent = a.label;
    btn.addEventListener('click', function (evt) {
      if (typeof a.onClick === 'function') { a.onClick(evt); }
    });
    actionsWrap.appendChild(btn);
  });
  sheet.appendChild(actionsWrap);

  backdrop.appendChild(sheet);
  document.body.appendChild(backdrop);

  function focusables() {
    var nodes = sheet.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    var out = [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (!el.disabled && el.offsetParent !== null) { out.push(el); }
    }
    return out;
  }

  var closed = false;
  function close() {
    if (closed) { return; }
    closed = true;
    document.removeEventListener('keydown', onKeydown, true);
    backdrop.removeEventListener('click', onBackdropClick);
    if (backdrop.parentNode) { backdrop.parentNode.removeChild(backdrop); }
    if (typeof opts.onClose === 'function') { opts.onClose(); }
    if (invoker && typeof invoker.focus === 'function') { invoker.focus(); }
  }

  function onKeydown(evt) {
    if (evt.key === 'Escape') {
      evt.preventDefault();
      close();
      return;
    }
    if (evt.key === 'Tab') {
      var items = focusables();
      if (!items.length) { evt.preventDefault(); return; }
      var first = items[0];
      var last = items[items.length - 1];
      if (evt.shiftKey && document.activeElement === first) {
        evt.preventDefault();
        last.focus();
      } else if (!evt.shiftKey && document.activeElement === last) {
        evt.preventDefault();
        first.focus();
      }
    }
  }

  function onBackdropClick(evt) {
    if (evt.target === backdrop) { close(); }
  }

  document.addEventListener('keydown', onKeydown, true);
  backdrop.addEventListener('click', onBackdropClick);

  var initial = focusables();
  (initial[0] || sheet).focus();

  return { close: close };
}

/* ---------- bxConfirm(opts) — styled two-button confirm ----------
   Renders as a bxSheet with data-kind="confirm" and resolves a Promise<boolean> once the
   user picks. Exists so nothing in this app ever needs window.confirm.
   opts: { title, message, confirmLabel, cancelLabel, invoker } */
function bxConfirm(opts) {
  opts = opts || {};
  return new Promise(function (resolve) {
    var settled = false;
    function settle(v) {
      if (settled) { return; }
      settled = true;
      resolve(v);
    }

    var msgEl = document.createElement('p');
    msgEl.className = 'bx-confirm__message';
    msgEl.textContent = opts.message || '';

    var handle = bxSheet({
      kind: 'confirm',
      title: opts.title || 'Are you sure?',
      bodyEl: msgEl,
      invoker: opts.invoker,
      onClose: function () { settle(false); },
      actions: [
        {
          label: opts.cancelLabel || 'Cancel',
          onClick: function () { settle(false); handle.close(); }
        },
        {
          label: opts.confirmLabel || 'Confirm',
          primary: true,
          onClick: function () { settle(true); handle.close(); }
        }
      ]
    });
  });
}
