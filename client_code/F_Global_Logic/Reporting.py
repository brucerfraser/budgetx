from datetime import date, timedelta

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
            "titlefont": {"color": "#ffffff"}
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
      "text": f"Spend by Category<br><span style='font-size:12px;color:#666'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
      "x": 0.5,
      "xanchor": "center",
      "yanchor": "top",
      "font": {"size": 14, "color": "#222222"}
    }
  }

  return _make_plot(traces, layout, height=height, interactive=False)


# ============================================================
# PUBLIC: Category Variance (Graphic #2)
# ============================================================

def category_variance_plot(start: date, end: date, *, height: int = 360, income: bool = False) -> Plot:
    """
    Horizontal grouped bar chart showing Budget vs Actual and Variance per main-category.
    - Budgets come from BUDGET.all_budgets (list of dicts with keys: belongs_to (sub-cat id),
      period (date), budget_amount (int cents)). We sum budgets for months in the selected range.
    - Actuals: incomes (amt>0) and spends (amt<0) are aggregated separately.
    - Variance = budget - actual (positive -> under budget => green; negative -> over budget => red)
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

    # If caller requests to exclude income rows, drop the Income main_id early
    if not income:
        for mid, info in main_cats.items():
            if info and info[0].strip().lower() == "income":
                main_ids.discard(mid)
                break

    # sort by total activity (spend + income) descending
    def _activity_value(mid):
        return (spends_by_main.get(mid, 0) + incomes_by_main.get(mid, 0))
    ordered = sorted(list(main_ids), key=_activity_value, reverse=True)

    # ensure Income appears at top if present and we're including income
    if income:
        income_mid = None
        for mid, info in main_cats.items():
            if info and info[0].strip().lower() == "income":
                income_mid = mid
                break
        if income_mid and income_mid in ordered:
            ordered.remove(income_mid)
            ordered.insert(0, income_mid)

    # build plotting arrays (values in R)
    labels = []
    actuals_spend = []
    budget_spend = []
    actuals_income = []
    budget_income = []
    variance_vals = []

    default_main = ["Uncategorised", "#CCCCCC", "#000000"]

    for mid in ordered:
        name = (main_cats.get(mid) or default_main)[0]
        labels.append(name)

        sp_c = spends_by_main.get(mid, 0)  # cents (negative or 0)
        in_c = incomes_by_main.get(mid, 0)  # cents (positive or 0)
        bud_c = budgets_by_main.get(mid, 0)  # cents (may be negative for spend budgets or positive for income)

        # classify budgets: if main category is Income, treat budgets as income budgets
        is_income_category = (name.strip().lower() == "income")

        if is_income_category:
            # budgets/incomes are positive numbers for income
            b_income = (bud_c or 0) / 100.0
            a_income = (in_c or 0) / 100.0
            # variance = actual - budget (negative => shortfall)
            var = round(a_income - b_income, 2)
            # spending fields zeroed
            b_spend = 0.0
            a_spend = 0.0
        else:
            # spend budgets may be stored negative; normalise to signed spend values
            b_spend = (bud_c or 0) / 100.0
            a_spend = (sp_c or 0) / 100.0  # sp_c is negative total of txn amounts
            # variance = actual - budget (negative => over budget)
            var = round(a_spend - b_spend, 2)
            b_income = 0.0
            a_income = 0.0

        # store values for plotting/hover
        actuals_spend.append(a_spend)            # negative for plotting left
        budget_spend.append(b_spend)            # may be negative for spend budgets
        actuals_income.append(a_income)         # positive
        budget_income.append(b_income)          # positive
        variance_vals.append(var)

    # Colors as requested:
    # - budget spending: blue
    # - actual spending: orange
    # - budget income: purple
    # - actual income: green
    # - variance: green if positive, red if negative
    budget_spend_color = "#2b8cff"   # blue
    actual_spend_color = "#FF8D33"   # orange
    budget_income_color = "#8A2BE2"  # purple
    actual_income_color = "#2ecc71"  # green

    # negative variance => red (over/short), positive => green
    variance_colors = [("#2ecc71" if v > 0 else "#e53935") for v in variance_vals]

    # prepare plotting values: ensure spend budgets and actuals are negative for left-side plotting,
    # while hover/customdata carries positive magnitudes for human-friendly display.
    actuals_spend_plot = [-abs(v) for v in actuals_spend]
    actuals_spend_hover = [abs(v) for v in actuals_spend]
    budget_spend_plot = [-abs(v) for v in budget_spend]
    budget_spend_hover = [abs(v) for v in budget_spend]

    # build traces with explicit colours and offsetgroups so bars don't visually merge
    traces = [
        {
            "type": "bar",
            "name": "Allocated Budget (Spend)",
            "orientation": "h",
            "y": labels,
            "x": budget_spend_plot,
            "customdata": budget_spend_hover,
            "marker": {"color": budget_spend_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "spend",
            "hovertemplate": "<b>%{y}</b><br>Budget (Spend): R%{customdata:,.2f}<extra></extra>"
        },
        {
            "type": "bar",
            "name": "Actual Spending",
            "orientation": "h",
            "y": labels,
            "x": actuals_spend_plot,
            "customdata": actuals_spend_hover,
            "marker": {"color": actual_spend_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "spend",
            "hovertemplate": "<b>%{y}</b><br>Actual Spend: R%{customdata:,.2f}<extra></extra>"
        }
    ]

    # income traces (positive -> right)
    traces += [
        {
            "type": "bar",
            "name": "Allocated Budget (Income)",
            "orientation": "h",
            "y": labels,
            "x": budget_income,
            "marker": {"color": budget_income_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "income",
            "hovertemplate": "<b>%{y}</b><br>Budget (Income): R%{x:,.2f}<extra></extra>"
        },
        {
            "type": "bar",
            "name": "Actual Income",
            "orientation": "h",
            "y": labels,
            "x": actuals_income,
            "marker": {"color": actual_income_color, "line": {"width": 1, "color": "#111111"}},
            "offsetgroup": "income",
            "hovertemplate": "<b>%{y}</b><br>Actual Income: R%{x:,.2f}<extra></extra>"
        }
    ]

    # variance trace (kept last)
    traces.append({
        "type": "bar",
        "name": "Variance (Budget − Actual)",
        "orientation": "h",
        "y": labels,
        "x": variance_vals,
        "marker": {"color": variance_colors, "line": {"width": 1, "color": "#111111"}},
        "offsetgroup": "variance",
        "hovertemplate": "<b>%{y}</b><br>Variance: R%{x:,.2f}<extra></extra>"
    })

    layout = {
        "height": height,
        # grouped mode with small gaps; increased bottom margin already set
        "barmode": "group",
        "bargap": 0.18,
        "bargroupgap": 0.08,
        "margin": {"l": 220, "r": 40, "t": 40, "b": 110},
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.18,
            "xanchor": "center",
            "x": 0.5,
            "font": {"color": "#ffffff", "size": 12}
        },
        "xaxis": {
            "title": "",
            "tickprefix": "R",
            "tickformat": ",.0f",
            "showgrid": True,
            "fixedrange": True,
            "tickfont": {"color": "#ffffff", "size": 11}
        },
        "yaxis": {
            "automargin": True,
            "categoryorder": "array",
            "categoryarray": labels,
            "tickfont": {"color": "#ffffff", "size": 12}
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "title": {
            "text": f"Budget vs Actual Analysis<br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"color": "#ffffff", "size": 14}
        }
    }

    return _make_plot(traces, layout, height=height, interactive=False)

