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
  def __init__(self, full_screen=False, **properties):
    self.init_components(**properties)
    self.full_screen = full_screen
    if full_screen:
      self.plot_1.height = 600
      self.plot_1.interactive = True

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
  # Tokenisation + grouping (INSTITUTION ONLY)
  # ---------------------------
  def _tokens(self, name: str):
    raw = re.findall(r"[A-Za-z0-9]+", name or "")
    return [t.lower() for t in raw if t.strip()]

  def _institution_key(self, name: str) -> str:
    """
    Group ONLY by institution (bank/provider), ignoring personal names & generic account words.
    This ensures Investec accounts share a hue just like the FNB accounts do.
    """
    tokens = self._tokens(name)

    ignore = {
      # personal names
      "bruce", "esther",
      # generic descriptors
      "card", "credit", "cheque", "checking", "current", "savings",
      "account", "acc", "a", "c", "black", "gold", "platinum",
      "visa", "mastercard", "amex", "debit", "business", "personal"
    }

    # Known institutions you want to group by (extend as needed)
    institutions = {"fnb", "investec", "discovery"}

    # Prefer an explicit institution token anywhere in the name
    for t in tokens:
      if t in institutions:
        return t

    # Fallback: first non-ignored token
    for t in tokens:
      if t not in ignore:
        return t

    return "other"

  def _build_groups_institution_only(self, account_names_by_id: dict):
    groups = {}
    for acc_id, name in account_names_by_id.items():
      g = self._institution_key(name)
      groups.setdefault(g, []).append((acc_id, name))

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

  def _assign_colors_institution_only(self, account_names_by_id: dict):
    """
    Groups by institution only, then assigns same hue per institution + shades per account.
    Returns {acc_id: "#RRGGBB"}.
    """
    base_hues = [210, 25, 145, 280, 95, 15, 200, 330, 60, 260]
    groups = self._build_groups_institution_only(account_names_by_id)

    group_keys = sorted([g for g in groups.keys() if g != "other"])
    if "other" in groups:
      group_keys.append("other")

    colors = {}
    for gi, g in enumerate(group_keys):
      hue = base_hues[gi % len(base_hues)]
      members = groups[g]
      n = len(members)

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

    # ✅ CHANGED: use institution-only coloring
    colors = self._assign_colors_institution_only(account_names_by_id)

    # ✅ CHANGED: sort by institution, then name
    def sort_key(acc_id):
      name = account_names_by_id.get(acc_id, "")
      g = self._institution_key(name)
      return (g, name.lower())

    def has_any_data(acc_id):
      return starting.get(acc_id, 0) != 0 or len(deltas.get(acc_id, {})) > 0

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
      # ✅ taller graph when full_screen=True
      "height": 260,

      # ✅ ONLY FIX: more space for y-axis labels
      "margin": {"l": 110, "r": 15, "t": 45, "b": 35},

      "paper_bgcolor": "white",
      "plot_bgcolor": "white",
      "hovermode": "x unified",
      "legend": {
        "orientation": "h",
        "yanchor": "top",
        "y": -0.14 if getattr(self, "full_screen", False) else -0.18,
        "xanchor": "left",
        "x": 0.0,
        "font": {"size": 10}
      },
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
        "automargin": True,
        "showgrid": True,
        "gridcolor": "rgba(0,0,0,0.08)",
        "zeroline": False,
        "fixedrange": True,
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