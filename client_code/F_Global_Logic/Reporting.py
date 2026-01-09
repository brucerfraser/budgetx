from datetime import date, timedelta
from operator import itemgetter

from anvil import Plot
import plotly.graph_objects as go  # OK to keep, but we won't use Figure/add_trace

from . import Global,BUDGET


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

def accounts_overview_plot(start: date, end: date, *, height: int = 320, dashboard: bool = False) -> Plot:
    """
    Multi-line balances by account over time, grouped by inferred institution, recon-aware.
    Returns an Anvil Plot component.
    """
    accounts = getattr(Global, "ACCOUNTS_WHOLE", []) or []  # [{"acc_name": ..., "acc_id": ...}, ...]
    acc_name_by_id = {acc["acc_id"]: acc["acc_name"] for acc in accounts}

    deltas_by_acc, min_d = _build_txn_deltas_by_acc()
    recon = _recon_by_acc()

    days = list(_daterange(start, end))
    # keep x as real date objects so Plotly treats axis as dates (not categories/strings)
    x = days

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
            "hovertemplate": "<b>%{fullData.name}</b><br>%{x|%d %b %Y}<br>Balance: R%{y:,.2f}<extra></extra>"
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
        "hovertemplate": "<b>Total</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
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
        "hovertemplate": "<b>Total</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
        "showlegend": False
    })

    # place total traces before account traces so they sit in the background
    traces = total_traces + traces

    # base layout (full reports)
    layout = {
        "height": height,
        # increase bottom margin so x-axis ticks do not overlap the legend
        "margin": {"l": 72, "r": 10, "t": 40, "b": 160},
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.40,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": "#ffffff", "size": 11},
            "traceorder": "normal"
        },
        # transparent background to match pie/variance charts
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "showgrid": False,
            "fixedrange": True,
            "tickfont": {"color": "#ffffff", "size": 11},
            "titlefont": {"color": "#ffffff"},
            "tickformat": ",.0f",
            "tickprefix": ""
        },
        "yaxis": {
            "showgrid": True,
            "fixedrange": True,
            "tickprefix": "R",
            "tickformat": ",.0f",
            "automargin": True,
            "tickfont": {"color": "#ffffff", "size": 11},
            "titlefont": {"color": "#ffffff"}
        },
        "title": {
            "text": f"<b>Accounts Overview</b><br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"color": "#ffffff", "size": 14}
        }
    }

    # dashboard mode: compact sizing and abbreviated axis ticks (use SI suffixes)
    if dashboard:
        # smaller overall footprint
        layout["height"] = max(160, int(height * 0.6))
        layout["margin"] = {"l": 56, "r": 8, "t": 20, "b": 90}
        # dashboard removes legend and uses compact number formatting on the y-axis
        layout.pop("legend", None)
        layout["showlegend"] = False
        # x-axis should be dates (short format)
        layout["xaxis"]["tickformat"] = "%d %b"
        layout["xaxis"]["tickfont"] = {"color": "#ffffff", "size": 9}
        # abbreviate y-axis numbers (SI) so 1,000,000 -> 1M (plotly SI formatting) with currency prefix
        layout["yaxis"]["tickformat"] = ".2s"
        layout["yaxis"]["tickprefix"] = "R"
        layout["yaxis"]["tickfont"] = {"color": "#ffffff", "size": 10}
        # smaller title for dashboard
        layout["title"]["font"]["size"] = 12

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
    "margin": {"l": 10, "r": 80, "t": 40, "b": 40},
    "showlegend": True,
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "legend": {"bgcolor": "rgba(255,255,255,0.95)"},
    "title": {
      "text": f"Spend by Category<br><span style='font-size:12px;color:#ffffff'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
      "x": 0.5,
      "xanchor": "center",
      "yanchor": "top",
      "font": {"size": 14, "color": "#ffffff"}
    }
  }

  return _make_plot(traces, layout, height=height, interactive=False)


# ============================================================
# PUBLIC: Category Variance (Graphic #2)
# ============================================================

def category_variance_plot(start: date, end: date, *, height: int = 360, income: bool = False) -> Plot:
    """
    Two-panel horizontal chart:
    - Left panel: Variance bars centered at 0 (green = under budget; red = over budget)
    - Right panel: Positive magnitude bars for Budget vs Actual amounts (spend shown as positive)
    """
    txns = getattr(Global, "TRANSACTIONS", []) or []
    cats = getattr(Global, "CATEGORIES", {}) or {}
    main_cats = getattr(Global, "MAIN_CATS", {}) or {}
    all_budgets = getattr(BUDGET, "all_budgets", []) or []

    # aggregate actuals separately for spends and incomes (cents)
    spends_by_main = {}
    incomes_by_main = {}

    for t in txns:
        d = t.get("date")
        if not (isinstance(d, date) and start <= d <= end):
            continue

        cat_key = t.get("category")
        if not cat_key or cat_key not in cats:
            main_id = "__uncat__"
        else:
            main_id = cats.get(cat_key, {}).get("belongs_to") or "__uncat__"

        # skip transfers
        if main_id == "ec8e0085-8408-43a2-953f-ebba24549d96":
            continue

        amt = t.get("amount")
        if amt is None:
            continue
        amt_c = int(amt)

        # keep original signs: spends negative, incomes positive
        if amt_c < 0:
            spends_by_main[main_id] = spends_by_main.get(main_id, 0) + amt_c  # negative total
        elif amt_c > 0:
            incomes_by_main[main_id] = incomes_by_main.get(main_id, 0) + amt_c  # positive total

    # aggregate budgets by main-category id (cents) for periods inside selected months
    budgets_by_main = {}
    start_month = _first_of_month(start)
    end_month = _first_of_month(end)
    for b in all_budgets:
        period = b.get("period")
        if not isinstance(period, date):
            continue
        period_month = _first_of_month(period)
        if period_month < start_month or period_month > end_month:
            continue
        sub_cat = b.get("belongs_to")
        main_id = (cats.get(sub_cat) or {}).get("belongs_to") or "__uncat__"
        budgets_by_main[main_id] = budgets_by_main.get(main_id, 0) + int(b.get("budget_amount", 0))

    # build master list of main_ids to display (include budget-only and income)
    main_ids = set(spends_by_main) | set(incomes_by_main) | set(budgets_by_main) | set(main_cats.keys())

    # Optionally exclude Income category entirely
    if not income:
        for mid, info in main_cats.items():
            if info and info[0].strip().lower() == "income":
                main_ids.discard(mid)
                break

    # sort by total activity (spend + income) descending
    def _activity_value(mid):
        return (abs(spends_by_main.get(mid, 0)) + abs(incomes_by_main.get(mid, 0)))
    ordered = sorted(list(main_ids), key=_activity_value, reverse=True)

    # if including income, ensure Income appears first
    if income:
        income_mid = None
        for mid, info in main_cats.items():
            if info and info[0].strip().lower() == "income":
                income_mid = mid
                break
        if income_mid and income_mid in ordered:
            ordered.remove(income_mid)
            ordered.insert(0, income_mid)

    # build plotting arrays (values in R, positive magnitudes for right panel)
    labels = []
    actuals_spend_abs = []
    budget_spend_abs = []
    actuals_income_abs = []
    budget_income_abs = []
    variance_vals = []

    default_main = ["Uncategorised", "#CCCCCC", "#000000"]

    for mid in ordered:
        name = (main_cats.get(mid) or default_main)[0]
        labels.append(name)

        sp_c = spends_by_main.get(mid, 0)      # cents (negative or 0)
        in_c = incomes_by_main.get(mid, 0)     # cents (positive or 0)
        bud_c = budgets_by_main.get(mid, 0)    # cents (may be negative for spend budgets or positive for income)
        is_income_category = (name.strip().lower() == "income")

        if is_income_category:
            b_income = (bud_c or 0) / 100.0
            a_income = (in_c or 0) / 100.0
            # variance (income) = actual - budget (negative => shortfall)
            var = round(a_income - b_income, 2)
            # store positive magnitudes for right panel
            budget_income_abs.append(abs(b_income))
            actuals_income_abs.append(abs(a_income))
            budget_spend_abs.append(0.0)
            actuals_spend_abs.append(0.0)
        else:
            # spend budgets may be stored negative; use positive magnitudes for right panel
            b_spend = abs((bud_c or 0) / 100.0)
            a_spend = abs((sp_c or 0) / 100.0)
            # variance (spend) = budget - actual (negative => over budget)
            # To match left panel colouring: green if under (positive), red if over (negative)
            var = round((b_spend) - (a_spend), 2)
            budget_spend_abs.append(b_spend)
            actuals_spend_abs.append(a_spend)
            budget_income_abs.append(0.0)
            actuals_income_abs.append(0.0)

        variance_vals.append(var)

    # Colors:
    budget_spend_color = "#2b8cff"   # blue
    actual_spend_color = "#FF8D33"   # orange
    budget_income_color = "#8A2BE2"  # purple
    actual_income_color = "#2ecc71"  # green
    variance_colors = [("#2ecc71" if v > 0 else "#e53935") for v in variance_vals]

    # Traces:
    # Left panel: variance only (centered at 0)
    variance_traces = [{
        "type": "bar",
        "name": "Variance (Under/Over)",
        "orientation": "h",
        "y": labels,
        "x": variance_vals,
        "marker": {"color": variance_colors, "line": {"width": 1, "color": "#111111"}},
        "xaxis": "x",
        "hovertemplate": "<b>%{y}</b><br>Variance: R%{x:,.2f}<extra></extra>"
    }]

    # Right panel: budget vs actual (positive magnitudes)
    right_traces = [
        {
            "type": "bar",
            "name": "Allocated Budget (Spend)",
            "orientation": "h",
            "y": labels,
            "x": budget_spend_abs,
            "marker": {"color": budget_spend_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "spend_bud",
            "xaxis": "x2",
            "hovertemplate": "<b>%{y}</b><br>Budget (Spend): R%{x:,.2f}<extra></extra>"
        },
        {
            "type": "bar",
            "name": "Actual Spending",
            "orientation": "h",
            "y": labels,
            "x": actuals_spend_abs,
            "marker": {"color": actual_spend_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "spend_act",
            "xaxis": "x2",
            "hovertemplate": "<b>%{y}</b><br>Actual Spend: R%{x:,.2f}<extra></extra>"
        }
    ]

    if income:
        right_traces += [
            {
                "type": "bar",
                "name": "Allocated Budget (Income)",
                "orientation": "h",
                "y": labels,
                "x": budget_income_abs,
                "marker": {"color": budget_income_color, "line": {"width": 1, "color": "#111111"}},
                "offsetgroup": "income_bud",
                "xaxis": "x2",
                "hovertemplate": "<b>%{y}</b><br>Budget (Income): R%{x:,.2f}<extra></extra>"
            },
            {
                "type": "bar",
                "name": "Actual Income",
                "orientation": "h",
                "y": labels,
                "x": actuals_income_abs,
                "marker": {"color": actual_income_color, "line": {"width": 1, "color": "#111111"}},
                "offsetgroup": "income_act",
                "xaxis": "x2",
                "hovertemplate": "<b>%{y}</b><br>Actual Income: R%{x:,.2f}<extra></extra>"
            }
        ]

    traces = variance_traces + right_traces

    # Axis ranges
    # variance symmetric around zero
    if variance_vals:
        vmin = min(variance_vals)
        vmax = max(variance_vals)
        m = max(abs(vmin), abs(vmax), 1)
        variance_range = [-m * 1.10, m * 1.10]
    else:
        variance_range = [-1, 1]

    # right axis max from whichever series are present
    right_vals = budget_spend_abs + actuals_spend_abs
    if income:
        right_vals += budget_income_abs + actuals_income_abs
    right_max = max(right_vals) if right_vals else 1
    right_range = [0, max(1, right_max * 1.10)]

    # Layout to match screenshot style
    layout = {
        "height": height,
        "barmode": "group",
        "bargap": 0.18,
        "bargroupgap": 0.10,
        # separate title from plot
        "margin": {"l": 220, "r": 40, "t": 72, "b": 120},
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.32,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": "#ffffff", "size": 12}
        },
        # left axis: variance
        "xaxis": {
            "type": "linear",
            "domain": [0.0, 0.46],
            "range": variance_range,
            "title": "",
            "tickprefix": "R",
            "tickformat": ",.0f",
            "showgrid": True,
            "fixedrange": True,
            "tickfont": {"color": "#ffffff", "size": 11},
            "zeroline": True,
            "zerolinecolor": "#888888",
            "zerolinewidth": 1
        },
        # right axis: positive magnitudes
        "xaxis2": {
            "type": "linear",
            "domain": [0.54, 1.0],
            "range": right_range,
            "title": "",
            "tickprefix": "R",
            "tickformat": ",.0f",
            "showgrid": True,
            "fixedrange": True,
            "tickfont": {"color": "#ffffff", "size": 11}
        },
        # shared y categories
        "yaxis": {
            "automargin": True,
            "categoryorder": "array",
            "categoryarray": labels,
            "tickfont": {"color": "#ffffff", "size": 12},
            "domain": [0, 1]
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "title": {
            "text": f"Budget vs Actual Analysis<br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            "x": 0.5,
            "xanchor": "center",
            "y": 0.98,
            "yanchor": "top",
            "font": {"color": "#ffffff", "size": 14}
        }
    }

    return _make_plot(traces, layout, height=height, interactive=False)


# ============================================================
# PUBLIC: Burn Rate Plot
# ============================================================

def _row_get(obj, key, default=None):
    # dict
    if isinstance(obj, dict):
        return obj.get(key, default)
    # Anvil row (attribute access)
    try:
        return getattr(obj, key)
    except Exception:
        pass
    # tuple/list support: allow common field positions: (date, amount, category)
    if isinstance(obj, (tuple, list)):
        index_map = {"date": 0, "amount": 1, "category": 2}
        idx = index_map.get(key)
        if idx is not None and idx < len(obj):
            return obj[idx]
    return default

def _is_date_in_range(d, start, end):
    return isinstance(d, date) and start <= d <= end

def burnrate_plot(start: date, end: date, *, height: int = 420) -> Plot:
    """
    Burn Rate graph for Anvil:
    - Bars: daily inflow (green pastel) and outflow (orange pastel)
    - Line: total accounts balance (green above zero, red below zero)
    - Single left axis for all monetary values
    Data pulled from app ledgers for integrity:
    - Accounts daily balances computed from transactions.
    - Income/Expense grouped by day/week/month depending on range.
    """
    # 1) Collect transactions and accounts from Global
    txns = getattr(Global, "TRANSACTIONS", []) or []
    accounts = getattr(Global, "ACCOUNTS", []) or []
    cats = getattr(Global, "CATEGORIES", {}) or {}
    main_cats = getattr(Global, "MAIN_CATS", {}) or {}

    # detect transfer main category id if available
    transfer_mid = None
    for mid, info in (main_cats or {}).items():
        name = str(info[0] if isinstance(info, (list, tuple)) else info).strip().lower()
        if name in ("transfers", "transfer"):
            transfer_mid = mid
            break

    def txn_main_id(tx):
        cat_key = _row_get(tx, "category")
        cat_info = cats.get(cat_key) or {}
        if isinstance(cat_info, dict):
            return cat_info.get("belongs_to")
        # cat_info might be tuple/list: (name, belongs_to, ...)
        if isinstance(cat_info, (tuple, list)) and len(cat_info) >= 2:
            return cat_info[1]
        return None

    # Date span and aggregation mode
    days = list(_daterange(start, end))
    span_days = (end - start).days + 1
    if span_days <= 60:
        agg_mode = "daily"
    elif span_days <= 183:
        agg_mode = "weekly"
    else:
        agg_mode = "monthly"

    # 2) Build daily net flows (income positive, expense negative) from transactions
    # Exclude transfers (if app has a dedicated main category for transfers)
    transfer_mid = None
    for mid, info in (main_cats or {}).items():
        if isinstance(info, (list, tuple)) and str(info[0]).strip().lower() in ("transfers", "transfer"):
            transfer_mid = mid
            break

    def txn_main_id(t):
        cat_key = t.get("category")
        return (cats.get(cat_key) or {}).get("belongs_to")

    # per-day cents
    daily_inc_c = {d: 0 for d in days}
    daily_exp_c = {d: 0 for d in days}
    for t in txns:
        d = t.get("date")
        if not (isinstance(d, date) and start <= d <= end):
            continue
        # Skip transfers
        if transfer_mid and txn_main_id(t) == transfer_mid:
            continue
        amt_c = int(t.get("amount") or 0)
        if amt_c > 0:
            daily_inc_c[d] = daily_inc_c.get(d, 0) + amt_c
        elif amt_c < 0:
            daily_exp_c[d] = daily_exp_c.get(d, 0) + amt_c  # negative

    # 3) Build daily total balance from accounts (if balances not stored, approximate via net flows)
    # Try account balances series if available
    have_account_series = False
    daily_total_bal_c = {d: 0 for d in days}
    if accounts:
        # If accounts carry balance history, sum per day
        # Expected structure: account["balances_cents"] aligned with days, else fallback
        for acc in accounts:
            acc_days = acc.get("days")
            acc_series = acc.get("balances_cents")
            if isinstance(acc_days, list) and isinstance(acc_series, list) and len(acc_days) == len(acc_series):
                have_account_series = True
                for d, bal in zip(acc_days, acc_series):
                    if isinstance(d, date) and start <= d <= end:
                        daily_total_bal_c[d] = daily_total_bal_c.get(d, 0) + int(bal)
        # If no per-day balances, fall back to cumulative net flows
    if not have_account_series:
        # Use cumulative of (income + expense) starting at 0
        running = 0
        for d in days:
            running += daily_inc_c.get(d, 0) + daily_exp_c.get(d, 0)
            daily_total_bal_c[d] = running

    # 4) Aggregate per chosen granularity
    x_points = []
    income_r = []
    expense_r = []
    burnline_r = []

    if agg_mode == "daily":
        running = 0
        for d in days:
            inc_c = daily_inc_c.get(d, 0)
            exp_c = daily_exp_c.get(d, 0)
            running = daily_total_bal_c.get(d, running)
            x_points.append(d)
            income_r.append(abs(inc_c) / 100.0)
            expense_r.append(abs(exp_c) / 100.0)
            burnline_r.append(running / 100.0)
        tickformat = "%d %b"
        tickvals = None
        ticktext = None
        tickmode = "auto"

    elif agg_mode == "weekly":
        from collections import defaultdict
        buckets = defaultdict(lambda: {"inc": 0, "exp": 0, "last_day": None})
        # Sum by ISO week; line uses last day’s balance
        for d in days:
            iso = d.isocalendar()
            key = (iso.year, iso.week)
            b = buckets[key]
            b["inc"] += daily_inc_c.get(d, 0)
            b["exp"] += daily_exp_c.get(d, 0)
            b["last_day"] = d
        keys = sorted(buckets.keys())
        for k in keys:
            b = buckets[k]
            x_points.append(b["last_day"])
            income_r.append(abs(b["inc"]) / 100.0)
            expense_r.append(abs(b["exp"]) / 100.0)
            burnline_r.append(daily_total_bal_c.get(b["last_day"], 0) / 100.0)

        # ticks every ~3 weeks with custom labels "wk48 16 Nov"
        step = max(1, len(x_points) // 8)
        tickvals = [x_points[i] for i in range(0, len(x_points), step)]
        ticktext = [f"wk{tv.isocalendar().week} {tv.strftime('%d %b')}" for tv in tickvals]
        tickformat = None
        tickmode = "array"

    else:  # monthly
        from collections import defaultdict
        buckets = defaultdict(lambda: {"inc": 0, "exp": 0, "month_end": None})
        def month_key(d: date): return (d.year, d.month)
        def month_end(d: date):
            if d.month == 12:
                return date(d.year, 12, 31)
            first_next = date(d.year, d.month + 1, 1)
            return first_next - timedelta(days=1)

        for d in days:
            key = month_key(d)
            b = buckets[key]
            b["inc"] += daily_inc_c.get(d, 0)
            b["exp"] += daily_exp_c.get(d, 0)
            b["month_end"] = month_end(d)

        keys = sorted(buckets.keys())
        for k in keys:
            b = buckets[k]
            m_end = b["month_end"]
            x_points.append(m_end)
            income_r.append(abs(b["inc"]) / 100.0)
            expense_r.append(abs(b["exp"]) / 100.0)
            burnline_r.append(daily_total_bal_c.get(m_end, 0) / 100.0)

        tickformat = "%b %Y"
        tickvals = [x_points[i] for i in range(0, len(x_points), max(1, len(x_points) // 6))]
        ticktext = None
        tickmode = "auto"

    # 5) Build traces with app style
    traces = [
        go.Bar(
            name="Expenses",
            x=x_points, y=expense_r,
            marker=dict(color="#FFB97A", line=dict(width=0)),
            hovertemplate="<b>Expense</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
        ),
        go.Bar(
            name="Income",
            x=x_points, y=income_r,
            marker=dict(color="#9BE7A1", line=dict(width=0)),
            hovertemplate="<b>Income</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
        ),
        go.Scatter(
            name="Total Balance (≥ 0)",
            x=x_points, y=[v if v >= 0 else None for v in burnline_r],
            mode="lines",
            line=dict(color="#2ecc71", width=2),
            hovertemplate="<b>Total Balance</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=True
        ),
        go.Scatter(
            name="Total Balance (< 0)",
            x=x_points, y=[v if v < 0 else None for v in burnline_r],
            mode="lines",
            line=dict(color="#e53935", width=2),
            hovertemplate="<b>Total Balance</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=True
        )
    ]

    # 6) Unified left axis range
    y_min = min(0, min(burnline_r) if burnline_r else 0)
    y_max = max(
        (max(expense_r) if expense_r else 0),
        (max(income_r) if income_r else 0),
        (max(burnline_r) if burnline_r else 0)
    )
    pad = max(1.0, (y_max - y_min) * 0.12)
    unified_range = [y_min - pad, y_max + pad]

    layout = dict(
        height=height,
        margin=dict(l=70, r=70, t=64, b=80),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.28,
            xanchor="center", x=0.5,
            font=dict(color="#ffffff", size=11)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        xaxis=dict(
            type="date",
            showgrid=True, gridcolor="#334", fixedrange=True,
            tickfont=dict(color="#ffffff", size=11),
            tickformat=tickformat,
            tickvals=tickvals,
            ticktext=ticktext,
            tickmode=tickmode
        ),
        yaxis=dict(
            title=dict(text="R (Daily Flow and Total Balance)", font=dict(color="#ffffff", size=12)),
            showgrid=True, gridcolor="#334", fixedrange=True,
            tickprefix="R", tickformat=",.0f",
            range=unified_range,
            tickfont=dict(color="#ffffff", size=11)
        ),
        title=dict(
            text=f"Burn Rate: Daily Flow vs Total Balance<br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            x=0.5, xanchor="center", y=0.98, yanchor="top",
            font=dict(color="#ffffff", size=14)
        )
    )

    return _make_plot(traces, layout, height=height, interactive=False)


