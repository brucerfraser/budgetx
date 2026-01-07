from datetime import date, timedelta

from anvil import Plot
import plotly.graph_objects as go  # OK to keep, but we won't use Figure/add_trace

from . import Global


# ============================================================
# Date helpers
# ============================================================

def _first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)

def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    month_days = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(d.day, month_days[m - 1])
    return date(y, m, day)

def _daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


# ============================================================
# Slider mapping
# ============================================================

_SLIDER_STOPS = [
  "Last month",
  "Last 2 months",
  "Last 6 months",
  "Last year",
  "Last 2 years",
  "All data"
]

def slider_label(value: int) -> str:
  v = int(value or 0)
  v = max(0, min(5, v))
  return _SLIDER_STOPS[v]

def slider_date_range(value: int):
  """
  0: beginning of last month -> today
  1: last 2 months -> today
  2: last 6 months -> today
  3: last year -> today (same day-of-month)
  4: last 2 years -> today (same day-of-month)
  5: all data -> today (start = min txn date if available else today)
  """
  today = date.today()
  v = int(value or 0)
  v = max(0, min(5, v))

  if v == 0:
    start = _add_months(_first_of_month(today), -1)
    return start, today

  if v == 1:
    start = _add_months(_first_of_month(today), -2)
    return start, today

  if v == 2:
    start = _add_months(_first_of_month(today), -6)
    return start, today

  if v == 3:
    return date(today.year - 1, today.month, today.day), today

  if v == 4:
    return date(today.year - 2, today.month, today.day), today

  # v == 5: all data
  txns = getattr(Global, "TRANSACTIONS", []) or []
  min_d = None
  for t in txns:
    d = t.get("date")
    if isinstance(d, date):
      min_d = d if (min_d is None or d < min_d) else min_d

  if min_d is None:
    min_d = today

  return min_d, today


# ============================================================
# Plot helpers
# ============================================================

def _make_plot(traces, layout, *, height=320, interactive=False):
    p = Plot()
    p.height = str(height)
    p.interactive = bool(interactive)
    p.config = {
        "doubleClick": "reset",
        "displaylogo": False,
        "scrollZoom": False,
        "responsive": True
    }
    p.data = traces
    p.layout = layout
    p.redraw()
    return p


# ============================================================
# Recon-aware balance construction
# ============================================================

def _build_txn_deltas_by_acc():
    """
    Returns:
      deltas_by_acc: {acc_id: {date: net_delta_cents}}
      min_date: earliest txn date found (or None)
    """
    txns = getattr(Global, "TRANSACTIONS", []) or []
    deltas_by_acc = {}
    min_date = None

    for t in txns:
        d = t.get("date")
        acc = t.get("account")
        amt = t.get("amount")

        if not (isinstance(d, date) and acc):
            continue
        if amt is None:
            continue

        amt_c = int(amt)

        if acc not in deltas_by_acc:
            deltas_by_acc[acc] = {}
        deltas_by_acc[acc][d] = deltas_by_acc[acc].get(d, 0) + amt_c

        min_date = d if (min_date is None or d < min_date) else min_date

    return deltas_by_acc, min_date


def _recon_by_acc():
    """
    Returns:
      {acc_id: (recon_date, recon_amount_cents)} for accounts with recon values.
    """
    recon = {}
    accounts_whole = getattr(Global, "ACCOUNTS_WHOLE", []) or []

    for a in accounts_whole:
        acc_id = a.get("acc_id")
        rd = a.get("recon_date")
        ra = a.get("recon_amount")

        if not acc_id:
            continue
        if isinstance(rd, date) and ra is not None:
            recon[acc_id] = (rd, int(ra))

    return recon

def _balance_series_for_account(start: date, end: date,
                                deltas_by_day: dict,
                                min_data_date: date,
                                recon_tuple=None):
    """
    End-of-day balances (cents) for each day in [start..end].

    Rule:
    - If recon exists: anchor on recon_date balance = recon_amount, work forwards and backwards.
    - If no recon: anchor at earliest txn date balance = 0, work forwards/backwards.
    """
    if start > end:
        return []

    # Decide anchor
    if recon_tuple is not None:
        anchor_date, anchor_bal = recon_tuple
    else:
        anchor_date = min_data_date if isinstance(min_data_date, date) else start
        anchor_bal = 0

    # Expand range to include anchor (so we can compute back/forward properly)
    work_start = min(start, anchor_date)
    work_end = max(end, anchor_date)

    balances = {anchor_date: anchor_bal}

    # forward: bal(d) = bal(d-1) + delta(d)
    d = anchor_date + timedelta(days=1)
    while d <= work_end:
        balances[d] = balances[d - timedelta(days=1)] + deltas_by_day.get(d, 0)
        d += timedelta(days=1)

    # backward:
    # bal(d+1) = bal(d) + delta(d+1) => bal(d) = bal(d+1) - delta(d+1)
    d = anchor_date - timedelta(days=1)
    while d >= work_start:
        balances[d] = balances[d + timedelta(days=1)] - deltas_by_day.get(d + timedelta(days=1), 0)
        d -= timedelta(days=1)

    # Slice to requested window
    return [balances.get(d, 0) for d in _daterange(start, end)]


# ============================================================
# PUBLIC: Accounts Overview (default)
# ============================================================

def accounts_overview_plot(start: date, end: date, *, height: int = 320) -> Plot:
    """
    Multi-line balances by account over time, grouped by inferred institution, recon-aware.
    Returns an Anvil Plot component.
    """
    accounts = getattr(Global, "ACCOUNTS_WHOLE", []) or []  # [{"acc_name": ..., "acc_id": ...}, ...]
    acc_name_by_id = {acc["acc_id"]: acc["acc_name"] for acc in accounts}

    deltas_by_acc, min_d = _build_txn_deltas_by_acc()
    recon = _recon_by_acc()

    days = list(_daterange(start, end))
    x = [d.isoformat() for d in days]

    traces = []

    # running total across all accounts (float R)
    totals = [0.0] * len(x)

    # Define a scalable color palette (20 base colors, each with 5 variations)
    base_colors = [
        "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF",  # Red, Green, Blue, Pink, Purple
        "#FFC300", "#FF8D33", "#DAF7A6", "#581845", "#C70039",  # Yellow, Orange, Light Green, Dark Purple, Crimson
        "#900C3F", "#33FFBD", "#FF33F6", "#33D4FF", "#8D33FF",  # Maroon, Coral, Teal, Magenta, Cyan, Violet
        "#FF8D33", "#33FF8D", "#8DFF33", "#338DFF"               # Amber, Lime, Chartreuse, Azure
    ]
    institution_colors = {}
    default_palette = ["#808080", "#A9A9A9", "#C0C0C0", "#D3D3D3", "#E0E0E0"]  # Shades of gray

    # Function to infer institution from account name
    def infer_institution(acc_name):
        keywords = {
            "Investec": "Investec",
            "FNB": "FNB",
            "Standard": "Standard Bank",
            "Capitec": "Capitec",
            "Nedbank": "Nedbank",
            "ABSA": "ABSA",
            "Discovery": "Discovery Bank"
        }
        for keyword, institution in keywords.items():
            if keyword.lower() in acc_name.lower():
                return institution
        # fallback: use first word as institution hint
        first_word = (acc_name or "").split()[0] if acc_name else "Other"
        return first_word or "Other"

    # Function to get or create a color palette for an institution
    def get_institution_palette(institution):
        # helper: hex -> (r,g,b)
        def _hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        # helper: (r,g,b) -> hex
        def _rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(x))) for x in rgb])

        # blend rgb towards white by factor (0 -> original, 1 -> white)
        def _blend_with_white(rgb, factor):
            return tuple(round(c + (255 - c) * factor) for c in rgb)

        if institution not in institution_colors:
            color_index = len(institution_colors) % len(base_colors)
            base_color = base_colors[color_index]
            base_rgb = _hex_to_rgb(base_color)
            # create 5 distinguishable variations by blending with white at increasing factors
            factors = [0.0, 0.25, 0.45, 0.65, 0.85]
            palette = [_rgb_to_hex(_blend_with_white(base_rgb, f)) for f in factors]
            institution_colors[institution] = palette
        return institution_colors[institution]

    # Track color usage per institution
    institution_color_index = {}

    for acc_id, acc_name in sorted(acc_name_by_id.items(), key=lambda kv: kv[1].lower()):
        deltas = deltas_by_acc.get(acc_id, {})
        recon_tuple = recon.get(acc_id)

        # If no activity and no recon, skip
        if not deltas and recon_tuple is None:
            continue

        y_cents = _balance_series_for_account(
            start=start,
            end=end,
            deltas_by_day=deltas,
            min_data_date=min_d if min_d is not None else start,
            recon_tuple=recon_tuple
        )
        y = [v / 100.0 for v in y_cents]

        # add to running total
        for i, v in enumerate(y):
            totals[i] += v

        # Infer institution from account name
        institution = infer_institution(acc_name)

        # Get the color palette for the institution
        institution_palette = get_institution_palette(institution)
        if institution not in institution_color_index:
            institution_color_index[institution] = 0
        color_index = institution_color_index[institution] % len(institution_palette)
        color = institution_palette[color_index]
        institution_color_index[institution] += 1

        traces.append({
            "type": "scatter",
            "mode": "lines",
            "name": f"{institution} - {acc_name}",
            "x": x,
            "y": y,
            "line": {"width": 2, "color": color},
            "hovertemplate": "<b>%{fullData.name}</b><br>%{x}<br>Balance: R%{y:,.2f}<extra></extra>"
        })

    # add total area traces (drawn first so they appear behind account lines)
    # positive area (green)
    y_pos = [v if v > 0 else 0 for v in totals]
    # negative area (negative values)
    y_neg = [v if v < 0 else 0 for v in totals]

    total_traces = []
    # positive fill
    total_traces.append({
        "type": "scatter",
        "mode": "lines",
        "name": "Total (positive)",
        "x": x,
        "y": y_pos,
        "line": {"width": 0, "color": "rgba(76,175,80,0.0)"},
        "fill": "tozeroy",
        "fillcolor": "rgba(76,175,80,0.18)",  # green with light alpha
        "hovertemplate": "<b>Total</b><br>%{x}<br>R%{y:,.2f}<extra></extra>",
        "showlegend": False
    })
    # negative fill
    total_traces.append({
        "type": "scatter",
        "mode": "lines",
        "name": "Total (negative)",
        "x": x,
        "y": y_neg,
        "line": {"width": 0, "color": "rgba(229,57,53,0.0)"},
        "fill": "tozeroy",
        "fillcolor": "rgba(229,57,53,0.18)",  # red with light alpha
        "hovertemplate": "<b>Total</b><br>%{x}<br>R%{y:,.2f}<extra></extra>",
        "showlegend": False
    })

    # place total traces before account traces so they sit in the background
    traces = total_traces + traces

    layout = {
        "height": height,
        # give more room at the bottom for the legend so it no longer crowds the y-axis tick labels
        "margin": {"l": 72, "r": 10, "t": 40, "b": 110},
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.36,               # push legend further below plot area
            "xanchor": "center",
            "x": 0.5,
            "font": {"size": 11},     # slightly smaller legend font to reduce crowding
            "traceorder": "normal"
        },
        "xaxis": {"showgrid": False, "fixedrange": True},
        "yaxis": {
            "showgrid": True,
            "fixedrange": True,
            "tickprefix": "R",
            "tickformat": ",.0f",
            "automargin": True
        }
    }

    return _make_plot(traces, layout, height=height, interactive=False)


# ============================================================
# PUBLIC: Category Pie (Graphic #1)
# ============================================================

def category_pie_plot(start: date, end: date, *, height: int = 320) -> Plot:
  """
  Donut/pie of spend by category.
  Convention:
    - spend = negative amounts only (absolute value aggregated)
  Returns an Anvil Plot component.
  """
  txns = getattr(Global, "TRANSACTIONS", []) or []
  cats = getattr(Global, "CATEGORIES", {}) or {}  # {cat_id: [name, back, text], ...}
  main_cats = getattr(Global, "MAIN_CATS", {}) or {}

  totals_cents = {}  # {cat_name: cents}
  for t in txns:
     print(t)
     break
  for c,v in cats.items():
     print(c,v)
     break
  for mc,v in main_cats.items():
     print(mc,v)
     break
  for t in txns:
    d = t.get("date")
    if not (isinstance(d, date) and start <= d <= end):
      continue

    # robust category handling: transactions may have None or unknown category keys
    cat_key = t.get("category")
    if not cat_key or cat_key not in cats:
      cat_id = "__uncat__"
    else:
      cat_id = cats.get(cat_key, {}).get("belongs_to") or "__uncat__"

    # skip transfer main-category id (existing behaviour)
    if cat_id == "ec8e0085-8408-43a2-953f-ebba24549d96":
      continue  # skip transfers

    amt = t.get("amount")
    if amt is None:
      continue

    amt_c = int(amt)
    if amt_c >= 0:
      continue  # only spend

    # resolve display name for the main category, provide generic Uncategorised fallback
    default_main = ["Uncategorised", "#CCCCCC", "#000000"]
    cat_name = (main_cats.get(cat_id) or default_main)[0]
    totals_cents[cat_name] = totals_cents.get(cat_name, 0) + abs(amt_c)

  items = sorted(totals_cents.items(), key=lambda kv: kv[1], reverse=True)
  labels = [k for k, _ in items]
  values = [v / 100.0 for _, v in items]

  traces = [{
    "type": "pie",
    "labels": labels,
    "values": values,
    "hole": 0.45,
    "textinfo": "percent",
    "hovertemplate": "<b>%{label}</b><br>R%{value:,.2f}<br>%{percent}<extra></extra>"
  }]

  layout = {
    "height": height,
    # give room on the right for a date-range annotation; keep some bottom space for the annotation anchor
    "margin": {"l": 10, "r": 150, "t": 20, "b": 40},
    "showlegend": True,
    "annotations": [
      {
        "text": f"Range:<br>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}",
        "xref": "paper",
        "yref": "paper",
        "x": 1.02,            # just outside plotting area to the right
        "y": 0.02,            # bottom-right (paper coords)
        "xanchor": "left",
        "yanchor": "bottom",
        "showarrow": False,
        "align": "left",
        "font": {"size": 12, "color": "#222222"},
        "bordercolor": "#dddddd",
        "borderwidth": 1,
        "bgcolor": "rgba(255,255,255,0.95)",
        "opacity": 0.98
      }
    ]
  }

  return _make_plot(traces, layout, height=height, interactive=False)

