import random
from datetime import date, timedelta
import argparse
import os

import plotly.graph_objects as go

# ---------- helpers ----------
def _first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)

def _daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)

def _save_figure(fig: go.Figure, name: str, outdir: str = "test_output"):
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"{name}.html")
    # dark page background + light text; keep Plotly JS from CDN
    html = fig.to_html(include_plotlyjs="cdn", full_html=True)
    dark_css = """
    <style>
      body { background-color: #0f1217; color: #e0e0e0; margin: 0; }
      .plotly-container { background-color: transparent !important; }
    </style>
    """
    # inject CSS after <head> tag
    html = html.replace("</head>", f"{dark_css}\n</head>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote: {path}")

# ---------- random data generators ----------
def gen_random_categories(n=5):
    cats = []
    for i in range(n):
        name = f"Category {i+1}"
        # random spend totals in cents (negative in ledger, but we’ll show as positive magnitudes)
        spend_cents = -random.randint(20_000, 200_000)  # -R200 to -R2000 (in cents)
        # optional budgets, also negative for spend
        budget_cents = -random.randint(25_000, 220_000)
        cats.append({
            "name": name,
            "spend_cents": spend_cents,
            "budget_cents": budget_cents
        })
    # optionally include Income category
    income_budget = random.randint(50_000, 300_000)
    income_actual = random.randint(40_000, 320_000)
    cats.append({
        "name": "Income",
        "spend_cents": 0,
        "budget_cents": income_budget,
        "income_cents": income_actual
    })
    return cats

def gen_random_accounts(n=2, start=None, end=None):
    if start is None or end is None:
        today = date.today()
        start = _first_of_month(today) - timedelta(days=30)
        end = today
    days = list(_daterange(start, end))
    accounts = []
    for i in range(n):
        acc_name = f"Account {i+1}"
        # generate a random walk balance in cents
        balance = 0
        series = []
        for _ in days:
            delta = random.randint(-50_00, 80_00)  # -R50 to +R80 (cents)
            balance += delta
            series.append(balance)
        accounts.append({
            "name": acc_name,
            "days": days,
            "balances_cents": series
        })
    return accounts

# ---------- graphs ----------
def accounts_overview_graph(start: date, end: date, height: int = 320, dashboard: bool = False):
    accounts = gen_random_accounts(2, start, end)
    days = list(_daterange(start, end))

    # aggregate totals in R
    totals_r = [0.0] * len(days)
    for acc in accounts:
        balances_r = [v / 100.0 for v in acc["balances_cents"]]
        totals_r = [t + b for t, b in zip(totals_r, balances_r)]

    # area fills for totals (pos/neg)
    y_pos = [v if v > 0 else 0 for v in totals_r]
    y_neg = [v if v < 0 else 0 for v in totals_r]

    traces = [
        go.Scatter(
            name="Total (positive)", x=days, y=y_pos, mode="lines",
            line=dict(width=0, color="rgba(76,175,80,0.0)"),
            fill="tozeroy", fillcolor="rgba(76,175,80,0.18)",
            hovertemplate="<b>Total</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=False
        ),
        go.Scatter(
            name="Total (negative)", x=days, y=y_neg, mode="lines",
            line=dict(width=0, color="rgba(229,57,53,0.0)"),
            fill="tozeroy", fillcolor="rgba(229,57,53,0.18)",
            hovertemplate="<b>Total</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=False
        ),
    ]

    # account lines
    palette = ["#33D4FF", "#8A2BE2", "#FF8D33", "#2ecc71"]
    for idx, acc in enumerate(accounts):
        traces.append(
            go.Scatter(
                name=f"{acc['name']}",
                x=days,
                y=[v/100.0 for v in acc["balances_cents"]],
                mode="lines",
                line=dict(width=2, color=palette[idx % len(palette)]),
                hovertemplate="<b>%{fullData.name}</b><br>%{x|%d %b %Y}<br>Balance: R%{y:,.2f}<extra></extra>"
            )
        )

    layout = dict(
        height=height,
        margin=dict(l=72, r=10, t=40, b=160),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.40, xanchor="center", x=0.5,
            font=dict(color="#ffffff", size=11), traceorder="normal"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            type="date",
            showgrid=False, fixedrange=True,
            tickfont=dict(color="#ffffff", size=11),
        ),
        yaxis=dict(
            showgrid=True, fixedrange=True,
            tickprefix="R", tickformat=",.0f",
            automargin=True,
            tickfont=dict(color="#ffffff", size=11)
        ),
        title=dict(
            text=f"<b>Accounts Overview</b><br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            x=0.5, xanchor="center",
            font=dict(color="#ffffff", size=14)
        )
    )

    if dashboard:
        layout["height"] = max(160, int(height * 0.6))
        layout["margin"] = dict(l=56, r=8, t=20, b=90)
        layout["showlegend"] = False
        layout.pop("legend", None)
        layout["xaxis"].update(tickformat="%d %b", tickfont=dict(color="#ffffff", size=9))
        layout["yaxis"].update(tickformat=".2s", tickprefix="R", tickfont=dict(color="#ffffff", size=10))
        layout["title"]["font"]["size"] = 12

    fig = go.Figure(data=traces, layout=layout)
    return fig

def category_pie_graph(start: date, end: date, height: int = 320):
    cats = gen_random_categories(5)
    labels = [c["name"] for c in cats if c["name"].lower() != "income"]
    values_r = [abs(c["spend_cents"]) / 100.0 for c in cats if c["name"].lower() != "income"]

    fig = go.Figure(
        data=[go.Pie(labels=labels, values=values_r, hole=0.45, textinfo="percent",
                     hovertemplate="<b>%{label}</b><br>R%{value:,.2f}<br>%{percent}<extra></extra>")],
        layout=dict(
            height=height,
            margin=dict(l=10, r=80, t=40, b=40),
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(bgcolor="rgba(255,255,255,0.95)"),
            title=dict(
                text=f"<b>Spend by Category</b><br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
                x=0.5, xanchor="center", yanchor="top",
                font=dict(size=14, color="#ffffff")
            )
        )
    )
    return fig

def category_variance_graph(start: date, end: date, height: int = 360, include_income: bool = False):
    cats = gen_random_categories(5)

    labels = []
    variance_vals = []
    budget_spend_abs = []
    actuals_spend_abs = []
    budget_income_abs = []
    actuals_income_abs = []

    for c in cats:
        name = c["name"]
        labels.append(name)
        if name.lower() == "income":
            b_income = (c.get("budget_cents", 0)) / 100.0
            a_income = (c.get("income_cents", 0)) / 100.0
            var = round(a_income - b_income, 2)
            budget_income_abs.append(abs(b_income) if include_income else 0.0)
            actuals_income_abs.append(abs(a_income) if include_income else 0.0)
            budget_spend_abs.append(0.0)
            actuals_spend_abs.append(0.0)
        else:
            b_spend = abs(c["budget_cents"]) / 100.0
            a_spend = abs(c["spend_cents"]) / 100.0
            var = round(b_spend - a_spend, 2)
            budget_spend_abs.append(b_spend)
            actuals_spend_abs.append(a_spend)
            budget_income_abs.append(0.0)
            actuals_income_abs.append(0.0)
        variance_vals.append(var)

    variance_colors = [("#2ecc71" if v > 0 else "#e53935") for v in variance_vals]

    # left: variance
    left = [
        go.Bar(
            name="Variance (Under/Over)",
            orientation="h",
            y=labels, x=variance_vals,
            marker=dict(color=variance_colors, line=dict(width=1, color="#111111")),
            hovertemplate="<b>%{y}</b><br>Variance: R%{x:,.2f}<extra></extra>",
            xaxis="x", offsetgroup="var"
        )
    ]
    # right: positive magnitudes (spend and optional income)
    right = [
        go.Bar(
            name="Allocated Budget (Spend)", orientation="h",
            y=labels, x=budget_spend_abs,
            marker=dict(color="#2b8cff", line=dict(width=1, color="#111111")),
            hovertemplate="<b>%{y}</b><br>Budget (Spend): R%{x:,.2f}<extra></extra>",
            xaxis="x2", offsetgroup="sp_bud"
        ),
        go.Bar(
            name="Actual Spending", orientation="h",
            y=labels, x=actuals_spend_abs,
            marker=dict(color="#FF8D33", line=dict(width=1, color="#111111")),
            hovertemplate="<b>%{y}</b><br>Actual Spend: R%{x:,.2f}<extra></extra>",
            xaxis="x2", offsetgroup="sp_act"
        )
    ]
    if include_income:
        right += [
            go.Bar(
                name="Allocated Budget (Income)", orientation="h",
                y=labels, x=budget_income_abs,
                marker=dict(color="#8A2BE2", line=dict(width=1, color="#111111")),
                hovertemplate="<b>%{y}</b><br>Budget (Income): R%{x:,.2f}<extra></extra>",
                xaxis="x2", offsetgroup="inc_bud"
            ),
            go.Bar(
                name="Actual Income", orientation="h",
                y=labels, x=actuals_income_abs,
                marker=dict(color="#2ecc71", line=dict(width=1, color="#111111")),
                hovertemplate="<b>%{y}</b><br>Actual Income: R%{x:,.2f}<extra></extra>",
                xaxis="x2", offsetgroup="inc_act"
            )
        ]

    traces = left + right

    # axis ranges
    if variance_vals:
        m = max(abs(min(variance_vals)), abs(max(variance_vals)), 1)
        variance_range = [-m * 1.10, m * 1.10]
    else:
        variance_range = [-1, 1]

    right_vals = budget_spend_abs + actuals_spend_abs
    if include_income:
        right_vals += budget_income_abs + actuals_income_abs
    rmax = max(right_vals) if right_vals else 1
    right_range = [0, max(1, rmax * 1.10)]

    layout = dict(
        height=height,
        barmode="group",
        bargap=0.18,
        bargroupgap=0.10,
        margin=dict(l=220, r=40, t=72, b=120),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.32,
            xanchor="center", x=0.5,
            font=dict(color="#ffffff", size=12)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            type="linear", domain=[0.0, 0.46],
            range=variance_range, title="",
            tickprefix="R", tickformat=",.0f",
            showgrid=True, fixedrange=True,
            tickfont=dict(color="#ffffff", size=11),
            zeroline=True, zerolinecolor="#888888", zerolinewidth=1
        ),
        xaxis2=dict(
            type="linear", domain=[0.54, 1.0],
            range=right_range, title="",
            tickprefix="R", tickformat=",.0f",
            showgrid=True, fixedrange=True,
            tickfont=dict(color="#ffffff", size=11)
        ),
        yaxis=dict(
            automargin=True,
            categoryorder="array",
            categoryarray=labels,
            tickfont=dict(color="#ffffff", size=12),
            domain=[0, 1]
        ),
        title=dict(
            text=f"Budget vs Actual Analysis<br><span style='font-size:12px;color:#dddddd'>{start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}</span>",
            x=0.5, xanchor="center", y=0.98, yanchor="top",
            font=dict(color="#ffffff", size=14)
        )
    )
    fig = go.Figure(data=traces, layout=layout)
    return fig

def burnrate_graph(start: date, end: date, height: int = 420):
    days = list(_daterange(start, end))
    span_days = (end - start).days + 1

    # choose aggregation granularity
    # - <= 60 days: daily
    # - > 60 days and <= ~180 days: weekly (ISO weeks)
    # - > ~180 days: monthly (calendar months)
    if span_days <= 60:
        agg_mode = "daily"
    elif span_days <= 183:  # ~6 months
        agg_mode = "weekly"
    else:
        agg_mode = "monthly"

    # synthesize raw daily income/expense in cents and cumulative account balance
    daily_income_c = []
    daily_expense_c = []
    balance = 0
    for _ in days:
        expense_c = -random.randint(0, 120_00)   # -R0 to -R120
        income_c = random.randint(0, 150_00)     # R0 to R150
        daily_income_c.append(income_c)
        daily_expense_c.append(expense_c)

    # aggregate by chosen granularity
    x_points = []
    income_r = []
    expense_r = []
    burnline_r = []

    if agg_mode == "daily":
        balance = 0
        for d, inc_c, exp_c in zip(days, daily_income_c, daily_expense_c):
            balance += inc_c + exp_c
            x_points.append(d)
            income_r.append(abs(inc_c) / 100.0)
            expense_r.append(abs(exp_c) / 100.0)
            burnline_r.append(balance / 100.0)
        tickformat = "%d %b"
        tickvals = None
    elif agg_mode == "weekly":
        # group by ISO year-week
        from collections import defaultdict
        buckets = defaultdict(lambda: {"inc": 0, "exp": 0, "last_day": None, "week": None})
        for d, inc_c, exp_c in zip(days, daily_income_c, daily_expense_c):
            iso = d.isocalendar()  # (year, week, weekday)
            key = (iso.year, iso.week)
            b = buckets[key]
            b["inc"] += inc_c
            b["exp"] += exp_c
            b["last_day"] = d  # keep last day for x marker
            b["week"] = iso.week
        # sort by year-week
        keys = sorted(buckets.keys())
        balance = 0
        for k in keys:
            b = buckets[k]
            balance += b["inc"] + b["exp"]
            x_points.append(b["last_day"])
            income_r.append(abs(b["inc"]) / 100.0)
            expense_r.append(abs(b["exp"]) / 100.0)
            burnline_r.append(balance / 100.0)
        # ticks every ~3 weeks with custom labels "wk48 16 Nov"
        step = max(1, len(x_points) // 8)  # 2–4 ticks depending on range
        tickvals = [x_points[i] for i in range(0, len(x_points), step)]
        # map tickvals to their week numbers and dates
        ticktext = []
        for tv in tickvals:
            iso = tv.isocalendar()
            ticktext.append(f"wk{iso.week} {tv.strftime('%d %b')}")
        tickformat = None  # using custom ticktext for weekly
    else:  # monthly
        from collections import defaultdict
        buckets = defaultdict(lambda: {"inc": 0, "exp": 0, "month_end": None})
        def month_key(d: date): return (d.year, d.month)
        def month_end(d: date):
            # last day of month
            if d.month == 12:
                return date(d.year, 12, 31)
            first_next = date(d.year, d.month + 1, 1)
            return first_next - timedelta(days=1)

        for d, inc_c, exp_c in zip(days, daily_income_c, daily_expense_c):
            key = month_key(d)
            b = buckets[key]
            b["inc"] += inc_c
            b["exp"] += exp_c
            b["month_end"] = month_end(d)

        keys = sorted(buckets.keys())
        balance = 0
        for k in keys:
            b = buckets[k]
            balance += b["inc"] + b["exp"]
            x_points.append(b["month_end"])
            income_r.append(abs(b["inc"]) / 100.0)
            expense_r.append(abs(b["exp"]) / 100.0)
            burnline_r.append(balance / 100.0)
        tickformat = "%b %Y"
        # ticks every ~3 months
        tickvals = [x_points[i] for i in range(0, len(x_points), max(1, len(x_points) // 6))]

    traces = [
        go.Bar(
            name="Expenses", x=x_points, y=expense_r,
            marker=dict(color="#FFB97A", line=dict(width=0)),  # pastel orange
            hovertemplate="<b>Expense</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
        ),
        go.Bar(
            name="Income", x=x_points, y=income_r,
            marker=dict(color="#9BE7A1", line=dict(width=0)),  # pastel green
            hovertemplate="<b>Income</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
        ),
        # Total Balance line: green above zero, red below zero (two traces with masking)
        go.Scatter(
            name="Total Balance (≥ 0)", x=x_points,
            y=[v if v >= 0 else None for v in burnline_r],
            mode="lines",
            line=dict(color="#2ecc71", width=2),
            hovertemplate="<b>Total Balance</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=True
        ),
        go.Scatter(
            name="Total Balance (< 0)", x=x_points,
            y=[v if v < 0 else None for v in burnline_r],
            mode="lines",
            line=dict(color="#e53935", width=2),
            hovertemplate="<b>Total Balance</b><br>%{x|%d %b %Y}<br>R%{y:,.2f}<extra></extra>",
            showlegend=True
        )
    ]

    # unify left axis range
    y_min = min(0, min(burnline_r) if burnline_r else 0)
    y_max = max((max(expense_r) if expense_r else 0),
                (max(income_r) if income_r else 0),
                (max(burnline_r) if burnline_r else 0))
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
            # if weekly, we provide ticktext; otherwise fall back to tickformat
            tickformat=tickformat,
            tickvals=tickvals,
            ticktext=(ticktext if 'ticktext' in locals() else None),
            tickmode=("array" if 'ticktext' in locals() else "auto")
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
    fig = go.Figure(data=traces, layout=layout)
    return fig

# ---------- CLI triggers ----------
def main():
    parser = argparse.ArgumentParser(description="Generate test graphs for Reporting")
    # support BOTH: --graph option and positional graph argument
    parser.add_argument("--graph", dest="graph_opt",
                        choices=["accounts", "accounts-dashboard", "pie", "variance", "variance-income", "burnrate"],
                        help="Which graph to generate (optional flag)")
    parser.add_argument("graph_pos", nargs="?",
                        choices=["accounts", "accounts-dashboard", "pie", "variance", "variance-income", "burnrate"],
                        help="Which graph to generate (positional)")
    parser.add_argument("--out", default="test_output", help="Output directory for HTML files")
    args = parser.parse_args()

    graph = args.graph_pos or args.graph_opt or "accounts"

    today = date.today()
    start = _first_of_month(today) - timedelta(days=130)
    end = today

    if graph == "accounts":
        fig = accounts_overview_graph(start, end, height=500, dashboard=False)
        _save_figure(fig, "accounts_overview", args.out)
    elif graph == "accounts-dashboard":
        fig = accounts_overview_graph(start, end, height=220, dashboard=True)
        _save_figure(fig, "accounts_overview_dashboard", args.out)
    elif graph == "pie":
        fig = category_pie_graph(start, end, height=500)
        _save_figure(fig, "category_pie", args.out)
    elif graph == "variance":
        fig = category_variance_graph(start, end, height=360, include_income=False)
        _save_figure(fig, "category_variance", args.out)
    elif graph == "variance-income":
        fig = category_variance_graph(start, end, height=360, include_income=True)
        _save_figure(fig, "category_variance_income", args.out)
    elif graph == "burnrate":
        fig = burnrate_graph(start, end, height=420)
        _save_figure(fig, "burnrate", args.out)

if __name__ == "__main__":
    main()