from ._anvil_designer import Reports_miniTemplate
from anvil import *
import plotly.graph_objects as go
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import plotly.graph_objects as go
import random
from datetime import date, timedelta
import math
from ... import Global
import re


class Reports_mini(Reports_miniTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.build_two_month_balance_plot()

  # ---------------------------
  # Date helpers
  # ---------------------------
  def _first_of_month(self, d: date) -> date:
    return date(d.year, d.month, 1)

  def _add_months_first(self, d_first: date, months: int) -> date:
    y = d_first.year + (d_first.month - 1 + months) // 12
    m = (d_first.month - 1 + months) % 12 + 1
    return date(y, m, 1)

  def _last_of_month(self, d: date) -> date:
    first_next = self._add_months_first(self._first_of_month(d), 1)
    return first_next - timedelta(days=1)

  def _daterange(self, start_d: date, end_d: date):
    cur = start_d
    while cur <= end_d:
      yield cur
      cur += timedelta(days=1)

  # ---------------------------
  # Tokenisation + grouping
  # ---------------------------
  def _tokens(self, name: str):
    # keep only letters/numbers as tokens, lowercase
    raw = re.findall(r"[A-Za-z0-9]+", name or "")
    return [t.lower() for t in raw if t.strip()]

  def _meaningful_tokens(self, name: str):
    # Words that should NOT drive grouping (generic descriptors)
    stop = {
      "card", "credit", "cheque", "checking", "current", "savings",
      "account", "acc", "a/c", "black", "gold", "platinum",
      "visa", "mastercard", "amex", "debit", "business", "personal"
    }
    toks = self._tokens(name)
    return [t for t in toks if t not in stop]

  def _build_groups_any_shared_word(self, account_names_by_id: dict):
    """
    Returns:
      groups: dict[group_key -> list[(acc_id, name)]]
      group_key is a token (e.g., 'fnb', 'investec', 'discovery') or 'other'
    """
    # Collect meaningful tokens per account
    tokens_by_id = {}
    for acc_id, name in account_names_by_id.items():
      tokens_by_id[acc_id] = set(self._meaningful_tokens(name))

    # Count token frequency across accounts to find "shared words"
    token_freq = {}
    for acc_id, toks in tokens_by_id.items():
      for t in toks:
        token_freq[t] = token_freq.get(t, 0) + 1

    # Candidate grouping tokens are ones appearing in >= 2 accounts
    shared_tokens = {t for t, c in token_freq.items() if c >= 2}

    # For each account, choose the "best" shared token (if any)
    # Heuristic: prefer tokens shared by more accounts, then shorter token
    def best_shared_token(toks):
      candidates = [t for t in toks if t in shared_tokens]
      if not candidates:
        return None
      candidates.sort(key=lambda t: (-token_freq.get(t, 0), len(t), t))
      return candidates[0]

    group_key_by_id = {}
    for acc_id, toks in tokens_by_id.items():
      g = best_shared_token(toks)
      group_key_by_id[acc_id] = g if g else "other"

    # Build group dict
    groups = {}
    for acc_id, name in account_names_by_id.items():
      g = group_key_by_id.get(acc_id, "other")
      groups.setdefault(g, []).append((acc_id, name))

    # Stable ordering inside groups
    for g in groups:
      groups[g].sort(key=lambda t: t[1].lower())

    return groups

  # ---------------------------
  # Color helpers (HSL -> HEX)
  # ---------------------------
  def _hsl_to_hex(self, h, s, l):
    h = (h % 360) / 360.0
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))

    def hue2rgb(p, q, t):
      if t < 0: t += 1
      if t > 1: t -= 1
      if t < 1/6: return p + (q - p) * 6 * t
      if t < 1/2: return q
      if t < 2/3: return p + (q - p) * (2/3 - t) * 6
      return p

    if s == 0:
      r = g = b = l
    else:
      q = l * (1 + s) if l < 0.5 else l + s - l * s
      p = 2 * l - q
      r = hue2rgb(p, q, h + 1/3)
      g = hue2rgb(p, q, h)
      b = hue2rgb(p, q, h - 1/3)

    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))

  def _assign_colors_any_shared_word(self, account_names_by_id: dict):
    """
    Groups by any shared meaningful word, then assigns same hue per group + shades per account.
    Returns {acc_id: "#RRGGBB"}.
    """
    base_hues = [210, 25, 145, 280, 95, 15, 200, 330, 60, 260]
    groups = self._build_groups_any_shared_word(account_names_by_id)

    # Make group order stable and pleasant:
    # Put "other" last, else alphabetical
    group_keys = sorted([g for g in groups.keys() if g != "other"])
    if "other" in groups:
      group_keys.append("other")

    colors = {}

    for gi, g in enumerate(group_keys):
      hue = base_hues[gi % len(base_hues)]
      members = groups[g]
      n = len(members)

      # Shades in the same hue
      l_min, l_max = 0.38, 0.74
      if n == 1:
        lightnesses = [(l_min + l_max) / 2]
      else:
        step = (l_max - l_min) / (n - 1)
        lightnesses = [l_min + i * step for i in range(n)]

      for (acc_id, _), l in zip(members, lightnesses):
        colors[acc_id] = self._hsl_to_hex(hue, s=0.65, l=l)

    return colors

  # ---------------------------
  # Main plotting function (Anvil-safe)
  # ---------------------------
  def build_two_month_balance_plot(self, **event_args):
    today = date.today()
    start_this = self._first_of_month(today)
    start_last = self._add_months_first(start_this, -1)
    end_this = self._last_of_month(today)

    accounts = getattr(Global, "ACCOUNTS", []) or []
    account_names_by_id = {acc_id: acc_name for (acc_name, acc_id) in accounts}

    txns = getattr(Global.Transactions_Form, "all_transactions", []) or []

    starting = {acc_id: 0 for acc_id in account_names_by_id.keys()}
    deltas = {acc_id: {} for acc_id in account_names_by_id.keys()}

    for t in txns:
      try:
        acc_id = t.get("account")
        amt = int(t.get("amount", 0))
        d = t.get("date")
        if acc_id not in account_names_by_id or not isinstance(d, date):
          continue

        if d < start_last:
          starting[acc_id] = starting.get(acc_id, 0) + amt
        elif start_last <= d <= end_this:
          dd = deltas.setdefault(acc_id, {})
          dd[d] = dd.get(d, 0) + amt
      except Exception:
        continue

    all_days = list(self._daterange(start_last, end_this))
    x = [d.isoformat() for d in all_days]

    tickvals = [start_last.isoformat(), start_this.isoformat(), end_this.isoformat()]
    ticktext = [start_last.strftime("1 %b"), start_this.strftime("1 %b"), end_this.strftime("%d %b")]

    colors = self._assign_colors_any_shared_word(account_names_by_id)

    def has_any_data(acc_id):
      return starting.get(acc_id, 0) != 0 or len(deltas.get(acc_id, {})) > 0

    def sort_key(acc_id):
      # sort by group token, then name
      name = account_names_by_id.get(acc_id, "")
      toks = self._meaningful_tokens(name)
      # pick deterministic group key for sorting
      g = "other"
      if toks:
        # the grouping function might choose a shared token; we can mirror that roughly:
        g = toks[0]
      return (g, name.lower())

    traces = []

    for acc_id in sorted(account_names_by_id.keys(), key=sort_key):
      if not has_any_data(acc_id):
        continue

      name = account_names_by_id[acc_id]
      bal = starting.get(acc_id, 0)

      y = []
      for d in all_days:
        bal += deltas.get(acc_id, {}).get(d, 0)
        y.append(bal / 100.0)

      traces.append({
        "type": "scatter",
        "mode": "lines",
        "name": name,
        "x": x,
        "y": y,
        "line": {"width": 2, "color": colors.get(acc_id, "#4c78a8")},
        "hovertemplate": "<b>%{fullData.name}</b><br>%{x}<br>Balance: R%{y:,.2f}<extra></extra>",
      })

    layout = {
      "title": {"text": "Account Balances — Last Month & This Month", "x": 0.02, "xanchor": "left"},
      "height": 260,

      # ✅ ONLY FIX: more space for y-axis labels
      "margin": {"l": 110, "r": 15, "t": 45, "b": 35},

      "paper_bgcolor": "white",
      "plot_bgcolor": "white",
      "hovermode": "x unified",
      "legend": {"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "left", "x": 0.0, "font": {"size": 10}},
      "xaxis": {
        "type": "category",
        "tickmode": "array",
        "tickvals": tickvals,
        "ticktext": ticktext,
        "showgrid": False,
        "zeroline": False,
        "fixedrange": True
      },
      "yaxis": {
        "tickprefix": "R",
        "tickformat": ",",

        # ✅ ONLY FIX: let Plotly auto-reserve label space
        "automargin": True,

        "showgrid": True,
        "gridcolor": "rgba(0,0,0,0.08)",
        "zeroline": False,
        "fixedrange": True,

        # ✅ OPTIONAL but helpful: slightly larger labels + padding from axis
        "tickfont": {"size": 11},
        "ticks": "outside",
        "ticklen": 4
      }
    }


    if len(traces) == 0:
      traces = [{
        "type": "scatter",
        "mode": "text",
        "x": [start_this.isoformat()],
        "y": [0],
        "text": ["No transaction data yet for the selected period."],
        "textposition": "middle center",
        "hoverinfo": "skip",
        "showlegend": False
      }]
      layout["xaxis"]["showgrid"] = False
      layout["yaxis"]["showgrid"] = False

    self.plot_1.data = traces
    self.plot_1.layout = layout
    self.plot_1.redraw()
