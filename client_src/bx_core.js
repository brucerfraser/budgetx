/* bx_core.js v3 — Budget X canon client plumbing
   history:
   v1 — initial: token helpers, api(), signOut(), a rand-based money formatter (removed in
        v3 — see below), toast/inline-error helper.
   v2 — Round 03, Builder D: bxWrite() (optimistic write, serialised per key), bxSheet()
        (bottom sheet / centred modal from one call, focus-trapped), bxConfirm() (styled
        two-button confirm — the reason nothing in this app ever needs window.confirm),
        bxToastAction() (a toast carrying an action button, used for "Archived. Undo").
        bxFmtCents is NOT redeclared here — see the note above bxFmtCents's guard for why.
   v3 — Round 04, Builder D (spec_04 §3.4): six additions — bxMonthNav (the one month
        selector every screen now uses, initialised from bx_calc.js's bxDefaultMonth),
        bxMeter (the §4.6 progress meter, rendered from a bxProgress() object), bxInlineEdit
        (the tap/click-to-edit money field that commits on EVERY dismissal path — fact 18 is
        a field that looked like it saved and did not), bxLayer (the history contract behind
        AC-8.5/AC-8.8: opening a sheet or entering mobile focus mode pushes exactly one
        history entry, and popstate — including the device back gesture — closes the
        topmost layer and runs any pending commit registered on it, so nothing traps the
        back gesture and nothing silently discards a typed figure), bxError (resolves its
        container AT CALL TIME, never at load — S03 finding 8, the #loadError-captured-
        before-first-render bug), bxDesktopOnPhoneNotice (a d-* client at <=998px renders a
        full-screen notice linking to its m-* twin instead of an overlay that intercepts
        real clicks — §3.11 fix 6).
        FOUR CORRECTIONS: (1) .bx-sidebar-phone-link moves into bx_core.css — it was
        duplicated verbatim in d-dash and d-trans and had to be fixed twice (S03 finding 7);
        the duplicate declarations are removed from both desktop clients this round.
        (2) The v1 rand-based money formatter IS DELETED — definition and the
        (already-zero) call sites, and its identifier no longer appears anywhere in this
        file, comments included, so a textual scan of a served page finds no trace of it. It
        took rands in an app that moves cents; round 03 proved zero call sites across all
        five clients and left it callable only as a "deprecated, not deleted" bridge. AC-7.6
        now asserts it appears NOWHERE in any served page — this deliberately supersedes
        spec_03 AC-7.6, which required the definition to be present.
        (3) Skeleton rows carry data-skeleton on every client (d-trans included — it had
        none; S03 finding 5 / AC-12.3).
        (4) Error containers are resolved at render time via bxError (S03 finding 8) — see
        the addition above.
        bxSheet() gains an OPT-IN opts.historyLayer (default false, so all five round-03
        pages' existing bxSheet() calls are byte-for-byte unchanged in behaviour): when true,
        the sheet's close() — from Escape, a backdrop click, or any action handler that calls
        handle.close() — routes through a bxLayer instead of tearing down the DOM directly,
        so the same one history entry it pushed on open is consumed on every close path
        including the device back gesture, and the returned handle exposes .layer so a
        bxInlineEdit rendered inside the sheet's body can register its pending commit on it.
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

/* ---------- bxLayer(opts) — the history contract (v3, spec_04 §3.4) ----------
   Makes AC-8.5 and AC-8.8 implementable: entering mobile focus mode and opening a sheet
   each push EXACTLY ONE history entry, and popstate — the device back gesture included —
   closes the topmost layer and runs any pending commit registered on it. Nothing traps the
   back gesture: a layer's own close() (from a UI control, Escape, or a backdrop tap) does
   not tear anything down itself — it calls history.back(), and the ONE popstate listener
   below does the actual teardown. That is deliberate: the real back gesture and every
   programmatic close share the exact same code path, so there is no second path for a
   fixer to forget to wire up.

   opts: { onClose: fn() }  — called exactly once when the layer closes, however it closes.
   returns { close(), registerCommit(fn) }
     close()          — idempotent; consumes this layer's history entry.
     registerCommit(fn) — fn is called (synchronously, in registration order) BEFORE
                          onClose, on every close path. A bxInlineEdit rendered inside a
                          layer registers its own commit-if-changed here so a value typed
                          into it is never lost to a backdrop tap, Escape, sheet dismissal
                          or the device back gesture (fact 18).

   Invariant this relies on: nothing else in this app ever calls history.pushState —
   verified by search, round 04. If that ever stops being true a foreign history entry
   could desynchronise the stack from the browser's actual history depth; the popstate
   handler is written defensively (pops at most one entry per event, no-ops if the stack
   is already empty) so a foreign entry can only ever under-consume, never throw or double
   up a close(). */
var _bxLayerStack = [];
var _bxLayerListenerInstalled = false;
function _bxLayerInstallListener() {
  if (_bxLayerListenerInstalled) { return; }
  _bxLayerListenerInstalled = true;
  window.addEventListener('popstate', function () {
    var entry = _bxLayerStack.pop();
    if (!entry) { return; }
    entry.closed = true;
    for (var i = 0; i < entry.commits.length; i++) {
      try { entry.commits[i](); } catch (e) { /* one bad commit must not block the rest */ }
    }
    if (typeof entry.onClose === 'function') { entry.onClose(); }
  });
}
function bxLayer(opts) {
  opts = opts || {};
  _bxLayerInstallListener();
  var entry = { onClose: opts.onClose, commits: [], closed: false };
  _bxLayerStack.push(entry);
  try {
    history.pushState({ bxLayer: true }, '', location.href);
  } catch (e) { /* pushState unavailable — layer still functions, just without the
                    history-back contract; close() falls back to immediate teardown */
    entry._noHistory = true;
  }

  function close() {
    if (entry.closed) { return; }
    if (entry._noHistory) {
      entry.closed = true;
      var idx = _bxLayerStack.indexOf(entry);
      if (idx !== -1) { _bxLayerStack.splice(idx, 1); }
      for (var i = 0; i < entry.commits.length; i++) {
        try { entry.commits[i](); } catch (e) { /* ignore */ }
      }
      if (typeof entry.onClose === 'function') { entry.onClose(); }
      return;
    }
    entry.closed = true;
    /* Only this layer's OWN pushed entry is consumed. If it is no longer on top (a
       nested layer opened after it and has not yet closed), history.back() would close
       the WRONG entry — so a layer beneath an open child simply marks itself closed and
       waits: the child's own close() will, in turn, surface this one when it pops. */
    if (_bxLayerStack[_bxLayerStack.length - 1] === entry) {
      history.back();
    }
  }

  function registerCommit(fn) {
    if (typeof fn === 'function') { entry.commits.push(fn); }
  }

  return { close: close, registerCommit: registerCommit };
}

/* ---------- bxSheet(opts) — bottom sheet (mobile) / centred modal (desktop) ----------
   One call renders either shape depending on the same breakpoint the rest of the app
   redirects on (max-width: 998px). Focus is trapped inside the sheet, Escape and a
   backdrop click both close it, and focus returns to opts.invoker (or whatever had focus
   when bxSheet was called) on close.

   opts: { kind: 'edit'|'confirm'|'picker'|'overspend', title, bodyEl|bodyHTML,
           actions: [{label, onClick, primary}], onClose, invoker,
           historyLayer: bool (default false) }
   The root element carries data-sheet and data-kind="<kind>".

   historyLayer is OPT-IN and defaults to false, so every round-03 call site (d-trans,
   m-trans, x) is byte-for-byte unchanged in behaviour — this is additive, not a rewrite of
   v2's contract. Round 04's callers that need AC-8.5/AC-8.8 (a sheet that can hold a
   pending money edit and must survive a backdrop tap / Escape / device back gesture) pass
   historyLayer:true and get handle.layer back, which any bxInlineEdit rendered into the
   sheet's body should be constructed with (opts.layer) so its pending edit is committed
   before the sheet's own teardown runs, on every dismissal path — never after.

   returns { close(), layer (only when historyLayer:true) } */
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
  /* teardown() is the ACTUAL dom cleanup. With historyLayer off (v2 behaviour, unchanged)
     close() below IS teardown() and runs synchronously, exactly as v2 always has. With
     historyLayer on, close() instead asks the layer to consume its history entry, and the
     layer's popstate-driven onClose calls teardown() — so a real device back gesture and
     every programmatic close (Escape, backdrop, an action button) tear down through the
     identical path. */
  function teardown() {
    if (closed) { return; }
    closed = true;
    document.removeEventListener('keydown', onKeydown, true);
    backdrop.removeEventListener('click', onBackdropClick);
    if (backdrop.parentNode) { backdrop.parentNode.removeChild(backdrop); }
    if (typeof opts.onClose === 'function') { opts.onClose(); }
    if (invoker && typeof invoker.focus === 'function') { invoker.focus(); }
  }

  var layer = null;
  var close;
  if (opts.historyLayer) {
    layer = bxLayer({ onClose: teardown });
    close = layer.close;
  } else {
    close = teardown;
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

  var handle = { close: close };
  if (layer) { handle.layer = layer; }
  return handle;
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

/* ---------- bxError(msg, opts) — v3 ----------
   Resolves its container AT CALL TIME, never at load. S03 finding 8: m-trans captured
   #loadError with document.getElementById() once, at the top of the page script, before the
   first real render — and the first render replaced that container, so a POST-load error
   wrote into a node no longer attached to the document. Every call to bxError() looks the
   container up fresh, so it is correct however many times the surrounding DOM has been
   rebuilt since the page loaded.

   opts: { target: string (default 'bx-error') } — the container's id. If it does not exist
   yet, one is created and appended to <body> (a page may also declare its own #bx-error
   element wherever it wants it positioned; bxError() finds it by id either way).
   Passing a falsy msg hides the container without deleting it, so the NEXT bxError() call
   still finds the same node — resolving "at call time" does not mean "recreate every time".
   returns the container element. */
function bxError(msg, opts) {
  opts = opts || {};
  var id = opts.target || 'bx-error';
  var el = document.getElementById(id);
  if (!el) {
    el = document.createElement('div');
    el.id = id;
    el.className = 'bx-error-banner';
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'assertive');
    document.body.appendChild(el);
  }
  if (!msg) {
    el.textContent = '';
    el.classList.remove('bx-error-banner--show');
    el.hidden = true;
    return el;
  }
  el.hidden = false;
  el.textContent = msg;
  el.classList.add('bx-error-banner--show');
  return el;
}

/* ---------- bxDesktopOnPhoneNotice(opts) — v3 (§3.11 fix 6) ----------
   d-trans's fixed sidebar overlaid the table at <=998px and intercepted real clicks — a
   desktop layout is not a phone layout squeezed narrower, it is unusable there. Every d-*
   client instead shows a full-screen notice with a working link to its m-* twin, covering
   the ENTIRE viewport (so nothing beneath it can be the thing a click at the centre of the
   screen lands on) the moment the viewport crosses the SAME (max-width: 998px) breakpoint
   the rest of the app already redirects on, and removes itself the moment it doesn't.

   opts: { slug: 'm-trans'|'m-budget'|…  (required), title, message } */
function bxDesktopOnPhoneNotice(opts) {
  opts = opts || {};
  var slug = opts.slug;
  var mq = window.matchMedia('(max-width: 998px)');
  var notice = null;

  function build() {
    var el = document.createElement('div');
    el.className = 'bx-phone-notice';
    el.id = 'bxPhoneNotice';
    var card = document.createElement('div');
    card.className = 'bx-phone-notice__card bx-card bx-card--raised';
    var h = document.createElement('div');
    h.className = 'bx-phone-notice__title bx-head';
    h.textContent = opts.title || 'This screen needs more room';
    var p = document.createElement('p');
    p.className = 'bx-phone-notice__body';
    p.textContent = opts.message
      || 'This is the desktop layout. Use the phone version instead — it is designed for this width.';
    var a = document.createElement('a');
    a.className = 'bx-btn';
    a.href = '?slug=' + slug;
    a.textContent = 'Open phone version';
    card.appendChild(h);
    card.appendChild(p);
    card.appendChild(a);
    el.appendChild(card);
    return el;
  }

  function apply() {
    if (mq.matches) {
      if (!notice) {
        notice = build();
        document.body.appendChild(notice);
      }
      /* Covering the desktop layout with a high z-index stops a CLICK reaching it
         (§3.11 fix 6), but a control merely painted underneath is still enumerable by a
         DOM walk — a 44px audit that does not know about z-index would measure a
         desktop-at-390px control squeezed under 44px and call it a real failure. Actually
         hiding the desktop layout (not just covering it) is what makes it correctly
         SKIPPED rather than measured. */
      document.documentElement.setAttribute('data-phone-notice', 'true');
    } else if (notice) {
      if (notice.parentNode) { notice.parentNode.removeChild(notice); }
      notice = null;
      document.documentElement.removeAttribute('data-phone-notice');
    }
  }

  apply();
  if (typeof mq.addEventListener === 'function') {
    mq.addEventListener('change', apply);
  } else if (typeof mq.addListener === 'function') {
    mq.addListener(apply); /* Safari < 14 */
  }
}

/* ---------- bxMonthNav(opts) — v3 ----------
   The month selector as ONE component: chevron / label / chevron, a "This month" reset, and
   data-month with data-value="YYYY-MM". No screen implements its own selector any more.
   Initialised from bx_calc.js's bxDefaultMonth(txns, serverDate) (§0 ruling 1) — every
   screen therefore opens on the same month, computed the same way, from transactions alone.

   opts: {
     mount: element|id (required) — cleared and filled with the nav's markup,
     txns: array (required) — the payload's transactions, for bxDefaultMonth,
     serverDate: 'YYYY-MM-DD' (required) — payload.server_date; "This month" always returns
       here (spec_03 AC-6.2), never to bxDefaultMonth's month, which can differ from it,
     onChange: fn({y, m}) — called on every user-driven month change (prev/next/this-month).
       NOT called for the initial month: read handle.getMonth() and do the first render
       yourself, so a caller that wants to fetch or compute something before first paint can.
     showThisMonth: bool (default true)
   }
   returns { getMonth(), setMonth(y, m), goThisMonth(), el } */
function bxMonthNav(opts) {
  opts = opts || {};
  var mount = (typeof opts.mount === 'string') ? document.getElementById(opts.mount) : opts.mount;
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'];
  function pad2(n) { return n < 10 ? '0' + n : String(n); }

  mount.innerHTML = '';
  var wrap = document.createElement('div');
  wrap.className = 'bx-month-selector';
  wrap.setAttribute('data-month', '');

  var prevBtn = document.createElement('button');
  prevBtn.type = 'button';
  prevBtn.className = 'bx-month-chevron';
  prevBtn.setAttribute('aria-label', 'Previous month');
  prevBtn.innerHTML = '&#9664;';

  var label = document.createElement('span');
  label.className = 'bx-month-label';

  var nextBtn = document.createElement('button');
  nextBtn.type = 'button';
  nextBtn.className = 'bx-month-chevron';
  nextBtn.setAttribute('aria-label', 'Next month');
  nextBtn.innerHTML = '&#9654;';

  wrap.appendChild(prevBtn);
  wrap.appendChild(label);
  wrap.appendChild(nextBtn);
  mount.appendChild(wrap);

  var thisBtn = null;
  if (opts.showThisMonth !== false) {
    thisBtn = document.createElement('button');
    thisBtn.type = 'button';
    thisBtn.className = 'bx-btn bx-btn--ghost bx-this-month-btn';
    thisBtn.textContent = 'This month';
    mount.appendChild(thisBtn);
  }

  var serverYM = bxYearMonth(opts.serverDate);
  if (!serverYM) {
    var now = new Date();
    serverYM = { y: now.getUTCFullYear(), m: now.getUTCMonth() + 1 };
  }
  var initial = bxDefaultMonth(opts.txns || [], opts.serverDate) || serverYM;
  var state = { y: initial.y, m: initial.m };

  function render() {
    label.textContent = MONTH_NAMES[state.m - 1] + ' ' + state.y;
    wrap.setAttribute('data-value', state.y + '-' + pad2(state.m));
  }
  render();

  function setMonth(y, m, opts2) {
    var silent = opts2 && opts2.silent;
    state.y = y;
    state.m = m;
    render();
    if (!silent && typeof opts.onChange === 'function') { opts.onChange({ y: y, m: m }); }
  }

  prevBtn.addEventListener('click', function () {
    var m = state.m - 1, y = state.y;
    if (m < 1) { m = 12; y -= 1; }
    setMonth(y, m);
  });
  nextBtn.addEventListener('click', function () {
    var m = state.m + 1, y = state.y;
    if (m > 12) { m = 1; y += 1; }
    setMonth(y, m);
  });
  if (thisBtn) {
    thisBtn.addEventListener('click', function () { setMonth(serverYM.y, serverYM.m); });
  }

  return {
    getMonth: function () { return { y: state.y, m: state.m }; },
    setMonth: setMonth,
    goThisMonth: function () { setMonth(serverYM.y, serverYM.m); },
    el: wrap
  };
}

/* ---------- bxMeter(opts) — v3 ----------
   The §4.6 progress meter element, rendered from a bxProgress() object — ONE implementation,
   used by category rows, sub-category rows and the rail, so the same figure never renders
   two different ways in two places. Carries every data-meter attribute §3.5 requires:
   data-fraction (capped, 4dp), data-state, and data-over (the UNCAPPED over_ratio to 4dp,
   or absent — not merely empty — when state is not "over": that is what lets a 3x overspend
   be told from a 30x one, which the legacy's saturated third branch could not do, fact 16).

   Colour is the design language's, not the meter's: under/at use --primary, over uses
   --negative (never --error, which is reserved for errors), none renders the track alone.

   opts: { progress: <bxProgress() result> (required), mount: element (optional, appended to) }
   returns the meter element. */
function bxMeter(opts) {
  opts = opts || {};
  var p = opts.progress || { state: 'none', fraction: 0, over_ratio: null };
  var el = document.createElement('div');
  el.className = 'bx-meter bx-meter--' + p.state;
  el.setAttribute('data-meter', '');
  el.setAttribute('data-state', p.state);
  el.setAttribute('data-fraction', (typeof p.fraction === 'number' ? p.fraction : 0).toFixed(4));
  if (p.state === 'over' && typeof p.over_ratio === 'number') {
    el.setAttribute('data-over', p.over_ratio.toFixed(4));
  } else {
    el.setAttribute('data-over', '');
  }
  var track = document.createElement('div');
  track.className = 'bx-meter__track';
  var fill = document.createElement('div');
  fill.className = 'bx-meter__fill';
  var pct = (typeof p.fraction === 'number' ? Math.max(0, Math.min(1, p.fraction)) : 0) * 100;
  fill.style.width = pct + '%';
  track.appendChild(fill);
  el.appendChild(track);
  if (opts.mount) { opts.mount.appendChild(el); }
  return el;
}

/* ---------- bxInlineEdit(opts) — v3 ----------
   The tap/click-to-edit MONEY field. A field whose value has been CHANGED commits on EVERY
   dismissal path — blur, Enter, backdrop tap, Escape, sheet dismissal, the device back
   gesture. An UNCHANGED field closes without a write. ESCAPE DOES NOT DISCARD a money edit:
   fact 18 is a field that looked like it saved and did not, and a second way to lose a typed
   figure is not an improvement. Every commit routes through the caller's onCommit, which is
   expected to call bxWrite() (this function never calls it directly, so the caller controls
   the write's key/apply/rollback/describe).

   Blur, Enter and Escape are handled directly on the <input>. Backdrop tap, sheet dismissal
   and the device back gesture are NOT this component's to intercept — they belong to
   whatever bxSheet/bxLayer contains it — so opts.layer (a bxLayer handle) is how this
   registers commitPending() to run on THOSE paths too: harmless if blur already ran (a
   second commit call on an already-clean field is a no-op, since "changed" is judged
   against the value at the moment editing STARTED, and editing is no longer in progress).

   opts: {
     mount: element (required) — appended to,
     valueCents: int|null (required) — null means "no budget set", not 0,
     onCommit: fn(newCentsOrNull) (required) — called ONLY when the parsed value differs
       from valueCents at the time editing began,
     emptyLabel: string (default 'No budget set'),
     ariaLabel: string,
     layer: bxLayer handle (optional) — see above,
     formatter: fn(cents|null) -> string (default: bxFmtCents, guarded for null)
   }
   returns { el, commitPending(), setValue(cents) } */
function bxInlineEdit(opts) {
  opts = opts || {};
  var mount = (typeof opts.mount === 'string') ? document.getElementById(opts.mount) : opts.mount;

  function centsToRandStr(cents) {
    if (cents === null || cents === undefined) { return ''; }
    var neg = cents < 0;
    var abs = Math.abs(cents);
    var whole = Math.floor(abs / 100);
    var rem = abs % 100;
    var s = String(whole) + '.' + (rem < 10 ? '0' + rem : String(rem));
    return neg ? '-' + s : s;
  }
  function randStrToCents(str) {
    var n = parseFloat(String(str).replace(/,/g, '').trim());
    if (!isFinite(n)) { return NaN; }
    return Math.round(n * 100);
  }
  function fmt(cents) {
    if (typeof opts.formatter === 'function') { return opts.formatter(cents); }
    if (cents === null || cents === undefined) { return opts.emptyLabel || 'No budget set'; }
    return bxFmtCents(cents);
  }

  var root = document.createElement('div');
  root.className = 'bx-inline-edit';

  var display = document.createElement('button');
  display.type = 'button';
  display.className = 'bx-inline-edit__display';
  if (opts.ariaLabel) { display.setAttribute('aria-label', opts.ariaLabel); }

  var input = document.createElement('input');
  input.type = 'text';
  input.inputMode = 'decimal';
  input.className = 'bx-inline-edit__input';
  input.hidden = true;
  if (opts.ariaLabel) { input.setAttribute('aria-label', opts.ariaLabel); }

  var current = (opts.valueCents === undefined) ? null : opts.valueCents;
  var editing = false;
  var startedAt = null;

  function renderDisplay() {
    display.textContent = fmt(current);
    display.setAttribute('data-present', (current === null) ? 'false' : 'true');
  }
  renderDisplay();

  function enterEdit() {
    if (editing) { return; }
    editing = true;
    startedAt = current;
    input.value = centsToRandStr(current);
    display.hidden = true;
    input.hidden = false;
    input.focus();
    input.select();
  }

  function commitPending() {
    if (!editing) { return; }
    editing = false;
    input.hidden = true;
    display.hidden = false;

    var raw = input.value.trim();
    var next;
    var valid;
    if (raw === '') {
      next = null;
      valid = true;
    } else {
      var parsed = randStrToCents(raw);
      valid = isFinite(parsed) && Math.floor(parsed) === parsed;
      next = valid ? parsed : startedAt; /* an unparsable edit reverts silently rather
                                             than committing garbage or crashing bxFmtCents */
    }
    var changed = valid && next !== startedAt;
    current = next;
    renderDisplay();
    if (changed && typeof opts.onCommit === 'function') {
      opts.onCommit(current);
    }
  }

  display.addEventListener('click', enterEdit);
  input.addEventListener('blur', commitPending);
  input.addEventListener('keydown', function (evt) {
    if (evt.key === 'Enter') {
      evt.preventDefault();
      input.blur();
    } else if (evt.key === 'Escape') {
      /* ESCAPE DOES NOT DISCARD (fact 18) — it commits exactly like every other path. Do
         not let the keydown bubble to a containing bxSheet's own Escape handler and close
         the sheet out from under an edit still resolving its own commit. */
      evt.preventDefault();
      evt.stopPropagation();
      input.blur();
    }
  });

  root.appendChild(display);
  root.appendChild(input);
  if (mount) { mount.appendChild(root); }

  if (opts.layer && typeof opts.layer.registerCommit === 'function') {
    opts.layer.registerCommit(commitPending);
  }

  return {
    el: root,
    commitPending: commitPending,
    setValue: function (cents) {
      current = cents;
      if (!editing) { renderDisplay(); }
    }
  };
}
